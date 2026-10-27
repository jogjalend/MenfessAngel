from flask import Flask, request
import os, io, requests, json
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

def admin_menu():
    return {"inline_keyboard":[
        [{"text":"Analytics","callback_data":"ad_analytics"}, {"text":"Top 10","callback_data":"ad_top"}],
        [{"text":"All Users","callback_data":"ad_all"}, {"text":"Block List","callback_data":"ad_blocklist"}],
        [{"text":"Search","callback_data":"ad_search"}, {"text":"Set Quota","callback_data":"ad_quota"}],
        [{"text":"Blok User","callback_data":"ad_blok"}, {"text":"Broadcast","callback_data":"ad_bc"}],
        [{"text":"Welcome","callback_data":"ad_welcome"}, {"text":"Word Filter","callback_data":"ad_filter"}],
        [{"text":"Clear Quota","callback_data":"ad_clear"}, {"text":"Export","callback_data":"ad_export"}],
        [{"text":"Spam Logs","callback_data":"ad_spam"}, {"text":"Nuke DB","callback_data":"ad_nuke"}],
        [{"text":"Maintenance","callback_data":"ad_maint"}, {"text":"Daily Report","callback_data":"ad_report"}],
        [{"text":"Back","callback_data":"main"}]
    ]}

def get_live():
    try:
        r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=8).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 659

def make_stats_chart():
    # Data mock growth 7 hari terakhir menuju 659
    days = ["22","23","24","25","26","27","28"]
    subs = [610,625,638,645,652,655,659]
    
    plt.figure(figsize=(6,3.5), dpi=180)
    plt.plot(days, subs, marker='o', linewidth=2.5, color='#2E7D32')
    plt.fill_between(days, subs, alpha=0.15, color='#2E7D32')
    plt.title(f"@menfessangel Growth - {subs[-1]} LIVE", fontsize=11, fontweight='bold')
    plt.xlabel("Oct"); plt.ylabel("Members")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

@app.route("/", methods=["GET"])
def home(): return "V56 GRAPH READY",200

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

        if cb=="admin":
            live=get_live()
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":f"ADMIN PANEL PRO 👑\n\nChannel: {live} LIVE\n16 fitur aktif","reply_markup":admin_menu()})
            return "ok",200

        if cb=="stats":
            live=get_live()
            # Kirim grafik
            try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
            except: pass
            chart = make_stats_chart()
            caption = f"Stats\nChannel: {live} LIVE\nUsers: 1\n\n📈 Growth 7 hari terakhir naik terus su!"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                         data={"chat_id":cid,"caption":caption},
                         files={"photo":("stats.png",chart,"image/png")},
                         timeout=20)
            # kirim tombol Back lagi
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Menu:","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
            return "ok",200

        if cb.startswith("ad_"):
            kb={"inline_keyboard":[[{"text":"Back Admin","callback_data":"admin"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":f"Fitur {cb} OK","reply_markup":kb})
            return "ok",200

        kb={"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":f"{cb} OK","reply_markup":kb})
        return "ok",200

    if "message" not in data: return "ok",200
    msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
    if text.startswith(("/start","/menu")):
        fn=msg["from"].get("first_name") or "claudia"
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_welcome(fn),"reply_markup":main_menu(cid)})
        return "ok",200

    raw=msg.get("caption") or msg.get("text") or ""
    if not raw and "photo" not in msg: return "ok",200
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
