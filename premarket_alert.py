import requests
from bs4 import BeautifulSoup
import re
import time
import datetime
import pytz
import os

# Telegram Bot Config (use Render Environment Variables)
BOT_TOKEN = os.environ.get("bot_token")
CHAT_ID = os.environ.get("chat_id")

# Constants
URL = "https://www.tradingview.com/markets/stocks-usa/market-movers-pre-market-gainers/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# EST Timezone
eastern = pytz.timezone("US/Eastern")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Error:", e)

def scrape_tradingview():
    try:
        response = requests.get(URL, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        if not table:
            send_telegram("[ERROR] Screener content not found.")
            return

        rows = table.find("tbody").find_all("tr")
        results = []

        for row in rows[:25]:  # Only top 25
            cols = row.find_all("td")
            try:
                symbol = cols[0].text.strip()
                name = cols[1].text.strip()
                last_price = cols[2].text.strip()
                change_percent = cols[4].text.strip()
                volume = cols[5].text.strip()

                match = re.search(r"([+-]?[0-9.]+)%", change_percent)
                if match and float(match.group(1)) >= 10:
                    results.append(f"*{symbol}* ({name})\nPrice: ${last_price} | Change: {change_percent} | Vol: {volume}")
            except Exception as e:
                continue  # Skip malformed rows

        if results:
            message = f"🚀 *Top Pre-market Gainers (10%+)*\n{datetime.datetime.now(eastern).strftime('%Y-%m-%d %H:%M %Z')}\n\n"
            message += "\n\n".join(results)
        else:
            message = "⚠️ No stocks found with 10%+ gain in pre-market right now."

        send_telegram(message)

    except Exception as e:
        send_telegram(f"[ERROR] Exception during scrape: {e}")

if __name__ == "__main__":
    now = datetime.datetime.now(eastern)
    if now.hour >= 4 and (now.hour < 9 or (now.hour == 9 and now.minute < 30)):
        scrape_tradingview()
    else:
        print("Outside pre-market hours.")
