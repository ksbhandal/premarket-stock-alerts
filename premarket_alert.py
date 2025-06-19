import os
import requests
from datetime import datetime
from flask import Flask
import pytz
import time
import threading

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

# To store last known %change per stock
last_seen_change = {}


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

    now_str = datetime.now(TIMEZONE).strftime("%I:%M %p EST")
    symbols = fetch_stocks()
    found_stocks = []

    for symbol in symbols:
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

        change_diff = ""
        last_change = last_seen_change.get(symbol)
        if last_change is not None:
            delta = percent_change - last_change
            if abs(delta) > 1:
                change_diff = f" (Δ {delta:+.1f}%)"

        last_seen_change[symbol] = percent_change

        msg = (f"🔥 ${symbol} ALERT @ {now_str}
"
               f"Price: ${price:.2f} | Prev Close: ${prev_close:.2f}
"
               f"Change: {percent_change:.1f}%{change_diff}
"
               f"Volume: {volume:,} | Rel Vol: {rel_vol:.2f}
"
               f"Market Cap: ${cap:.0f}M")

        found_stocks.append(msg)

    if found_stocks:
        send_telegram_message(f"🔍 Pre-market Scan @ {now_str}\n\n" + "\n\n".join(found_stocks))
    else:
        send_telegram_message(f"🔍 Pre-market Scan @ {now_str}: No stocks found.")


@app.route("/")
def home():
    return "Pre-market scanner online."


@app.route("/scan")
def scan():
    scan_and_alert()
    return "Scan completed."


if __name__ == '__main__':
    def ping_self():
        while True:
            try:
                requests.get("https://premarket-stock-alerts.onrender.com/scan")
            except:
                pass
            time.sleep(600)  # every 10 minutes

    threading.Thread(target=ping_self).start()
    app.run(host="0.0.0.0", port=10000)
