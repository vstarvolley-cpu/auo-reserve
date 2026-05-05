import os
import time
import datetime
import smtplib
import jpholiday  # 日本の祝日判定用
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

# 部屋名のキーワード（反面A、反面B、および表記揺れに対応）
TARGET_ROOM_KEYWORDS = ["体育館反面", "体育館（反面）", "体育館 反面", "体育館　反面", "半面"]

def is_holiday_or_weekend(dt):
    """土日または日本の祝日（振替休日含む）かどうかを判定"""
    return dt.weekday() >= 5 or jpholiday.is_holiday(dt)

def is_target_time(date_str, time_str, facility_key):
    """
    判定ロジック：
    1. 全施設：土日祝は全時間帯OK
    2. 梅田のみ：平日の18:30-21:00枠もOK[cite: 4]
    """
    try:
        # 日付文字列 (例: 2026/05/05(火)) から日付部分のみ抽出
        clean_date = date_str.split('(')[0].strip()
        dt = datetime.datetime.strptime(clean_date, "%Y/%m/%d").date()
        
        # 土日祝の判定
        if is_holiday_or_weekend(dt):
            return True
        
        # 梅田の平日夜間判定 (18:30〜21:00付近の枠)
        if facility_key == "梅田":
            target_night_slots = ["18:30", "19:00", "20:00", "夜間"]
            return any(slot in time_str for slot in target_night_slots)
            
        return False
    except Exception as e:
        return False

def send_email(body):
    """結果をメール送信"""
    try:
        msg = MIMEText(body)
        msg["Subject"] = "【Vstars】体育館空き状況通知"
        msg["From"] = os.environ["GMAIL_USER"]
        msg["To"] = os.environ["TARGET_MAIL"]
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.environ["GMAIL_USER"], os.environ["GMAIL_PASS"])
            smtp.send_message(msg)
    except Exception as e:
        print(f"メール送信エラー: {e}")

def run_check():
    options = Options()
    options.add_argument("--headless")  # ブラウザを表示しない
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1024")
    
    driver = webdriver.Chrome(options=options)
    found_list = []
    
    # 2ヶ月先の末日を計算
    today = datetime.date.today()
    # 3ヶ月後の1日から1日引くことで、2ヶ月後の末日を算出
    target_end_date = (today.replace(day=1) + datetime.timedelta(days=92)).replace(day=1) - datetime.timedelta(days=1)
    print(f"探索期限: {target_end_date} まで取得します")

    try:
        # セッション確立
        driver.get("https://k5.p-kashikan.jp/adachi-ku/index.php")
        time.sleep(2)

        for key, f_id in FACILITIES.items():
            print(f"--- 調査開始: {key} ---")
            driver.get(f"https://k5.p-kashikan.jp/adachi-ku/index.php?shisetsu_pk={f_id}")
            time.sleep(3)
            
            # 「空き状況」ボタンをすべて取得
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '空き状況')]")
            
            # 各部屋（反面A, 反面Bなど）のボタンを巡回
            # ボタンの親要素のテキストを見てターゲットかどうか判断
            target_buttons = []
            for el in elements:
                try:
                    row = el.find_element(By.XPATH, "./ancestor::tr")
                    if any(kw in row.text for kw in TARGET_ROOM_KEYWORDS):
                        target_buttons.append((el, row.text.split()[0]))
                except:
                    continue

            for btn_el, room_name in target_buttons:
                print(f"  [発見] {room_name} のカレンダーへ移動")
                
                # ボタンが隠れている場合を考慮してJSでクリック
                driver.execute_script("arguments[0].click();", btn_el)
                time.sleep(3)
                
                # --- カレンダーページング・ループ (2ヶ月先の末日まで) ---
                while True:
                    # カレンダーの日付とセルの取得
                    cal_cells = driver.find_elements(By.CSS_SELECTOR, "table.calendar_table td, table.calendar_table th")
                    current_date_in_page = ""
                    last_date_on_page = today # 期限判定用
                    
                    for cell in cal_cells:
                        c_text = cell.text.strip()
                        if not c_text: continue
                        
                        # 日付ラベルの保存 (例: 2026/05/05(火))
                        if "/" in c_text and "(" in c_text:
                            current_date_in_page = c_text
                            # ページ内の最後の日付を更新
                            clean_d = c_text.split('(')[0].strip()
                            last_date_on_page = datetime.datetime.strptime(clean_d, "%Y/%m/%d").date()
                            continue
                        
                        # 空き記号の判定
                        if any(mark in c_text for mark in ["○", "◯", "〇"]):
                            try:
                                time_row = cell.find_element(By.XPATH, "./ancestor::tr")
                                time_range = time_row.find_elements(By.TAG_NAME, "td")[0].text
                                
                                if is_target_time(current_date_in_page, time_range, key):
                                    msg = f"【{key}】{current_date_in_page} {time_range} ({room_name})"
                                    if msg not in found_list:
                                        found_list.append(msg)
                                        print(f"    ★ヒット: {current_date_in_page} {time_range}")
                            except:
                                continue

                    # 2ヶ月先の末日を超えていたら次の部屋へ
                    if last_date_on_page >= target_end_date:
                        print(f"    -> {target_end_date} まで到達したため、この部屋の確認を終了します")
                        break

                    # 「2週間後」や「1ヶ月後」ボタンを探して次へ進む
                    try:
                        next_btn = driver.find_element(By.XPATH, "//a[contains(text(), '2週間後') or contains(text(), '1ヶ月後')]")
                        driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(3)
                    except:
                        # 次のボタンがなければループを抜ける
                        break
                
                # 施設トップに戻って次の部屋（反面Bなど）を探す
                driver.get(f"https://k5.p-kashikan.jp/adachi-ku/index.php?shisetsu_pk={f_id}")
                time.sleep(3)
                # ボタン要素がリセットされるため、再取得
                elements = driver.find_elements(By.XPATH, "//*[contains(text(), '空き状況')]")

        # 全施設終了後の処理
        if found_list:
            report = "以下の空きが見つかりました：\n\n" + "\n".join(found_list)
            print(report)
            send_email(report)
        else:
            print(">> 条件に合う空きはありませんでした。")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_check()
