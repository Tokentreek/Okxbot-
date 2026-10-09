from flask import Flask, request
import threading, time, requests, os
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"TG Error: {e}")

@app.route('/')
def home():
    return "BOT LIVE RENDER TOP5 - OKX Scanner Running! ✅", 200

@app.route('/health')
def health():
    return "OK", 200

def get_okx_top5():
    try:
        # OKX public tickers
        r = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", timeout=15).json()
        if r.get("code") != "0": return None
        tickers = r.get("data", [])
        # filter USDT pairs, sort by 24h change
        usdt = [t for t in tickers if t["instId"].endswith("USDT") and float(t.get("vol24h",0))>100000]
        sorted_t = sorted(usdt, key=lambda x: float(x.get("sodUtc8","0") or 0), reverse=True)
        top5 = sorted_t[:5]
        return top5
    except Exception as e:
        print(f"OKX Error: {e}")
        return None

def bot_loop():
    time.sleep(5)
    send_telegram("🚀 *BOT LIVE RENDER TOP5* ✅\nOKX scanner started on Render!")
    while True:
        try:
            top5 = get_okx_top5()
            if top5:
                msg = f"🔥 *TOP5 OKX Gainers* - {datetime.now().strftime('%H:%M:%S')}\n\n"
                for i, t in enumerate(top5, 1):
                    change = float(t.get("sodUtc8","0") or 0)
                    price = t.get("last","0")
                    msg += f"{i}. `{t['instId']}`: {price} ({change:.2f}%)\n"
                send_telegram(msg)
                print("Sent TOP5")
            time.sleep(300)  # every 5 min - change to 60 for 1 min
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
