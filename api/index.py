from flask import Flask, request
import os, requests
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
WIB = timezone(timedelta(hours=7))

def send(chat_id, text, kb=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if kb:
        payload["reply_markup"] = kb  # jangan json.dumps, langsung dict
    requests.post(url, json=payload)

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "V55 FULL LIVE - MENFESS ANGEL READY - NO JAVANESE", 200

    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")

        if text.startswith("/start"):
            start_text = """Menfess Angel • o f f i c i a l

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
            send(chat_id, start_text, kb)

    if "callback_query" in data:
        cq = data["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        cdata = cq["data"]
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})

        if cdata == "profil":
            send(chat_id, "👤 Profile\nID: {}\nMenfess hari ini: 0/5".format(chat_id))
        elif cdata == "rules":
            send(chat_id, "📜 Rules:\n1. No SARA, porn, spam\n2. Limit 5 text & 5 media/hari\n3. No doxxing\n4. Admin berhak reject")
        elif cdata == "post":
            send(chat_id, "📝 Kirim menfess lu sekarang.\nBisa text, foto, video, gif.\n\nKetik /cancel buat batal.")
        elif cdata == "threads":
            send(chat_id, "🧵 Threads Setting\n\nMode: OFF ❌\n\nHubungkan Threads: @jogjalend\nKetik username Threads lu:")
        elif cdata == "stats":
            send(chat_id, "📊 Stats Today\nTotal: 0\nText: 0\nMedia: 0")
        elif cdata == "help":
            send(chat_id, "ℹ️ Help\nDM: @jogjalend\nChannel: @menfessangel")

    return "ok", 200
