from chains.rag import create_rag_chain
from vectorstore.pinecone import HybridPineconeVectorStore, get_or_create_pinecone_index
from vectorstore.sparse import BM25Encoder, KiwiTokenizer
from langchain_core.prompts.few_shot import FewShotPromptTemplate

import os
import re
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import streamlit as st
from streamlit import session_state as sst

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_PROJECT"] = "hyundai"

st.title("RAG 기반 답변 생성")
sst.csv = st.sidebar.file_uploader("upload a csv file")

INDEX_NAME = st.sidebar.text_input("Pinecone 인덱스 이름", value="casper")
NAMESPACE = st.sidebar.text_input("Pinecone 인덱스 내 Namespace 이름", value="rag")
USER_DICT_PATH = "./user_dict_1018.txt"
BM25_ENCODER_PATH = "bm25_통합 Q&A_상품탐색_유형 분류 중간결과_1018_납품.json"


# @st.cache_resource
def init(index_name=INDEX_NAME, user_dict_path=USER_DICT_PATH):
    sst.pc_index = get_or_create_pinecone_index(index_name)
    sst.embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
    )
    kiwi = KiwiTokenizer(user_dict_path)
    bm25 = BM25Encoder()
    bm25.load(BM25_ENCODER_PATH)
    bm25.replace_with_Kiwi_tokenizer(kiwi)

    sst.vs = HybridPineconeVectorStore(
        sst.pc_index,
        sst.embeddings,
        sparse_encoder=bm25,
        namespace=NAMESPACE,
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
    )

    sst.llm = ChatOpenAI(model="gpt-4o", temperature=0.0)


@st.cache_data
def get_data(csv):
    df = pd.read_csv(csv)
    return df


def upsert_from_dataframe_to_pinecone(
    csv_path, text_col: str = None, id_col: str = None, metadata_cols: list[str] = None
):
    text_col = text_col or "유사질의"
    id_col = id_col or "id"
    if metadata_cols is None:
        metadata_cols = [
            "date",
            "url",
            "title",
            "content",
            "ev",
            "intent",
            "대표질의",
            "final_label",
            "hyundai_label",
        ]

    if "vs" in sst:
        sst.vs.upsert_from_dataframe(
            csv_path=csv_path,
            text_col=text_col,
            id_col=id_col,
            metadata_cols=metadata_cols,
        )

    # def contains_korean(text):
    #     if isinstance(text, str):
    #         # Regex pattern to match Korean characters
    #         korean_pattern = re.compile(
    #             r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF\uA960-\uA97F\uD7B0-\uD7FF]+"
    #         )
    #         return bool(korean_pattern.search(text))
    #     return False

    # if sst.csv:
    #     sst.df = get_data(sst.csv)

    #     with st.spinner("Pinecone에 연결하는 중"):
    #         sst.vs = init()
    #         st.info(sst.vs.get_pinecone_index(INDEX_NAME).describe_index_stats())

    #     sst.rag_chain = create_rag_chain(
    #         llm=sst.llm, retriever=sst.vs.as_retriever(search_kwargs={"k": 4})
    #     )

    #     with st.expander("DataFrame 분석", expanded=True):
    #         st.write("columns")
    #         st.info(sst.df.columns)
    #         st.write("DataFrame shape")
    #         st.info(f"{sst.df.shape[0]}행")

    #     if "id" in sst.df.columns and sum(sst.df["id"].apply(contains_korean)):
    #         st.warning(
    #             "id를 위한 column에 한글이 포함되어 있습니다. Pincecone의 id는 ascii 만 지원하므로 자동으로 id내 한글 문자를 알파벳으로 바꿔 다시 업로드해주세요. 알파벳으로 바꿀 시 'id' 칼럼만 바뀌도록 주의하세요."
    #         )

    #     if sst.vs and st.button(
    #         f"Pinecone 인덱스: '{INDEX_NAME}' -- 네임스페이스: '{NAMESPACE}'에 Upsert"
    #     ):
    #         upsert_from_dataframe_to_pinecone(
    #             csv_path=sst.csv,
    #             text_col="text",
    #             metadata_cols=["url", "text"],
    #             id_col="id",
    #         )


with st.form("검색 및 답변 구축"):
    user_input = st.text_input("검색할 대표질의 또는 유사질의를 입력해주세요.")
    user_prefix = st.selectbox(
        label="검색 범위 지정", options=["None", "FAQ", "Options"]
    )

    submitted = st.form_submit_button("검색")
    if submitted:
        init()
        if "rag_chain" not in sst:
            sst.rag_chain = create_rag_chain(
                llm=sst.llm, retriever=sst.vs.as_retriever(search_kwargs={"k": 4})
            )

        output = sst.rag_chain.invoke({"input": user_input})

        answer = output["answer"].content
        docs = output["context"]
        if len(answer) > 3:
            st.success(answer)
        else:
            st.warning("검색 결과가 없습니다.")

        st.write("참고 자료")
        for i, doc in enumerate(docs):
            st.write(f"{i}번째 참고 자료 // id: {doc.id}")
            st.info(doc.page_content)

    # if sst.rag_chain and st.button("RAG 답변 생성"):
    #     sst.df_target = sst.df[
    #         (sst.df["유사질의"] != "") & (sst.df["hyundai_label"] == "구매절차")
    #     ][:100]
    #     st.dataframe(sst.df_target)
    #     st.info(f"타겟 행 수: {sst.df_target.shape[0]}")

    #     chunk_size = 100
    #     chunked_dfs = [
    #         sst.df_target.iloc[i : i + chunk_size]
    #         for i in range(0, len(sst.df_target), chunk_size)
    #     ]

    #     dfs = []
    #     with st.spinner("LLM 작업 중"):
    #         for chunk_df in chunked_dfs:
    #             inputs = [{"input": value} for value in chunk_df["유사질의"].tolist()]
    #             outputs = sst.rag_chain.batch(inputs)

    #             chunk_df["답변"] = [o["answer"] for o in outputs]
    #             chunk_df["답변_출처"] = [
    #                 o["sources"] if "sources" in o else "" for o in outputs
    #             ]
    #             dfs.append(chunk_df)

    #     total_df = pd.concat(dfs)

    #     st.download_button(
    #         label="RAG 답변 다운로드",
    #         file_name="rag 결과.csv",
    #         data=total_df.to_csv().encode("utf-8"),
    #     )
