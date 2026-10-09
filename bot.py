from flask import Flask
import threading, time, requests, os

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID_HERE")

@app.route('/')
def home():
    return "BOT LIVE RENDER TOP5 - OKX Bot Running!", 200

@app.route('/health')
def health():
    return "OK", 200

def send_telegram(msg):
    try:
        if BOT_TOKEN and CHAT_ID and "YOUR_" not in BOT_TOKEN:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}", timeout=5)
    except: pass

def bot_loop():
    time.sleep(10)
    send_telegram("BOT LIVE RENDER TOP5 ✅ Bot started on Render!")
    while True:
        try:
            # Your OKX TOP5 logic here - placeholder ping
            print("Bot loop running...")
            time.sleep(60)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(30)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
