import json
import os
import re
import requests
import pickle
import urllib.request
import pandas as pd

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


def parse(url) -> dict:
    resp = requests.get(url)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.content, "html.parser")
        parsed = parse_soup(soup)
    return parsed


def parse_soup(soup) -> dict:
    ptn_question_title = re.compile("(?<=\n질문하기\n질문\n)[^\n]+")
    ptn_question_content = re.compile(
        "(?<=작성일\d{4}\.\d{2}\.\d{2}\n).+?(?=\n댓글)", re.DOTALL
    )
    ptn_replies = re.compile(
        "(?<=\d번째 답변\n).*?(?=\d{4}\.\d{2}\.\d{2}\.\n)", re.DOTALL
    )
    ptn_reply_content = re.compile("(?<=         ).+")

    src = soup.get_text()
    txt = re.sub(r"[\n\t]+", "\n", src)

    question_title = ptn_question_title.search(txt).group().strip()
    question_content = ptn_question_content.search(txt).group().strip()
    replies = ptn_replies.findall(txt)
    replies = [
        ptn_reply_content.search(reply).group().strip()
        for reply in replies
        if ptn_reply_content.search(reply)
    ]

    return {
        "title": question_title if question_title else None,
        "content": question_content if question_content else None,
        "replies": replies if replies else None,
        "hyundai_label": "시승",
    }


def get_query_response(query, num):
    num = 10000 if num > 10000 else num
    total_items = []
    for page_idx in tqdm(range(1, 1001, 100)):  # start_idx: 1~1000
        resp_json = get_query_response_per_start_idx(query, start_idx=page_idx)
        if not resp_json:
            break
        num -= len(resp_json["items"])
        for item in resp_json["items"]:
            try:
                parsed = parse(item["link"])
                parsed.update({"url": item["link"], "query": query})
                total_items.append(parsed)
            except:
                print(item["link"])
                continue

        if num <= 0:
            break

    data = {
        "lastBuildDate": resp_json["lastBuildDate"],
        "total": resp_json["total"],
        "last": resp_json["start"],
        "display": resp_json["display"],
        "items": total_items,
        "query": query,
    }

    with open(f"kin_{query}.pkl", "wb") as file:
        pickle.dump(data, file)


def get_query_response_per_start_idx(query, start_idx=1):
    encText = urllib.parse.quote(query)
    url = (
        "https://openapi.naver.com/v1/search/kin?query="
        + encText
        + "&display=100&start="
        + str(start_idx)
    )  # JSON 결과
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode == 200:
        response_body = response.read()
        return json.loads(response_body.decode("utf-8"))
    else:
        print("Error Code:" + rescode)
        return False


def load_from_pickle(filename: str):
    assert filename.endswith(".pkl"), "확장자는 '.pkl'이여야 합니다"
    try:
        with open(filename, "rb") as file:
            return pickle.load(file)
    except FileNotFoundError:
        return {"items": []}


def pickle_to_dataframe(filename):
    # Load the pickle file
    with open(filename, "rb") as file:
        data_dict = pickle.load(file)

    df = pd.DataFrame(data_dict["items"])
    return df


# for query in ["모터 스튜디오"]:
#     get_query_response(query, num=500)
#     df = pickle_to_dataframe(f"/Users/lwj/workspace/QnA/kin_{query}.pkl")
#     df.to_csv(f"kin_{query}.csv")

# r = load_from_pickle("/Users/lwj/workspace/QnA/kin_현대차 시승.pkl")
# print(len(r["items"]))
# print(r.keys())
