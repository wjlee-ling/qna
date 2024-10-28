import os
import pandas as pd
from dotenv import load_dotenv

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


def search_regex(regex, df, columns: list[str], labels: list[str], intents: list[str]):
    combined_condition = pd.Series(False, index=df.index)

    target_df = df.copy()
    if labels:
        target_df = target_df[df["final_label"].isin(labels)]
    if intents:
        target_df = target_df[df["intent"].isin(intents)]

    for col in columns:
        if col in df.columns:
            combined_condition |= (
                df[col].astype(str).str.contains(regex, regex=True, na=False)
            )
        else:
            print(f"Warning: Column '{col}' not found in DataFrame.")

    return target_df[combined_condition][
        ["Q", "final_label", "intent", "regex"]
    ].sort_values(by=["final_label", "intent"])


@st.cache_resource
def get_unique_values_per_label(df):
    filtered_df = (
        df[df["final_label"].isin(labels_pre)]
        .groupby(["final_label"])["intent"]
        .unique()
        .reset_index()
    )

    return filtered_df


def reset():
    if "edited_df" in sst:
        del sst.edited_df


st.title("QnA 데이터 검색 & 분석")

sst.csv = st.sidebar.file_uploader("upload a csv file")

if sst.csv:
    df, df_counts = get_data()

    with st.expander(f"전체 데이터 분포: {sst.csv.name}", expanded=False):

        label_df = get_unique_values_per_label(df)
        st.data_editor(
            label_df,
            column_config={
                "intent": st.column_config.Column(
                    "intent",
                    width="large",
                    required=True,
                )
            },
        )

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
else:
    st.warning("csv 파일 업로드 해 주세요.")
    st.stop()


with st.form("form"):
    regex = st.text_input(value="", label="검색어")
    column = st.multiselect(
        label="검색범위 (복수선택 가능)",
        options=["Q", "final_question"],
        default="Q",
    )
    labels = st.multiselect(
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
        sst.edited_df = search_regex(regex, df, column, labels, intents)

    updated_df = st.data_editor(
        sst.edited_df,
        hide_index=True,
        use_container_width=True,
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
