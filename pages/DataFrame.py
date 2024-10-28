import os
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

import matplotlib.pyplot as plt
import streamlit as st
from streamlit import session_state as sst


cols = [
    "Q",
    "title",
    "content",
    "final_question",
    "final_label",
    "분류 수정",
    "cluster",
    "regex",
    "intent",
    "수정사항",
]  # last_modified

labels_pre = [
    "buying",
    "membership",
    "benefit",
    "tax_benefit",
    "promotion/event",
    "carmaster",
    "estimation",
    "info",
    "opinions_models",
    "opinions_trims",
    "test_driving",
]

st.set_page_config(layout="wide")


@st.cache_data
def get_data():
    df = pd.read_csv(
        "통합 Q&A_상품탐색_유형 분류 중간결과_1021_TEXTNET 사내용_1025.csv"
    )[cols]
    df = df[df["Q"].notna()]
    df["수정사항"].fillna("", inplace=True)
    df["final_label"] = df["final_label"].where(df["분류 수정"].isna(), df["분류 수정"])
    df = df[
        (~df["수정사항"].str.contains("구매이후"))
        & (~df["수정사항"].str.contains("삭제"))
        & (df["final_label"] != "구매이후")
    ]

    df_counts = (
        df.groupby(by=["final_label", "intent"])
        .count()
        .reset_index()[["final_label", "intent", "Q"]]
        .sort_values(by="Q", ascending=False)
    )
    return df, df_counts


def search_regex(regex, df, columns: list[str]):
    combined_condition = pd.Series(False, index=df.index)

    for col in columns:
        if col in df.columns:
            combined_condition |= (
                df[col].astype(str).str.contains(regex, regex=True, na=False)
            )
        else:
            print(f"Warning: Column '{col}' not found in DataFrame.")

    return df[combined_condition][["Q", "final_label", "intent", "regex"]].sort_values(
        by=["final_label", "intent"]
    )


def reset():
    if "edited_df" in sst:
        del sst.edited_df


st.title("QnA 데이터 검색 & 분석")

# top_k = st.number_input(label="검색 결과 갯수", min_value=10, max_value=20)

df, df_counts = get_data()
with st.expander("전체 데이터 분포", expanded=False):
    # plt.figure(figsize=(10, 6))
    # for label, group in df_counts.groupby("final_label"):
    #     plt.bar(group["intent"], group["Q"], label=f"final_label: {label}")

    # plt.legend(title="Label")
    # plt.xticks(rotation=45, ha="right")
    # plt.tight_layout()
    # st.pyplot(plt)
    st.data_editor(
        df_counts,
        column_config={
            "intent": st.column_config.Column(
                "intent",
                width="medium",
                required=True,
            ),
            "regex": st.column_config.Column(
                "regex",
                width="medium",
                required=True,
            ),
        },
    )

with st.form("form"):
    regex = st.text_input(value="", label="검색어")
    column = st.multiselect(
        label="검색범위 (복수선택 가능)",
        options=["Q", "final_question"],
        default="Q",
    )
    label = st.multiselect(
        label="분류 (복수선택 가능)",
        options=labels_pre,
    )
    intents = sorted([x for x in df["intent"].unique() if isinstance(x, str)])
    intents = st.multiselect(
        label="인텐트 (복수선택 가능)",
        options=intents,
    )

    submit = st.form_submit_button("검색", on_click=reset)


if submit:
    st.markdown("### 검색 결과")

    if "edited_df" not in sst:
        sst.edited_df = search_regex(regex, df, column)
        with st.expander(f"분포 분석", expanded=False):
            result = (
                df[df["final_label"].isin(intents)]
                .groupby(["final_label", "intent"])["regex"]
                .unique()
                .reset_index()
                .sort_values(by=["final_label", "intent", "regex"])
            )
            st.write(result)

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
