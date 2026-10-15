import os
import time
import threading
import requests
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- CONFIG ---
BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT_ID = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

print(f"========== BOOT ==========")
print(f"BOOT TOKEN len={len(BOT_TOKEN)} token_start={BOT_TOKEN[:6]}...")
print(f"BOOT CHAT={CHAT_ID}")
print(f"==========================")

def send_tg(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(f"ERROR: Missing TOKEN len={len(BOT_TOKEN)} CHAT={CHAT_ID}")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    
    try:
        print(f"TRY SEND to {CHAT_ID}: {msg[:50]}...")
        r = requests.post(url, json=payload, timeout=15)
        print(f"SEND RESP {r.status_code} -> {r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        print(f"SEND EXCEPTION: {e}")
        return False

# --- GATE NEWS SCANNER CORE ---
def gate_scan_loop():
    # Wait for Flask to start
    time.sleep(5)
    
    if not send_tg("✅
