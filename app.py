from vectorstore.pinecone import PineconeVectorStore, get_or_create_pinecone_index
from vectorstore.sparse import BM25Encoder, KiwiTokenizer

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

import streamlit as st
from streamlit import session_state as sst


INDEX_NAME = "hyundai-test"
NAMESPACE = "test"
USER_DICT_PATH = "user_dict_1018.txt"


@st.cache_resource
def init(index_name, user_dict_path):
    sst.pc_index = get_or_create_pinecone_index(index_name)
    sst.embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
    )
    kiwi = KiwiTokenizer(user_dict_path)
    bm25 = BM25Encoder()
    bm25.replace_with_Kiwi_tokenizer(kiwi)

    sst.vs = PineconeVectorStore(
        sst.pc_index,
        sst.embeddings,
        sparse_encoder=bm25,
        namespace=NAMESPACE,
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
    )


init(index_name=INDEX_NAME, user_dict_path=USER_DICT_PATH)
st.title("현대차 Casper AI 크루 작업 도구")
query = st.text_input(label="작업할 문장을 입력해 주세요.")
if query:
    resp = sst.vs.similarity_search(query=query)
    for item in resp:
        st.write(item)
