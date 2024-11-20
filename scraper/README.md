# 네이버 크롤러

## 1. [네이버 지식인](naver_kin.py)

- prerequisites
  - 네이버 공식 개발자 client_id, client_secret 발급
  - 발급 후 `.env`에 저장
- `scraper/naver_kin.py`내 `get_query_response`에 검색 키워드 및 검색 수량 지정

## 2. [네이버 카페](naver_cafe.py)

- 특정 카페의 특정 게시판의 포스트 수집
- 수집 데이터

  - 글 제목
  - 글 본문
  - url
  - 고유 id (url에서 추출 가능)
  - 작성자
  - 작성일
  - 댓글수
  - 조회수
  - 댓글
    - 네이버 카페 게시글 구조상 depth 2까지만 위계 추출 가능 (댓글 및 1차 대댓글의 위계만 추출 가능)

- TODO:
  - 웹 로딩 관련 파싱 오류로 인한 중단 수정
    - 현재는 마지막까지 수집한 `고유 id`를 로컬에 저장함으로써 대응
