import requests, time, os
from flask import Flask
import threading, math

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
BAR = "15m"
sent = {}
last_hb = 0

PRIORITY = ["WAL-USDT-SWAP","PYTH-USDT-SWAP","GRASS-USDT-SWAP","PUMP-USDT-SWAP","DATA-USDT-SWAP","SUI-USDT-SWAP","SOL-USDT-SWAP","NEAR-USDT-SWAP"]

def send(m):
    try:
        if TOKEN:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass
    print(m, flush=True)

@app.route('/')
def home():
    return f"LIVE {BAR} OK"

def sma(a,p):
    if len(a)<p:
        return None
    return sum(a[-p:])/p

def boll(c,p=20,d=2):
    if len(c)<p:
        return None,None,None
    m=sma(c,p)
    if m is None:
        return None,None,None
    var=sum((x-m)**2 for x in c[-p:])/p
    s=math.sqrt(var)
    return m+d*s, m, m-d*s

def rsi(prices,p=6):
    if len(prices)<p+1:
        return 50
    g=0
    l=0
    for i in range(1,p+1):
        dlt=prices[-i]-prices[-i-1]
        if dlt>0:
            g+=dlt
        else:
            l+=abs(dlt)
    if l==0:
        return 100
    rs=(g/p)/(l/p)
    return 100-(100/(1+rs))

def scan():
    global last_hb
    if time.time()-last_hb>14400:
        send(f"HB {BAR} {time.strftime('%H:%M')}")
        last_hb=time.time()
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        data=requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP",headers=headers,timeout=10).json().get('data',[])
        top=sorted([x for x in data if 'USDT' in x['instId'] and float(x.get('vol24h',0)or 0)>50000], key=lambda x: float(x.get('vol24h',0)or 0), reverse=True)[:80]
        ids=[x['instId'] for x in top]
        scan_list=PRIORITY+ids
        scan_list=list(dict.fromkeys(scan_list))
    except:
        return
    for inst in scan_list:
        coin=inst.split('-')[0]
        if coin in sent and time.time()-sent[coin]<1800:
            continue
        try:
            kl=requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar={BAR}&limit=100",headers={"User-Agent":"Mozilla/5.0"},timeout=10).json().get('data',[])
            if len(kl)<50:
                continue
            kl.reverse()
            closes=[float(c[4]) for c in kl]
            lows=[float(c[3]) for c in kl]
            highs=[float(c[2]) for c in kl]
            vols=[float(c[5]) for c in kl]
            ub,mid,lb=boll(closes,20,2)
            if lb is None:
                continue
            r6=rsi(closes,6)
            r6p=rsi(closes[:-1],6)
            low_now=lows[-1]
            close_now=closes[-1]
            vol_ratio=vols[-1]/(sum(vols[-21:-1])/20) if sum(vols[-21:-1])>0 else 0
            bw=(ub-lb)/mid if mid else 0
            c1=low_now<=lb*1.03
            c2=bw>0.025
            c3=vol_ratio>1.15
            c4=r6p<45 or r6<50
            c5=close_now<mid*0.995
            score=sum([c1,c2,c3,c4,c5])
            if c1 and score>=3:
                sl=lb*0.985
                dip=(close_now/mid-1)*100
                msg=f"DUMP {coin} S{score}/5 {BAR} Now:{close_now:.5f} LB:{lb:.5f} MID:{mid:.5f} Dip:{dip:.1f}% Vol:{vol_ratio:.1f}x RSI:{r6:.0f} SL:{sl:.5f} {inst}"
                send(msg)
                sent[coin]=time.time()
        except:
            continue

def loop():
    send(f"LIVE {BAR} START")
    global last_hb
    last_hb=time.time()
    while True:
        scan()
        time.sleep(30)

threading.Thread(target=loop,daemon=True).start()

if __name__=="__main__":
    app.run(host='0.0.0.0',port=PORT)
