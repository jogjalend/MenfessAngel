from flask import Flask, request
import os, requests
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION = requests.Session()

@app.route("/", methods=["GET"])
def home():
    return "BOT HIDUP", 200

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print(data)
    if not data or "message" not in data:
        return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text","")
    if text.startswith("/start"):
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": "BOT NYALA SU! Webhook fix 100%"
        })
    return "ok", 200

@app.route("/api/index.py", methods=["POST"])
def webhook2():
    return webhook()
