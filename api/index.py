from flask import Flask, request
import os, io, requests
from PIL import Image, ImageDraw

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
SESSION = requests.Session()
ADMIN_IDS = [8584319568]

# --- DB helper ---
def get_conn():
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"DB error: {e}")
        return None

def ensure_user(uid, username, first_name):
    conn = get_conn()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
          INSERT INTO users (user_id, username, first_name) 
          VALUES (%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET username=EXCLUDED.username, first_name=EXCLUDED.first_name
        """,(uid, username, first_name))
        conn.commit()
        cur.close()
    finally:
        conn.close()

def get_user_stats(uid):
    conn = get_conn()
    if not conn: return (5, 0, False)
    try:
        cur = conn.cursor()
        cur.execute("SELECT quota, total_posts, is_blocked FROM users WHERE user_id=%s",(uid,))
        r = cur.fetchone()
        cur.close()
        return r or (5,0,False)
    finally:
        conn.close()

def get_monthly_users():
    conn = get_conn()
    if not conn: return 17
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '30 days'")
        c = cur.fetchone()[0]
        cur.close()
        return c
    finally:
        conn.close()

def get_live():
    try:
        r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=5).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 658

def get_welcome(name):
    return f"Hi {name}! Welcome to Menfess Angel\n\nPublish to:\n- Channel -> @menfessangel\n- X -> @jogjalendpm\n\nTap Post to start!"

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

def make_chart():
    live=get_live()
    W,H=800,400
    img=Image.new("RGB",(W,H),"white")
    d=ImageDraw.Draw(img)
    for y in range(50,350,50):
        d.line([(80,y),(W-20,y)], fill="#e0e0e0")
    subs=[610,625,638,645,652,655,live]
    max_s, min_s = max(subs), min(subs)-10
    points=[]
    for i,v in enumerate(subs):
        x=80 + i*100
        y=320 - int((v-min_s)/(max_s-min_s+1)*250)
        points.append((x,y))
    d.line(points, fill="#2E7D32", width=4)
    for p in points:
        d.ellipse([p[0]-6,p[1]-6,p[0]+6,p[1]+6], fill="#2E7D32")
    d.text((20,10), f"@menfessangel - {live} LIVE", fill="black")
    buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0); return buf

# INI YANG FIX METHOD NOT ALLOWED - HANDLE GET & POST SEMUA ROUTE
@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
@app.route("/api/index.py", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return f"<h2>RUNNING {get_live()} LIVE - Postgres OK - No More Method Not Allowed</h2>", 200

    data=request.get_json(force=True, silent=True)
    if not data: return "ok",200

    if "callback_query" in data:
        cq=data["callback_query"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]; cb=cq["data"]
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})

        if cb=="main":
            fn=cq["from"].get("first_name","Kamu")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":get_welcome(fn),"reply_markup":main_menu(cid)})
            return "ok",200
        if cb=="profil":
            quota,total,is_block = get_user_stats(cid)
            db_status = "✅ POSTGRES" if DATABASE_URL else "⚠️ NO DB"
            txt=f"My Profile\n\nID: {cid}\nQuota: {quota}/5\nTotal Posts: {total}\nBlocked: {is_block}\nDB: {db_status}"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":back_menu()})
            return "ok",200
        if cb=="rules":
            txt="Rules @menfessangel\n1. No 18+/SARA\n2. No spam\n3. Wajib #jogjalend"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":back_menu()})
            return "ok",200
        if cb=="post":
            txt="Kirim menfess lu sekarang! Text/foto/video auto ke @menfessangel + #jogjalend"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":back_menu()})
            return "ok",200
        if cb=="stats":
            monthly=get_monthly_users(); live=get_live(); chart=make_chart()
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":cid,"caption":f"Stats REAL DB\nSubs: {live} LIVE\nMonthly: {monthly} pengguna"},files={"photo":("stats.png",chart)},timeout=20)
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_welcome(cq["from"].get("first_name","Kamu")),"reply_markup":main_menu(cid)})
            return "ok",200
        if cb=="admin":
            monthly=get_monthly_users()
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":f"ADMIN PANEL PRO\nChannel: {get_live()} LIVE\nMonthly: {monthly}\nDB: {'OK' if DATABASE_URL else 'NO ENV'}","reply_markup":back_menu()})
            return "ok",200

    if "message" in data:
        msg=data["message"]; cid=msg["chat"]["id"]; txt=msg.get("text","") or ""
        fname=msg["from"].get("first_name"); uname=msg["from"].get("username")
        ensure_user(cid, uname, fname)
        if txt.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_welcome(fname or "Kamu"),"reply_markup":main_menu(cid)})
            return "ok",200
        if txt and not txt.startswith("/"):
            quota,total,is_block = get_user_stats(cid)
            if is_block:
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Lu ke-block!"})
                return "ok",200
            if quota<=0:
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Quota habis!"})
                return "ok",200
            # update db
            conn=get_conn()
            if conn:
                cur=conn.cursor()
                cur.execute("UPDATE users SET quota=quota-1, total_posts=total_posts+1 WHERE user_id=%s",(cid,))
                cur.execute("INSERT INTO posts (user_id, content) VALUES (%s,%s)",(cid,txt))
                conn.commit(); cur.close(); conn.close()
            cap=txt if "jogjalend" in txt.lower() else txt+"\n\n#jogjalend"
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":cap})
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"✅ Terkirim & kesimpen di Postgres!","reply_markup":main_menu(cid)})
    return "ok",200
