import requests, time, os, numpy as np
from flask import Flask
import threading

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
sent = {}
last_heartbeat = 0

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Telegram fail: {e}", flush=True)
    print(msg, flush=True)

@app.route('/')
def home():
    return "Vik Long Sniper 1h 9-COND LIVE ✅ 5/9 ENTRY"

def sma(arr,p): return sum(arr[-p:])/p if len(arr)>=p else None
def bollinger(c,p=20,d=2):
    if len(c)<p: return None,None,None
    m=sma(c,p); s=np.std(c[-p:]); return m+d*s, m, m-d*s
def rsi(prices,p=6):
    if len(prices)<p+1: return 50
    g=l=0
    for i in range(1,p+1):
        dlt=prices[-i]-prices[-i-1]
        if dlt>0: g+=dlt
        else: l+=abs(dlt)
    return 100 if l==0 else 100-(100/(1+(g/p)/(l/p)))
def macd_hist(closes):
    if len(closes)<35: return [0]*len(closes)
    e12=closes[0]; e26=closes[0]
    k12=2/13; k26=2/27
    ema12=[]; ema26=[]
    for c in closes:
        e12=c*k12+e12*(1-k12); e26=c*k26+e26*(1-k26)
        ema12.append(e12); ema26.append(e26)
    dif=[a-b for a,b in zip(ema12,ema26)]
    ed=dif[0]; k9=2/10; dea=[]
    for d in dif:
        ed=d*k9+ed*(1-k9); dea.append(ed)
    return [d-e for d,e in zip(dif,dea)]
def skdj(closes,highs,lows,n=9,m1=3,m2=3):
    rsvs=[]
    for i in range(len(closes)):
        if i<n-1: rsvs.append(50)
        else:
            hh=max(highs[i-n+1:i+1]); ll=min(lows[i-n+1:i+1])
            rsvs.append(50 if hh==ll else (closes[i]-ll)/(hh-ll)*100)
    k=sma(rsvs,m1)
    ks=[sma(rsvs[i-m1+1:i+1],m1) for i in range(m1-1,len(rsvs))]
    d=sma(ks,m2) if len(ks)>=m2 else None
    return k,d

def scan():
    global last_heartbeat
    if time.time() - last_heartbeat > 1800:
        send(f"Vik LIVE heartbeat ✅ {time.strftime('%H:%M EAT')} scanning 5/9")
        last_heartbeat = time.time()
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        data = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", headers=headers, timeout=10).json()['data']
        top = sorted([x for x in data if 'USDT' in x['instId'] and float(x.get('vol24h',0)or 0)>50000],
                       key=lambda x: float(x.get('vol24h',0)or 0), reverse=True)[:80]
        print(f"--- SCAN {time.strftime('%H:%M:%S')} {len(top)} coins ---", flush=True)
    except Exception as e:
        print(f"Tickers error: {e}", flush=True); return

    best_score=0; best_coin=""
    for t in top:
        inst=t['instId']; coin=inst.split('-')[0]
        if coin in sent and time.time()-sent[coin]<14400: continue
        try:
            kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1h&limit=100", headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json().get('data',[])
            if len(kl)<50: continue
            kl.reverse()
            closes=[float(c[4]) for c in kl]; highs=[float(c[
