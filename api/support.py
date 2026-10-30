import os, json, requests

SUPPORT_TOKEN = os.getenv("SUPPORT_TOKEN") or ""
ADMIN_ID = os.getenv("ADMIN_ID") or ""

def send_msg(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{SUPPORT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except: pass

class handler:
    def __call__(self, req):
        return self.handle(req)
    
    def handle(self, req):
        # For Vercel Python runtime
        pass

# Vercel entry point
def handler_func(request):
    return main(request)

def main(req=None):
    # Fallback for different vercel runtimes
    try:
        from flask import Flask, request as flask_request
        app = Flask(__name__)

        @app.route("/", methods=["GET","POST"])
        @app.route("/api/support", methods=["GET","POST"])
        def index():
            if flask_request.method == "GET":
                return "Support OK", 200
            try:
                data = flask_request.get_json(force=True, silent=True) or {}
                if "message" in data:
                    msg = data["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text","")
                    name = msg["from"].get("first_name","")
                    username = msg["from"].get("username","-")
                    if text.startswith("/start"):
                        send_msg(chat_id, f"Hi {name}!\nKirim pertanyaan lu disini.")
                    else:
                        if ADMIN_ID:
                            for adm in ADMIN_ID.split(","):
                                try:
                                    requests.post(f"https://api.telegram.org/bot{SUPPORT_TOKEN}/sendMessage", json={"chat_id": adm.strip(), "text": f"📩 Support dari {name} @{username} ID:{chat_id}\n\n{text}"}, timeout=5)
                                except: pass
                        send_msg(chat_id, "✅ Kekirim ke admin!")
                return "ok", 200
            except:
                return "ok", 200

        return app
    except:
        return "ok"

# Export for Vercel
try:
    from flask import Flask, request
    app = Flask(__name__)
    
    @app.route("/", methods=["GET","POST"])
    @app.route("/api/support", methods=["GET","POST"])
    def support():
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
                    send_msg(chat_id, f"Hi {name}!\nKirim pertanyaan lu disini.")
                else:
                    if ADMIN_ID:
                        for adm in ADMIN_ID.split(","):
                            try:
                                requests.post(f"https://api.telegram.org/bot{SUPPORT_TOKEN}/sendMessage", json={"chat_id": adm.strip(), "text": f"📩 Support dari {name} @{username} ID:{chat_id}\n\n{text}"}, timeout=5)
                            except: pass
                    send_msg(chat_id, "✅ Kekirim ke admin!")
            return "ok", 200
        except Exception as e:
            print(e)
            return "ok", 200
            
except Exception as e:
    print(e)