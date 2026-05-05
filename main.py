import os
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- ターゲット設定 ---
FACILITIES = {
    "梅田": {"id": "114", "name": "梅田地域学習センター", "targets": ["体育館反面A", "体育館反面B"]},
    "中央本町": {"id": "115", "name": "中央本町地域学習センター", "targets": ["体育館反面A", "体育館反面B"]},
    "伊興": {"id": "120", "name": "伊興地域学習センター", "targets": ["体育館反面A", "体育館反面B"]},
    "スイム": {"id": "131", "name": "スイムスポーツセンター", "targets": ["体育館反面A", "体育館反面B"]},
    "東和": {"id": "116", "name": "東和地域学習センター", "targets": ["体育館反面A", "体育館反面B"]},
    "興本": {"id": "118", "name": "興本地域学習センター", "targets": ["体育館反面A", "体育館反面B"]},
    "花畑": {"id": "121", "name": "花畑地域学習センター", "targets": ["体育館反面A", "体育館反面B"]},
    "江北": {"id": "119", "name": "江北地域学習センター", "targets": ["体育館反面A", "体育館反面B"]},
    "鹿浜": {"id": "117", "name": "鹿浜地域学習センター", "targets": ["体育館反面A", "体育館反面B"]}
}

def is_target_day(date_str, facility_key):
    # 日付文字列 (例: "2026/05/10(日)") から判定
    try:
        date_part = date_str.split('(')[0]
        dt = datetime.datetime.strptime(date_part, "%Y/%m/%d")
        is_weekend = dt.weekday() >= 5 # 5=土, 6=日
        
        if facility_key == "梅田":
            return True # 梅田は平日(夜間判定は別途)・土日祝すべて対象
        return is_weekend # その他は土日祝のみ
    except:
        return False

def send_email(body):
    msg = MIMEText(body)
    msg["Subject"] = "【Vstars】体育館空き情報通知"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = os.environ["TARGET_MAIL"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["GMAIL_USER"], os.environ["GMAIL_PASS"])
        smtp.send_message(msg)

def run_check():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    
    found_list = []
    
    try:
        for key, info in FACILITIES.items():
            print(f"Checking: {info['name']}...")
            # 直接、施設別の空き状況URLへ（施設IDを動的に差し替え）
            url = f"https://k5.p-kashikan.jp/adachi-ku/index.php?shisetsu_pk={info['id']}"
            driver.get(url)
            time.sleep(3)
            
            # 反面A、反面Bなどの室場をループ
            rooms = driver.find_elements(By.CLASS_NAME, "room_name")
            for room in rooms:
                room_text = room.text
                if any(t in room_text for t in info["targets"]):
                    # その室場の「空き状況」ボタンをクリック
                    try:
                        btn = room.find_element(By.XPATH, "./ancestor::tr//button[contains(text(), '空き状況')]")
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)
                        
                        # カレンダー解析（◯がついている場所を探す）
                        # ※簡易版：特定の曜日の"◯"を抽出
                        # 実際にはtableのtr/tdを走査して日時を特定
                        days = driver.find_elements(By.CSS_SELECTOR, "table.calendar_table td")
                        for day in days:
                            if "◯" in day.text:
                                date_info = "特定の日時" # ここで日付行から取得
                                if is_target_day(date_info, key):
                                    found_list.append(f"{info['name']} - {room_text}: {date_info}")
                        
                        driver.back() # 一覧に戻る
                        time.sleep(1)
                    except:
                        continue

        if found_list:
            send_email("\n".join(found_list))
            print("メールを送信しました。")
        else:
            print("対象の空きは見つかりませんでした。")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_check()
