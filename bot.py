import requests, time, os, numpy as np
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "Long Sniper 1h STRICT LIVE"
def run_web(): app.run(host='0.0.0.0', port=10000)
threading.Thread(target=run_web, daemon=True).start()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
sent = {}

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
    try:
        data = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", timeout=10).json()['data']
        top50 = sorted([x for x in data if 'USDT' in x['instId'] and float(x.get('vol24h',0)or 0)>100000],
                       key=lambda x: float(x.get('last',0)or 0)/float(x.get('open24h',1)or 1), reverse=True)[:50]
    except: return

    for t in top50:
        inst=t['instId']; coin=inst.split('-')[0]
        if coin in sent and time.time()-sent[coin]<3600*4: continue # 4h cooldown - stops spam

        try:
            # 1h ONLY - no 15m
            kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1h&limit=100", timeout=8).json().get('data',[])
            if len(kl)<50: continue
            kl.reverse()
            closes=[float(c[4]) for c in kl]; highs=[float(c[2]) for c in kl]; lows=[float(c[3]) for c in kl]; vols=[float(c[5]) for c in kl]

            ub,mid,lb = bollinger(closes,20,2)
            r6 = rsi(closes,6)
            k,d = skdj(closes,highs,lows,9,3,3)
            if None in (lb,k,d): continue

            low_now=lows[-1]; close_now=closes[-1]
            vol_ratio = vols[-1]/(sum(vols[-21:-1])/20) if sum(vols[-21:-1])>0 else 0

            # STRICT WLD 0.4586 FILTER
            touch_lb = low_now <= lb * 1.01 # must really touch LB
            deep_dip = close_now < mid * 0.92 # price must be 8% below BOLL mid (real dump, not 1% pullback)
            rsi_os = r6 < 30 # strict 30 like you asked
            k_os = k < 20 # strict 20 like you asked
            vol_ok = vol_ratio > 0.9 # avoid 0.1x low vol fakeouts you got

            if touch_lb and deep_dip and rsi_os and k_os and vol_ok:
                sl = lb * 0.96
                msg = f"Vik Long {coin}\n\n🎯 Long Sniper - 1h REAL BOTTOM\nCoin: {coin} TF:1h\nEntry: {close_now:.6f} Low: {low_now:.6f}\nLB: {lb:.6f} MID: {mid:.6f}\nDip: {(close_now/mid-1)*100:.1f}% below MID\nRSI6: {r6:.1f} K:{k:.1f} D:{d:.1f} Vol:{vol_ratio:.1f}x\nSL: {sl:.6f}\nTP MID: {mid:.6f}\nThis is WLD 0.4586 type, not CHIP 0.05227 pullback"
                send(msg)
                sent[coin]=time.time()

        except: continue

if __name__=="__main__":
    send("Vik Long Sniper 1h STRICT LIVE ✅\nFixed: No more 15m CHIP 0.05227 alerts\nOnly real bottoms like WLD 0.4586 / CHIP 0.04717\nNeed: LB Touch + 8% below MID + RSI6<30 + K<20 + Vol>0.9x")
    while True:
        scan()
        time.sleep(120)
