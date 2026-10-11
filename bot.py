import requests, time, os, numpy as np
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "Long Sniper 1h 9-COND LIVE"
def run_web(): app.run(host='0.0.0.0', port=10000)
threading.Thread(target=run_web, daemon=True).start()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
sent = {}
last_heartbeat = time.time()
last_signals = 0

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except: pass
    print(msg)

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
    global last_signals
    found = 0
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        data = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", headers=headers, timeout=10).json()['data']
        top50 = sorted([x for x in data if 'USDT' in x['instId'] and float(x.get('vol24h',0)or 0)>100000],
                       key=lambda x: float(x.get('vol24h',0)or 0), reverse=True)[:80]
    except: return 0

    for t in top50:
        inst=t['instId']; coin=inst.split('-')[0]
        if coin in sent and time.time()-sent[coin]<3600*4: continue

        try:
            headers={"User-Agent":"Mozilla/5.0"}
            kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1h&limit=100", headers=headers, timeout=10).json().get('data',[])
            if len(kl)<50: continue
            kl.reverse()
            closes=[float(c[4]) for c in kl]; highs=[float(c[2]) for c in kl]; lows=[float(c[3]) for c in kl]; vols=[float(c[5]) for c in kl]

            ub,mid,lb = bollinger(closes,20,2)
            r6 = rsi(closes,6)
            r6_prev = rsi(closes[:-1],6)
            k,d = skdj(closes,highs,lows,9,3,3)
            hist = macd_hist(closes)
            if None in (lb,k,d,mid): continue

            low_now=lows[-1]; close_now=closes[-1]; high_now=highs[-1]
            vol_ratio = vols[-1]/(sum(vols[-21:-1])/20) if sum(vols
