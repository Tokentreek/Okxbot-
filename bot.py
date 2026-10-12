import requests, time, os, numpy as np
from flask import Flask
import threading
app = Flask(__name__)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
sent = {}
PRIORITY = ["DATA","STRK","GRASS","NEAR","SOL","BUNKER","MAGIC","SUI"]
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
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        r = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", headers=headers, timeout=10)
        data = r.json()['data']
        all_coins = [x for x in data if 'USDT' in x['instId']]
        top = sorted([x for x in all_coins if float(x.get('vol24h',0) or 0)>20000], key=lambda x: float(x.get('vol24h',0) or 0), reverse=True)[:100]
        print(f"SCAN {len(top)}", flush=True)
    except Exception as e:
        print(f"Tickers error {e}", flush=True)
        return
    for coin_name in PRIORITY:
        try:
            match = None
            for x in top:
                if coin_name in x['instId']:
                    match = x
                    break
            if match is None:
                continue
            inst = match['instId']
            coin = inst.split('-')[0]
            if coin in sent and time.time()-sent[coin] < 7200:
                continue
            kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1h&limit=100", headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json().get('data',[])
            if len(kl) < 50:
                continue
            kl.reverse()
            closes = [float(c[4]) for c in kl]
            highs = [float(c[2]) for c in kl]
            lows = [float(c[3]) for c in kl]
            vols = [float(c[5]) for c in kl]
            ub,mid,lb = bollinger(closes,20,2)
            if lb is None:
                continue
            r6 = rsi(closes,6)
            r6_prev = rsi(closes[:-1],6)
            k,d = skdj(closes,highs,lows,9,3,3)
            if k is None or d is None:
                continue
            hist = macd_hist(closes)
            low_now = lows[-1]
            close_now = closes[-1]
            high_now = highs[-1]
            avg_vol = sum(vols[-21:-1])/20
            vol_ratio = vols[-1]/avg_vol if avg_vol>0 else 0
            bw = (ub-lb)/mid if mid else 0
            ll = min(lows[-9:])
            hh = max(highs[-9:])
            rsv = 50 if hh==ll else (close_now-ll)/(hh-ll)*100
            c1 = 1 if low_now <= lb*1.05 else 0
            c2 = 1 if bw > 0.02 else 0
            c3 = 1 if vol_ratio > 1.2 else 0
            c4 = 1 if r6_prev < 45 or r6 < 50 else 0
            c5 = 1 if hist[-1] > hist[-2] else 0
            c6 = 1 if close_now < mid*0.99 else 0
            c7 = 1 if (close_now-low_now)/(high_now-low_now+1e-9) > 0.15 else 0
            c8 = 1 if rsv < 50 else 0
            c9 = 1 if close_now < closes[-3] else 0
            score = c1+c2+c3+c4+c5+c6+c7+c8+c9
            if score >= 4 and c1==1:
                sl = lb*0.94
                msg = f"PRIORITY {coin} Score {score}/9 Entry {close_now} LB {lb} MID {mid} Vol {vol_ratio:.1f}x RSI {r6:.0f} {inst}"
                send(msg)
                sent[coin]=time.time()
        except Exception as e:
            print(f"err {e}", flush=True)
            continue
    print("Done", flush=True)
def bot_loop():
    send("Vik PRIORITY LIVE 4/9")
    while True:
        scan()
        time.sleep(45)
threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host='0.0.0.0', port=PORT)
