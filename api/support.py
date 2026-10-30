from flask import Flask, request
import os, requests

app = Flask(__name__)
SUPPORT_TOKEN = os.getenv("SUPPORT_TOKEN") or ""
ADMIN_ID = os.getenv("ADMIN_ID") or ""

def send_msg(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{SUPPORT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except: pass

@app.route("/", methods=["GET","POST"])
@app.route("/api/support", methods=["GET","POST"])
@app.route("/<path:path>", methods=["GET","POST"])
def handler(path=None):
    if request.method == "GET":
        return "Support Bot OK", 200
    try:
        data = request.get_json(force=True, silent=True) or {}
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text","")
            name = msg["from"].get("first_name","")
            username = msg["from"].get("username","-")
            
            if text.startswith("/start"):
                send_msg(chat_id, f"Hi {name}!\n\nKirim pertanyaan / bug / saran lu disini, nanti diterusin ke admin JogjaLend.")
            else:
                if ADMIN_ID:
                    for adm in ADMIN_ID.split(","):
                        try:
                            requests.post(f"https://api.telegram.org/bot{SUPPORT_TOKEN}/sendMessage", json={"chat_id": adm.strip(), "text": f"📩 Support dari {name} @{username} ID:{chat_id}\n\n{text}"}, timeout=5)
                        except: pass
                send_msg(chat_id, "✅ Pesan kekirim ke admin!")
        return "ok", 200
    except:
        return "ok", 200