from chains.example_selector import (
    CustomExampleSelector,
    example_prompt,
    get_example_selector_chain_with_structured_output,
)
from langchain_core.prompts.few_shot import FewShotPromptTemplate

import os
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

import streamlit as st
from streamlit import session_state as sst

st.title("Example Selector 기반 라벨링")
sst.csv = st.sidebar.file_uploader("라벨링할 csv 파일 업로드")

INDEX_NAME = st.sidebar.text_input("Pinecone 인덱스 이름", value="casper")
NAMESPACE = st.sidebar.text_input("Pinecone 인덱스 내 Namespace 이름", value="pre_1018")
USER_DICT_PATH = "./user_dict_1018.txt"
BM25_ENCODER_PATH = "bm25_통합 Q&A_상품탐색_유형 분류 중간결과_1018_납품.json"


# @st.cache_resource
def init(index_name=INDEX_NAME, user_dict_path=USER_DICT_PATH):
    sst.example_selector = CustomExampleSelector.from_vectorstore(
        index_name=index_name,
        namespace=NAMESPACE,
        openai_model="text-embedding-3-small",
        tokenizer_dict_path=user_dict_path,
        sparse_encoder_path=BM25_ENCODER_PATH,
    )
    sst.llm = ChatOpenAI(
        model="gpt-4o-mini", temperature=0.0, api_key=os.getenv("OPENAI_API_KEY")
    )


@st.cache_data
def get_data(csv):
    df = pd.read_csv(csv)
    return df


if sst.csv or True:
    # sst.df = get_data(sst.csv)
    with st.spinner("Pinecone에 연결 중"):
        init()

    # with st.expander("DataFrame 분석", expanded=True):
    #     st.write("columns")
    #     st.info(sst.df.columns)
    #     st.write("DataFrame shape")
    #     st.info(f"{sst.df.shape[0]}행")

    example_selector_prompt = FewShotPromptTemplate(
        example_selector=sst.example_selector,
        example_prompt=example_prompt,
        suffix="input:\n{input}\noutput:\n",
        prefix="Your task is to, given a new query as input, classify its intent and label.\nYou will be given previous parsed results to which you can refer to parse the new query. If you are uncertain with the intent, leave it an empty string.",
        input_variables=["input"],
    )

    example_selector_chain = get_example_selector_chain_with_structured_output(
        example_selector_prompt, sst.llm
    )

    inputs = [
        {"input": "할부는 몇 개월까지 가능한가요?"},
        {"input": "전액 현대캐피탈로 할부하려면 캐피탈에 미리 처리해 놓아야 하나요?"},
    ]

    output = example_selector_chain.batch(inputs)
    st.info(output)
