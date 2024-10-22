from __future__ import annotations

import logging
import os
import time
import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeVar,
)

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langchain_core._api.deprecation import deprecated
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.utils.iter import batch_iterate
from langchain_core.vectorstores import VectorStore
from pinecone import Pinecone as PineconeClient  # type: ignore
from pinecone import ServerlessSpec

from langchain_pinecone._utilities import DistanceStrategy, maximal_marginal_relevance

if TYPE_CHECKING:
    from pinecone import Index

logger = logging.getLogger(__name__)

VST = TypeVar("VST", bound=VectorStore)

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")


def get_or_create_pinecone_index(index_name, dimension=1536, metric="dotproduct"):
    pc = PineconeClient(api_key=PINECONE_API_KEY)
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(
            f"🤖 Created a new Pinecone index w/ name: {index_name}, dimension: {dimension}, metric: {metric}"
        )
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)

    index = pc.Index(index_name)
    print(f"🤖 Index:\n{index.describe_index_stats()}")
    return index


class PineconeVectorStore(VectorStore):
    """Pinecone vector store integration.

    Setup:
        Install ``langchain-pinecone`` and set the environment variable ``PINECONE_API_KEY``.

        .. code-block:: bash

            pip install -qU langchain-pinecone
            export PINECONE_API_KEY = "your-pinecone-api-key"

    Key init args — indexing params:
        embedding: Embeddings
            Embedding function to use.

    Key init args — client params:
        index: Optional[Index]
            Index to use.


    # TODO: Replace with relevant init params.
    Instantiate:
        .. code-block:: python

            import time
            import os
            from pinecone import Pinecone, ServerlessSpec
            from langchain_pinecone import PineconeVectorStore
            from langchain_openai import OpenAIEmbeddings

            pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

            index_name = "langchain-test-index"  # change if desired

            existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

            if index_name not in existing_indexes:
                pc.create_index(
                    name=index_name,
                    dimension=1536,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
                while not pc.describe_index(index_name).status["ready"]:
                    time.sleep(1)

            index = pc.Index(index_name)
            vector_store = PineconeVectorStore(index=index, embedding=OpenAIEmbeddings())

    Add Documents:
        .. code-block:: python

            from langchain_core.documents import Document

            document_1 = Document(page_content="foo", metadata={"baz": "bar"})
            document_2 = Document(page_content="thud", metadata={"bar": "baz"})
            document_3 = Document(page_content="i will be deleted :(")

            documents = [document_1, document_2, document_3]
            ids = ["1", "2", "3"]
            vector_store.add_documents(documents=documents, ids=ids)

    Delete Documents:
        .. code-block:: python

            vector_store.delete(ids=["3"])

    Search:
        .. code-block:: python

            results = vector_store.similarity_search(query="thud",k=1)
            for doc in results:
                print(f"* {doc.page_content} [{doc.metadata}]")

        .. code-block:: python

            * thud [{'bar': 'baz'}]

    Search with filter:
        .. code-block:: python

            results = vector_store.similarity_search(query="thud",k=1,filter={"bar": "baz"})
            for doc in results:
                print(f"* {doc.page_content} [{doc.metadata}]")

        .. code-block:: python

            * thud [{'bar': 'baz'}]

    Search with score:
        .. code-block:: python

            results = vector_store.similarity_search_with_score(query="qux",k=1)
            for doc, score in results:
                print(f"* [SIM={score:3f}] {doc.page_content} [{doc.metadata}]")

        .. code-block:: python

            * [SIM=0.832268] foo [{'baz': 'bar'}]

    Async:
        .. code-block:: python

            # add documents
            # await vector_store.aadd_documents(documents=documents, ids=ids)

            # delete documents
            # await vector_store.adelete(ids=["3"])

            # search
            # results = vector_store.asimilarity_search(query="thud",k=1)

            # search with score
            results = await vector_store.asimilarity_search_with_score(query="qux",k=1)
            for doc,score in results:
                print(f"* [SIM={score:3f}] {doc.page_content} [{doc.metadata}]")

        .. code-block:: python

            * [SIM=0.832268] foo [{'baz': 'bar'}]

    Use as Retriever:
        .. code-block:: python

            retriever = vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={"k": 1, "fetch_k": 2, "lambda_mult": 0.5},
            )
            retriever.invoke("thud")

        .. code-block:: python

            [Document(metadata={'bar': 'baz'}, page_content='thud')]

    """  # noqa: E501

    def __init__(
        self,
        # setting default params to bypass having to pass in
        # the index and embedding objects - manually throw
        # exceptions if they are not passed in or set in environment
        # (keeping param for backwards compatibility)
        index: Optional[Any] = None,
        embedding: Optional[Embeddings] = None,
        sparse_encoder=None,
        text_key: Optional[str] = "text",
        namespace: Optional[str] = None,
        distance_strategy: Optional[DistanceStrategy] = DistanceStrategy.COSINE,
        *,
        pinecone_api_key: Optional[str] = None,
        index_name: Optional[str] = None,
    ):
        if embedding is None:
            raise ValueError("Embedding must be provided")
        self._embedding = embedding
        self.sparse_encoder = sparse_encoder
        if text_key is None:
            raise ValueError("Text key must be provided")
        self._text_key = text_key

        self._namespace = namespace
        self.distance_strategy = distance_strategy

        if index:
            # supports old way of initializing externally
            self._index = index
        else:
            # all internal initialization
            _pinecone_api_key = (
                pinecone_api_key or os.environ.get("PINECONE_API_KEY") or ""
            )
            if not _pinecone_api_key:
                raise ValueError(
                    "Pinecone API key must be provided in either `pinecone_api_key` "
                    "or `PINECONE_API_KEY` environment variable"
                )

            _index_name = index_name or os.environ.get("PINECONE_INDEX_NAME") or ""
            if not _index_name:
                raise ValueError(
                    "Pinecone index name must be provided in either `index_name` "
                    "or `PINECONE_INDEX_NAME` environment variable"
                )

            # needs
            client = PineconeClient(api_key=_pinecone_api_key, source_tag="langchain")
            self._index = client.Index(_index_name)

    @property
    def embeddings(self) -> Optional[Embeddings]:
        """Access the query embedding object if available."""
        return self._embedding

    def upsert_from_dataframe(
        self,
        csv_path: str,
        text_col: str,
        id_col: Optional[str] = None,
        metadata_cols: Optional[List[str]] = None,
        namespace: Optional[str] = None,
        batch_size: int = 32,
    ):
        """
        csv를 import 하여 정해진 column 이름대로 text/id/metadata 분리하여 upsert
        Args
            - text_col: column to embed
            - id_col: column of unique ids
            - metadata: column(s) of metadata. If not specified, use all the columns except for the `text_col` column.

        """
        original_df = pd.read_csv(csv_path, chunksize=300)
        for chunk_df in original_df:
            texts = chunk_df[text_col].to_list()
            ids = chunk_df[id_col].astype(str).to_list() if id_col else None
            metadatas = (
                chunk_df[metadata_cols].to_dict(orient="records")
                if metadata_cols
                else chunk_df.drop(columns=[text_col]).to_dict(orient="records")
            )

            self.add_texts(
                texts=texts,
                metadatas=metadatas,
                ids=ids,
                namespace=namespace,
                batch_size=batch_size,
            )

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        namespace: Optional[str] = None,
        batch_size: int = 32,
        embedding_chunk_size: int = 1000,
        *,
        async_req: bool = True,
        id_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> List[str]:
        """Run more texts through the embeddings and add to the vectorstore.

        Upsert optimization is done by chunking the embeddings and upserting them.
        This is done to avoid memory issues and optimize using HTTP based embeddings.
        For OpenAI embeddings, use pool_threads>4 when constructing the pinecone.Index,
        embedding_chunk_size>1000 and batch_size~64 for best performance.
        Args:
            texts: Iterable of strings to add to the vectorstore.
            metadatas: Optional list of metadatas associated with the texts.
            ids: Optional list of ids to associate with the texts.
            namespace: Optional pinecone namespace to add the texts to.
            batch_size: Batch size to use when adding the texts to the vectorstore.
            embedding_chunk_size: Chunk size to use when embedding the texts.
            async_req: Whether runs asynchronously.
            id_prefix: Optional string to use as an ID prefix when upserting vectors.

        Returns:
            List of ids from adding the texts into the vectorstore.

        """
        if namespace is None:
            namespace = self._namespace

        texts = list(texts)
        ids = ids or [str(uuid.uuid4()) for _ in texts]
        if id_prefix:
            ids = [
                id_prefix + "#" + id if id_prefix + "#" not in id else id for id in ids
            ]
        metadatas = metadatas or [{} for _ in texts]
        for metadata, text in zip(metadatas, texts):
            metadata[self._text_key] = text.strip()

        # For loops to avoid memory issues and optimize when using HTTP based embeddings
        # The first loop runs the embeddings, it benefits when using OpenAI embeddings
        # The second loops runs the pinecone upsert asynchronously.
        for i in range(0, len(texts), embedding_chunk_size):
            chunk_texts = texts[i : i + embedding_chunk_size]
            chunk_ids = ids[i : i + embedding_chunk_size]
            chunk_metadatas = metadatas[i : i + embedding_chunk_size]
            embeddings = self._embedding.embed_documents(chunk_texts)
            if self.sparse_encoder is None:  # dense only
                vector_tuples = zip(chunk_ids, embeddings, chunk_metadatas)
                if async_req:
                    # Runs the pinecone upsert asynchronously.
                    async_res = [
                        self._index.upsert(
                            vectors=batch_vector_tuples,
                            namespace=namespace,
                            async_req=async_req,
                            **kwargs,
                        )
                        for batch_vector_tuples in batch_iterate(
                            batch_size, vector_tuples
                        )
                    ]
                    [res.get() for res in async_res]
                else:
                    self._index.upsert(
                        vectors=vector_tuples,
                        namespace=namespace,
                        async_req=async_req,
                        **kwargs,
                    )
            else:
                # hybrid (dense+sparse)
                sparse_embeddings = self.sparse_encoder.encode_documents(chunk_texts)
                vectors = [
                    {
                        "id": _id,
                        "sparse_values": sparse,
                        "values": dense,
                        "metadata": metadata,
                    }
                    for _id, sparse, dense, metadata in zip(
                        chunk_ids, sparse_embeddings, embeddings, chunk_metadatas
                    )
                ]

                self._index.upsert(
                    vectors=vectors,
                    namespace=namespace,
                    async_req=False,
                    **kwargs,
                )

        return ids

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
        namespace: Optional[str] = None,
    ) -> List[Tuple[Document, float]]:
        """Return pinecone documents most similar to query, along with scores.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            filter: Dictionary of argument(s) to filter on metadata
            namespace: Namespace to search in. Default will search in '' namespace.

        Returns:
            List of Documents most similar to the query and score for each
        """
        return self.similarity_search_by_vector_with_score(
            self._embedding.embed_query(query), k=k, filter=filter, namespace=namespace
        )

    def similarity_search_by_vector_with_score(
        self,
        embedding: List[float],
        *,
        k: int = 4,
        filter: Optional[dict] = None,
        namespace: Optional[str] = None,
    ) -> List[Tuple[Document, float]]:
        """Return pinecone documents most similar to embedding, along with scores."""

        if namespace is None:
            namespace = self._namespace
        docs = []
        results = self._index.query(
            vector=embedding,
            top_k=k,
            include_metadata=True,
            namespace=namespace,
            filter=filter,
        )
        for res in results["matches"]:
            metadata = res["metadata"]
            id = res.get("id")
            if self._text_key in metadata:
                text = metadata.pop(self._text_key)
                score = res["score"]
                docs.append(
                    (Document(id=id, page_content=text, metadata=metadata), score)
                )
            else:
                logger.warning(
                    f"Found document with no `{self._text_key}` key. Skipping."
                )
        return docs

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
        namespace: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """Return pinecone documents most similar to query.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            filter: Dictionary of argument(s) to filter on metadata
            namespace: Namespace to search in. Default will search in '' namespace.

        Returns:
            List of Documents most similar to the query and score for each
        """
        docs_and_scores = self.similarity_search_with_score(
            query, k=k, filter=filter, namespace=namespace, **kwargs
        )
        return [doc for doc, _ in docs_and_scores]

    def _select_relevance_score_fn(self) -> Callable[[float], float]:
        """
        The 'correct' relevance function
        may differ depending on a few things, including:
        - the distance / similarity metric used by the VectorStore
        - the scale of your embeddings (OpenAI's are unit normed. Many others are not!)
        - embedding dimensionality
        - etc.
        """

        if self.distance_strategy == DistanceStrategy.COSINE:
            return self._cosine_relevance_score_fn
        elif self.distance_strategy == DistanceStrategy.MAX_INNER_PRODUCT:
            return self._max_inner_product_relevance_score_fn
        elif self.distance_strategy == DistanceStrategy.EUCLIDEAN_DISTANCE:
            return self._euclidean_relevance_score_fn
        else:
            raise ValueError(
                "Unknown distance strategy, must be cosine, max_inner_product "
                "(dot product), or euclidean"
            )

    @staticmethod
    def _cosine_relevance_score_fn(score: float) -> float:
        """Pinecone returns cosine similarity scores between [-1,1]"""
        return (score + 1) / 2

    def max_marginal_relevance_search_by_vector(
        self,
        embedding: List[float],
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filter: Optional[dict] = None,
        namespace: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """Return docs selected using the maximal marginal relevance.

        Maximal marginal relevance optimizes for similarity to query AND diversity
        among selected documents.

        Args:
            embedding: Embedding to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            fetch_k: Number of Documents to fetch to pass to MMR algorithm.
            lambda_mult: Number between 0 and 1 that determines the degree
                        of diversity among the results with 0 corresponding
                        to maximum diversity and 1 to minimum diversity.
                        Defaults to 0.5.
            filter: Dictionary of argument(s) to filter on metadata
            namespace: Namespace to search in. Default will search in '' namespace.

        Returns:
            List of Documents selected by maximal marginal relevance.
        """
        if namespace is None:
            namespace = self._namespace
        results = self._index.query(
            vector=[embedding],
            top_k=fetch_k,
            include_values=True,
            include_metadata=True,
            namespace=namespace,
            filter=filter,
        )
        mmr_selected = maximal_marginal_relevance(
            np.array([embedding], dtype=np.float32),
            [item["values"] for item in results["matches"]],
            k=k,
            lambda_mult=lambda_mult,
        )
        selected = [results["matches"][i]["metadata"] for i in mmr_selected]
        return [
            Document(page_content=metadata.pop((self._text_key)), metadata=metadata)
            for metadata in selected
        ]

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filter: Optional[dict] = None,
        namespace: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """Return docs selected using the maximal marginal relevance.

        Maximal marginal relevance optimizes for similarity to query AND diversity
        among selected documents.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            fetch_k: Number of Documents to fetch to pass to MMR algorithm.
            lambda_mult: Number between 0 and 1 that determines the degree
                        of diversity among the results with 0 corresponding
                        to maximum diversity and 1 to minimum diversity.
                        Defaults to 0.5.
            filter: Dictionary of argument(s) to filter on metadata
            namespace: Namespace to search in. Default will search in '' namespace.

        Returns:
            List of Documents selected by maximal marginal relevance.
        """
        embedding = self._embedding.embed_query(query)
        return self.max_marginal_relevance_search_by_vector(
            embedding, k, fetch_k, lambda_mult, filter, namespace
        )

    @classmethod
    def get_pinecone_index(
        cls,
        index_name: Optional[str],
        pool_threads: int = 4,
        *,
        pinecone_api_key: Optional[str] = None,
    ) -> Index:
        """Return a Pinecone Index instance.

        Args:
            index_name: Name of the index to use.
            pool_threads: Number of threads to use for index upsert.
            pinecone_api_key: The api_key of Pinecone.
        Returns:
            Pinecone Index instance."""
        _pinecone_api_key = pinecone_api_key or os.environ.get("PINECONE_API_KEY") or ""
        client = PineconeClient(
            api_key=_pinecone_api_key, pool_threads=pool_threads, source_tag="langchain"
        )
        indexes = client.list_indexes()
        index_names = [i.name for i in indexes.index_list["indexes"]]

        if index_name in index_names:
            index = client.Index(index_name)
        elif len(index_names) == 0:
            raise ValueError(
                "No active indexes found in your Pinecone project, "
                "are you sure you're using the right Pinecone API key and Environment? "
                "Please double check your Pinecone dashboard."
            )
        else:
            raise ValueError(
                f"Index '{index_name}' not found in your Pinecone project. "
                f"Did you mean one of the following indexes: {', '.join(index_names)}"
            )
        return index

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        batch_size: int = 32,
        text_key: str = "text",
        namespace: Optional[str] = None,
        index_name: Optional[str] = None,
        upsert_kwargs: Optional[dict] = None,
        pool_threads: int = 4,
        embeddings_chunk_size: int = 1000,
        async_req: bool = True,
        *,
        id_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> PineconeVectorStore:
        """Construct Pinecone wrapper from raw documents.

        This is a user-friendly interface that:
            1. Embeds documents.
            2. Adds the documents to a provided Pinecone index

        This is intended to be a quick way to get started.

        The `pool_threads` affects the speed of the upsert operations.

        Setup: set the `PINECONE_API_KEY` environment variable to your Pinecone API key.

        Example:
            .. code-block:: python

                from langchain_pinecone import PineconeVectorStore, PineconeEmbeddings

                embeddings = PineconeEmbeddings(model="multilingual-e5-large")

                index_name = "my-index"
                vectorstore = PineconeVectorStore.from_texts(
                    texts,
                    index_name=index_name,
                    embedding=embedding,
                    namespace=namespace,
                )
        """
        pinecone_index = cls.get_pinecone_index(index_name, pool_threads)
        pinecone = cls(pinecone_index, embedding, text_key, namespace, **kwargs)

        pinecone.add_texts(
            texts,
            metadatas=metadatas,
            ids=ids,
            namespace=namespace,
            batch_size=batch_size,
            embedding_chunk_size=embeddings_chunk_size,
            async_req=async_req,
            id_prefix=id_prefix,
            **(upsert_kwargs or {}),
        )
        return pinecone

    @classmethod
    def from_existing_index(
        cls,
        index_name: str,
        embedding: Embeddings,
        text_key: str = "text",
        namespace: Optional[str] = None,
        pool_threads: int = 4,
    ) -> PineconeVectorStore:
        """Load pinecone vectorstore from index name."""
        pinecone_index = cls.get_pinecone_index(index_name, pool_threads)
        return cls(pinecone_index, embedding, text_key, namespace)

    def delete(
        self,
        ids: Optional[List[str]] = None,
        delete_all: Optional[bool] = None,
        namespace: Optional[str] = None,
        filter: Optional[dict] = None,
        **kwargs: Any,
    ) -> None:
        """Delete by vector IDs or filter.
        Args:
            ids: List of ids to delete.
            delete_all: Whether delete all vectors in the index.
            filter: Dictionary of conditions to filter vectors to delete.
            namespace: Namespace to search in. Default will search in '' namespace.
        """

        if namespace is None:
            namespace = self._namespace

        if delete_all:
            self._index.delete(delete_all=True, namespace=namespace, **kwargs)
        elif ids is not None:
            chunk_size = 1000
            for i in range(0, len(ids), chunk_size):
                chunk = ids[i : i + chunk_size]
                self._index.delete(ids=chunk, namespace=namespace, **kwargs)
        elif filter is not None:
            self._index.delete(filter=filter, namespace=namespace, **kwargs)
        else:
            raise ValueError("Either ids, delete_all, or filter must be provided.")

        return None

    def update_metadata(
        self,
        ids: Optional[List[str]],
        new_data: Optional[List[Dict]],
        namespace: Optional[str] = None,
    ):
        for id, record in zip(ids, new_data):
            self._index.update(
                id=id,
                set_metadata=record,
                namespace=namespace,
            )

    def filter_by_metadata(
        self,
        filters: Dict,
        namespace: Optional[str] = None,
        top_k: int = 10,
    ):
        """
        For the valid syntax for `filters`, refer to [Pinecone Docs](https://docs.pinecone.io/guides/data/filter-with-metadata)
        """
        return self._index.query(
            namespace=namespace,
            filter=filters #{"genre": {"$eq": "documentary"}},
            top_k=top_k,
            include_metadata=True,  # Include metadata in the response.
        )


@deprecated(since="0.0.3", removal="0.3.0", alternative="PineconeVectorStore")
class Pinecone(PineconeVectorStore):
    """Deprecated. Use PineconeVectorStore instead."""

    pass
