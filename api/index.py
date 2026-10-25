from flask import Flask, request
import os
import requests

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")

@app.route('/')
@app.route('/api/index.py')
def home():
    return "Menfess Angel is running", 200

@app.route('/', methods=['POST'])
@app.route('/api/index.py', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data:
            return "ok", 200
        
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text.startswith("/start"):
            send_telegram(chat_id, "Halo! Kirim menfess lu, nanti gue posting ke Threads ✨")
            return "ok", 200
        
        if not text:
            return "ok", 200

        # Balas ke Telegram dulu biar gak pending 7 lagi
        send_telegram(chat_id, f"✅ Menfess diterima:\n\n{text}\n\n(Akan diposting ke Threads)")

        return "ok", 200
    except Exception as e:
        print(f"Error: {e}")
        return "ok", 200

def send_telegram(chat_id, text):
    if not BOT_TOKEN:
        print("BOT_TOKEN not set")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"Send telegram error: {e}")
