import os, json, random, string, time, datetime, traceback, re, io, html
from flask import Flask, request, jsonify
import requests
from PIL import Image, ImageDraw, ImageFont
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# ============ CONFIG ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()]
CHANNEL_ID = os.getenv("CHANNEL_ID","@menfessangel")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME","menfessangel")
HASHTAG = os.getenv("HASHTAG","#JogjaLend")
SUPPORT_BOT = "@joglendsupportBot"
TEAM = "@jogja_lend"
DATABASE_URL = os.getenv("DATABASE_URL")
THREADS_TOKEN = os.getenv("THREADS_TOKEN","")
BOT_VERSION = "V110.6"
PYTHON_VERSION = "3.12"
DB_NAME = "PostgreSQL (Neon)"

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ============ FANCY FONT ============
_FANCY_MAP = {}
_normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_fancy = "𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝗏𝗐𝗑𝗒𝗓𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"
for a,b in zip(_normal, _fancy):
    _FANCY_MAP[a]=b

def F(text):
    return "".join(_FANCY_MAP.get(c,c) for c in text)

SEP = "●-----------------------------------------------------●"

# ============ DB ============
def get_db():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    try:
        db = get_db()
        if not db: return
        cur = db.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_banned BOOLEAN DEFAULT FALSE,
            warnings INT DEFAULT 0,
            threads_on BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS posts(
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            message_id BIGINT,
            channel_msg_id BIGINT,
            type TEXT,
            caption TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS quota(
            user_id BIGINT,
            date DATE,
            text_count INT DEFAULT 0,
            media_count INT DEFAULT 0,
            PRIMARY KEY(user_id, date)
        );
        """)
        db.commit(); db.close()
    except Exception as e:
        print("DB init error", e)

init_db()

def get_user(user_id):
    try:
        db=get_db(); cur=db.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=%s",(user_id,))
        r=cur.fetchone(); db.close(); return r
    except: return None

def upsert_user(user):
    try:
        db=get_db(); cur=db.cursor()
        cur.execute("""INSERT INTO users(user_id,username,first_name) VALUES(%s,%s,%s)
        ON CONFLICT(user_id) DO UPDATE SET username=EXCLUDED.username, first_name=EXCLUDED.first_name""",
        (user.get("id"), user.get("username",""), user.get("first_name","")))
        db.commit(); db.close()
    except Exception as e: print(e)

def get_quota(user_id):
    today = datetime.date.today()
    try:
        db=get_db(); cur=db.cursor()
        cur.execute("SELECT * FROM quota WHERE user_id=%s AND date=%s",(user_id,today))
        r=cur.fetchone(); db.close()
        return r or {"text_count":0,"media_count":0}
    except: return {"text_count":0,"media_count":0}

def add_quota(user_id, is_media):
    today = datetime.date.today()
    try:
        db=get_db(); cur=db.cursor()
        cur.execute("""INSERT INTO quota(user_id,date,text_count,media_count) VALUES(%s,%s,%s,%s)
        ON CONFLICT(user_id,date) DO UPDATE SET text_count=quota.text_count+EXCLUDED.text_count, media_count=quota.media_count+EXCLUDED.media_count""",
        (user_id,today, 0 if is_media else 1, 1 if is_media else 0))
        db.commit(); db.close()
    except Exception as e: print(e)

# ============ TELEGRAM HELPERS ============
def tg(method, data=None, files=None):
    try:
        r = requests.post(f"{API}/{method}", data=data, files=files, timeout=30)
        return r.json()
    except Exception as e:
        print("TG error", e); return {}

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    data={"chat_id":chat_id,"text":text}
    if reply_markup: data["reply_markup"]=json.dumps(reply_markup)
    if parse_mode: data["parse_mode"]=parse_mode
    return tg("sendMessage", data)

def edit_message_fast(chat_id, msg_id, text, reply_markup=None, fancy=True):
    if fancy:
        # Jangan convert yang ada di dalam `...` dan @username / link
        parts = re.split(r'(`[^`]+`|@\w+)', text)
        out=""
        for p in parts:
            if p.startswith("`") or p.startswith("@"):
                out+=p
            else:
                out+=F(p)
        text=out
    data={"chat_id":chat_id,"message_id":msg_id,"text":text}
    if reply_markup: data["reply_markup"]=json.dumps(reply_markup)
    return tg("editMessageText", data)

def delete_message(chat_id, msg_id):
    tg("deleteMessage",{"chat_id":chat_id,"message_id":msg_id})

# ============ KEYBOARDS ============
def get_main_keyboard(is_admin=False):
    kb={"inline_keyboard":[
        [{"text":"📮 Post","callback_data":"post_menu"}],
        [{"text":"📊 Stats","callback_data":"stats"},{"text":"ℹ️ Info Bot","callback_data":"info_bot"}],
        [{"text":"⚙️ Threads Setting","callback_data":"threads_setting"}],
    ]}
    if is_admin:
        kb["inline_keyboard"].append([{"text":"🛠️ System Tools","callback_data":"system_tools"}])
        kb["inline_keyboard"].append([{"text":"👥 List Users","callback_data":"list_users"}])
    return kb

def get_back_keyboard():
    return {"inline_keyboard":[[{"text":"🔙 Back","callback_data":"back_main"}]]}

def get_post_keyboard():
    return {"inline_keyboard":[
        [{"text":"📝 Text","callback_data":"post_text"},{"text":"🖼️ Media","callback_data":"post_media"}],
        [{"text":"🔙 Back","callback_data":"back_main"}]
    ]}

# ============ WATERMARK ============
def add_watermark(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img, "RGBA")
        w,h = img.size
        text = f"{HASHTAG} | @jogja_lend"
        try: font = ImageFont.truetype("arial.ttf", int(w*0.035))
        except: font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        x, y = w-tw-20, h-th-20
        draw.rectangle([x-10,y-5,x+tw+10,y+th+5], fill=(0,0,0,120))
        draw.text((x,y), text, fill=(255,255,255,255), font=font)
        out = io.BytesIO(); img.save(out, format="JPEG", quality=88)
        out.seek(0); return out
    except Exception as e:
        print("watermark err", e); return io.BytesIO(image_bytes)

# ============ HANDLERS ============
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status":"ok","version":BOT_VERSION,"bot":"JogjaLend"})

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(force=True, silent=True) or {}
        # Callback
        if "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            user_id = cq["from"]["id"]
            cdata = cq.get("data","")
            upsert_user(cq["from"])
            tg("answerCallbackQuery",{"callback_query_id":cq["id"]})
            is_admin = user_id in ADMIN_IDS

            if cdata=="back_main":
                edit_message_fast(chat_id, msg_id, f"Selamat datang di JogjaLend Bot!\n\nSilahkan pilih menu di bawah.", get_main_keyboard(is_admin))

            elif cdata=="post_menu":
                edit_message_fast(chat_id, msg_id, "Pilih jenis postingan:", get_post_keyboard())

            elif cdata=="post_text":
                edit_message_fast(chat_id, msg_id, "Kirim text menfess kamu sekarang.\nKuota: 5 text / hari", get_back_keyboard())

            elif cdata=="post_media":
                edit_message_fast(chat_id, msg_id, "Kirim foto / video + caption sekarang.\nKuota: 5 media / hari", get_back_keyboard())

            elif cdata=="stats":
                q = get_quota(user_id)
                edit_message_fast(chat_id, msg_id, f"Stats Kamu:\nText hari ini: {q['text_count']}/5\nMedia hari ini: {q['media_count']}/5\nThreads: ON\nReset: 00:00 WIB", get_back_keyboard())

            elif cdata=="threads_setting":
                u = get_user(user_id)
                cur = u["threads_on"] if u else True
                try:
                    db=get_db(); cur2=db.cursor()
                    cur2.execute("UPDATE users SET threads_on=%s WHERE user_id=%s",(not cur, user_id))
                    db.commit(); db.close()
                except: pass
                edit_message_fast(chat_id, msg_id, f"Threads Setting: {'ON' if not cur else 'OFF'}\nPost kamu akan {'ikut' if not cur else 'tidak'} di-post ke Threads.", get_back_keyboard())

            # ===== INFO BOT - FINAL PAS =====
            elif cdata=="info_bot":
                info_text = f"""Bot Information

{F("JogjaLend Bot adalah bot yang dikembangkan oleh tim")} @jogja_lend.
`Versi Bot : {BOT_VERSION}`
`Database : {DB_NAME}`

{F("Untuk pertanyaan tentang penggunaan bot, saran untuk fitur baru atau laporan bug Anda dapat menulis ke")} @joglendsupportBot."""
                edit_message_fast(chat_id, msg_id, info_text, get_back_keyboard(), fancy=False)

            # ===== SYSTEM TOOLS =====
            elif cdata=="system_tools":
                if not is_admin:
                    edit_message_fast(chat_id, msg_id, "Akses ditolak.", get_back_keyboard()); return jsonify({"ok":True})
                try:
                    db=get_db(); cur=db.cursor()
                    cur.execute("SELECT COUNT(*) as c FROM users"); total=cur.fetchone()["c"]
                    cur.execute("SELECT COUNT(*) as c FROM posts WHERE DATE(created_at)=CURRENT_DATE"); today_posts=cur.fetchone()["c"]
                    db.close()
                except: total=0; today_posts=0
                edit_message_fast(chat_id, msg_id, f"System Tools\n\nTotal Users: {total}\nPost Hari Ini: {today_posts}\nVersi: {BOT_VERSION}\nPython: {PYTHON_VERSION}\nDatabase: {DB_NAME}\nUptime: OK", get_back_keyboard())

            # ===== LIST USERS =====
            elif cdata=="list_users":
                if not is_admin:
                    edit_message_fast(chat_id, msg_id, "Akses ditolak.", get_back_keyboard()); return jsonify({"ok":True})
                try:
                    db=get_db(); cur=db.cursor()
                    cur.execute("SELECT user_id, username, first_name, is_banned FROM users ORDER BY created_at DESC LIMIT 20")
                    rows=cur.fetchall(); db.close()
                    txt="List Users (20 terbaru):\n\n"
                    for r in rows:
                        txt+=f"- {r['first_name']} @{r['username']} | ID: {r['user_id']} {'[BANNED]' if r['is_banned'] else ''}\n"
                    edit_message_fast(chat_id, msg_id, txt, get_back_keyboard())
                except Exception as e:
                    edit_message_fast(chat_id, msg_id, f"Error: {e}", get_back_keyboard())

            return jsonify({"ok":True})

        # Message
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            text = msg.get("text","")
            upsert_user(msg["from"])
            is_admin = user_id in ADMIN_IDS
            u = get_user(user_id)
            if u and u["is_banned"]:
                send_message(chat_id, "Kamu di-banned."); return jsonify({"ok":True})

            if text.startswith("/start"):
                send_message(chat_id, "Selamat datang di JogjaLend Bot!\n\nSilahkan pilih menu di bawah.", get_main_keyboard(is_admin))
                return jsonify({"ok":True})

            if text.startswith("/info"):
                info_text = f"""Bot Information

{F("JogjaLend Bot adalah bot yang dikembangkan oleh tim")} @jogja_lend.
`Versi Bot : {BOT_VERSION}`
`Database : {DB_NAME}`

{F("Untuk pertanyaan tentang penggunaan bot, saran untuk fitur baru atau laporan bug Anda dapat menulis ke")} @joglendsupportBot."""
                send_message(chat_id, info_text)
                return jsonify({"ok":True})

            # Post Text
            if text and not text.startswith("/"):
                q = get_quota(user_id)
                if q["text_count"] >= 5:
                    send_message(chat_id, "Kuota text habis! Coba lagi besok 00:00 WIB")
                    return jsonify({"ok":True})
                caption = f"{text}\n\n{HASHTAG}\nvia @jogja_lend"
                r = tg("sendMessage",{"chat_id":CHANNEL_ID,"text":caption})
                if r.get("ok"):
                    add_quota(user_id, False)
                    send_message(chat_id, "Menfess sent! ✅", get_main_keyboard(is_admin))
                else:
                    send_message(chat_id, "Gagal kirim. Coba lagi.")
                return jsonify({"ok":True})

            # Post Media
            if "photo" in msg or "video" in msg:
                q = get_quota(user_id)
                if q["media_count"] >= 5:
                    send_message(chat_id, "Kuota media habis!")
                    return jsonify({"ok":True})
                caption = msg.get("caption","") + f"\n\n{HASHTAG}\nvia @jogja_lend"
                if "photo" in msg:
                    file_id = msg["photo"][-1]["file_id"]
                    # get file path
                    f = tg("getFile",{"file_id":file_id})
                    if f.get("ok"):
                        fp = f["result"]["file_path"]
                        img_bytes = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
                        wm = add_watermark(img_bytes)
                        tg("sendPhoto",{"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":("img.jpg", wm)})
                elif "video" in msg:
                    file_id = msg["video"]["file_id"]
                    tg("sendVideo",{"chat_id":CHANNEL_ID,"video":file_id,"caption":caption})
                add_quota(user_id, True)
                send_message(chat_id, "Menfess media sent! ✅", get_main_keyboard(is_admin))
                return jsonify({"ok":True})

        return jsonify({"ok":True})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"ok":False,"error":str(e)})

if __name__=="__main__":
    app.run(debug=True)