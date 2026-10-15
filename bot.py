import requests, time, os, math
from flask import Flask
import threading

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
BAR = "15m"
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
    return "GATE LB+GREEN BOT - TOP 40 GAINERS - RSI<45 - FIXED"

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

def get_top_gainers():
    try:
        url = f"{GATE_HOST}/api/v4/futures/usdt/tickers"
        resp = requests.get(url, timeout=15).json()
        valid = []
        for t in resp:
            try:
                contract = t.get('contract', '')
                if '_USDT' not in contract:
                    continue
                if not contract.endswith('_USDT'):
                    continue
                last = float(t.get('last', 0) or 0)
                if last < 0.000001:
                    continue
                change = float(t.get('change_percentage', 0) or 0)
                vol = float(t.get('volume_24h', 0) or 0)
                valid.append((contract, change, vol))
            except:
                continue
        valid_sorted = sorted(valid, key=lambda x: x[1], reverse=True)
        top_40 = [x[0] for x in valid_sorted[:40]]
        if not top_40:
            raise Exception("empty")
        print(f"Top 40: {top_40[:5]}", flush=True)
        return top_40
    except Exception as e:
        print(f"gainers err {e}", flush=True)
        return ["BTC_USDT","ETH_USDT","SOL_USDT","ARB_USDT","UNI_USDT","SUI_USDT","WAL_USDT","PYTH_USDT","ZAMA_USDT","PUMP_USDT"]

def get_candles(contract, limit=80):
    try:
        url = f"{GATE_HOST}/api/v4/futures/usdt/candlesticks"
        params = {"contract": contract, "interval": GATE_INTERVAL, "limit": limit}
        resp = requests.get(url, params=params, timeout=15).json()
        resp = sorted(resp, key=lambda x: x['t'])
        opens = [float(c['o']) for c in resp]
        highs = [float(c['h']) for c in resp]
        lows = [float(c['l']) for c in resp]
        closes = [float(c['c']) for c in resp]
        vols = [float(c['v']) for c in resp]
        return opens, highs, lows, closes, vols
    except Exception as e:
        print(f"candle err {contract} {e}", flush=True)
        return None

def scan():
    top_gainers = get_top_gainers()
    for contract in top_gainers:
        try:
            coin = contract.split('_')[0]
            if coin in sent and time.time() - sent[coin] < 3600:
                continue
            data = get_candles(contract, 80)
            if not data:
                continue
            opens, highs, lows, closes, vols = data
            if len(closes) < 50:
                continue

            ub, mid, lb = boll(closes, 20, 2)
            if lb is None:
                continue

            close_now = closes[-1]
            open_now = opens[-1]
            low_now = lows[-1]
            prev_low = lows[-2]

            is_green = close_now > open_now
            touched_lb = (low_now <= lb*1.02) or (prev_low <= lb*1.02)
            reclaimed = close_now > lb

            if not (is_green and touched_lb and reclaimed):
                continue

            r6 = rsi_wilder(closes, 6)
            r6p = rsi_wilder(closes[:-1], 6)
            vol_ratio = vols[-1] / (sum(vols[-21:-1])/20) if sum(vols[-21:-1]) > 0 else 0
            bw = (ub-lb)/mid if mid else 0

            if r6 > 45:
                continue
            if r6p > 50:
                continue
            if vol_ratio < 1.3:
                continue
            if bw < 0.03:
                continue

            rsv_min = min(lows[-9:])
            rsv_max = max(highs[-9:])
            if rsv_max == rsv_min:
                rsv = 50
            else:
                rsv = (close_now - rsv_min) / (rsv_max - rsv_min) * 100
            if rsv > 40:
                continue

            dip = (close_now/mid-1)*100
            sl = lb*0.985
            msg = (
                f"🟢 GATE LB BOUNCE {coin} 15m\n"
                f"Top #{top_gainers.index(contract)+1} Green Reclaim\n"
                f"Now:{close_now:.5f
