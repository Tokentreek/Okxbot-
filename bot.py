import requests, time, os, numpy as np
from flask import Flask
import threading

app = Flask(__name__)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
sent = {}
last_heartbeat = 0
PRIORITY = ["DATA", "STRK", "GRASS", "NEAR", "SOL", "BUNKER", "MAGIC", "SUI"]

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except:
        pass
    print(msg, flush=True)

@app.route('/')
def home():
    return "Vik PRIORITY 4/9 LIVE OK"

def sma(arr,p):
    if len(arr) < p:
        return None
    return sum(arr[-p:]) / p

def bollinger(c,p=20,d=2):
    if len(c) < p:
        return None,None,None
    m = sma(c,p)
    s = np.std(c[-p:])
    return m+d*s, m, m-d*s

def rsi(prices,p=6):
    if len(prices) < p+1:
        return 50
    g=0
    l=0
    for i in range(1,p+1):
        dlt = prices[-i] - prices[-i-1]
        if dlt>0:
            g+=dlt
        else:
            l+=abs(dlt)
    if l==0:
        return 100
    return 100 - (100 / (1 + (g/p)/(l/p)))

def macd_hist(closes):
    if len(closes) < 35:
        return [0]*len(closes)
    e12 = closes[0]
    e26 = closes[0]
    ema12=[]
    ema26=[]
    for c in closes:
        e12 = c*0.1538 + e12*0.8462
        e26 = c*0.0740 + e26*0.9260
        ema12.append(e12)
        ema26.append(e26)
    dif = [a-b for a,b in zip(ema12,ema26)]
    ed = dif[0]
    dea=[]
    for d in dif:
        ed = d*0.2 + ed*0.8
        dea.append(ed)
    return [d-e for d,e in zip(dif,dea)]

def skdj(closes,highs,lows,n=9,m1=3,m2=3):
    rsvs=[]
    for i in range(len(closes)):
        if i < n-1:
            rsvs.append(50)
        else:
            hh = max(highs[i-n+1:i+1])
            ll = min(lows[i-n+1:i+1])
            if hh==ll:
                rsvs.append(50)
            else:
                rsvs.append((closes[i]-ll)/(hh-ll)*100)
    k = sma(rsvs,m1)
    ks=[]
    for i in range(m1-1,len(rsvs)):
        ks.append(sma(rsvs[i-m1+1:i+1],m1))
    d = sma(ks,m2) if len(ks)>=m2 else None
    return k,d

def scan():
    global last_heartbeat
    if time.time() - last_heartbeat > 1800:
        send("Vik PRIORITY LIVE heartbeat 4/9")
        last_heartbeat = time.time()
    try:
