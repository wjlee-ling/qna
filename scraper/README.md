# 네이버 지식인 크롤러

## 0. Prerequisites

- 네이버 공식 개발자 client_id, client_secret 발급
- 발급 후 `.env`에 저장

## 1. 검색할 키워드 및 수량 지정

- `scraper/naver_kin.py`내 `get_query_response`에 검색 키워드 및 검색 수량 지정
