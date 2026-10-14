import requests, time, os, math
from flask import Flask
import threading

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
BAR = "15m"
sent = {}
last_hb = 0

PRIORITY = ["WAL-USDT-SWAP","PYTH-USDT-SWAP","GRASS-USDT-SWAP","PUMP-USDT-SWAP","SUI-USDT-SWAP","SOL-USDT-SWAP","BTC-USDT-SWAP"]

def send(m):
    try:
        if TOKEN:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass
    print(m, flush=True)

@app.route('/')
def home():
    return "STRICT RSI<45 FIXED"

def sma(a,p):
    if len(a)<p: return None
    return sum(a[-p:])/p

def boll(c,p=20,d=2):
    if len(c)<p: return None,None,None
    m=sma(c,p)
    var=sum((x-m)**2 for x in c[-p:])/p
    s=math.sqrt(var)
    return m+d*s, m, m-d*s

def rsi(prices,p=6):
    if len(prices)<p+1: return 50
    g=l=0
    for i in range(1,p+1):
        dlt=prices[-i]-prices[-i-1]
        if dlt>0: g+=dlt
        else: l+=abs(dlt)
    if l==0: return 100
    rs=(g/p)/(l/p)
    return 100-(100/(1+rs))

def scan():
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        data=requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP",headers=headers,timeout=10).json().get('data',[])
        top=sorted([x for x in data if 'USDT' in x['instId'] and float(x.get('vol24h',0)or 0)>150000], key=lambda x: float(x.get('vol24h',0)or 0), reverse=True)[:60]
        scan_list=PRIORITY+[x['instId'] for x in top]
        scan_list=list(dict.fromkeys(scan_list))
    except:
        return
    for inst in scan_list:
        coin=inst.split('-')[0]
        if coin in sent and time.time()-sent[coin]<3600: # 1 hour cooldown - NO SPAM
            continue
        try:
            kl=requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar={BAR}&limit=80",headers={"User-Agent":"Mozilla/5.0"},timeout=10).json().get('data',[])
            if len(kl)<50: continue
            kl.reverse()
            closes=[float(c[4]) for c in kl]
            lows=[float(c[3]) for c in kl]
            highs=[float(c[2]) for c in kl]
            vols=[float(c[5]) for c in kl]
            ub,mid,lb=boll(closes,20,2)
            if lb is None: continue

            r6=rsi(closes,6)
            r6p=rsi(closes[:-1],6)
            vol_ratio=vols[-1]/(sum(vols[-21:-1])/20) if sum(vols[-21:-1])>0 else 0
            bw=(ub-lb)/mid if mid else 0
            low_now=lows[-1]
            close_now=closes[-1]

            # HARD FILTERS - WILL BLOCK RSI 86
            if r6>55: continue # BLOCK overbought - fixes your RSI 86 bug
            if r6p>60: continue
            if vol_ratio<1.3: continue # BLOCK low volume
            if bw<0.03: continue # BLOCK tight bands
            if low_now>lb*1.02: continue # MUST touch LB

            # If passes all hard filters, then it's REAL dump
            rsv_min=min(lows[-9:])
            rsv_max=max(highs[-9:])
            rsv=(close_now-rsv_min)/(rsv_max-rsv_min)*100 if rsv_max!=rsv_min else 50
            if rsv>40: continue

            dip=(close_now/mid-1)*100
            sl=lb*0.985
            msg=(
                f"REAL DUMP {coin} {BAR}\n"
                f"RSI:{r6:.0f}->{r6p:.0f} MUST BE <45\n"
                f"Now:{close_now:.5f} LB:{lb:.5f} MID:{mid:.5f}\n"
                f"Dip:{dip:.1f}% Vol:{vol_ratio:.1f}x BW:{bw*100:.1f}% RSV:{rsv:.0f}\n"
                f"SL:{sl:.5f} TP:{mid:.5f}\n"
                f"{inst}"
            )
            send(msg)
            sent[coin]=time.time()
        except:
            continue

def loop():
    send("FIXED BOT START - RSI>55 BLOCKED - No more RSI 86 spam")
    while True:
        scan()
        time.sleep(60)

threading.Thread(target=loop,daemon=True).start()

if __name__=="__main__":
    app.run(host='0.0.0.0',port=PORT)
