from flask import Flask, request
import os, requests

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "V54 DEBUG LIVE - menfess-angel", 200

    data = request.get_json(force=True, silent=True) or {}
    print("INCOMING:", data)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        
        # BALAS APAPUN YANG MASUK
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"DEBUG PONG! Lu kirim: {text}\n\nBOT_TOKEN ada: {bool(BOT_TOKEN)}\n\nKalau ini muncul, webhook jalan!"
        }
        r = requests.post(url, json=payload)
        print("SEND RESULT:", r.text)

    return "ok", 200
