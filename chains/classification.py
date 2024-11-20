from chains.prompts import PROMPT_PURCHASE_PHASE, PROMPT_CLASSIFY
from chains.schemas import ConsiderPurchaseIntent, PurchasePhase

from langchain.output_parsers import RetryOutputParser
from langchain.output_parsers.enum import EnumOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


enum_parser = EnumOutputParser(enum=PurchasePhase)
fallback_parser = RetryOutputParser.from_llm(
    parser=enum_parser, llm=ChatOpenAI(model="gpt-4o-mini", temperature=0)
)

prompt_purchase_phase = ChatPromptTemplate.from_template(PROMPT_PURCHASE_PHASE).partial(
    instructions=enum_parser.get_format_instructions()
)


def handle_parsing_error(x):
    try:
        parsed = enum_parser.parse(x.content)
        return parsed

    except:
        return PurchasePhase.in_or_after


classify_phase_chain = (
    prompt_purchase_phase
    | ChatOpenAI(model="gpt-4o-mini", temperature=0)
    | handle_parsing_error
)

prompt_classify_ConsiderPurchase = ChatPromptTemplate.from_template(PROMPT_CLASSIFY)

classify_consider_purchase_chain = prompt_classify_ConsiderPurchase | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(ConsiderPurchaseIntent)
