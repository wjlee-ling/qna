from scraper.helpers import *
from scraper.naver_login import login_naver

import copy
import os
import time
from datetime import datetime
from typing import List, Dict

from dotenv import load_dotenv
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


load_dotenv()

URL = os.getenv("NAVER_CAFE_URL")
TARGET_BOARD_NUM = "669"  # 통합 Q&A

chrome_options = Options()
driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(15)


def get_to_board_click_first():
    driver.get(URL)
    target_board = driver.find_element(By.CSS_SELECTOR, f"#menuLink{TARGET_BOARD_NUM}")
    target_board.click()
    driver.switch_to.frame("cafe_main")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#main-area"))
    )

    # Click the first post in the main table
    driver.find_element(
        By.XPATH, '//*[@id="main-area"]/div[4]/table/tbody/tr[1]/td[1]/div[2]/div/a[1]'
    ).click()
    time.sleep(1.5)


def read_board(
    num,
    include_comments=False,
    start_idx=None,
    cafe_url=URL,
    board_num=TARGET_BOARD_NUM,
):
    """
    특정 네이버 cafe의 특정 게시판(board)의 게시물을 순서대로 읽어옵니다. 포스트의 고유 id('URL 복사' 클릭 후 추출 가능)를 포함한 url로 크롤링을 시작할 포스트를 지정 후, '다음글'을 계속 클릭하며 읽어옵니다.
    Args:
        - num: 읽어올 게시물 갯수
        - start_idx: 읽어올 게시물의 시작 인덱스 (post_number 기준)
        - cafe_url: 읽어올 카페의 기본 url
        - board_num: 읽어올 게시판의 번호 (직접 카페의 해당 게시판에 들어가서 url에서 확인)

    ref: https://velog.io/@mino0121/Python-Selenium%EC%9D%84-%EC%9D%B4%EC%9A%A9%ED%95%9C-Naver-cafe-%EA%B2%8C%EC%8B%9C%EB%AC%BC-%ED%85%8D%EC%8A%A4%ED%8A%B8-%EC%8A%A4%ED%81%AC%EB%9E%98%ED%95%91
    """
    last_post_id = load_last_post_id()
    if start_idx is None:
        if last_post_id is None:
            get_to_board_click_first()
        else:
            post_url = URL + f"/{last_post_id}"
            print("🤖🤖 Resuming from last post: ", post_url)
            driver.get(post_url)
            turn_post()
    else:
        post_url = URL + f"/{start_idx}"
        driver.get(post_url)
        driver.switch_to.frame("cafe_main")
        # driver.implicitly_wait(1.1)

    # Parsing each post
    parsed = []
    current_time = (datetime.now()).strftime("%Y%m%d_%H%M%S")

    for i in tqdm(range(num), desc="Reading posts"):
        try:
            parsed.extend(parse_post(include_comments=include_comments))
            if start_idx is None:
                start_idx = parsed[-1]["post_id"]

        except Exception as e:
            print(f"🚨 Error at {i}th post: {e}")
            continue

        # Save to csv every 50 posts
        if i % 50 == 0 and parsed:
            save_to_csv(
                parsed,
                filename=f"scraper/parsed/{current_time}_starting_{start_idx}.csv",
            )
            save_last_post_id(parsed[-1]["post_id"])
            parsed = []

        # Turn to the next post
        turn_post()

    if parsed != []:
        save_to_csv(
            parsed, filename=f"scraper/parsed/{current_time}_starting_{start_idx}.csv"
        )
        save_last_post_id(parsed[-1]["post_id"])

    return parsed


def parse_post(include_comments: bool) -> List[Dict]:
    try:
        driver.switch_to.frame("cafe_main")
    except:
        pass

    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="spiButton"]'))
    )
    url = driver.find_element(By.XPATH, '//*[@id="spiButton"]').get_attribute(
        "data-url"
    )
    id = url.split("/")[-1]
    date = driver.find_element(By.CLASS_NAME, "date").text
    nickname = driver.find_element(By.CLASS_NAME, "nickname").text
    title = driver.find_element(By.CLASS_NAME, "title_text").text
    view = driver.find_element(By.CLASS_NAME, "count").text.lstrip("조회 ")
    comment_count = (
        driver.find_element(By.CLASS_NAME, "ArticleTool")
        .find_element(By.CLASS_NAME, "num")
        .text.strip()
    )

    # Find body of the article
    content = driver.find_element(By.CLASS_NAME, "ArticleContentBox")
    content_text = content.find_element(By.CLASS_NAME, "article_viewer").text.strip()

    data_main_body = {
        "type": "post",
        "post_id": id,
        "title": title,
        "nickname": nickname,
        "date": date,
        "content": content_text,
        "url": url,
        "view": view,
        "comment_count": comment_count,
        "comment_id": None,
        "parent_id": None,
    }
    if not include_comments:
        return [data_main_body]

    try:
        data_comments = parse_comments(content, payload=data_main_body)
    except:
        # 댓글 현재 없음
        data_comments = []

    return [data_main_body] + data_comments


def parse_comments(content, payload: Dict) -> List[Dict]:
    comment_list = content.find_element(By.CLASS_NAME, "comment_list")
    parsed = []

    # Find all 'li' elements with class 'CommentItem', but only top-level (recursive=False)
    comment_items = comment_list.find_elements(
        By.XPATH, './li[contains(@class, "CommentItem")]'
    )
    current_top_level_id = None

    for comment in comment_items:
        # Extract the comment ID
        comment_id = comment.get_attribute("id")

        # Determine if the comment is a top-level comment or a reply
        if "CommentItem--reply" not in comment.get_attribute("class"):
            # Update current top-level ID for top-level comments
            current_top_level_id = comment_id
            parent_id = None  # itself
        else:
            # Nested reply, use the current top-level comment's ID as parent
            parent_id = current_top_level_id

        # Extract the nickname
        nickname_tag = comment.find_element(By.CLASS_NAME, "comment_nickname")
        nickname = nickname_tag.text.strip()

        # Extract the comment text
        try:
            comment_text_tag = comment.find_element(By.CLASS_NAME, "text_comment")
            comment_text = comment_text_tag.text.strip()
        except:
            comment_text = None

        # Extract the comment time
        comment_date_tag = comment.find_element(By.CLASS_NAME, "comment_info_date")
        comment_date = comment_date_tag.text.strip()

        # Skip comments that are deleted or empty
        if (
            comment_text is None
            or "삭제된 댓글입니다" in comment_text
            or comment_text == ""
        ):
            continue

        # Update the comment data
        comment_data = copy.deepcopy(payload)
        comment_data.update(
            {
                "type": "comment",
                "date": comment_date,
                "nickname": nickname,
                "content": comment_text,
                "view": None,
                "comment_count": None,
                "comment_id": comment_id,
                "parent_id": parent_id,
            }
        )
        # Append the comment data to the list
        parsed.append(comment_data)

    return parsed


def turn_post():
    try:
        driver.switch_to.frame("cafe_main")
    except:
        pass

    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "btn_next"))
    )
    try:
        driver.find_element(
            By.CSS_SELECTOR,
            "#app > div > div > div.ArticleTopBtns > div.right_area > a.BaseButton.btn_next.BaseButton--skinGray.size_default",
        ).click()

    except:
        driver.find_element(
            By.CSS_SELECTOR,
            "#app > div > div > div.ArticleTopBtns > div.right_area > a.BaseButton.btn_next.BaseButton--skinGray.size_default > span",
        ).click()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--num", "-n", type=int, required=True)
    parser.add_argument("--idx", type=int, default=None)
    parser.add_argument("--url", type=str, default=URL)
    parser.add_argument("--board_num", "-b", type=str, default=TARGET_BOARD_NUM)
    parser.add_argument("--id", type=str, default=None)
    parser.add_argument("--password", type=str, default=None)
    parser.add_argument("--include_comments", action="store_true")

    args = parser.parse_args()
    if not login_naver(driver, naver_id=args.id, naver_password=args.password):
        raise Exception("Failed to login to Naver")

    read_board(
        args.num,
        start_idx=args.idx,
        include_comments=args.include_comments,
        cafe_url=args.url,
        board_num=args.board_num,
    )
