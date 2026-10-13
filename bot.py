import requests, time, os, numpy as np
from flask import Flask
import threading

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
sent = {}
last_heartbeat = 0

PRIORITY = ["DATA-USDT-SWAP", "SUI-USDT-SWAP", "SOL-USDT-SWAP", "NEAR-USDT-SWAP", "STRK-USDT-SWAP"]

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except: pass
    print(msg, flush=True)

@app.route('/')
def home():
    return "Vik Long Sniper 5/9 DUMP HUNTER LIVE ✅"

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
    if time.time() - last_heartbeat > 14400:
        send(f"Vik 5/9 Dump Hunter LIVE heartbeat ✅\n{time.strftime('%H:%M EAT')}")
        last_heartbeat = time.time()
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        data = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", headers=headers, timeout=10).json()['data']
        top80 = sorted([x for x in data if 'USDT' in x['instId'] and float(x.get('vol24h',0)or 0)>100000],
                       key=lambda x: float(x.get('vol24h',0)or 0), reverse=True)[:80]
        top_ids = [x['instId'] for x in top80]
        # PRIORITY FIRST
        scan_list = PRIORITY + top_ids
        scan_list = list(dict.fromkeys(scan_list))
    except: return

    for inst in scan_list:
        coin=inst.split('-')[0]
        if coin in sent and time.time()-sent[coin]<1800: continue # 30min cooldown for dumps
        try:
            kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1h&limit=100", headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json().get('data',[])
            if len(kl)<50: continue
            kl.reverse()
            closes=[float(c[4]) for c in kl]; highs=[float(c[2]) for c in kl]; lows=[float(c[3]) for c in kl]; vols=[float(c[5]) for c in kl]
            ub,mid,lb = bollinger(closes,20,2)
            r6 = rsi(closes,6); r6_prev = rsi(closes[:-1],6)
            k,d = skdj(closes,highs,lows,9,3,3)
            hist = macd_hist(closes)
            if None in (lb,k,d,mid): continue
            low_now=lows[-1]; close_now=closes[-1]; high_now=highs[-1]
            vol_ratio = vols[-1]/(sum(vols[-21:-1])/20) if sum(vols[-21:-1])>0 else 0
            bw = (ub-lb)/mid if mid else 0
            ll = min(lows[-9:]); hh = max(highs[-9:])
            rsv = (close_now-ll)/(hh-ll)*100 if hh!=ll else 50

            # === 5/9 DUMP CONDITIONS - LOOSER ===
            c1_lb = low_now <= lb * 1.05 # was 1.03, now 1.05 to catch DATA 0.2043 when LB 0.2033
            c2_wide = bw > 0.04
            c3_vol = vol_ratio > 1.2 # was 1.8
            c4_rsi = r6_prev < 45 or r6 < 50 # was 38/42
            c5_macd = hist[-2] <= min(hist[-20:])*0.8
            c6_low = close_now < mid * 0.99 # was 0.97
            c7_wick = (close_now - low_now) / (high_now - low_now + 1e-9) > 0.20 # was 0.25
            c8_rsv = rsv < 45 # was 35
            c9_down = close_now < closes[-4] # was -6

            score = sum([c1_lb,c2_wide,c3_vol,c4_rsi,c5_macd,c6_low,c7_wick,c8_rsv,c9_down])

            # === FIRE ON 5/9 ===
            if c1_lb and score >= 5:
                sl = lb * 0.96
                dip = (close_now/mid-1)*100
                msg = (f"🔻 DUMP ALERT {coin} S{score}/9\n\n"
                       f"Coin: {coin} TF:1h\n"
                       f"Now: {close_now:.6f} Low: {low_now:.6f}\n"
                       f"LB: {lb:.6f} MID: {mid:.6f} UB:{ub:.6f}\n"
                       f"Dip: {dip:.1f}% Vol:{vol_ratio:.1f}x BW:{bw
