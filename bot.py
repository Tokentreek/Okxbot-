import requests
import time
import pandas as pd
from datetime import datetime
import os
import threading
from flask import Flask

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# OKX SWAP - perpetual futures

# --- FAKE WEBSITE FOR RENDER FREE PLAN ---
app = Flask(__name__)
@app.route('/')
def home():
    return "🟢 BOT LIVE - OKX SWAP RSI BOT"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_rsi(candles, period=14):
    closes = [float(c[4]) for c in candles]
    df = pd.Series(closes)
    delta = df.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 2)

def bot_loop():
    send_telegram("🟢 BOT STARTED TOP 40 LIVE VOL | RSI<40 | SWAP")
    while True:
        try:
            # get top 40 swap volume
            url = "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
            data = requests.get(url, timeout=15).json().get('data', [])
            top = sorted(data, key=lambda x: float(x.get('vol24h',0)), reverse=True)[:40]

            for t in top:
                sym = t['instId']
                # get candles
                c_url = f"https://www.okx.com/api/v5/market/candles?instId={sym}&bar=1H&limit=100"
                candles = requests.get(c_url, timeout=15).json().get('data', [])
                if not candles:
                    continue
                candles = list(reversed(candles))
                rsi = get_rsi(candles)
                if rsi < 40:
                    send_telegram(f"📉 {sym} RSI {rsi} < 40 | SWAP Vol Top40")
                time.sleep(1)
            time.sleep(300)
        except Exception as e:
            print(f"Error {e}")
            time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot_loop()
