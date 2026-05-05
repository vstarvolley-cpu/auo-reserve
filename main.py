import os
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- ターゲット設定 ---
FACILITIES = {
    "梅田": "114", "中央本町": "115", "伊興": "120", "スイム": "131",
    "東和": "116", "興本": "118", "花畑": "121", "江北": "119", "鹿浜": "117"
}
TARGET_ROOMS = ["体育館反面A", "体育館反面B"]

def is_target_time(date_str, time_str, facility_key):
    try:
        dt = datetime.datetime.strptime(date_str.split('(')[0], "%Y/%m/%d")
        is_weekend = dt.weekday() >= 5
        if facility_key == "梅田":
            return is_weekend or "夜間" in time_str
        return is_weekend
    except:
        return False

def send_email(body):
    msg = MIMEText(body)
    msg["Subject"] = "【Vstars】体育館空き発見通知"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = os.environ["TARGET_MAIL"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["GMAIL_USER"], os.environ["GMAIL_PASS"])
        smtp.send_message(msg)

def run_check():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    found_list = []
    
    try:
        for key, f_id in FACILITIES.items():
            print(f"--- Checking: {key} ---")
            driver.get(f"https://k5.p-kashikan.jp/adachi-ku/index.php?shisetsu_pk={f_id}")
            time.sleep(4) # 読み込み待ちを長めに
            
            # 全ての「空き状況」ボタンを取得
            buttons = driver.find_elements(By.XPATH, "//button[contains(text(), '空き状況')]")
            
            for btn in buttons:
                # ボタンの親要素の行から部屋名を取得
                row = btn.find_element(By.XPATH, "./ancestor::tr")
                room_name = row.text.split()[0]
                
                if any(t in room_name for t in TARGET_ROOMS):
                    print(f"  [発見] {room_name} のカレンダーへ...")
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
                    
                    # カレンダーの全行を走査
                    cal_rows = driver.find_elements(By.CSS_SELECTOR, "table.calendar_table tr")
                    current_date = ""
                    for c_row in cal_rows:
                        cells = c_row.find_elements(By.TAG_NAME, "td")
                        # 日付行の処理
                        if "calendar_day" in c_row.get_attribute("class") or len(cells) < 2:
                            if "(" in c_row.text:
                                current_date = c_row.text.strip()
                            continue
                        
                        # 枠ごとの処理
                        if len(cells) >= 2:
                            t_range = cells[0].text
                            status = cells[1].text
                            if "○" in status or "◯" in status:
                                if is_target_time(current_date, t_range, key):
                                    found_list.append(f"【{key}】{current_date} {t_range} ({room_name})")
                                    print(f"    ★空きあり: {current_date} {t_range}")
                    
                    driver.back()
                    time.sleep(2)
                    # ページが戻るとボタン要素が古くなるので、再度取得し直す
                    break # 今回は1施設1部屋ずつ確実に回るため一旦抜ける

        if found_list:
            send_email("以下の空きが見つかりました：\n\n" + "\n".join(found_list))
            print(">> メールを送信完了")
        else:
            print(">> 条件に合う空きはありませんでした。")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_check()
