from vectorstore.pinecone import PineconeVectorStore, get_or_create_pinecone_index
from vectorstore.sparse import BM25Encoder, KiwiTokenizer

import os
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

import streamlit as st
from streamlit import session_state as sst


INDEX_NAME = "hyundai"
NAMESPACE = "final_question_pt1"
USER_DICT_PATH = "user_dict_1018.txt"
BM25_ENCODER_PATH = "bm25_통합 Q&A_상품탐색_유형 분류 중간결과_1018_납품.json"
st.set_page_config(layout="wide")
cols = ["title", "content", "page_content", "label"]  # last_modified
labels_pre = [""]


# @st.cache_resource
def init(index_name, user_dict_path):
    sst.pc_index = get_or_create_pinecone_index(index_name)
    sst.embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
    )
    kiwi = KiwiTokenizer(user_dict_path)
    bm25 = BM25Encoder()
    bm25.load(BM25_ENCODER_PATH)
    bm25.replace_with_Kiwi_tokenizer(kiwi)

    sst.vs = PineconeVectorStore(
        sst.pc_index,
        sst.embeddings,
        sparse_encoder=bm25,
        namespace=NAMESPACE,
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
    )


def reset():
    if "edited_df" in sst:
        del sst.edited_df


init(index_name=INDEX_NAME, user_dict_path=USER_DICT_PATH)
st.title("현대차 Casper AI 크루 작업 도구")

top_k = st.number_input(label="검색 결과 갯수", min_value=10, max_value=20)
query = st.text_input(label="작업할 문장을 입력해 주세요.", on_change=reset)
if query:
    st.markdown("## 유사 데이터")

    sst.resp = sst.vs.similarity_search(query=query, k=top_k)

    texts = [doc.page_content for doc in sst.resp]
    labels = [doc.metadata["final_label"] for doc in sst.resp]

    df = pd.DataFrame({"question": texts, "label": labels})
    if "edited_df" not in sst:
        sst.edited_df = df.copy()

    updated_df = st.data_editor(
        sst.edited_df,
        hide_index=True,
        # disabled=("post_id"),
        # column_config={
        #     "widgets": st.column_config.Column(
        #         "Streamlit Widgets",
        #         width="medium",
        #         required=True,
        #     ),
        # },
    )

    if not updated_df.equals(sst.edited_df):
        sst.edited_df = updated_df

    ## 1
    # # Compare the original DataFrame (df) and the edited DataFrame (sst.edited_df)
    # comparison = df.compare(sst.edited_df)

    # # Identify positions where values are different
    # if not comparison.empty:
    #     st.write("Changed values:")
    #     st.write(comparison)
    # else:
    #     st.write("No changes detected.")

    ## 2
    # comparison = df != sst.edited_df
    # # Identify positions where values are different
    # changes = comparison.stack()[comparison.stack()]
    # changed_positions = changes.index.tolist()

    # st.write(changed_positions)

    ## TODO:
    # 'done': 1. 작업했음 -> 초록색 2. 작업 안함 -> 노란색
