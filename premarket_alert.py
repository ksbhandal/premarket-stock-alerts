import os
import requests
from datetime import datetime, timedelta
import pytz

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_API_KEY = os.getenv("API_KEY")

PREVIOUS_SYMBOLS = set()

def get_us_stocks():
    url = f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={FINNHUB_API_KEY}"
    res = requests.get(url)
    return res.json()

def get_quote(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    res = requests.get(url)
    return res.json()

def get_metrics(symbol):
    url = f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={FINNHUB_API_KEY}"
    res = requests.get(url)
    return res.json()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

def run_screener():
    global PREVIOUS_SYMBOLS
    timezone = pytz.timezone("US/Eastern")
    now = datetime.now(timezone)

    stock_list = get_us_stocks()
    selected = []
    current_symbols = set()

    for stock in stock_list:
        symbol = stock.get("symbol", "")
        if "." in symbol:  # Skip weird symbols like BRK.A
            continue

        try:
            quote = get_quote(symbol)
            metric = get_metrics(symbol)

            price = quote.get("c")
            pc = quote.get("pc")
            vol = quote.get("v")
            market_cap = metric.get("metric", {}).get("marketCapitalization", 0)

            if not all([price, pc, vol]):
                continue

            price_change = ((price - pc) / pc) * 100 if pc > 0 else 0

            if price < 5 and price_change > 10 and vol > 100_000 and market_cap < 300:
                selected.append((symbol, price, price_change, vol, market_cap))
                current_symbols.add(symbol)

                if symbol not in PREVIOUS_SYMBOLS:
                    msg = (
                        f"🚨 New Penny Stock Alert 🚨\n"
                        f"Symbol: {symbol}\n"
                        f"Price: ${price:.2f}\n"
                        f"Change: {price_change:.2f}%\n"
                        f"Volume: {vol:,}\n"
                        f"Market Cap: ${market_cap:.1f}M"
                    )
                    send_telegram(msg)

        except Exception as e:
            continue

    # Hourly update
    if now.minute % 60 == 0:
        if selected:
            full = "\n\n".join(
                f"{s[0]}: ${s[1]:.2f} | {s[2]:.2f}% | Vol: {s[3]:,} | MC: ${s[4]:.1f}M"
                for s in selected
            )
            send_telegram(f"📊 Hourly Update ({now.strftime('%I:%M %p')} EST):\n\n{full}")
        else:
            send_telegram(f"📊 Hourly Update ({now.strftime('%I:%M %p')} EST): No stocks matched.")

    PREVIOUS_SYMBOLS = current_symbols

if __name__ == "__main__":
    run_screener()
