from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "BOT LIVE RENDER TOP5 - Working!", 200

@app.route('/health')
def health():
    return "OK", 200
