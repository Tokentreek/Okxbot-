import requests, time, os, numpy as np
from datetime import datetime
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "Long Sniper LIVE - Vik Edition"
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

def sma(arr, p): return sum(arr[-p:])/p if len(arr)>=p else None

def bollinger(closes, p=20, dev=2):
    if len(closes)<p: return None,None,None
    mid=sma(closes,p)
    std=np.std(closes[-p:])
    return mid+dev*std, mid, mid-dev*std

def rsi(prices, p=6):
    if len(prices)<p+1: return 50
    g=l=0
    for i in range(1,p+1):
        d=prices[-i]-prices[-i-1]
        if d>0: g+=d
        else: l+=abs(d)
    if l==0: return 100
    return 100-(100/(1+(g/p)/(l/p)))

def skdj(closes, highs, lows, n=9, m1=3, m2=3):
    if len(closes)<n+m1: return None,None
    rsvs=[]
    for i in range(len(closes)):
        if i<n-1: rsvs.append(50)
        else:
            hh=max(highs[i-n+1:i+1]); ll=min(lows[i-n+1:i+1])
            rsvs.append(50 if hh==ll else (closes[i]-ll)/(hh-ll)*100)
    k=sma(rsvs,m1)
    ks=[]
    for i in range(len(rsvs)):
        if i>=m1-1: ks.append(sma(rsvs[i-m1+1:i+1],m1))
    d=sma(ks,m2) if len(ks)>=m2 else None
    return k,d

def scan():
    try:
        all_t = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", timeout=10).json()['data']
        top50 = sorted([x for x in all_t if 'USDT' in x['instId'] and float(x.get('vol24h',0)or 0)>50000],
                       key=lambda x: float(x.get('last',0)or 0)/float(x.get('open24h',1)or 1), reverse=True)[:50]
    except: return

    for t in top50:
        inst=t['instId']; coin=inst.split('-')[0]
        if coin in sent and time.time()-sent[coin]<7200: continue

        try:
            for tf in ['15m','1h']:
                kl = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar={tf}&limit=100", timeout=8).json().get('data',[])
                if len(kl)<50: continue
                kl.reverse()
                closes=[float(c[4]) for c in kl]; highs=[float(c[2]) for c in kl]; lows=[float(c[3]) for c in kl]; vols=[float(c[5]) for c in kl]

                ub,mid,lb = bollinger(closes,20,2)
                r6 = rsi(closes,6)
                k,d = skdj(closes,highs,lows,9,3,3)
                if None in (lb,k,d): continue

                curr_low=lows[-1]; curr_close=closes[-1]
                vol_ratio = vols[-1]/(sum(vols[-21:-1])/20) if sum(vols[-21:-1])>0 else 0

                touch_lb = curr_low <= lb or curr_close <= lb*1.005
                rsi_os = r6 < 30
                k_os = k < 20

                if touch_lb and rsi_os and k_os:
                    entry=curr_close
                    sl=min(curr_low,lb)*0.985
                    gain_mid=(mid-entry)/entry*100

                    # YOUR CUSTOM MESSAGE
                    msg = (
                        f"Vik Long {coin}\n"
                        f"\n"
                        f"🎯 Long Sniper Found\n"
                        f"Coin: {coin} ({inst}) TF:{tf}\n"
                        f"Entry: {entry:.6f}\n"
                        f"Low: {curr_low:.6f} | LB: {lb:.6f}\n"
                        f"RSI6: {r6:.1f} | K:{k:.1f} D:{d:.1f} | Vol {vol_ratio:.1f}x\n"
                        f"SL: {sl:.6f} | TP MID: {mid:.6f} (+{gain_mid:.1f}%) | TP UB: {ub:.6f}"
                    )
                    send(msg)
                    sent[coin]=time.time()
                    break
        except: continue

if __name__=="__main__":
    send("Vik Long Sniper LIVE ✅\nScanning TOP50 Gainers - WLD 0.4586 setup\nBOLL LB + RSI6<30 + K<20")
    while True:
        scan()
        time.sleep(30)
