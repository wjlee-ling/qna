# Pinecone 기반 Hybrid VectorStore

```python
from vectorstore.pinecone import PineconeVectorStore, get_or_create_pinecone_index
from vectorstore.sparse import BM25Encoder, KiwiTokenizer
from langchain_openai import OpenAIEmbeddings
```

## Pinecone index 생성/호출

### 1. index_name 및 (필요시) namespace 정의

### 2. index 및 vectorstore 생성/호출

```python
pc_index = get_or_create_pinecone_index(index_name)
```

### 3. (한국어 sparse 사용시) kiwi tokenizer 기반 bm25 encoder 생성/호출

#### 0. bm25 encoder에 한국어 전용 KiwiTokenizer 장착

- Kiwi 토큰나이저가 허용하는 꼴로 사용자 사전이 있을 시 `user_dict_path`로 경로 입력

```python
kiwi = KiwiTokenizer(user_dict_path="[사용자_사전_경로.txt]")
bm25 = BM25Encoder()
bm25.replace_with_Kiwi_tokenizer(kiwi)
```

#### 1. bm25 encoder 훈련 및 저장

- docs: 훈련할 데이터 `List[str]`

```python
bm25.fit(docs)
bm25.dump("[저장경로].json")
```

#### 2. (이전에 훈련된) bm25 encoder 불러오기

```pyton
bm25.load("[저장경로].json")
```

#### 4. upsert_from_dataframe

- 주의: 이전에 저장된 record가 중복 업로드 되지 않게 주의
- 필수:
  - dense embedding_fn: (기본) `OpenAIEmbeddings` 객체
  - 임베딩할 data/metadata/id가 있는 csv의 경로
- 옵션:
  - sparse encoder: 이전 과정에서 불러온 bm25 encoder

```python
embeddings = OpenAIEmbeddings(...)
vs = PineconeVectorStore(
    pc_index,
    embeddings,
    sparse_encoder=bm25,
    namespace=NAMESPACE,
    pinecone_api_key=os.getenv("PINECONE_API_KEY"),
)
vs.upsert_from_dataframe(
    csv_path: str,
    text_col: str, # dense + (sparse) 임베딩할 칼럼명
    id_col: Optional[str] = None, # id로 사용할 칼럼명
    metadata_cols: Optional[List[str]] = None, # metadata로 사용할 칼럼명들
    namespace: Optional[str] = None,
    batch_size: int = 32,
)
```
