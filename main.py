import os
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

# --- 設定エリア ---
TARGET_CLUBS = {
    "梅田": ["梅田地域学習センター"],
    "その他": [
        "中央本町地域学習センター", "伊興地域学習センター", "スイムスポーツセンター",
        "東和地域学習センター", "興本地域学習センター", "花畑地域学習センター",
        "江北地域学習センター", "鹿浜地域学習センター"
    ]
}

def send_email(body):
    msg = MIMEText(body)
    msg["Subject"] = f"【空き通知】足立区体育館チェック_{datetime.date.today()}"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = os.environ["TARGET_MAIL"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["GMAIL_USER"], os.environ["GMAIL_PASS"])
        smtp.send_message(msg)

def check_availability():
    options = Options()
    options.add_argument("--headless")  # 画面なしモード
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    
    results = []
    base_url = "https://k5.p-kashikan.jp/adachi-ku/index.php"

    try:
        for category, facilities in TARGET_CLUBS.items():
            for facility_name in facilities:
                driver.get(base_url)
                time.sleep(3)
                
                # 「空き状況検索」ボタンをクリック（サイト構造に合わせて調整）
                # 実際には施設名から直接検索ページへ遷移する処理を記述
                # ※ここはサイトの動的IDを解析したロジックが必要です
                
                # --- ここから簡易ロジック（実際には詳細なXPath指定が必要） ---
                # 各施設・各反面A/Bを巡回し、◯がついている日時を抽出
                # 平日夜間、土日祝の判定ロジックをここに集約
                
                # 暫定：見つかったと仮定したシミュレーションコード
                # 実際の実装では driver.find_elements でカレンダーを解析します
                pass 

        # 結果があればメール送信
        if results:
            send_email("\n".join(results))
        else:
            print("空きはありませんでした。")

    finally:
        driver.quit()

if __name__ == "__main__":
    check_availability()