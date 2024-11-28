# from chains.prompts import RAG_TEMPLATE
from typing import List

from langchain import hub
from langchain_core.output_parsers import StrOutputParser

prompt = hub.pull("casper-gpt")


def create_basic_chain(llm):

    return prompt | llm | StrOutputParser()
