import requests, time, os, math
from flask import Flask
import threading

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
BAR = "15m"
sent = {}

# Gate.io uses 15m format
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
    return "GATE LB+GREEN BOT - TOP 40 GAINERS - RSI<45"

def sma(a,p):
    if len(a)<p: return None
    return sum(a[-p:])/p

def boll(c,p=20,d=2):
    if len(c)<p: return None,None,None
    m=sma(c,p)
    var=sum((x-m)**2 for x in c[-p:])/p
    s=math.sqrt(var)
    return m+d*s, m, m-d*s

def rsi_wilder(prices,p=6):
    if len(prices)<p+1: return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i-1]
        gains.append(max(d,0))
        losses.append(max(-d,0))
    if len(gains) < p: return 50
    avg_gain = sum(gains[-p:])/p
    avg_loss = sum(losses[-p:])/p
    if avg_loss == 0: return 100
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

def get_top_gainers():
    """Get Top 40 Gainers from Gate.io USDT Futures"""
    try:
        url = f"{GATE_HOST}/api/v4/futures/usdt/tickers"
        headers = {"Accept": "application/json"}
        resp = requests.get(url, headers=headers, timeout=15).json()
        # resp is list of tickers
        valid = []
        for t in resp:
            try:
                contract = t.get('contract','') # e.g. BTC_USDT
                if not contract.endswith('_USDT'): continue
