import requests, time, os, math
from flask import Flask
import threading

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
sent = {}
GATE_HOST = "https://api.gateio.ws"

def send(m):
    try:
        if TOKEN:
            url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
            requests.post(url, json={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass
    print(m, flush=True)

@app.route('/')
def home():
    return "GATE BOT V5 OK"

def sma(a, p):
    if len(a) < p:
        return None
    return sum(a[-p:]) / p

def boll(c, p=20, d=2):
    if len(c) < p:
        return None, None, None
    m = sma(c, p)
    var = sum((x - m) ** 2 for x in c[-p:]) / p
    s = math.sqrt(var)
    return m + d * s, m, m - d * s

def rsi_wilder(prices, p=6):
    if len(prices) < p + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    if len(gains) < p:
        return 50
    ag = sum(gains[-p:]) / p
    al = sum(losses[-p:]) / p
    if al == 0:
        return 100
    rs = ag / al
    return 100 - (100 / (1 + rs))

def get_movers():
    try:
        url = GATE_HOST + "/api/v4/futures/usdt/tickers"
        resp = requests.get(url, timeout=15).json()
        valid = []
        for t in resp:
            contract = t.get('contract', '')
            if not contract.endswith('_USDT'):
                continue
            last = float(t.get('last', 0) or 0)
            if last < 0.000001:
                continue
            change = float(t.get('change_percentage', 0) or 0)
            valid.append((contract, change))
        gainers = sorted(valid, key=lambda x: x[1], reverse=True)
        losers = sorted(valid, key=lambda x: x[1])
        top_g = []
        top_l = []
        for i in range(40):
            if i < len(gainers):
                top_g.append(gainers[i][0])
            if i < len(losers):
                top_l.append(losers[i][0])
        combined = []
        for c in top_g + top_l:
            if c not in combined:
                combined.append(c)
        print("Movers ok", flush=True)
        return combined, top_g, top_l
    except Exception as e:
        print("movers err", flush=True)
        return ["BTC_USDT", "ETH_USDT", "SOL_USDT"], [], []

def get_candles(contract):
    try:
        url = GATE_HOST + "/api/v4/futures/usdt/candlesticks"
        params = {"contract": contract, "interval": "15m", "limit": 80}
        resp = requests.get(url, params=params, timeout=15).json()
        resp = sorted(resp, key=lambda x: x['t'])
        o = []
        h = []
        l = []
        c = []
        v = []
        for x in resp:
            o.append(float(x['o']))
            h.append(float(x['h']))
            l.append(float(x['l']))
            c.append(float(x['c']))
            v.append(float(x['v']))
        return o, h, l, c, v
    except Exception as e:
        print("candle err", flush=True)
        return None

def scan():
    all_coins, gainers, losers = get_movers()
    for contract in all_coins:
        try:
            coin = contract.split('_')[0]
            if coin in sent:
                if time.time() - sent[coin] < 3600:
                    continue
            data = get_candles(contract)
            if data is None:
                continue
            opens = data[0]
            highs = data[1]
            lows = data[2]
            closes = data[3]
            vols = data[4]
            if len(closes) < 50:
                continue
            ub_mid_lb = boll(closes, 20, 2)
            ub = ub_mid_lb[0]
            mid = ub_mid_lb[1]
            lb = ub_mid_lb[2]
            if lb is None:
                continue
            close_now = closes[-1]
            open_now = opens[-1]
            low_now = lows[-1]
            prev_low = lows[-2]
            is_green = close_now > open_now
            touched = False
            if low_now <= lb * 1.02:
                touched = True
            if prev_low <= lb * 1.02:
                touched = True
            reclaimed = close_now > lb
            if not is_green:
                continue
            if not touched:
                continue
            if not reclaimed:
                continue
            r6 = rsi_wilder(closes, 6
