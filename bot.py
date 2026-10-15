import requests, time, os, math
from flask import Flask
import threading

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
sent = {}

GATE_INTERVAL = "15m"
GATE_HOST = "https://api.gateio.ws"

def send(m):
    try:
        if TOKEN:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass
    print(m, flush=True)

@app.route('/')
def home():
    return "GATE LB+GREEN - TOP 40 GAINERS + TOP 40 LOSERS - RSI<45"

def sma(a,p):
    if len(a) < p:
        return None
    return sum(a[-p:]) / p

def boll(c,p=20,d=2):
    if len(c) < p:
        return None,None,None
    m = sma(c,p)
    var = sum((x-m)**2 for x in c[-p:]) / p
    s = math.sqrt(var)
    return m+d*s, m, m-d*s

def rsi_wilder(prices,p=6):
    if len(prices) < p+1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(prices)):
        dlt = prices[i] - prices[i-1]
        if dlt > 0:
            gains.append(dlt)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(dlt))
    if len(gains) < p:
        return 50
    avg_gain = sum(gains[-p:]) / p
    avg_loss = sum(losses[-p:]) / p
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

def get_top_movers():
    try:
        url = f"{GATE_HOST}/api/v4/futures/usdt/tickers"
        resp = requests.get(url, timeout=15).json()
        valid = []
        for t in resp:
            try:
                contract = t.get('contract', '')
                if not contract.endswith('_USDT'):
                    continue
                last = float(t.get('last', 0) or 0)
                if last < 0.000001:
                    continue
                change = float(t.get('change_percentage', 0) or 0)
                vol = float(t.get('volume_24h', 0) or 0)
                # filter low vol
                if vol < 1000:
                    continue
                valid.append((contract, change))
            except:
                continue

        # Top 40 Gainers (highest %)
        gainers_sorted = sorted(valid, key=lambda x: x[1], reverse=True)
        top_gainers = [x[0] for x in gainers_sorted[:40]]

        # Top 40 Losers (lowest %)
        losers_sorted = sorted(valid, key=lambda x: x[1])
        top_losers = [x[0] for x in losers_sorted[:40]]

        # Combine, remove duplicates
        combined = list(dict.fromkeys(top_gainers + top_losers))
        print(f"Gainers: {top_gainers[:3]} | Losers: {top_losers[:3]} | Total: {len(combined)}", flush=True)
        return combined, top_gainers, top_losers
    except Exception as e:
        print(f"movers err {e}", flush=True)
        fallback =
