import os, time, threading, requests, statistics
from flask import Flask
app = Flask(__name__)

TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
print(f"BOOT @Vikgateiobot CHAT={CHAT} TOKEN len={len(TOKEN)}")

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT, "text": msg}, timeout=10)
        print(f"SEND {r.status_code}")
        return r.status_code==200
    except Exception as e:
        print(f"ERR {e}")
        return False

def calc_bb(closes, period=20, mult=2):
    if len(closes) < period: return None,None,None
    sma = statistics.mean(closes[-period:])
    stdev = statistics.stdev(closes[-period:]) if len(closes[-period:])>1 else 0
    return sma+mult*stdev, sma, sma-mult*stdev

def calc_rsi(closes, period=14):
    if len(closes) < period+1: return 50.0
    gains=0; losses=0
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
        if diff>0: gains+=diff
        else: losses+=abs(diff)
    if losses==0: return 100.0
    rs = (gains/period) / (losses/period)
    return 100 - (100/(1+rs))

def calc_rsi_list(closes, period):
    # for RSI6 and RSI12 like your screenshot
    if len(closes) < period+1: return 50.0
    return calc_rsi(closes, period)

def calc_macd(closes):
    # MACD(12,26,9) like screenshot MACD:0.000041 DIF:0.000099 DEA:0.000057
    if len(closes) < 26+9: return 0,0,0
    def ema(data, p):
        k=2/(p+1)
        e=data[0]
        for v in data[1:]: e = v*k + e*(1-k)
        return e
    ema12 = ema(closes[-12:], 12)
    ema26 = ema(closes[-26:], 26)
    dif = ema12 - ema26
    # DEA = EMA9 of DIF - simplified with last 9 difs
    # For speed, use dif history
    difs=[]
    for i in range(9):
        slice_c = closes[-(26+i):-i] if i!=0 else closes[-26:]
        if len(slice_c)>=26:
            e12 = ema(slice_c[-12:],12)
            e26 = ema(slice_c[-26:],26)
            difs.append(e12-e26)
    dea = ema(difs[::-1], 9) if difs else 0
    macd = (dif-dea)*2
    return macd, dif, dea

def get_tickers():
    try:
        url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
        r = requests.get(url, timeout=15).json()
        sorted_t = sorted(r, key=lambda x: float(x.get('change_percentage',0)))
        losers = sorted_t[:35]
        gainers = sorted_t[-35:]
        return list(set([t['contract'] for t in losers+gainers if 'USDT' in t['contract']]))
    except Exception as e:
        print(f"TICK {e}")
        return []

def get_candles(contract):
    try:
        url = f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={contract}&interval=15m&limit=100"
        data = requests.get(url, timeout=15).json()
        return sorted(data, key=lambda x: x['t'])
    except:
        return []

def is_small_candle(c):
    o=float(c['o']); cc=float(c['c']); h=float(c['h']); l=float(c['l'])
    body=abs(cc-o); rng=h-l
    if rng==0: return True
    return (body/rng < 0.4) and (body/cc < 0.008 if cc!=0 else True)

def check_setup(candles):
    if len(candles) < 30: return False,0,0,0,None,{}
    closes = [float(c['c']) for c in candles]
    ub, mb, lb = calc_bb(closes[:-1])
    if lb is None: return False,0,0,0,None,{}

    # RSI + MACD calc (INFO ONLY, not mandatory)
    rsi6 = calc_rsi_list(closes, 6)
    rsi12 = calc_rsi_list(closes, 12)
    macd, dif, dea = calc_macd(closes)

    extra = {"rsi6": rsi6, "rsi12": rsi12, "macd": macd, "dif": dif, "dea": dea}

    for i in range(-5, -2):
        try:
            touch_c = candles[i-1]
            small_c = candles[i]
            pump_c = candles[i+1]
            l_touch = float(touch_c['l'])
            touched = l_touch <= lb * 1.015
            small = is_small_candle(small_c)
            green_pump = float(pump_c['c']) > float(pump_c['o']) and float(pump_c['c']) > float(small_c['h'])
            if touched and small and green_pump and i+1==-2:
                return True, lb, mb, ub, pump_c, extra
        except:
            continue
    return False, lb, mb, ub, None, extra

notified={}
def loop():
    time.sleep(3)
    send("V11.2 LIVE - LB Touch + Small Candle + Pump\nRSI+MACD added as INFO (not mandatory)")
    while True:
        try:
            for contract in get_tickers():
                candles = get_candles(contract)
                if not candles: continue
                found, lb, mb, ub, pump_c, extra = check_setup(candles)
                if found:
                    if contract in notified and time.time()-notified[contract] < 3600: continue
                    notified[contract]=time.time()
                    coin=contract.replace('_USDT','')
                    price=float(pump_c['c'])
                    # RSI + MACD info but NOT mandatory for signal
                    msg = (
                        f"Vik {coin} found\n"
                        f"{contract} 15m\n"
                        f"LB Touch -> Small -> Pump\n"
                        f"Price: {price}\n"
                        f"LB: {lb:.6f} MB: {mb:.6f}\n"
                        f"RSI(6):{extra['rsi6']:.2f} RSI(12):{extra['rsi12']:.2f}\n"
                        f"MACD:{extra['macd']:.6f} DIF:{extra['dif']:.6f} DEA:{extra['dea']:.6f}\n"
                        f"Note: RSI/MACD INFO ONLY"
                    )
                    send(msg)
                    print(f"FOUND {coin} RSI6 {extra['rsi6']:.1f}")
                time.sleep(0.25)
            time.sleep(90)
        except Exception as e:
            print(f"LOOP {e}")
            time.sleep(20)

@app.route('/')
def home():
    return "V11.2 RSI+MACD Info Running"

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
