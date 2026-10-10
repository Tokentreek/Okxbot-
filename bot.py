import os, time, requests, threading
from flask import Flask
from datetime import datetime

# --- FAKE WEB SERVER FOR RENDER ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Tokentrek V2 LIVE - MERL alert worked!"
def run_web():
    app.run(host='0.0.0.0', port=10000)
threading.Thread(target=run_web, daemon=True).start()

# --- YOUR BOT CONFIG ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
sent_coins = {}
COOLDOWN = 3600

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except: pass

def get_ema(prices, period):
    if len(prices) < period: return None
    k = 2/(period+1)
    ema = sum(prices[:period])/period
    for p in prices[period:]:
        ema = p*k + ema*(1-k)
    return ema

def get_rsi(prices, period=14):
    if len(prices) < period+1: return 100
    gains=[]; losses=[]
    for i in range(1, period+1):
        d = prices[-i]-prices[-i-1]
        (gains if d>0 else losses).append(abs(d))
    avg_g = sum(gains)/period if gains else 0
    avg_l = sum(losses)/period if losses else 0.001
    if avg_l==0: return 100
    return 100-(100/(1+avg_g/avg_l))

def scan():
    try:
        tickers = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", timeout=10).json().get("data",[])
        usdt = [x for x in tickers if "USDT" in x["instId"]]
        top40 = sorted(usdt, key=lambda x: float(x.get("vol24h",0)), reverse=True)[:40]
    except: return

    for t in top40:
        instId = t["instId"]
        coin = instId.split("-")[0]
        if coin in sent_coins and time.time()-sent_coins[coin] < COOLDOWN: continue
        try:
            kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=5m&limit=200", timeout=10).json().get("data",[])
            if len(kl)<60: continue
            kl.reverse()
            closes = [float(c[4]) for c in kl]
            vols = [float(c[5]) for c in kl]
            close_now = closes[-1]
            rsi = get_rsi(closes)
            vol_ratio = vols[-1]/(sum(vols[-21:-1])/20) if sum(vols[-21:-1])>0 else 0
            ema20 = get_ema(closes,20)
            ema50 = get_ema(closes,50)
            ema200 = get_ema(closes,200) if len(closes)>=200 else ema50
            if not ema20 or not ema50 or not ema200: continue
            trend_up = (close_now > ema200) and (ema20 > ema50)

            if rsi < 40 and vol_ratio > 0.8 and trend_up:
                sl = close_now*0.97
                tp = close_now*1.15 if vol_ratio>2.5 else close_now*1.06
                msg = f"🚀 TOKENTREK V2\n{instId} RSI {rsi:.2f} < 40 | Vol {vol_ratio:.1f}x Top40\nPrice: {close_now}\nTrend: EMA20>50 & Price>EMA200 ✅\nSL {sl:.5f} TP {tp:.5f}"
                send_tg(msg)
                sent_coins[coin]=time.time()
                print(f"ALERT {coin} RSI {rsi:.1f}")
        except Exception as e:
            print(e); continue

if __name__ == "__main__":
    send_tg("✅ Tokentrek V2 FIXED - Port + Trend Filter + Cooldown LIVE")
    while True:
        print(f"[{datetime.now()}] Scanning TOP40...")
        scan()
        time.sleep(90)
