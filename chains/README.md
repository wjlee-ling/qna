# LangChain 기반 QnA 구축 chain

## 1. [자동 분류 chain](classification.py)

- LangChain의 `EnumOutputParser`와 LangChain/OpenAI의 `structured output`을 이용하여 정해진 schema대로 데이터 자동 분류
- LangChain의 `RetryOutputParser` 이용하여 파싱 오류 대처

## 2. [자동 파싱/라벨링 chain](example_selector.py)

- (Pinecone 벡터스토어에 저장된) 기구축된 데이터를 기반으로 새로운 데이터를 파싱/라벨링
- LangChain의 `example selector`를 사용하여 동적인 few-shot prompting 가능
  - 기본적으로 dense embedding 기반 유사도 검색하여 현재 input과 유사한 기구축 레코드 검색 후 예시로 사용
  - sparse encoder 추가 시 hybrid 검색 가능
- LangChain/OpenAI의 `structured output`을 사용하여 정해진 schema의 output 추출
