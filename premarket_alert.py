import os
import requests
from datetime import datetime
import pytz
from flask import Flask

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Pre-market screener is running."

@app.route("/scan")
def run_scan():
    send_telegram("🔄 Pre-market scan triggered.")
    run_screener()
    return "✅ Pre-market scan completed."

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        response = requests.post(url, data=payload)
        print("📨 Telegram:", response.status_code, response.text)
    except Exception as e:
        print("❌ Telegram error:", str(e))

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
    now = datetime.now(pytz.timezone("US/Eastern"))
    print(f"⏱ Scan triggered at {now.strftime('%Y-%m-%d %I:%M:%S %p EST')}")

    if not (4 <= now.hour < 9 or (now.hour == 9 and now.minute <= 0)):
        print("⚠️ Outside pre-market hours, skipping scan.")
        return

    try:
        stock_list = get_us_stocks()
        print(f"📦 Retrieved {len(stock_list)} symbols from Finnhub.")
    except Exception as e:
        print("❌ Failed to fetch stock list:", e)
        send_telegram("❌ ERROR: Could not fetch stock list.")
        return

    matches = 0

    for stock in stock_list:
        symbol = stock.get("symbol", "")
        if "." in symbol:
            continue

        try:
            quote = get_quote(symbol)
            metric = get_metrics(symbol)

            price = quote.get("c")
            pc = quote.get("pc")
            vol = quote.get("v")
            mcap = metric.get("metric", {}).get("marketCapitalization", 0)

            if not all([price, pc, vol]):
                print(f"⚠️ Skipped {symbol}: Missing price/vol.")
                continue

            change = ((price - pc) / pc) * 100 if pc > 0 else 0

            if price < 5 and change > 10 and vol > 100_000 and mcap < 300:
                print(f"🚀 Match: {symbol} | ${price:.2f} | {change:.2f}% | Vol: {vol:,}")
                send_telegram(
                    f"🚀 Pre-market Alert\n"
                    f"Symbol: {symbol}\n"
                    f"Price: ${price:.2f}\n"
                    f"% Change: {change:.2f}%\n"
                    f"Volume: {vol:,}\n"
                    f"Market Cap: ${mcap:.1f}M"
                )
                matches += 1
        except Exception as e:
            print(f"❌ Error for {symbol}:", str(e))

    if matches == 0:
        send_telegram("🔍 Scan complete — no stocks matched pre-market criteria.")
    else:
        print(f"✅ Scan complete. {matches} stocks matched.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
