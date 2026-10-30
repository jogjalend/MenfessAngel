from flask import Flask, request
import os, requests, traceback

app = Flask(__name__)
SUPPORT_TOKEN = os.getenv("SUPPORT_TOKEN") or os.getenv("BOT_TOKEN_SUPPORT") or ""
ADMIN_ID = os.getenv("ADMIN_ID") or ""
LOG_CHANNEL = os.getenv("LOG_CHANNEL") or ""

def send_support(chat_id, text, kb=None):
    try:
        payload = {"chat_id": chat_id, "text": text}
        if kb: payload["reply_markup"] = kb
        requests.post(f"https://api.telegram.org/bot{SUPPORT_TOKEN}/sendMessage", json=payload, timeout=10)
    except: pass

@app.route("/", methods=["GET","POST"])
@app.route("/api/support", methods=["GET","POST"])
def support_handler():
    try:
        if request.method == "GET":
            return "Support Bot OK", 200
        
        data = request.get_json(force=True, silent=True) or {}
        
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text","")
            name = msg["from"].get("first_name","")
            
            if text.startswith("/start"):
                send_support(chat_id, f"Hi {name}!\n\nKirim pertanyaan / bug / saran lu disini, nanti diterusin ke admin JogjaLend.\n\nTulis langsung aja.")
            else:
                # forward ke admin
                if ADMIN_ID:
                    for admin in ADMIN_ID.split(","):
                        admin = admin.strip()
                        if admin:
                            try:
                                fwd_text = f"📩 Support dari {name} (@{msg['from'].get('username','-')}) ID:{chat_id}\n\n{text}"
                                requests.post(f"https://api.telegram.org/bot{SUPPORT_TOKEN}/sendMessage", json={"chat_id": admin, "text": fwd_text}, timeout=5)
                            except: pass
                send_support(chat_id, "✅ Pesan lu udah kekirim ke admin, tunggu dibales ya!")
                
        return "ok", 200
    except Exception as e:
        print(f"[SUPPORT ERROR] {e}\n{traceback.format_exc()}")
        # PENTING: tetep return 200 biar gak 500
        return "ok", 200
