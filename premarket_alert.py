import os
import requests
import threading
import time
from datetime import datetime
import pytz
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_API_KEY = os.getenv("API_KEY")

PREVIOUS_SYMBOLS = set()

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Penny Stock Screener is running on Render!"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)
send_telegram("✅ TEST: Render web service is LIVE and connected to Telegram.")

def get_us_stocks():
    url = f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={FINNHUB_API_KEY}"
    return requests.get(url).json()

def get_quote(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    return requests.get(url).json()

def get_metrics(symbol):
    url = f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={FINNHUB_API_KEY}"
    return requests.get(url).json()

def run_screener():
    global PREVIOUS_SYMBOLS
    try:
        stock_list = get_us_stocks()
        current_symbols = set()
        selected = []

        for stock in stock_list:
            symbol = stock.get("symbol", "")
            if "." in symbol:
                continue

            quote = get_quote(symbol)
            metric = get_metrics(symbol)
            price = quote.get("c")
            pc = quote.get("pc")
            vol = quote.get("v")
            mcap = metric.get("metric", {}).get("marketCapitalization", 0)

            if not all([price, pc, vol]):
                continue

            change = ((price - pc) / pc) * 100 if pc > 0 else 0

            if price < 5 and change > 10 and vol > 100_000 and mcap < 300:
                current_symbols.add(symbol)
                if symbol not in PREVIOUS_SYMBOLS:
                    send_telegram(
                        f"🚨 New Stock Alert 🚨\nSymbol: {symbol}\nPrice: ${price:.2f}\nChange: {change:.2f}%\nVolume: {vol:,}\nMarket Cap: ${mcap:.1f}M"
                    )
                selected.append((symbol, price, change, vol, mcap))

        # Hourly update
        now = datetime.now(pytz.timezone("US/Eastern"))
        if now.minute < 10:
            if selected:
                msg = "\n\n".join(
                    f"{s[0]}: ${s[1]:.2f} | {s[2]:.1f}% | Vol: {s[3]:,} | MC: ${s[4]:.1f}M"
                    for s in selected
                )
                send_telegram(f"📊 Hourly Update ({now.strftime('%I:%M %p')} EST):\n\n{msg}")
            else:
                send_telegram(f"📊 Hourly Update ({now.strftime('%I:%M %p')} EST): No matching stocks.")

        PREVIOUS_SYMBOLS.clear()
        PREVIOUS_SYMBOLS.update(current_symbols)

    except Exception as e:
        print("Error:", str(e))


def background_loop():
    while True:
        now = datetime.now(pytz.timezone("US/Eastern"))
        if 4 <= now.hour < 9:
            run_screener()
        else:
            print("Outside trading hours, sleeping longer...")
        time.sleep(600)  # Run every 10 minutes

# Start background thread
threading.Thread(target=background_loop, daemon=True).start()

# Start Flask app to keep port open
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
test: telegram connection from Render
