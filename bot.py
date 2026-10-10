import requests
import time
import pandas as pd
from datetime import datetime
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# OKX SWAP - perpetual futures

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_rsi(candles, period=14):
    closes = [float(c[4]) for c in candles]
    df = pd.Series(closes)
    delta = df.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 2)

def get_top_scan():
    # FIX 1: LIVE TOP 40 by 24h Volume - not % gainer
    url = "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
    try:
        res = requests.get(url, timeout=15).json()
        data = res.get('data', [])
        # Filter only USDT pairs
        usdt_pairs = [d for d in data if d['instId'].endswith('-USDT-SWAP')]
        # Sort by vol24h LIVE - biggest volume now
        top40 = sorted(usdt_pairs, key=lambda x: float(x.get('vol24h', 0) or 0), reverse=True)[:40]
        return top40
    except Exception as e:
        print(f"Top scan error: {e}")
        return []

def get_candles(instId):
    url = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=15m&limit=100"
    try:
        res = requests.get(url, timeout=10).json()
        return res.get('data', [])[::-1] # reverse to old->new
    except:
        return []

def main_loop():
    send_telegram("🟢 *BOT STARTED*\nTOP 40 LIVE VOL | RSI<40 | VOL>0.8x\nScanning every 5 mins")

    while True:
        try:
            top40 = get_top_scan()
            if not top40:
                time.sleep(60)
                continue

            # Build TOP5 msg for header
            top5_text = ""
            for i, t in enumerate(top40[:5]):
                inst = t['instId'].replace('-USDT-SWAP','')
                change = float(t.get('vol24h',0)) # or use
