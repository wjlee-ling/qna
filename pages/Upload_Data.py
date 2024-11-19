from chains.example_selector import CustomExampleSelector, example_prompt
from vectorstore.pinecone import HybridPineconeVectorStore, get_or_create_pinecone_index
from vectorstore.sparse import BM25Encoder, KiwiTokenizer
from langchain_core.prompts.few_shot import FewShotPromptTemplate

import os
import re
import pandas as pd
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from langchain_openai import OpenAIEmbeddings

load_dotenv()

import streamlit as st
from streamlit import session_state as sst

st.title("csv 업로드 & Pinecone 업데이트")
sst.csv = st.sidebar.file_uploader("upload a csv file")

INDEX_NAME = st.sidebar.text_input("Pinecone 인덱스 이름", value="casper")
NAMESPACE = st.sidebar.text_input("Pinecone 인덱스 내 Namespace 이름", value="pre_1018")
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

    vs = HybridPineconeVectorStore(
        sst.pc_index,
        sst.embeddings,
        sparse_encoder=bm25,
        namespace=NAMESPACE,
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
    )
    return vs


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


def contains_korean(text):
    if isinstance(text, str):
        # Regex pattern to match Korean characters
        korean_pattern = re.compile(
            r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF\uA960-\uA97F\uD7B0-\uD7FF]+"
        )
        return bool(korean_pattern.search(text))
    return False


# def extract_qb(url):
#     if isinstance(url, str):
#         try:
#             parsed_url = urlparse(url)
#             query_params = parse_qs(parsed_url.query)
#             qb_values = query_params.get("qb", None)
#             if qb_values:
#                 # parse_qs returns a list for each key
#                 return qb_values[0]
#             else:
#                 print(f"qb parameter not found in URL: {url}")
#                 return None
#         except Exception as e:
#             print(f"Error parsing URL '{url}': {e}")
#             return None
#     return None


# def replace_korean_with_qb(id_text, qb):
#     if isinstance(id_text, str) and qb:
#         # Regex pattern to match Korean characters
#         korean_pattern = re.compile(
#             r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF\uA960-\uA97F\uD7B0-\uD7FF]+"
#         )
#         # Replace the first occurrence of Korean characters with qb
#         return korean_pattern.sub(qb, id_text, count=1)
#     return id_text


# def check_non_ascii_from_id_column(df):
#     mask_korean_id = df["id"].apply(contains_korean)
#     if sum(mask_korean_id) > 0:
#         st.warning(
#             "id를 위한 column에 한글이 포함되어 있습니다. Pincecone의 id는 ascii 만 지원하므로 자동으로 id내 한글 문자를 url의 일부로 치환합니다."
#         )
#         df.loc[mask_korean_id, "qb_extracted"] = df.loc[mask_korean_id, "url"].apply(
#             extract_qb
#         )
#         df.loc[mask_korean_id, "id"] = df.loc[mask_korean_id].apply(
#             lambda row: replace_korean_with_qb(row["id"], row["qb_extracted"]), axis=1
#         )
#         st.info(
#             f"id의 한글 부분을 다음과 같이 바꿨습니다.\n{df['qb_extracted'].unique()}"
#         )
#     return df


if sst.csv:
    sst.df = get_data(sst.csv)
    with st.spinner("Pinecone에 연결하는 중"):
        sst.vs = init()
        st.info(sst.vs.get_pinecone_index(INDEX_NAME).describe_index_stats())

    with st.expander("DataFrame 분석", expanded=True):
        st.write("columns")
        st.info(sst.df.columns)
        st.write("DataFrame shape")
        st.info(f"{sst.df.shape[0]}행")

    if "id" in sst.df.columns and sum(sst.df["id"].apply(contains_korean)):
        st.warning(
            "id를 위한 column에 한글이 포함되어 있습니다. Pincecone의 id는 ascii 만 지원하므로 자동으로 id내 한글 문자를 알파벳으로 바꿔 다시 업로드해주세요. 알파벳으로 바꿀 시 'id' 칼럼만 바뀌도록 주의하세요."
        )

    if sst.vs and st.button(
        f"Pinecone 인덱스: '{INDEX_NAME}' -- 네임스페이스: '{NAMESPACE}'에 Upsert"
    ):
        with st.spinner("Pinecone에 upsert 중"):
            upsert_from_dataframe_to_pinecone(csv_path=sst.csv)
        st.success("Pinecone에 upsert 완료")
        st.info(sst.vs.get_pinecone_index(INDEX_NAME).describe_index_stats())

    # ids = sst.df["id"].tolist()
    # ids_index = sst.pc_index.list(namespace=NAMESPACE)
    # ids_total = []
    # for _ids in ids_index:
    #     ids_total.extend(_ids)

    # st.write(len(ids_total))

    # non = []
    # for _id in ids:
    #     print(_id)
    #     if _id not in ids_total:
    #         non.append(id)

    # st.write(non)
    # st.write(len(non))

    # examples = sst.vs.similarity_search_with_score(
    #     query="지금 주문하면 언제 출고되는 건가요?",
    #     k=4,
    #     namespace=NAMESPACE,
    # )
    # examples = [ex[0].metadata for ex in examples if ex[1] > 0.6]
    # st.success(examples)
