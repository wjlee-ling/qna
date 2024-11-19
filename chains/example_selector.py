from vectorstore.pinecone import get_or_create_pinecone_index, HybridPineconeVectorStore

import os

from dotenv import load_dotenv
from enum import Enum
from pydantic import BaseModel, Field
from langchain.output_parsers.enum import EnumOutputParser
from langchain_core.example_selectors.base import BaseExampleSelector
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict

load_dotenv()

typo_mapping = {
    "상품탐색_엔진/바디타입": "상품 탐색 _ 엔진 / 바디타입",
    "상품탐색_트림/옵션/옵션조합": "상품 탐색 _ 트림 / 옵션 / 옵션조합",
    "상품탐색_디자인": "상품 탐색 _ 디자인",
    "상품탐색_차종비교": "상품 탐색_차종비교",
    "상품탐색_라이프스타일": "상품탐색_라이프스타일",
}


class Label(str, Enum):
    buying = "구매절차"
    payment = "결제조합"
    aftermarket = "애프터마켓"
    tax_benefit = "세제혜택"
    test_driving = "시승"
    model = "상품 탐색 _ 엔진 / 바디타입"
    trim_option = "상품 탐색 _ 트림 / 옵션 / 옵션조합"
    design = "상품 탐색 _ 디자인"
    comparison = "상품 탐색_차종비교"
    lifestyle = "상품탐색_라이프스타일"
    etc = "기타"


class Parsed(BaseModel):
    intent: str = Field(
        description="the intent of the input query. Should be one of the intents of the examples."
    )
    label: Label = Field(description="the (classified) label of the input query.")


# "Your task is to, given a new query, (1) classify its intent and label and (2) generate its representative_query.\nYou will be given previous parsed results to which you can refer to parse the new query.",


class CustomExampleSelector(BaseExampleSelector):
    def __init__(self, vectorstore, namespace):
        self.vectorstore = vectorstore
        self.namespace = namespace
        self.examples = []

    def add_example(self, example):
        self.examples.append(example)

    def select_examples(
        self, input_variables: Dict, threshold: int = 0.6
    ) -> List[Dict]:
        input_query = input_variables["input"]

        examples = self.vectorstore.similarity_search_with_score(
            query=input_query,
            k=4,
            namespace=self.namespace,
        )
        for ex, score in examples:
            if score < threshold:
                continue

            record = ex.metadata
            parsed = Parsed(intent=record["intent"], label=record["hyundai_label"])
            self.examples.append({"input": ex.page_content, "output": str(parsed)})

        return self.examples

    @classmethod
    def from_vectorstore(
        cls,
        index_name: str,
        namespace: str = None,
        *,
        openai_model: str = None,
        tokenizer_dict_path: str = None,
        sparse_encoder_path: str = None,
    ):
        from vectorstore.pinecone import (
            HybridPineconeVectorStore,
            get_or_create_pinecone_index,
        )
        from vectorstore.sparse import BM25Encoder, KiwiTokenizer

        pc_index = get_or_create_pinecone_index(index_name)

        # dense
        embeddings = OpenAIEmbeddings(
            model=openai_model, api_key=os.getenv("OPENAI_API_KEY")
        )

        # sparse
        kiwi = KiwiTokenizer(user_dict_path=tokenizer_dict_path)
        bm25 = BM25Encoder()
        bm25.load(sparse_encoder_path)
        bm25.replace_with_Kiwi_tokenizer(kiwi)

        vs = HybridPineconeVectorStore(
            pc_index,
            embeddings,
            sparse_encoder=bm25,
            namespace=namespace,
            pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        )

        return CustomExampleSelector(
            vectorstore=vs,
            namespace=namespace,
        )


example_prompt = PromptTemplate.from_template("input:\n{input}\noutput:\n{output}")
example_selector_prefix = """\
Your task is to, given a new query as input and example(s), classify its **most likely** intent and label. \
You will be given previous parsed results to which you can refer in order to parse the new query. \
Specifically,
1. Find the most relevant or similar example(s) to the current input query.
2. The intent of the query should be the same as that of the most relevant or similar example query. Make sure not to use the label(s) of the example querie(s) as the intent of the current input query.
3. The label of the query should be the same as that of the most relevant or similar example query.
4. If no examples are given or given examples bear no resemblance or relevance to the current input query, label the intent of the current query as "" (empty string)."""

# example_selector_prompt = FewShotPromptTemplate(
#     example_selector=example_selector,
#     example_prompt=example_prompt,
#     suffix="input:\n{input}\noutput:\n",
#     prefix="Your task is to, given a new query as input, classify its **most likely** intent and label.\nYou will be given previous parsed results to which you can refer in order to parse the new query. AIf you are uncertain with the intent, leave it an empty string.",
#     input_variables=["input"],
# )


def get_example_selector_prompt(example_selector):
    example_selector_prompt = FewShotPromptTemplate(
        example_selector=example_selector,
        example_prompt=example_prompt,
        suffix="input:\n{input}\noutput:\n",
        prefix=example_selector_prefix,
        input_variables=["input"],
    )
    return example_selector_prompt


def get_example_selector_chain_with_structured_output(example_selector_prompt, llm):
    from langchain_core.runnables import RunnableLambda

    enum_parser = EnumOutputParser(enum=Label)

    def _parse(x) -> Dict:
        try:
            return {
                "intent": x.intent,
                "hyundai_label": enum_parser.invoke(x.label).value,
            }
        except:
            return {"intent": x.intent, "hyundai_label": "기타"}

    def wrapper_with_fallback(x) -> Dict:
        try:
            x = chain.invoke(x)
            return x
        except:
            return {
                "intent": "",
                "hyundai_label": "",
            }

    chain = (
        example_selector_prompt
        | llm.with_structured_output(Parsed)
        | RunnableLambda(_parse)
    )

    return RunnableLambda(wrapper_with_fallback)
