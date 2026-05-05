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
    "梅田": "114", "中央本町": "115", "伊興": "120", "スイム": "131",
    "東和": "116", "興本": "118", "花畑": "121", "江北": "119", "鹿浜": "117"
}
# 部屋名は「含まれているか」で判定（表記の揺れ対策）
TARGET_ROOM_KEYWORDS = ["体育館反面", "体育館（反面）"]

def is_target_time(date_str, time_str, facility_key):
    """平日夜間・土日祝の判定ロジック"""
    try:
        # 日付文字列から曜日を判定 (例: 2026/05/05(火))
        clean_date = date_str.split('(')[0].strip()
        dt = datetime.datetime.strptime(clean_date, "%Y/%m/%d")
        is_weekend = dt.weekday() >= 5 # 5=土, 6=日
        
        # 梅田：平日夜間 または 土日祝すべて
        if facility_key == "梅田":
            if is_weekend: return True
            return "夜間" in time_str or "18:00" in time_str or "19:00" in time_str
        
        # その他：土日祝のみ
        return is_weekend
    except:
        return False

def send_email(body):
    msg = MIMEText(body)
    msg["Subject"] = "【Vstars】足立区体育館 空き通知"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = os.environ["TARGET_MAIL"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["GMAIL_USER"], os.environ["GMAIL_PASS"])
        smtp.send_message(msg)

def run_check():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,1024")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    found_list = []
    
    try:
        # 1. 最初に必ずトップページを開いてセッションを確立
        driver.get("https://k5.p-kashikan.jp/adachi-ku/index.php")
        time.sleep(2)

        for key, f_id in FACILITIES.items():
            print(f"--- 調査開始: {key} ---")
            driver.get(f"https://k5.p-kashikan.jp/adachi-ku/index.php?shisetsu_pk={f_id}")
            time.sleep(3)
            
            # 全ての「空き状況」ボタンらしき要素を抽出
            # テキストに「空き状況」が含まれるすべての要素を探す
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '空き状況')]")
            
            if not elements:
                print(f"  [!] ボタンが見つかりません。ページ情報を確認中...")
                continue

            # 各ボタンに対して、その周辺に「体育館反面」という文字があるかチェック
            for el in elements:
                try:
                    # ボタンの親要素の行（tr）を取得
                    row = el.find_element(By.XPATH, "./ancestor::tr")
                    row_text = row.text.replace("\n", " ")
                    
                    if any(kw in row_text for kw in TARGET_ROOM_KEYWORDS):
                        room_name = row_text.split()[0]
                        print(f"  [発見] {room_name} のカレンダーへ移動")
                        
                        # ボタンをクリック
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(3)
                        
                        # カレンダー解析
                        current_date = ""
                        cal_cells = driver.find_elements(By.CSS_SELECTOR, "table.calendar_table td, table.calendar_table th")
                        
                        # カレンダーの各セルをループ
                        for cell in cal_cells:
                            c_text = cell.text.strip()
                            if not c_text: continue
                            
                            # 日付を保持 (例: 2026/05/05)
                            if "/" in c_text and "(" in c_text:
                                current_date = c_text
                                continue
                            
                            # 空き状況をチェック
                            if "○" in c_text or "◯" in c_text or "〇" in c_text:
                                # 親要素の行から時間帯を取得
                                try:
                                    time_row = cell.find_element(By.XPATH, "./ancestor::tr")
                                    time_range = time_row.find_elements(By.TAG_NAME, "td")[0].text
                                    
                                    if is_target_time(current_date, time_range, key):
                                        msg = f"【{key}】{current_date} {time_range} ({room_name})"
                                        found_list.append(msg)
                                        print(f"    ★ヒット: {current_date} {time_range}")
                                except:
                                    continue
                        
                        # 施設ページに戻る
                        driver.get(f"https://k5.p-kashikan.jp/adachi-ku/index.php?shisetsu_pk={f_id}")
                        time.sleep(2)
                        # 一度戻ると要素が無効になるため、次のループへ（1施設1件ヒットすればOKの設計）
                        break
                except:
                    continue

        if found_list:
            send_email("以下の空きが見つかりました：\n\n" + "\n".join(found_list))
            print(">> メール送信完了！")
        else:
            print(">> 条件に合う空きはありませんでした。")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_check()
