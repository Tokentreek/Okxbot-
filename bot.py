import requests
import time
import os
import math
from flask import Flask
import threading

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID","5042879835")
PORT = int(os.getenv("PORT","10000"))
sent = {}
GATE_HOST = "https://api.gateio.ws"

def send(m):
    try:
        if TOKEN:
            u = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
            requests.post(u, json={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass
    print(m, flush=True)

@app.route('/')
def home():
    return "GATE V6 OK - 80 MOVERS"

def sma(a,p):
    if len(a) < p:
        return None
    s = 0
    for x in a[-p:]:
        s = s + x
    return s / p

def boll(c):
    p = 20
    d = 2
    if len(c) < p:
        return None,None,None
    m = sma(c,p)
    var = 0
    for x in c[-p:]:
        var = var + (x - m) * (x - m)
    var = var / p
    s = math.sqrt(var)
    return m + d * s, m, m - d * s

def rsi_wilder(prices):
    p = 6
    if len(prices) < p + 1:
        return 50
    gains = []
    losses = []
    for i in range(1,len(prices)):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    if len(gains) < p:
