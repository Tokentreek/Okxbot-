import requests, time, os, math
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")

# MEMORY - stops spam
sent_coins = {}
COOLDOWN = 3600 # 60 min

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"TG Error: {e}")

def get_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
    return ema

def get_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 100
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
    print(f"[{datetime.now()}] Scanning...")
    try:
        tickers = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", timeout=10).json()
        data = tickers.get("data", [])
        usdt = [x for x in data if "USDT" in x["instId"]]
        top40 = sorted(usdt, key=lambda x: float(x.get("vol24h",0)), reverse=True)[:40]
    except Exception as e:
        print(f"Ticker error {e}")
        return

    for ticker in top40:
        instId = ticker["instId"] # e.g. STRK-USDT-SWAP
        coin = instId.split("-")[0]

        # Cooldown check
        if coin in sent_coins and time.time() - sent_coins[coin] < COOLDOWN:
            continue

        try:
            kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=5m&limit=100", timeout=10).json()
            candles = kl.get("data", [])
            if len(candles) < 60:
                continue
            candles.reverse() # oldest first
            closes = [float(c[4]) for c in candles]
            vols = [float(c[5]) for c in candles]

            close_now = closes[-1]
            rsi = get_rsi(closes)
            vol_ratio = vols[-1] / (sum(vols[-21:-1]) / 20) if sum(vols[-21:-1]) > 0 else 0

            # TREND FILTER - NEW
            ema20 = get_ema(closes, 20)
            ema50 = get_ema(closes, 50)
            ema200 = get_ema(closes, 200) if len(closes) >= 200 else get_ema(closes, 50) # fallback if not enough data

            if ema20 is None or ema50 is None or ema200 is None:
                continue

            trend_up = (close_now > ema200) and (ema20 > ema50)

            # ENTRY
            if rsi < 45 and vol_ratio > 0.8 and trend_up:
                sl = close_now * 0.97
                tp = close_now * 1.15 if vol_ratio > 2.5 else close_now * 1.06

                msg = f"🚀 TOKEN-TREK ALERT\n\nCoin: {coin} ({instId})\nPrice: {close_now:.6f}\nRSI: {rsi:.1f}\nVol: {vol_ratio:.1f}x\nTrend: EMA20>50 + Price>EMA200 ✅\n\nSL: {sl:.6f} (-3%)\nTP: {tp:.6f} (+{'15' if vol_ratio>2.5 else '6'}%)"
                send_telegram(msg)
                sent_coins[coin] = time.time()
                print(f"ALERTED {coin} RSI {rsi:.1f} VOL {vol_ratio:.1f}x TREND OK")

        except Exception as e:
            print(f"Error {instId}: {e}")
            continue

if __name__ == "__main__":
    send_telegram("✅ Tokentrek V2 LIVE - Trend Filter Added (EMA20>50 + Price>EMA200)")
    while True:
        scan()
        time.sleep(90)
