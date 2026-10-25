from flask import Flask, request
import os
import requests

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")

@app.route('/', methods=['GET'])
def home():
    return "Menfess Angel is running", 200

@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data:
            return "ok", 200
        
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        if not text:
            return "ok", 200

        # Balas ke Telegram dulu biar gak pending
        send_telegram(chat_id, f"Menfess diterima: {text}")

        # TODO: Kirim ke Threads (nanti)
        # requests.post(...)

        return "ok", 200
    except Exception as e:
        print(f"Error: {e}")
        return "ok", 200

def send_telegram(chat_id, text):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

# Vercel butuh ini
# app = app
