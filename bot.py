import requests,time,os,math
from flask import Flask
import threading
app=Flask(__name__)
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID","5042879835")
PORT=int(os.getenv("PORT","10000"))
sent={}
GATE_HOST="https://api.gateio.ws"
def send(m):
 try:
  if TOKEN:
   u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
   requests.post(u,json={"chat_id":CHAT,"text":m},timeout=10)
 except: pass
 print(m,flush=True)
@app.route('/')
def home(): return "GATE V7 OK"
def sma(a,p):
 if len(a)<p: return None
 s=0
 for x in a[-p:]: s=s+x
 return s/p
def boll(c):
 p=20;d=2
 if len(c)<p: return [None,None,None]
 m=sma(c,p)
 var=0
 for x in c[-p:]: var=var+(x-m)*(x-m)
 var=var/p
 s=math.sqrt(var)
 return [m+d*s,m,m-d*s]
def rsi_wilder(prices):
 p=6
 if len(prices)<p+1: return 50
 gains=[];losses=[]
 for i in range(1,len(prices)):
  diff=prices[i]-prices[i-1]
  if diff>0: gains.append(diff);losses.append(0)
  else: gains.append(0);losses.append(abs(diff))
 if len(gains)<p: return 50
 ag=sum(gains[-p:])/p;al=sum(losses[-p:])/p
 if al==0: return 100
 rs=ag/al;return 100-(100/(1+rs))
def get_movers():
 try:
  url=GATE_HOST+"/api/v4/futures/usdt/tickers"
  resp=requests.get(url,timeout=15).json()
  valid=[]
  for t in resp:
   contract=t.get('contract','')
   if not contract.endswith('_USDT'): continue
   last=float(t.get('last',0) or 0)
   if last<0.000001: continue
   change=float(t.get('change_percentage',0) or 0)
   valid.append([contract,change])
  valid.sort(key=lambda x:x[1],reverse=True)
  top_g=[]
  for i in range(40):
   if i<len(valid): top_g.append(valid[i][0])
  valid.sort(key=lambda x:x[1])
  top_l=[]
  for i in range(40):
   if i<len(valid): top_l.append(valid[i][0])
  combined=[]
  for c in top_g+top_l:
   if c not in combined: combined.append(c)
  return [combined,top_g,top_l]
 except: return [["BTC_USDT","ETH_USDT","SOL_USDT"],[],[]]
def get_candles(contract):
 try:
  url=GATE_HOST+"/api/v4/futures/usdt/candlesticks"
  params={"contract":contract,"interval":"15m","limit":80}
  resp=requests.get(url,params=params,timeout=15).json()
  resp.sort(key=lambda x:x['t'])
  o=[];h=[];l=[];c=[];v=[]
  for x in resp: o.append(float(x['o']));h.append(float(x['h']));l.append(float(x['l']));c.append(float(x['c']));v.append(float(x['v']))
  return [o,h,l,c,v]
 except: return None
def scan():
 movers_data=get_movers()
 all_coins=movers_data[0];top_g=movers_data[1];top_l=movers_data[2]
 for contract in all_coins:
  try:
   coin=contract.split('_')[0]
   if coin in sent:
    if time.time()-sent[coin]<3600: continue
   data=get_candles(contract)
   if data is None: continue
   opens=data[0];highs=data[1];lows=data[2];closes=data[3];vols=data[4]
   if len(closes)<50: continue
   b=boll(closes);ub=b[0];mid=b[1];lb=b[2]
   if lb is None: continue
   close_now=closes[-1];open_now=opens[-1];low_now=lows[-1];prev_low=lows[-2]
   is_green=close_now>open_now
   touched=False
   if low_now<=lb*1.02: touched=True
   if prev_low<=lb*1.02: touched=True
   reclaimed=close_now>lb
   if not is_green: continue
   if not touched: continue
   if not reclaimed: continue
   r6=rsi_wilder(closes);prev_closes=closes[:-1];r6p=rsi_wilder(prev_closes)
   if r6>45: continue
   if r6p>50: continue
   avg_vol=sum(vols[-21:-1])/20;vol_ratio=vols[-1]/avg_vol if avg_vol>0 else 0
   if vol_ratio<1.3: continue
   bw=(ub-lb)/mid if mid else 0
   if bw<0.03: continue
   rsv_min=min(lows[-9:]);rsv_max=max(highs[-9:])
   if rsv_max==rsv_min: rsv=50
   else: rsv=(close_now-rsv_min)/(rsv_max-rsv_min)*100
   if rsv>40: continue
   tag="MOVER"
   if contract in top_g: tag="GAINER"
   if contract in top_l: tag="LOSER BEST DIP"
   cn=str(round(close_now,5));lb_s=str(round(lb,5))
   msg="GATE BOUNCE "+coin+" "+tag+" "+cn+" LB "+lb_s+" RSI "+str(round(r6))+" "+contract
   send(msg);sent[coin]=time.time()
  except: continue
def loop():
 send("GATE BOT V7 START OK - 80 Movers")
 while True:
  try: scan()
  except: pass
  time.sleep(60)
threading.Thread(target=loop,daemon=True).start()
if __name__=="__main__": app.run(host='0.0.0.0',port=PORT)
