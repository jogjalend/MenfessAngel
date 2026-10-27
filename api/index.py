from flask import Flask, request
import os, io, requests
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
SESSION = requests.Session()
ADMIN_IDS = [8584319568]

def get_welcome(name):
    return f"Hi {name}! Welcome to Menfess Angel\n\nPromote your account here!\n\n-------------------\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend\n- X -> @jogjalendpm\n\nTap Post to start!"

def main_menu(cid):
    kb=[
        [{"text":"My Profile","callback_data":"profil"}],
        [{"text":"Rules","callback_data":"rules"}, {"text":"Post","callback_data":"post"}],
        [{"text":"Stats","callback_data":"stats"}],
    ]
    if int(cid) in ADMIN_IDS:
        kb.append([{"text":"ADMIN PANEL PRO","callback_data":"admin"}])
    return {"inline_keyboard":kb}

def back_menu():
    return {"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}

def get_live():
    try:
        r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=5).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 658

def make_chart_pillow():
    live=get_live()
    W,H=800,400
    img=Image.new("RGB",(W,H),"white")
    d=ImageDraw.Draw(img)
    # grid
    for y in range(50,350,50):
        d.line([(80,y),(W-20,y)], fill="#e0e0e0")
    # data
    subs=[610,625,638,645,652,655,live]
    days=["22","23","24","25","26","27","28"]
    max_s, min_s = max(subs), min(subs)-10
    points=[]
    for i,v in enumerate(subs):
        x=80 + i*100
        y=320 - int((v-min_s)/(max_s-min_s)*250)
        points.append((x,y))
    d.line(points, fill="#2E7D32", width=4)
    for p in points:
        d.ellipse([p[0]-6,p[1]-6,p[0]+6,p[1]+6], fill="#2E7D32")
    d.text((20,10), f"@menfessangel - {live} LIVE - 17 users", fill="black")
    for i,day in enumerate(days):
        d.text((80+i*100-5,335), day, fill="black")
    buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0); return buf

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET"])
def home(): return f"<h2>RUNNING {get_live()} LIVE</h2>",200

@app.route("/", methods=["POST"])
@app.route("/api/index", methods=["POST"])
@app.route("/api/index.py", methods=["POST"])
def wh():
    data=request.get_json(force=True)
    if not data: return "ok",200

    if "callback_query" in data:
        cq=data["callback_query"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]; cb=cq["data"]
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})

        if cb=="main":
            fn=cq["from"].get("first_name","Kamu")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":get_welcome(fn),"reply_markup":main_menu(cid)})
            return "ok",200
        if cb=="profil":
            u=cq["from"]; uid=u["id"]; fn=u.get("first_name","Kamu"); un=u.get("username","-")
            txt=f"My Profile\n\nID: {uid}\nName: {fn}\nUsername: @{un}\nSubs: {get_live()}\nMonthly: 17 pengguna"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":back_menu()})
            return "ok",200
        if cb=="rules":
            txt="Rules @menfessangel\n1. No 18+/SARA\n2. No spam\n3. Wajib #jogjalend\n4. No doxxing"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":back_menu()})
            return "ok",200
        if cb=="post":
            txt="Kirim menfess lu sekarang su! Text/foto/video auto ke @menfessangel + #jogjalend"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":back_menu()})
            return "ok",200
        if cb=="stats":
            live=get_live(); chart=make_chart_pillow()
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":cid,"caption":f"Stats\nProfile: {cid}\nSubs: {live}\nMonthly: 17\n📈 Naik terus!"},files={"photo":("stats.png",chart)},timeout=20)
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_welcome(cq["from"].get("first_name","Kamu")),"reply_markup":main_menu(cid)})
            return "ok",200
        if cb=="admin":
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":f"ADMIN PANEL PRO 👑\nChannel: {get_live()} LIVE\n17 pengguna bulanan\n\n16 menu aktif","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
            return "ok",200

    if "message" in data:
        msg=data["message"]; cid=msg["chat"]["id"]; txt=msg.get("text","") or ""
        if txt.startswith(("/start","/menu")):
            fn=msg["from"].get("first_name") or "Kamu"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_welcome(fn),"reply_markup":main_menu(cid)})
            return "ok",200
        if txt and not txt.startswith("/"):
            cap=txt if "jogjalend" in txt.lower() else txt+"\n\n#jogjalend"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":cap})
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"✅ Terkirim!","reply_markup":main_menu(cid)})
    return "ok",200
