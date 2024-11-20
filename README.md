# QnA Streamlit 작업툴

## 1. csv 업로드 & Pinecone 업데이트

- `pages/Upload_Data.py`
- Pinecone 벡터스토어에 hybrid 벡터 저장

1. sidebar에서 Pinecone에 upsert할 csv 파일 업로드
2. Pinecone 내 index 이름과 namespace 이름 지정
   - 현재 현대차 프로젝트 (챗봇팀 구글 계정으로 로그인 후 확인 가능)
     - index: `casper`
     - namespace: `pre_1018`
3. 해당 index/namespace의 정보값(dimension, 저장된 벡터수) 및 업로드한 파일의 크기 확인
4. Upsert 버튼 클릭

## 2. Example Selector 기반 라벨링

- `pages/Pasrse.py`
- Pinecone 벡터스토어에 저장된 벡터값 기반 유사도 검색하여 few-shot 예시 지정 (`chains/example_selector.py`)
- few-shot 예시를 기반으로 자동 라벨링

1. sidebar에 라벨링할 csv 파일 업로드
2. 기저장된 Pinecone index/namespace 입력
3. 임베딩 후 벡터스토어에서 유사도 검색할 대상 column명 지정 (기본값: `Q` 칼럼) 후 '라벨링 시작' 버튼 클릭
4. 100행씩 임베딩 후 유사도 검색으로 추출된 기존 데이터 예시를 기반으로 자동 라벨링
5. '작업된 csv 다운로드 버튼' 클릭 후 `Downloads/` 폴더 확인
