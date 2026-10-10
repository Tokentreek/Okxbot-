import requests, time, os
from datetime import datetime
from flask import Flask
import threading

# --- RENDER WEB SERVER (REQUIRED) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Tokentrek V2 LIVE"
def run_web(): app.run(host='0.0.0.0', port=10000)
threading.Thread(target=run_web, daemon=True).start()
# ------------------------------------

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")

print(f"BOT TOKEN SET: {bool(TELEGRAM_BOT_TOKEN)}") # debug

sent_coins = {}
COOLDOWN = 3600

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in Render Environment!")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
        print(f"TG Response: {r.text}")
    except Exception as e:
        print(f"TG Error: {e}")

def get_ema(prices, period):
    if len(prices) < period: return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
    return ema

def get_rsi(prices, period=14):
    if len(prices) < period + 1: return 100
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = prices[-i] - prices[-i-1]
        if diff > 0: gains.append(diff)
        else: losses.append(abs(diff))
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0.001
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def scan():
    print(f"[{datetime.now()}] Scanning TOP40...")
    try:
        tickers = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", timeout=10).json()
        data = tickers.get("data", [])
        usdt = [x for x in data if "USDT" in x["instId"]]
        top40 = sorted(usdt, key=lambda x: float(x.get("vol24h",0) or 0), reverse=True)[:40]
    except Exception as e:
        print(f"Ticker error {e}"); return

    for ticker in top40:
        instId = ticker["instId"]
        coin = instId.split("-")[0]
        if coin in sent_coins and time.time() - sent_coins[coin] < COOLDOWN:
            continue
        try:
            kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=5m&limit=200", timeout=10).json()
            candles = kl.get("data", [])
            if len(candles) < 200: continue
            candles.reverse()
            closes = [float(c[4]) for c in candles]
            vols = [float(c[5]) for c in candles]
            close_now = closes[-1]
            rsi = get_rsi(closes)
            vol_ratio = vols[-1] / (sum(vols[-21:-1]) / 20) if sum(vols[-21:-1]) > 0 else 0
            ema20 = get_ema(closes, 20)
            ema50 = get_ema(closes, 50)
            ema200 = get_ema(closes, 200)
            if None in (ema20, ema50, ema200): continue
            trend_up = (close_now > ema200) and (ema20 > ema50)
            if rsi < 40 and vol_ratio > 0.8 and trend_up:
                sl = close_now * 0.97
                tp = close_now * 1.15 if vol_ratio > 2.5 else close_now * 1.06
                msg = f"🚀 TOKEN-TREK V2\nCoin: {coin} ({instId})\nPrice: {close_now:.6f}\nRSI: {rsi:.1f} Vol: {vol_ratio:.1f}x\nTrend: OK ✅\nSL: {sl:.6f} TP: {tp:.6f}"
                send_telegram(msg)
                sent_coins[coin] = time.time()
                print(f"ALERTED {coin} RSI {rsi:.1f}")
        except Exception as e:
            print(f"Error {instId}: {e}"); continue

if __name__ == "__main__":
    send_telegram("✅ Tokentrek V2 FIXED - Flask + 200 candles - LIVE NOW")
    while True:
        scan()
        time.sleep(90)
