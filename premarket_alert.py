import os
import requests
from datetime import datetime
from flask import Flask
import pytz
import time

app = Flask(__name__)

BOT_TOKEN = os.environ.get("bot_token")
CHAT_ID = os.environ.get("chat_id")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")

HEADERS = {
    "X-Finnhub-Token": FINNHUB_API_KEY
}

EXCHANGES = ["US"]
PRICE_LIMIT = 5.00
GAP_PERCENT = 20
VOLUME_MIN = 100000
REL_VOL_MIN = 2
TIMEZONE = pytz.timezone("US/Eastern")
SCAN_HOURS = range(4, 9)  # 4 AM to 8:59 AM EST

last_alerted = set()


def is_premarket():
    now = datetime.now(TIMEZONE)
    return now.hour in SCAN_HOURS


def fetch_stocks():
    url = f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={FINNHUB_API_KEY}"
    res = requests.get(url)
    if res.status_code == 200:
        return [s['symbol'] for s in res.json() if s.get("type") == "Common Stock"]
    return []


def get_metrics(symbol):
    try:
        quote = requests.get(f"https://finnhub.io/api/v1/quote?symbol={symbol}", headers=HEADERS).json()
        profile = requests.get(f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}", headers=HEADERS).json()
        stats = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all", headers=HEADERS).json()

        return {
            "symbol": symbol,
            "current_price": quote.get("c"),
            "previous_close": quote.get("pc"),
            "market_cap": profile.get("marketCapitalization"),
            "volume": quote.get("v"),
            "rel_vol": stats.get("metric", {}).get("relativeVolume")
        }
    except:
        return None


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, data=data)
    except:
        pass


def scan_and_alert():
    if not is_premarket():
        return

    send_telegram_message("\ud83d\udd0d Pre-market scan triggered.")
    symbols = fetch_stocks()
    for symbol in symbols:
        if symbol in last_alerted:
            continue

        metrics = get_metrics(symbol)
        if not metrics:
            continue

        price = metrics["current_price"]
        prev_close = metrics["previous_close"]
        cap = metrics["market_cap"]
        volume = metrics["volume"]
        rel_vol = metrics["rel_vol"]

        if not all([price, prev_close, cap, volume, rel_vol]):
            continue

        if price > PRICE_LIMIT:
            continue

        percent_change = ((price - prev_close) / prev_close) * 100 if prev_close else 0
        if percent_change < GAP_PERCENT:
            continue

        if volume < VOLUME_MIN:
            continue

        if rel_vol < REL_VOL_MIN:
            continue

        last_alerted.add(symbol)

        msg = (f"\ud83d\udd25 ${symbol} ALERT!\n"
               f"Price: ${price:.2f} | Prev Close: ${prev_close:.2f}\n"
               f"Change: {percent_change:.1f}%\n"
               f"Volume: {volume:,} | Rel Vol: {rel_vol:.2f}\n"
               f"Market Cap: ${cap:.0f}M")

        send_telegram_message(msg)


@app.route("/")
def home():
    return "Pre-market scanner online."


@app.route("/scan")
def scan():
    scan_and_alert()
    return "Scan completed."


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
