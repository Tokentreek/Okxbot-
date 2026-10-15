import os, time, threading, requests, statistics
from flask import Flask
app = Flask(__name__)

TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": CHAT, "text": msg}, timeout=10)
        print(f"SEND {r.status_code} {r.text[:100]}")
        return True
    except Exception as e:
        print(f"SEND ERR {e}")
        return False

def calc_bb(closes, period=20, mult=2):
    if len(closes) < period: return None,None,None
    sma = statistics.mean(closes[-period:])
    stdev = statistics.pstdev(closes[-period:]) # FIX: use pstdev not stdev
    return sma+mult*stdev, sma, sma-mult*stdev

def calc_rsi_fixed(closes, period):
    # FIXED: Wilder's RSI, stable
    if len(closes) < period+1: return 50.0
    deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains = [max(0,d) for d in deltas[-period:]]
    losses = [max(0,-d) for d in deltas[-period:]]
    avg_gain = sum(gains)/period
    avg_loss = sum(losses)/period
    if avg_loss == 0: return 100.0 if avg_gain>0 else 50.0
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

def calc_macd_fixed(closes):
    # FIXED: proper EMA
    if len(closes) < 35: return 0,0,0
    def ema(values, period):
        k = 2/(period+1)
        ema_val = sum(values[:period])/period
        for v in values[period:]:
            ema_val = v*k + ema_val*(1-k)
        return ema_val
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    dif = ema12 - ema26
    # DEA is EMA9 of DIF - need dif history
    difs = []
    for i in range(26, len(closes)):
        e12 = ema(closes[:i+1], 12)
        e26 = ema(closes[:i+1], 26)
        difs.append(e12-e26)
    dea = ema(difs, 9) if len(difs)>=9 else sum(difs[-9:])/9 if difs else 0
    macd = (dif-dea)*2
    return macd, dif, dea

def get_tickers():
    try:
        data = requests.get("https://api.gateio.ws/api/v4/futures/usdt/tickers", timeout=15).json()
        sorted_t = sorted(data, key=lambda x: float(x.get('change_percentage',0)))
        coins = [t['contract'] for t in sorted_t[:35]+sorted_t[-35:] if 'USDT' in t['contract']]
        return list(set(coins))
    except: return []

def get_candles(c):
    try:
        d = requests.get(f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={c}&interval=15m&limit=100", timeout=15).json()
        return sorted(d, key=lambda x: x['t'])
    except: return []

def is_small(c):
    o=float(c['o']); cc=float(c['c']); h=float(c['h']); l=float(c['l'])
    body=abs(cc-o); rng=h-l
    if rng==0: return True
    return (body/rng < 0.45) and (body/cc < 0.01 if cc else True)

# FIXED DEDUP: store last alert price + time
notified = {}
STARTED = False

def loop():
    global STARTED
    time.sleep(2)
    if not STARTED:
        send("V11.3 FIXED - No Dup Alerts\nLB Touch + Small -> Pump\nRSI/MACD INFO ONLY")
        STARTED = True

    while True:
        try:
            for contract in get_tickers():
                candles = get_candles(contract)
                if len(candles) < 30: continue
                closes = [float(x['c']) for x in candles]

                ub, mb, lb = calc_bb(closes[:-1])
                if lb is None: continue

                # Check last closed pattern only once
                touch_c = candles[-4]
                small_c = candles[-3]
                pump_c = candles[-2]

                l_touch = float(touch_c['l'])
                touched = l_touch <= lb * 1.015
                small = is_small(small_c)
                green = float(pump_c['c']) > float(pump_c['o']) and float(pump_c['c']) > float(small_c['h'])

                if touched and small and green:
                    price = float(pump_c['c'])
                    # DEDUP FIX: same coin + same price = don't resend for 4 hours
                    key = f"{contract}_{price}"
                    last = notified.get(contract)
                    if last and last['price']==price and time.time()-last['time'] < 14400:
                        print(f"SKIP DUP {contract} {price}")
                        continue
                    # Also skip if alerted this coin in last 1 hour at all
                    if last and time.time()-last['time'] < 3600:
                        continue

                    rsi6 = calc_rsi_fixed(closes, 6)
                    rsi12 = calc_rsi_fixed(closes, 12)
                    macd, dif, dea = calc_macd_fixed(closes)

                    notified[contract] = {'price': price, 'time': time.time()}
                    coin = contract.replace('_USDT','')
                    msg = f"Vik {coin} found\n{contract} 15m\nLB Touch -> Small -> Pump\nPrice: {price}\nLB: {lb:.6f} MB: {mb:.6f}\nRSI(6):{rsi6:.1f} RSI(12):{rsi12:.1f}\nMACD:{macd:.6f} DIF:{dif:.6f} DEA:{dea:.6f}"
                    send(msg)
                    print(f"ALERT {coin} RSI6 {rsi6:.1f}")

                time.sleep(0.3)
            time.sleep(120) # Scan every 2 min - not 90 sec to reduce restarts
        except Exception as e:
            print(f"LOOP ERR {e}")
            time.sleep(30)

@app.route('/')
def home():
    return "V11.3 Fixed - No Duplicates Running"

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
