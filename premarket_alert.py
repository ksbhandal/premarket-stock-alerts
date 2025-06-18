import time
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# Telegram Bot Config
bot_token = os.environ.get('bot_token')
chat_id = os.environ.get('chat_id')

# Chrome Driver Setup
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')

# Set your path to chromedriver
service = Service('C:/Users/kamal/chromedriver/chromedriver.exe')
driver = webdriver.Chrome(service=service, options=chrome_options)

# Screener URL (Premarket Penny Stocks)
driver.get("https://www.tradingview.com/screener/")
time.sleep(8)

# Expand columns (optional if custom view is saved)
try:
    driver.find_element(By.XPATH, '//button[contains(text(),"Customize columns")]').click()
    time.sleep(2)
except:
    pass  # columns may already be visible

# Grab table
rows = driver.find_elements(By.XPATH, '//div[@data-widget="screener-table"]//tbody/tr')
stocks = []
for row in rows:
    try:
        cols = row.find_elements(By.TAG_NAME, 'td')
        if len(cols) < 10:
            continue

        symbol = cols[0].text
        premarket_change = cols[2].text
        premarket_gap = cols[3].text
        premarket_volume = cols[4].text
        price = cols[5].text
        change = cols[6].text
        gap = cols[7].text
        volume = cols[8].text
        vol_change = cols[9].text
        relvol_15m = cols[10].text if len(cols) > 10 else 'N/A'
        relvol_5m = cols[11].text if len(cols) > 11 else 'N/A'

        # Custom filter logic
        if relvol_15m != 'N/A' and float(relvol_15m) >= 2:
            message = (
                f"🚀 [Premarket Alert] {symbol}\n"
                f"Price: ${price}\n"
                f"PreMkt Chg: {premarket_change}\n"
                f"Gap: {premarket_gap}\n"
                f"Vol: {volume}\n"
                f"RelVol 15m: {relvol_15m}\n"
                f"RelVol 5m: {relvol_5m}"
            )
            stocks.append(message)
    except:
        continue

# Send Alerts via Telegram
for stock_msg in stocks:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": stock_msg}
    requests.get(url, params=payload)

print(f"✅ Sent {len(stocks)} premarket stock alerts.")
driver.quit()
