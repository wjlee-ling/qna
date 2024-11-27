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


def contains_korean(text):
    if isinstance(text, str):
        # Regex pattern to match Korean characters
        korean_pattern = re.compile(
            r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF\uA960-\uA97F\uD7B0-\uD7FF]+"
        )
        return bool(korean_pattern.search(text))
    return False


if sst.logged_in and "vs" not in sst:
    with st.spinner("환경 설정 중"):
        init()

if sst.csv:
    sst.df = get_data(sst.csv)

    with st.spinner("Pinecone에 연결하는 중"):
        st.info(sst.vs.get_pinecone_index(INDEX_NAME).describe_index_stats())

    if "id" in sst.df.columns and sum(sst.df["id"].apply(contains_korean)):
        st.warning(
            "id를 위한 column에 한글이 포함되어 있습니다. Pincecone의 id는 ascii 만 지원하므로 자동으로 id내 한글 문자를 알파벳으로 바꿔 다시 업로드해주세요. 알파벳으로 바꿀 시 'id' 칼럼만 바뀌도록 주의하세요."
        )

    st.info(f"새로운 csv의 행의 갯수: {sst.df.shape[0]}")
    if sst.vs and st.button(
        f"Pinecone 인덱스: '{INDEX_NAME}' -- 네임스페이스: '{NAMESPACE}'에 Upsert"
    ):

        upsert_from_dataframe_to_pinecone(
            csv_path=sst.csv,
            text_col="text",
            metadata_cols=["url", "text"],
            id_col="id",
        )


if "logged_in" not in sst or not sst.logged_in:
    st.warning("로그인 해주세요.")
    st.stop()

with st.expander("작업 가이드라인", expanded=False):
    st.write(
        """\
## 크루 작업 가이드라인
모바일 어플에서 캐스퍼 & 캐스퍼 일렉트릭 관련 질의응답을 하는 챗봇의 답변을 만드는 작업입니다.

1. 작업도구 접속 후 로그인 뒤 RAG 창 클릭
2. [검수] 열이나 [특이사항] 열이 특이사항 (’삭제’ 또는 ‘보류’)이 없는지 확인. 있으면 넘어가기
3. 작업할 행의 [대표질의] 값을 복사해서 [검색할 대표질의 또는 유사질의를 입력해주세요] 칸에 입력 후 검색
4. GPT가 만든 1차 답변이 초록색 칸안에 생성됨. 같이 출력되는 [참고 자료]들을 확인하여 답변이 질문의 문맥과 일치하는지 확인하고, 반드시 있어야 하는 정보가 누락되어 있으면 보충하는 등 수정하여 작업시트의 [답변]열에 최종 답변 작성. 

4-1. 최종 답변은 최대 3문장까지 가능.

4-2. 최종 답변을 만들 때 근거가 된 내용이 [참고 자료]에 있었으면 해당 내용(파란색 칸) 부분만 복사하여 작업시트의 [출처]에 기입. 여러 참고자료를 참고하였으면 contrl+엔터로 구별하여 모두 기입

[출처]에 기입한 참고자료의 ‘id’ 도 모두 작업시트의 [출처id] 열에 기입. 

4-3. GPT가 만든 답변이 없거나 [참고 자료]들에 근거가 없는 경우도 있음. 이럴 경우 검색한 [대표질의] 대신 해당 [대표질의]의 [유사질의]를 이용하여 재검색 (3번째 과정). [대표질의]와 [유사질의]가 거의 유사한 경우 검색결과가 많이 다르지 않으니 [대표질의]에 없는 핵심 키워드 등이 있는  [유사질의]로 검색하는 것이 좋음

4-4. [참고 자료]를 이용하여 근거가 있는 최종 답변을  만들었어도, 현대자동차 직원들의 검수가 필요할 것 같은 질문/답변이면 작업시트의 [검수] 칸의 ‘현대차 2차 검수 필요’ 선택
4-5. [참고 자료]가 홈페이지 사용자 대상으로 쓰여진 자료일 수 있으므로, 홈페이지에 관련된 내용은 '캐스퍼 공식 홈페이지' 라는 말을 추가하는 등 모바일 어플에서 접속하는 사용자가 읽는 상황을 생각하여 답변 구축 필요
4-6. 그래도 답변을 만들기 어려우면 그냥 해당 행을 넘어가기

5. [참고 자료]를 이용하여 해당 대표질의/유사질의에 답이 되는 최종 답변을 만들었다면 해당 대표질의를 갖고 있는 행들의 [답변]에 복사 붙여넣기. 다만 [유사질의]와 문맥이 맞지 않는 경우 해당 [유사질의]가 있는 행은 답변을 채우지 않고 넘어가기.
6. 과정 (5)에서 새로 답변을 채운 모든 행들의 [최종작업일]을 수정. 
7. 과정 (5)에서 새로 답변을 채운 모든 행들의 질문/답변이 전기차/ev “특화” 질문/답변이라면 [ev] TRUE로 기입\
"""
    )

with st.form("검색 및 답변 구축"):
    user_input = st.text_input("검색할 대표질의 또는 유사질의를 입력해주세요.")
    user_prefix = st.selectbox(
        label="검색 범위 지정", options=["None", "FAQ", "Options"]
    )

    submitted = st.form_submit_button("검색")
    if submitted:

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
            try:
                st.write(f"{i}번째 참고 자료 // id: {doc.id} // url: {doc.url}")
            except:
                st.write(f"{i}번째 참고 자료 // id: {doc.id}")
            st.info(doc.page_content)
