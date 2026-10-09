import os, time, json, threading, requests
from flask import Flask
from datetime import datetime

BOT_TOKEN=os.getenv("BOT_TOKEN","8656315835:AAF3SWSIaGo9JwGc7GkaoJKROZxGdC6s5L8")
CHAT_ID=os.getenv("CHAT_ID","5042879835")
app=Flask(__name__)

def tg(m):
 try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":m},timeout=10)
 except: pass
 print(m)

def get_candles(instId, bar="5m"):
 try:
  url=f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar={bar}&limit=100"
  r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
  if r['code']!='0': return []
  return list(reversed(r['data']))
 except: return []

def calc_rsi(closes, p=14):
 if len(closes)<p+1: return 50
 g=l=0
 for i in range(-p,0):
  ch=closes[i]-closes[i-1]
  if ch>0: g+=ch
  else: l+=-ch
 if l==0: return 100
 return 100-(100/(1+g/l))

def get_top_scan():
 try:
  url="https://www.okx.com/api/v5/market/tickers?instType=SPOT"
  j=requests.get(url,timeout=10).json()
  lst=[]
  for t in j['data']:
   if not t['instId'].endswith('-USDT'): continue
   sym=t['instId'].replace("-","/")
   if sym in ["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","BNB/USDT"]: continue
   try: vol=float(t['last'])*float(t['vol24h'])
   except: continue
   try:
    open_price=float(t['open24h'])
    last=float(t['last'])
    pct=(last-open_price)/open_price*100 if open_price else 0
   except: pct=0
   if 150000 < vol < 40000000 and abs(pct)>2:
    lst.append((sym, pct, vol, float(t['last'])))
  lst.sort(key=lambda x:x[1], reverse=True)
  return lst[:40]
 except Exception as e:
  print("top error",e)
  return []

def check_strategy(sym):
 try:
  inst=sym.replace("/","-")
  c5=get_candles(inst,"5m")
  c15=get_candles(inst,"15m")
  if len(c5)<30 or len(c15)<30: return None
  closes5=[float(x[4]) for x in c5]
  closes15=[float(x[4]) for x in c15]
  vols5=[float(x[5]) for x in c5]
  vols15=[float(x[5]) for x in c15]
  cc5=closes5[-2]; cc15=closes15[-2]
  e9_5=sum(closes5[-11:-2])/9; e21_5=sum(closes5[-23:-2])/21
  e9_15=sum(closes15[-11:-2])/9; e21_15=sum(closes15[-23:-2])/21
  rsi5=calc_rsi(closes5[:-1],14); rsi15=calc_rsi(closes15[:-1],14)
  vavg5=sum(vols5[-21:-1])/20; vavg15=sum(vols15[-21:-1])/20
  vr5=vols5[-2]/vavg5 if vavg5 else 0; vr15=vols15[-2]/vavg15 if vavg15 else 0
  cond5 = cc5 > e9_5 > e21_5 and rsi5 < 28 and vr5>1.0
  cond15 = cc15 > e9_15 > e21_15 and rsi15 < 28 and vr15>1.0
  if cond5 and cond15:
   score = 0
   if rsi5<25: score+=10
   if rsi15<25: score+=10
   if vr5>1.5: score+=10
   if vr15>1.5: score+=10
   return (rsi5,rsi15,vr5,vr15,cc5,score)
 except Exception as e:
  print("check err",sym,e)
 return None

def loop():
 tg(f"🚀 BOT LIVE 5MIN SCAN ✅\nScanning 40 coins\nRule: 5m & 15m > EMA9>EMA21 + RSI<28 + Vol>1x\n{datetime.now().strftime('%H:%M:%S')}")
 seen={}
 while True:
  try:
   top=get_top_scan()
   if not top:
    time.sleep(30); continue
   msg=f"🔥 TOP5 OKX Gainers - {datetime.now().strftime('%H:%M:%S')}\n\n"
   for i,(sym,pct,vol,price) in enumerate(top[:5],1):
    msg+=f"{i}. {sym}: {price} ({pct:.2f}%)\n"
   tg(msg)
   found=[]
   for sym,pct,vol,price in top:
    res=check_strategy(sym)
    time.sleep(0.4)
    if res:
     r5,r15,vr5,vr15,cc,sc=res
     if sym not in seen or time.time()-seen[sym]>3600*2:
      found.append((sym,r5,r15,vr5,cc,sc,pct))
      seen[sym]=time.time()
   if found:
    found=sorted(found,key=lambda x:x[5],reverse=True)
    m=f"💎 STRATEGY MATCH ({len(found)}) - 5m+15m DIP\n\n"
    for sym,r5,r15,vr5,cc,sc,pct in found[:5]:
     m+=f"✅ {sym}\n Price {cc} ({pct:+.1f}%)\n RSI 5m:{r5:.0f} 15m:{r15:.0f} V:{vr5:.1f}x Score:{sc}\n LONG now SL {cc*0.97:.4f} TP {cc*1.06:.4f}\n\n"
    tg(m)
   else:
    tg("⏳ Scan done: No strategy match this round. Waiting 5m.")
  except Exception as e:
   print("loop err",e)
   tg(f"Error: {e}")
  time.sleep(300)

threading.Thread(target=loop,daemon=True).start()

@app.route('/')
def home(): return "OKX TOP5+STRATEGY 5MIN LIVE"

if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
