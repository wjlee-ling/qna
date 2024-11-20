import os
import pyperclip
import time

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

NAVER_ID = os.getenv("NAVER_ID")
NAVER_PASSWORD = os.getenv("NAVER_PASSWORD")


def login_naver(driver, naver_id=None, naver_password=None):
    """
    MacOS 기준으로 작성되는 코드. Windows의 경우 Keys.COMMAND를 Keys.CONTROL로 변경해야 함.
    """
    driver.get("https://nid.naver.com/nidlogin.login")
    naver_id = naver_id or NAVER_ID
    naver_password = naver_password or NAVER_PASSWORD

    try:
        pyperclip.copy(naver_id)
        id = driver.find_element(
            By.CSS_SELECTOR, "#id"
        )  # 예외처리에 필요 이 구문이 없으면 아이디가 클립보드에 계속 복사됨
        id.click()
        time.sleep(0.8)
        id.send_keys(Keys.COMMAND + "v")
        time.sleep(0.7)

        pyperclip.copy(naver_password)
        pw = driver.find_element(By.CSS_SELECTOR, "#pw")
        pw.send_keys(Keys.COMMAND + "v")
        time.sleep(0.7)

        secure = "blank"
        pyperclip.copy(secure)  # 비밀번호 보안을 위해 클립보드에 blank 저장

        driver.find_element(By.XPATH, '//*[@id="log.login"]').click()

        try:
            time.sleep(1.0)
            if driver.find_element(By.CSS_SELECTOR, ".error_message"):
                print("로그인 정보 불일치로 실패")
                return False
            else:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "span.btn_cancel")
                        )
                    )
                    element.click()
                except:
                    print("기기 '등록안함' 버튼이 없습니다")

        except:
            pass

    except:
        print("no such element")  # 예외처리
        return False

    return True
