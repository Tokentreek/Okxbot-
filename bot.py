import requests, time, os, numpy as np
from flask import Flask
import threading

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
BAR = os.getenv("BAR", "15m")
sent = {}
last_heartbeat = 0

PRIORITY = [
    "WAL-USDT-SWAP",
    "PYTH-USDT-SWAP",
    "GRASS-USDT-SWAP",
    "PUMP-USDT-SWAP",
    "DATA-USDT-SWAP",
    "SUI-USDT-SWAP",
    "SOL-USDT-SWAP",
    "NEAR-USDT-SWAP",
    "BTC-USDT-SWAP"
]

def send(msg):
    try:
        if TELEGRAM_BOT_TOKEN:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
                timeout=10
            )
    except Exception:
        pass
    print(msg, flush=True)

@app.route('/')
def home():
    return f"Vik Long Sniper 5/9 DUMP HUNTER LIVE - {BAR} LB - OK"

def sma(arr, p):
    if len(arr) < p:
        return None
    return sum(arr[-p:]) / p

def bollinger(c, p=20, d=2):
    if len(c) < p:
        return None, None, None
    m = sma(c, p)
    if m is None:
        return None, None, None
    s = np.std(c[-p:])
    return m + d * s, m, m - d * s

def rsi(prices, p=6):
    if len(prices) < p + 1:
        return 50
    g = 0.0
    l = 0.0
    for i in range(1, p + 1):
        dlt = prices[-i] - prices[-i - 1]
        if dlt > 0:
            g += dlt
        else:
            l += abs(dlt)
    if l == 0:
        return 100
    return 100 - (100 / (1 + (g / p) / (l / p)))

def macd_hist(closes):
    if len(closes) < 35:
        return [0] * len(closes)
    e12 = closes[0]
    e26 = closes[0]
    k12 = 2 / 13
    k26 = 2 / 27
    ema12 = []
    ema26 =
