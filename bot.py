import time, json, urllib.request, urllib.parse, os, threading
from flask import Flask
TOKEN="8656315835:AAF3SWSIaGo9JwGc7GkaoJKROZxGdC6s5L8"
CHAT="5042879835"
app=Flask(__name__)
@app.route('/')
def home(): return "BOT LIVE TOP5 RSI20"
def send(m):
 url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
 data=urllib.parse.urlencode({"chat_id":CHAT,"text":m}).encode()
 try: urllib.request.urlopen(url,data,timeout=10)
 except: pass
 print(m)
def get_top5():
 url="https://www.okx.com/api/v5/market/tickers?instType=SPOT"
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
 with urllib.request.urlopen(req,timeout=10) as r: j=json.loads(r.read().decode())
 lst=[]
 for t in j["data"]:
  if not t["instId"].endswith("-USDT"): continue
  if t["instId"] in ["BTC-USDT","ETH-USDT","SOL-USDT"]: continue
  try:
   last=float(t["last"]); o=float(t.get("open24h",last)); v=last*float(t["vol24h"])
   gain=(last-o)/o*100 if o else 0
  except: continue
  if v>200000: lst.append((t["instId"],gain))
 lst.sort(key=lambda x:x[1],reverse=True)
 return [x[0] for x in lst[:5]]
def get_candles(inst):
 url=f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=5m&limit=100"
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
  with urllib.request.urlopen(req,timeout=10) as r: return list(reversed(json.loads(r.read().decode())["data"]))
 except: return []
def calc_rsi(closes,p=14):
 r=[50.0]*len(closes)
 for i in range(p,len(closes)):
  g=l=0
  for j in range(i-p+1,i+1):
   ch=closes[j]-closes[j-1]
   g+=ch if ch>0 else 0; l+=-ch if ch<0 else 0
  r[i]=100 if l==0 else 100-(100/(1+g/l))
 return r
def calc_kdj(data):
 closes=[float(x[4]) for x in data]; highs=[float(x[2]) for x in data]; lows=[float(x[3]) for x in data]
 n=9; rsv=[]
 for i in range(len(closes)):
  if i<n-1: rsv.append(50)
  else:
   hh=max(highs[i-n+1:i+1]); ll=min(lows[i-n+1:i+1]); rsv.append((closes[i]-ll)/(hh-ll)*100 if hh!=ll else 50)
 k=[50.0]; d=[50.0]
 for i in range(1,len(rsv)): k.append((2/3)*k[-1]+(1/3)*rsv[i]); d.append((2/3)*d[-1]+(1/3)*k[-2])
 return k,d
def calc_macd(closes):
 def ema(arr,p):
  e=[]; kk=2/(p+1)
  for i,v in enumerate(arr): e.append(v if i==0 else v*kk+e[-1]*(1-kk))
  return e
 ef=ema(closes,12); es=ema(closes,26); macd=[a-b for a,b in zip(ef,es)]; sig=ema(macd,9)
 return [m-s for m,s in zip(macd,sig)]
def bot_loop():
 top5=get_top5(); send(f"BOT LIVE RENDER TOP5\n{', '.join(top5)}")
 last=time.time(); seen={}
 while True:
  try:
   if time.time()-last>300: top5=get_top5(); send(f"Top5: {', '.join(top5)}"); last=time.time()
   for coin in top5:
    data=get_candles(coin)
    if len(data)<40: continue
    closes=[float(x[4]) for x in data]; rsi=calc_rsi(closes,14); k,d=calc_kdj(data); hist=calc_macd(closes)
    r_now=rsi[-2]; k_now=k[-2]; d_now=d[-2]; k_prev=k[-3]; d_prev=d[-3]; h_now=hist[-2]; h_prev=hist[-3]
    if r_now<=20 and k_prev<=d_prev and k_now>d_now and h_now<0 and h_now>h_prev:
     if coin not in seen or time.time()-seen[coin]>1800:
      seen[coin]=time.time(); send(f"🟢 TRIPLE {coin} 5m RSI {r_now:.1f} K {k_now:.1f} D {d_now:.1f} price {data[-2][4]}")
   time.sleep(10)
  except Exception as e: print(e); time.sleep(5)
threading.Thread(target=bot_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
