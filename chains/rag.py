from chains.prompts import RAG_TEMPLATE

from typing import List
from typing_extensions import Annotated, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough


# class AnswerWithSources(TypedDict):
#     """An answer to the question, with sources."""

#     answer: str
#     sources: Annotated[
#         List[str],
#         ...,
#         "List of sources used to answer the question",
#     ]


def _format_docs(docs):
    return "\n---\n".join(doc.page_content for doc in docs)


RAG_PROMPT = ChatPromptTemplate.from_template(RAG_TEMPLATE)


def create_rag_chain(llm, retriever):
    retrieve = RunnableLambda(lambda x: x["input"]) | retriever
    answer = (
        {
            "input": lambda x: x["input"],
            "context": lambda x: _format_docs(x["context"]),
        }
        | RAG_PROMPT
        | llm  # .with_structured_output(AnswerWithSources)
    )

    RAG_chain = RunnablePassthrough.assign(context=retrieve).assign(answer=answer)
    return RAG_chain
