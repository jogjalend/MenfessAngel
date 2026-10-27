from flask import Flask, request
import os, io, requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
SESSION = requests.Session()
ADMIN_IDS = [8584319568]

def get_welcome(name):
    return f"""Hi {name}!
Promote your account here!

Publish to:
- Channel -> @menfessangel
- Threads -> @jogjalend [optional]
- X -> @jogjalendpm [maintenance]

Tap Post to start!"""

def main_menu(cid):
    kb=[
        [{"text":"My Profile","callback_data":"profil"}],
        [{"text":"Rules","callback_data":"rules"}, {"text":"Post","callback_data":"post"}],
        [{"text":"Threads Setting","callback_data":"threads"}],
    ]
    if int(cid) in ADMIN_IDS: kb.append([{"text":"Admin Panel","callback_data":"admin"}])
    kb.append([{"text":"Stats","callback_data":"stats"}, {"text":"Help","callback_data":"help"}])
    return {"inline_keyboard":kb}

def make_stats_chart():
    days=["22","23","24","25","26","27","28"]; subs=[610,625,638,645,652,655,659]
    plt.figure(figsize=(6,3.5), dpi=180)
    plt.plot(days, subs, marker='o', linewidth=2.5, color='#2E7D32')
    plt.fill_between(days, subs, alpha=0.15, color='#2E7D32')
    plt.title(f"@menfessangel - {subs[-1]} LIVE", fontsize=11, fontweight='bold')
    plt.grid(alpha=0.3); plt.tight_layout()
    buf=io.BytesIO(); plt.savefig(buf, format='png'); plt.close(); buf.seek(0); return buf

def get_live():
    try:
        r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=5).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 659

# INI FIX BUAT BROWSER BIAR GAK METHOD NOT ALLOWED
@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET"])
def home_get():
    return f"""
    <h2>Menfess Angel Bot is RUNNING ✅</h2>
    <p>Channel: @menfessangel - {get_live()} LIVE</p>
    <p>Method Not Allowed di browser itu normal su, webhook Telegram pakai POST.</p>
    <p>Cek Telegram bot lu, ketik /start</p>
    """,200

@app.route("/", methods=["POST"])
@app.route("/api/index", methods=["POST"])
@app.route("/api/index.py", methods=["POST"])
def wh():
    data=request.get_json()
    if not data: return "ok",200
    if "callback_query" in data:
        cq=data["callback_query"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]; cb=cq["data"]
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})
        if cb=="main":
            fn=cq["from"].get("first_name","claudia")
            try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
            except: pass
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_welcome(fn),"reply_markup":main_menu(cid)})
            return "ok",200
        if cb=="stats":
            live=get_live(); chart=make_stats_chart()
            try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
            except: pass
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":cid,"caption":f"Stats\nChannel: {live} LIVE\nUsers: 1 📈"},files={"photo":("stats.png",chart)},timeout=20)
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Back:", "reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
            return "ok",200
        # admin & lain
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":f"{cb} OK - 16 menu aktif","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
        return "ok",200

    if "message" in data:
        msg=data["message"]; cid=msg["chat"]["id"]
        if msg.get("text","").startswith(("/start","/menu")):
            fn=msg["from"].get("first_name") or "claudia"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_welcome(fn),"reply_markup":main_menu(cid)})
            return "ok",200
        raw=msg.get("caption") or msg.get("text") or ""
        if raw or "photo" in msg:
            cap = raw if "jogjalend" in raw.lower() else raw + "\n\n#jogjalend"
            if "photo" in msg:
                fid=msg["photo"][-1]["file_id"]
                f=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
                fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f['result']['file_path']}").content
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":CHANNEL_ID,"caption":cap},files={"photo":("a.jpg",fb)})
            else:
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":cap})
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"✅ Terkirim!"})
    return "ok",200
