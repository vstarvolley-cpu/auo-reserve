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
    "梅田": {"id": "114", "targets": ["体育館反面A", "体育館反面B"]},
    "中央本町": {"id": "115", "targets": ["体育館反面A", "体育館反面B"]},
    "伊興": {"id": "120", "targets": ["体育館反面A", "体育館反面B"]},
    "スイム": {"id": "131", "targets": ["体育館反面A", "体育館反面B"]},
    "東和": {"id": "116", "targets": ["体育館反面A", "体育館反面B"]},
    "興本": {"id": "118", "targets": ["体育館反面A", "体育館反面B"]},
    "花畑": {"id": "121", "targets": ["体育館反面A", "体育館反面B"]},
    "江北": {"id": "119", "targets": ["体育館反面A", "体育館反面B"]},
    "鹿浜": {"id": "117", "targets": ["体育館反面A", "体育館反面B"]}
}

def is_target_time(date_str, time_str, facility_key):
    """曜日と時間帯の判定"""
    try:
        # 日付から曜日を取得 (date_str: "2026/05/10")
        dt = datetime.datetime.strptime(date_str, "%Y/%m/%d")
        is_weekend = dt.weekday() >= 5 # 5=土, 6=日
        # 祝日の判定は簡易化のため週末に含めるか、土日条件で判定
        
        if facility_key == "梅田":
            if is_weekend: return True
            return "夜間" in time_str # 平日は夜間のみ
        return is_weekend # その他は土日祝のみ
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
        for key, info in FACILITIES.items():
            print(f"--- Checking: {key} ---")
            url = f"https://k5.p-kashikan.jp/adachi-ku/index.php?shisetsu_pk={info['id']}"
            driver.get(url)
            time.sleep(3)
            
            # ページ内のすべての行を取得
            rows = driver.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows:
                row_text = row.text
                # 指定したターゲット（反面Aなど）が含まれる行かチェック
                if any(t in row_text for t in info["targets"]):
                    print(f"  [発見] {row_text.split()[0]}")
                    try:
                        # その行にある「空き状況」ボタンを探してクリック
                        btn = row.find_element(By.PARTIAL_LINK_TEXT, "空き状況")
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(3)
                        
                        # カレンダーテーブルの解析
                        # 1ヶ月分チェック
                        cal_rows = driver.find_elements(By.CSS_SELECTOR, ".calendar_table tr")
                        current_date = ""
                        for cal_row in cal_rows:
                            cols = cal_row.find_elements(By.TAG_NAME, "td")
                            if not cols: continue
                            
                            # 日付行の取得
                            if "calendar_day" in cal_row.get_attribute("class") or len(cols) < 3:
                                current_date = cal_row.text.split('(')[0].strip()
                                continue
                            
                            # 時間帯と空き状況の取得
                            time_range = cols[0].text
                            status = cols[1].text
                            
                            if "○" in status or "◯" in status:
                                if is_target_time(current_date, time_range, key):
                                    found_list.append(f"【{key}】{current_date} {time_range} ({row_text.split()[0]})")
                                    print(f"    ★空きあり: {current_date} {time_range}")

                        driver.back()
                        time.sleep(2)
                    except Exception as e:
                        print(f"    × ボタン操作失敗")
                        continue

        if found_list:
            send_email("以下の空きが見つかりました：\n\n" + "\n".join(found_list))
            print(">> メールを送信しました！")
        else:
            print(">> 条件に合う空きはありませんでした。")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_check()
