import requests, time, os, math
from flask import Flask
import threading

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "5042879835")
PORT = int(os.getenv("PORT", 10000))
sent = {}
GATE_HOST = "https://api.gateio.ws"

def send(m):
    try:
        if TOKEN:
            requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage", json={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass
    print(m, flush=True)

@app.route('/')
def home():
    return "GATE LB GREEN BOT - 80 MOVERS - OK"

def sma(a,p):
    if len(a)<p:
        return None
    return sum(a[-p:])/p

def boll(c,p=20,d=2):
    if len(c)<p:
        return None,None,None
    m=sma(c,p)
    var=sum((x-m)**2 for x in c[-p:])/p
    s=math.sqrt(var)
    return m+d*s, m, m-d*s

def rsi_wilder(prices,p=6):
    if len(prices)<p+1:
        return 50
    gains=[]
    losses=[]
    for i in range(1,len(prices)):
        d=prices[i]-prices[i-1]
        if d>0:
            gains.append(d)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(d))
    if len(gains)<p:
        return 50
    ag=sum(gains[-p:])/p
    al=sum(losses[-p:])/p
    if al==0:
        return 100
    rs=ag/al
    return 100-(100/(1+rs))

def get_movers():
    try:
        url=GATE_HOST+"/api/v4/futures/usdt/tickers"
        resp=requests.get(url,timeout=15).json()
        valid=[]
        for t in resp:
            try:
                contract=t.get('contract','')
                if not contract.endswith('_USDT'):
                    continue
                last=float(t.get('last',0) or 0)
                if last<0.000001:
                    continue
                change=float(t.get('change_percentage',0) or 0)
                vol=float(t.get('volume_24h',0) or 0)
                if vol<500:
                    continue
                valid.append((contract,change))
            except:
                continue
        gainers=sorted(valid,key=lambda x:x[1],reverse=True)
        losers=sorted(valid,key=lambda x:x[1])
        top_g=[x[0] for x in gainers[:40]]
        top_l=[x[0] for x in losers[:40]]
        combined=list(dict.fromkeys(top_g+top_l))
        print("Movers G:"+str(len(top_g))+" L:"+str(len(top_l)),flush=True)
        return combined, top_g, top_l
    except Exception as e:
        print("movers err "+str(e),flush=True)
        return ["BTC_USDT","ETH_USDT","SOL_USDT","ARB_USDT","UNI_USDT"], [], []

def get_candles(contract,limit=80):
    try:
        url=GATE_HOST+"/api/v4/futures/usdt/candlesticks"
        params={"contract":contract,"interval":"15m","limit":limit}
        resp=requests.get(url,params=params,timeout=15).json()
        resp=sorted(resp,key=lambda x:x['t'])
        opens=[float(c['o']) for c in resp]
        highs=[float(c['h']) for c in resp]
        lows=[float(c['l']) for c in resp]
        closes=[float(c['c']) for c in resp]
        vols=[float(c['v']) for c in resp]
        return opens,highs,lows,closes,vols
    except Exception as e:
        print("candle err "+str(e),flush=True)
        return None

def scan():
    all_coins,gainers,losers=get_movers()
    for contract in all_coins:
        try:
            coin=contract.split('_')[0]
            if coin in sent and time.time()-sent[coin]<3600:
                continue
            data=get_candles(contract,80)
            if not data:
                continue
            opens,highs,l
