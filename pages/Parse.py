from chains.example_selector import (
    CustomExampleSelector,
    example_prompt,
    get_example_selector_prompt,
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


if sst.csv:
    sst.df = get_data(sst.csv)
    with st.spinner("Pinecone에 연결 중"):
        init()

    with st.expander("DataFrame 분석", expanded=True):
        st.write("columns")
        st.info(sst.df.columns)
        st.write("DataFrame shape")
        st.info(f"{sst.df.shape[0]}행")

    example_selector_prompt = get_example_selector_prompt(sst.example_selector)
    example_selector_chain = get_example_selector_chain_with_structured_output(
        example_selector_prompt, sst.llm
    )

    with st.form("설정"):
        text_col = st.selectbox(
            label="임베딩 및 분류할 column",
            options=sst.df.columns.tolist(),
            index=sst.df.columns.tolist().index("Q"),
        )
        submit = st.form_submit_button("라벨링 시작")

    if submit:
        chunk_size = 10
        chunked_dfs = [
            sst.df.iloc[i : i + chunk_size] for i in range(0, len(sst.df), chunk_size)
        ]
        dfs = []
        with st.spinner("LLM 작업 중"):
            for chunk_df in chunked_dfs:
                outputs = example_selector_chain.batch(chunk_df[text_col].tolist())
                chunk_df["hyundai_label"] = [o["hyundai_label"] for o in outputs]
                chunk_df["intent"] = [o["intent"] for o in outputs]
                dfs.append(chunk_df)

                # st.dataframe(chunk_df)
                # for output in outputs:
                #     st.info(output)

        total_df = pd.concat(dfs)
        if total_df.shape[0] > 0 and st.download_button(
            "작업된 csv 다운로드",
            total_df.to_csv().encode("utf-8"),
            file_name=f"{sst.csv.name}_라벨링.csv",
        ):
            st.info("다운로드 완료")
