from flask import Flask, request
import os, requests, json
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
WIB = timezone(timedelta(hours=7))

@app.route("/", methods=["GET"])
def home():
    return "V53 LIVE - NO MORE METHOD NOT ALLOWED - READY FOR WEBHOOK", 200

@app.route("/api/index", methods=["GET", "POST"])
def handler():
    if request.method == "GET":
        return "V53 LIVE - WEBHOOK OK - menfess-angel.vercel.app", 200
    
    # --- POST = dari Telegram ---
    data = request.get_json(silent=True)
    if not data:
        return "ok", 200
    
    # simpel dulu, cuma bales start biar tau bot hidup
    if "message" in data:
        msg = data["message"]
        cid = msg["chat"]["id"]
        txt = msg.get("text","")
        if txt.startswith("/start"):
            start_text = f"""Menfess Angel • o f f i c i a l

Your post will be published to:

Channel → @menfessangel
Threads → @jogjalend [optional]
X → @jogjalendpm [maintenance]

Threads mode: OFF ❌
Daily reset: 00:00 WIB
Limit: 5 texts & 5 media"""
            kb = {
                "inline_keyboard": [
                    [{"text": "👤 Profile", "callback_data": "profil"}],
                    [{"text": "📜 Rules", "callback_data": "rules"}, {"text": "📝 Post Menfess", "callback_data": "post"}],
                    [{"text": "🧵 Threads Setting", "callback_data": "threads"}],
                    [{"text": "📊 Stats", "callback_data": "stats"}, {"text": "ℹ️ Help", "callback_data": "help"}]
                ]
            }
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": start_text, "reply_markup": kb})
    
    return "ok", 200
