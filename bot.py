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
GATE_HOST = "https://api.gateio.ws"

# V10 FULL NEWS PRIORITY
PRIORITY = [
    "SUI_USDT",
    "WAL_USDT",
    "DATA_USDT",
    "IP_USDT",
    "ARB_USDT",
    "STRK_USDT",
    "CRO_USDT",
    "DBR_USDT",
    "SEI_USDT",
    "APT_USDT",
    "OKB_USDT",
    "RENDER_USDT",
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "HOOKED_USDT",
]

def send(m):
    try:
        if TOKEN:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass
    print(m, flush=True)

@app.route('/')
def home():
    return "V10 GATE NEWS FULL - SUI $30M DATA ARB STRK CRO OKX"

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

def get_movers():
    try:
        url=GATE_HOST+"/api/v4/futures/usdt/tickers"
        resp=requests.get(url, timeout=15).json()
        valid=[]
        for t in resp:
            c=t.get('contract','')
            if not c.endswith('_USDT'): continue
            if float(t.get('last',0) or 0) < 1e-7: continue
            if float(t.get('volume_24h',0) or 0) < 100000: continue
            valid.append([c, float(t.get('volume_24h',0) or 0)])
        valid.sort(key=lambda x: x[1], reverse=True)
        top=[x[0] for x in valid[:40]]
        combined=PRIORITY+top
        return list(dict.fromkeys(combined))
    except Exception as e:
        print(f"MOVER ERR {e}", flush=True)
        return PRIORITY

def get_candles(contract):
    try:
        url=GATE_HOST+"/api/v4/futures/usdt/candlesticks"
        params={"contract": contract, "interval": "15m", "limit": 80}
        resp=requests.get(url, params=params, timeout=15).json()
        resp.sort(key=lambda x: x['t'])
        closes=[float(x['c']) for x in resp]
        lows=[float(x['l']) for x in resp]
        highs=[float(x['h']) for x in resp]
        vols=[float(x['v']) for x in resp]
        return closes, lows, highs, vols
    except Exception as e:
        print(f"CANDLE ERR {contract} {e}", flush=True)
        return None

def scan():
    global last_hb
    checked=0
    bounced=0
    last_info="none"
    scan_list=get_movers()
    for contract in scan_list:
        coin=contract.split('_')[0]
        if coin in sent and time.time()-sent[coin]<1200: continue
        data=get_candles(contract)
        if data is None: continue
        try:
            closes,lows,highs,vols=data
            if len(closes)<50: continue
            ub,mid,lb=boll(closes,20,2)
            if lb is None: continue
            checked+=1
            r6=rsi(closes,6)
            r6p=rsi(closes[:-1],6)
            vol_ratio=vols[-1]/(sum(vols[-21:-1])/20) if sum(vols[-21:-1])>0 else 0
            bw=(ub-lb)/mid if mid else 0
            low_now=lows[-1]
            close_now=closes[-1]
            last_info=f"{coin} {close_now:.5f}"
            if r6>55: continue
            if r6p>60: continue
            if vol_ratio<1.1: continue
            if bw<0.03: continue
            if low_now>lb*1.02: continue
            rsv_min=min(lows[-9:])
            rsv_max=max(highs[-9:])
            rsv=(close_now-rsv_min)/(rsv_max-rsv_min)*100 if rsv_max!=rsv_min else 50
            if rsv>50: continue
            dip=(close_now/mid-1)*100
            sl=lb*0.985
            tag="NEWS"
            if coin in ["SUI","WAL","DATA","IP"]: tag="SUI $30M DATA"
            elif coin in ["ARB","STRK","CRO","DBR"]: tag="UNLOCK"
            elif coin in ["OKB"]: tag
