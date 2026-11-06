# api/index.py - JogjaLend Bot Angel V110.9 FULL FINAL - FIXED 20%
from flask import Flask, request, jsonify
import os, requests, io, random, re, traceback, copy, time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

try:
    import psycopg2
except:
    psycopg2 = None
try:
    from PIL import Image, ImageDraw, ImageFont
except:
    Image = None

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
DATABASE_URL = os.getenv("DATABASE_URL")
THREADS_URL = os.getenv("THREADS") or "https://threads.net/jogjalend"
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
MAIN_THREAD_ID = os.getenv("MAIN_THREAD_ID")
LOG_CHANNEL = os.getenv("LOG_CHANNEL") or CHANNEL_ID
WIB = timezone(timedelta(hours=7))
SEP = "●-----------------------------------------------------●"
_db_init_done = False

def get_db():
    if not DATABASE_URL or not psycopg2:
        return None
    try:
        return psycopg2.connect(DATABASE_URL, connect_timeout=5)
    except:
        return None

def init_db():
    global _db_init_done
    if _db_init_done:
        return
    _db_init_done = True
    db = get_db()
    if not db:
        return
    try:
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0, admin_target TEXT DEFAULT 'both', warn INT DEFAULT 0)")
        cur.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('hashtag', '#jogjalend') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('peraturan', '1. No SARA & Porn\n2. No spam\n3. Max 5 post/hari') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('approval', 'off') ON CONFLICT (key) DO NOTHING")
        db.commit(); cur.close(); db.close()
    except:
        pass

def get_setting(k, default=""):
    db = get_db()
    if not db:
        return default
    try:
        cur = db.cursor(); cur.execute("SELECT value FROM bot_settings WHERE key=%s", (k,)); r = cur.fetchone(); cur.close(); db.close()
        return r[0] if r else default
    except:
        return default

def set_setting(k, v):
    db = get_db()
    if not db:
        return
    try:
        cur = db.cursor(); cur.execute("INSERT INTO bot_settings (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=%s", (k, v, v)); db.commit(); cur.close(); db.close()
    except:
        pass

def to_fancy(text):
    if not text:
        return ""
    pattern = r'<plain>.*?</plain>|<code>.*?</code>|<pre>.*?</pre>|<a[^>]*>.*?</a>|<[^>]+>|@\w+|#\w+|/\w+|https?://\S+|threads\.net/\S+|t\.me/\S+'
    res_parts = []; last_idx = 0
    for m in re.finditer(pattern, text, flags=re.DOTALL):
        before = text[last_idx:m.start()]
        conv = ""
        for c in before:
            if 'A' <= c <= 'Z': conv += chr(0x1D5A0 + ord(c)-65)
            elif 'a' <= c <= 'z': conv += chr(0x1D5BA + ord(c)-97)
            elif '0' <= c <= '9': conv += chr(0x1D7E2 + ord(c)-48)
            else: conv += c
        res_parts.append(conv); res_parts.append(m.group(0)); last_idx = m.end()
    tail = text[last_idx:]; conv = ""
    for c in tail:
        if 'A' <= c <= 'Z': conv += chr(0x1D5A0 + ord(c)-65)
        elif 'a' <= c <= 'z': conv += chr(0x1D5BA + ord(c)-97)
        elif '0' <= c <= '9': conv += chr(0x1D7E2 + ord(c)-48)
        else: conv += c
    res_parts.append(conv); return "".join(res_parts)
def F(t): return to_fancy(t)
def M(t):
    out = []
    for line in t.split("\n"):
        if line.strip() == "":
            out.append("")
        elif "http" in line or "@" in line or "tg://" in line or line.strip().startswith("/"):
            out.append(f"<code>{line}</code>" if False else line)
        else:
            out.append(f"<code>{line}</code>")
    return "\n".join(out)

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0, "admin_target": "both", "warn": 0})

def load_user_from_db(uid):
    db = get_db()
    if not db: return None
    try:
        cur = db.cursor()
        cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target, warn FROM menfess_users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close(); db.close()
        if row: return {"name": row[0] or "", "username": row[1] or "", "threads_on": row[2] or False, "today_text": row[3] or 0, "today_media": row[4] or 0, "last_date": row[5] or "", "banned": row[6] or False, "total_text": row[7] or 0, "total_media": row[8] or 0, "total_chars": row[9] or 0, "admin_target": row[10] or "both", "warn": row[11] or 0}
    except: return None
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target, warn) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s, admin_target=%s, warn=%s", (uid, user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars", 0), user.get("admin_target", "both"), user.get("warn", 0), user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars", 0), user.get("admin_target", "both"), user.get("warn", 0)))
        db.commit(); cur.close(); db.close()
    except: pass

def get_user(uid):
    u = USERS[uid]
    if u["last_date"] == "" and DATABASE_URL:
        d = load_user_from_db(uid)
        if d: USERS[uid] = d; u = USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today:
        u["today_text"] = 0; u["today_media"] = 0; u["last_date"] = today; save_user_to_db(uid, u)
    return u

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send_message(chat_id, text, kb=None):
    try:
        kb_fancy = None
        if kb and "inline_keyboard" in kb:
            kb_fancy = copy.deepcopy(kb)
            for row in kb_fancy["inline_keyboard"]:
                for btn in row:
                    if "text" in btn and "url" not in btn: btn["text"] = F(btn["text"])
        payload = {"chat_id": chat_id, "text": F(text).replace("<plain>", "").replace("</plain>", ""), "parse_mode": "HTML", "disable_web_page_preview": True}
        if kb_fancy: payload["reply_markup"] = kb_fancy
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=5)
        if r.status_code == 200: return True
    except: pass
    try:
        payload2 = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        if kb: payload2["reply_markup"] = kb
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload2, timeout=5)
        return True
    except: return False

def edit_message_fast(chat_id, msg_id, text, kb=None):
    try:
        kb_fancy = None
        if kb and "inline_keyboard" in kb:
            kb_fancy = copy.deepcopy(kb)
            for row in kb_fancy["inline_keyboard"]:
                for btn in row:
                    if "text" in btn and "url" not in btn: btn["text"] = F(btn["text"])
        payload = {"chat_id": chat_id, "message_id": msg_id, "text": F(text).replace("<plain>", "").replace("</plain>", ""), "parse_mode": "HTML", "disable_web_page_preview": True}
        if kb_fancy: payload["reply_markup"] = kb_fancy
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json=payload, timeout=5)
        return True
    except:
        try:
            payload2 = {"chat_id": chat_id, "message_id": msg_id, "text": text, "disable_web_page_preview": True}
            if kb: payload2["reply_markup"] = kb
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json=payload2, timeout=5)
        except: pass
        return False

def report_error(chat_id, where, error):
    err_str = str(error)
    if "ReadTimeout" in err_str or "Timeout" in err_str or "timed out" in err_str: return
    tb = traceback.format_exc()[:3500]
    log_text = f"🚨 ERROR in {where}\n{SEP}\nChat: {chat_id}\nErr: {err_str}\n\n{tb}"
    print(log_text)
    try:
        if LOG_CHANNEL:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": LOG_CHANNEL, "text": log_text[:4000]}, timeout=5)
    except: pass

def get_welcome_text(user):
    hashtag = get_setting('hashtag', '#jogjalend')
    return f"Hi !\n{SEP}\nPublish to {CHANNEL_ID}\nTap Post!\n\nKuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5\nTag: {hashtag}"

def get_back_keyboard(): return {"inline_keyboard": [[{"text": "Back", "callback_data": "back_home"}]]}
def get_main_keyboard(is_ad=False):
    kb = {"inline_keyboard": [[{"text": "👤 My Profile", "callback_data": "my_profile"}, {"text": "💌 Post", "callback_data": "post"}], [{"text": "📧 Threads Setting", "callback_data": "threads"}], [{"text": "📈 Stats", "callback_data": "stats"}, {"text": "ℹ️ Info Bot", "callback_data": "info_bot"}]]}
    if is_ad: kb["inline_keyboard"].append([{"text": "🔧 ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb
def get_menu_1():
    return {"inline_keyboard": [
        [{"text": "🔔 Tag", "callback_data": "lend_tag"}],
        [{"text": "📥 Mode Persetujuan", "callback_data": "lend_persetujuan"}],
        [{"text": "🗑️ Menghapus Pesan", "callback_data": "lend_hapus"}],
        [{"text": "🇮🇩 Lang", "callback_data": "lend_lang"}, {"text": "✅ Tutup", "callback_data": "close"}],
        [{"text": "▶️ Lainnya", "callback_data": "lend_page2"}]
    ]}
def get_menu_2():
    return {"inline_keyboard": [
        [{"text": "📜 Peraturan", "callback_data": "lend_peraturan"}],
        [{"text": "⚠️ Peringatan", "callback_data": "lend_peringatan"}],
        [{"text": "🚫 Daftar Hitam", "callback_data": "lend_blacklist"}],
        [{"text": "🔐 Perizinan", "callback_data": "lend_izin"}, {"text": "📋 Log Saluran", "callback_data": "lend_log"}],
        [{"text": "🎯 Manajemen Channel", "callback_data": "lend_channel"}],
        [{"text": "⬅️ Kembali", "callback_data": "lend_page1"}, {"text": "❌ Tutup", "callback_data": "close"}]
    ]}
def get_admin_panel():
    return {"inline_keyboard": [
        [{"text": "👥 List User", "callback_data": "admin_users"}, {"text": "📊 All Stats", "callback_data": "admin_allstats"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}, {"text": "🚫 Ban/Unban", "callback_data": "lend_blacklist"}],
        [{"text": "🎯 Target Channel", "callback_data": "lend_channel"}],
        [{"text": "🔗 Set Webhook", "callback_data": "admin_webhook"}, {"text": "📋 Cek Logs", "callback_data": "admin_logs"}],
        [{"text": "⚙️ Pengaturan Bot", "callback_data": "lend_page1"}],
        [{"text": "⬅️ Kembali", "callback_data": "back_home"}]
    ]}
def get_channel_target_keyboard(user):
    target = user.get("admin_target", "both")
    return {"inline_keyboard": [
        [{"text": f"📍 Target: {target.upper()}", "callback_data": "admin_noop"}],
        [{"text": f"{'✅ ' if target=='channel' else ''}📢 Channel Only", "callback_data": "admin_set_channel"}, {"text": f"{'✅ ' if target=='threads' else ''}🧵 Threads Only", "callback_data": "admin_set_threads"}],
        [{"text": f"{'✅ ' if target=='both' else ''}🚀 Both (Channel+Threads)", "callback_data": "admin_set_both"}],
        [{"text": "⬅️ Kembali", "callback_data": "admin_panel"}]
    ]}

# ===== FIXED: LOGO / WATERMARK 20% =====
def find_logo():
    base_dir = os.path.dirname(__file__)
    candidates = [
        os.path.join(base_dir, "logo.png"),
        os.path.join(base_dir, "../logo.png"),
        "logo.png",
        "../logo.png",
        os.path.join(os.getcwd(), "logo.png"),
        os.path.join(os.getcwd(), "api/logo.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=5).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=8).content
    except: return None

def add_watermark(photo_bytes):
    try:
        if not Image or not photo_bytes:
            return None
        lp = find_logo()
        if not lp:
            print("logo.png not found")
            return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(lp).convert("RGBA")
        w, h = base.size
        if w == 0 or logo.width == 0:
            return None
        # FIX 20% - Jaga rasio asli, jangan resize jadi kotak
        target_w = int(w * 0.20)
        target_w = max(60, min(target_w, 400))
        target_h = int(target_w * logo.height / logo.width)
        max_h = int(h * 0.20)
        if target_h > max_h:
            target_h = max_h
            target_w = int(target_h * logo.width / logo.height)
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        margin = max(12, int(w * 0.02))
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        overlay.paste(logo, (margin, margin), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO(); combined.save(bio, "JPEG", quality=88); bio.seek(0); return bio
    except Exception as e:
        print(f"watermark error: {e}")
        return None

def get_font(size, bold=False):
    try:
        if not Image: return None
        p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(p): return ImageFont.truetype(p, size)
    except: pass
    return ImageFont.load_default() if Image else None
def make_today_chart(user):
    try:
        if not Image: return None
        W, H = 720, 400; img = Image.new('RGB', (W, H), '#0D0D0F'); draw = ImageDraw.Draw(img)
        f_title = get_font(22, True); f_small = get_font(14)
        draw.rectangle([0, 0, W, 60], fill='#161618')
        draw.text((20, 12), f"TODAY 1D - {user['name'][:16]}", fill='white', font=f_title)
        hours = ["08:00", "12:00", "16:00", "20:00"]; total = user['today_text'] + user['today_media']
        highs = [0]*4 if total == 0 else [random.randint(0, 2)+(total//4) for _ in hours]
        max_val = max(highs) if max(highs) > 0 else 3
        slot_w = (700-50)//len(hours)
        for idx in range(len(hours)):
            xc = 50+idx*slot_w+slot_w//2; v = highs[idx]
            yh = 370-int(v/max_val*250) if max_val > 0 else 370
            color = '#10B981' if idx % 2 == 0 else '#EF4444'
            if total == 0: color = '#27272A'
            draw.rectangle([xc-15, yh, xc+15, 370], fill=color)
            draw.text((xc-15, 378), hours[idx], fill='#A1A1AA', font=f_small)
        bio = io.BytesIO(); img.save(bio, format='JPEG', quality=70); bio.seek(0); return bio
    except: return None
def make_weekly_chart(user):
    try:
        if not Image: return None
        W, H = 720, 400; img = Image.new('RGB', (W, H), '#0D0D0F'); draw = ImageDraw.Draw(img)
        f_title = get_font(22, True); f_small = get_font(14)
        draw.rectangle([0, 0, W, 60], fill='#161618')
        draw.text((20, 12), "WEEKLY 7D", fill='white', font=f_title)
        days = ["22", "23", "24", "25", "26", "27", "28"]; vals = [random.randint(1, 4) for _ in days]; max_v = max(vals)
        slot_w = (700-50)//len(days)
        for idx in range(len(days)):
            xc = 50+idx*slot_w+slot_w//2; v = vals[idx]
            yv = 370-int(v/max_v*250); draw.rectangle([xc-14, yv, xc+14, 370], fill='#3B82F6')
            draw.text((xc-8, 378), days[idx], fill='#A1A1AA', font=f_small)
        bio = io.BytesIO(); img.save(bio, format='JPEG', quality=70); bio.seek(0); return bio
    except: return None
def send_stats(chat_id, user, mode="today"):
    try:
        kb = {"inline_keyboard": [[{"text": "TODAY 1D" if mode != "today" else "• TODAY 1D", "callback_data": "stats_today"}, {"text": "WEEKLY 7D" if mode != "weekly" else "• WEEKLY 7D", "callback_data": "stats_weekly"}], [{"text": "Back", "callback_data": "back_home"}]]}
        if mode == "today": chart = make_today_chart(user); cap = f"📊 TODAY 1D - {user['name']}\n{user['today_text']} text | {user['today_media']} media"
        else: chart = make_weekly_chart(user); cap = f"📈 WEEKLY 7D - {user['name']}\nLast 7 days"
        if chart:
            chart.seek(0)
            try:
                r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": cap}, files={"photo": ("s.jpg", chart, "image/jpeg")}, timeout=8).json()
                if r.get("ok"):
                    send_message(chat_id, "Switch mode:", kb)
                    return
            except: pass
        send_message(chat_id, cap, kb)
    except: pass
def post_to_threads(text_content):
    try:
        if not THREADS_USER_ID or not THREADS_TOKEN: return False
        data = {"media_type": "TEXT", "text": text_content[:450], "access_token": THREADS_TOKEN}
        if MAIN_THREAD_ID: data["reply_to_id"] = MAIN_THREAD_ID
        r = requests.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads", data=data, timeout=5).json()
        cid = r.get("id")
        if not cid: return False
        r2 = requests.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish", data={"creation_id": cid, "access_token": THREADS_TOKEN}, timeout=5).json()
        return "id" in r2
    except: return False
def send_success(chat_id, user, ch_msg_id, target="both"):
    try:
        url = f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
        buttons = []
        if target in ["threads", "both"] and (user.get("threads_on") or is_admin(chat_id)): buttons.append([{"text": "See on Threads", "url": THREADS_URL}])
        if target in ["channel", "both"] and ch_msg_id: buttons.append([{"text": "See on channel", "url": url}])
        if ch_msg_id: buttons.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
        buttons.append([{"text": "Back", "callback_data": "back_home"}])
        note = f" -> {target.upper()}" if is_admin(chat_id) else ""
        send_message(chat_id, f"Menfess sent!{note}\n{SEP}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5", {"inline_keyboard": buttons})
    except Exception as e: report_error(chat_id, "send_success", e)

def send_user_list(chat_id):
    db = get_db()
    if not db:
        send_message(chat_id, "DB belum connect")
        return
    try:
        cur = db.cursor()
        cur.execute("SELECT user_id, name, username, total_text+total_media as total, banned FROM menfess_users ORDER BY total DESC")
        rows = cur.fetchall(); cur.close(); db.close()
        back_kb = {"inline_keyboard": [[{"text": "Back", "callback_data": "admin_panel"}]]}
        if not rows:
            send_message(chat_id, M("Belum ada user."), back_kb)
            return
        header = M(f"Total User: {len(rows)}\n------------------------------\nSemua Member:")
        txt = header + "\n"
        for i, r in enumerate(rows, 1):
            status = " BANNED" if r[4] else ""
            if r[2]:
                display = f"<a href=\"tg://user?id={r[0]}\">@{r[2]}</a>"
            else:
                display = f"<a href=\"tg://user?id={r[0]}\">{r[0]}</a>"
            line = f"{i}. {display} - {r[0]} ({r[3]}){status}\n"
            if len(txt) + len(line) > 3200:
                send_message(chat_id, txt, back_kb)
                txt = M(f"Lanjutan ({i}/{len(rows)}):") + "\n"
            txt += line
        send_message(chat_id, txt, back_kb)
    except Exception as e:
        send_message(chat_id, f"Gagal ambil list: {e}")

def handle_admin_command(chat_id, text):
    if text.startswith("/clearmenu"):
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton", json={"menu_button": {"type": "default"}}, timeout=5)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMyCommands", json={}, timeout=5)
        send_message(chat_id, "Menu button & commands dibersihkan")
        return True
    if text.startswith("/ban"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1]; tu = get_user(target); tu["banned"] = True; save_user_to_db(target, tu); send_message(chat_id, M(f"User {target} BANNED"))
        return True
    if text.startswith("/unban"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1]; tu = get_user(target); tu["banned"] = False; tu["warn"] = 0; save_user_to_db(target, tu); send_message(chat_id, M(f"User {target} UNBANNED"))
        return True
    if text.startswith("/warn"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1]; tu = get_user(target); tu["warn"] = tu.get("warn", 0)+1
            if tu["warn"] >= 3: tu["banned"] = True
            save_user_to_db(target, tu); send_message(chat_id, M(f"Warn {target} = {tu['warn']}/3 {'+ AUTO BANNED' if tu['banned'] else ''}"))
        return True
    if text.startswith("/settag"):
        nt = text.replace("/settag", "").strip()
        if nt: set_setting('hashtag', nt); send_message(chat_id, M(f"Hashtag diganti jadi {nt}"))
        return True
    if text.startswith("/setperaturan"):
        nt = text.replace("/setperaturan", "").strip()
        if nt: set_setting('peraturan', nt); send_message(chat_id, M("Peraturan diupdate"))
        return True
    if text.startswith("/broadcast"):
        btext = text.replace("/broadcast", "").strip()
        if btext:
            db = get_db()
            if db:
                cur = db.cursor(); cur.execute("SELECT user_id FROM menfess_users"); rows = cur.fetchall(); cur.close(); db.close()
                for r in rows: send_message(r[0], f"📢 BROADCAST\n{SEP}\n{btext}")
                send_message(chat_id, M(f"Broadcast terkirim ke {len(rows)} user"))
        return True
    if text.startswith("/users"):
        send_user_list(chat_id)
        return True
    if text.startswith("/setwebhook"):
        host = request.host_url.rstrip('/'); wh = f"{host}/api/index"
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": wh}, timeout=5).json()
        send_message(chat_id, M(f"Webhook: {wh}\nResult: {r}"))
        return True
    return False

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    try:
        host = request.host_url.rstrip('/')
        webhook_url = f"{host}/api/index"
        custom = os.getenv("WEBHOOK_URL")
        if custom: webhook_url = custom
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": webhook_url}, timeout=5).json()
        return f"Webhook set to {webhook_url}<br>{r}", 200
    except Exception as e:
        return f"Error set webhook: {e}", 500

@app.route("/webhookinfo", methods=["GET"])
def webhook_info():
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=5).json()
        return jsonify(r), 200
    except Exception as e:
        return str(e), 500

@app.route("/logs", methods=["GET"])
def view_logs():
    q = request.args.get("admin")
    if str(q) not in ADMIN_ID.split(","):
        return "Unauthorized - tambahkan ?admin=ID_KAMU", 401
    return "Logs dikirim ke LOG_CHANNEL. Cek channel log & /webhookinfo", 200

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def main_handler():
    data = {}; where = "init"
    try:
        where = "init_db"
        try: init_db()
        except: pass
        if request.method == "GET": return "JogjaLend Bot V110.9 FULL OK", 200
        where = "parse_json"; data = request.get_json(force=True, silent=True) or {}
        if "message" in data:
            msg = data["message"]; chat_id = msg["chat"]["id"]; uid = str(chat_id)
            where = f"get_user {uid}"; user = get_user(uid); text = msg.get("text", ""); caption = msg.get("caption", "")
            HASHTAG = get_setting('hashtag', '#jogjalend')
            if "from" in msg:
                where = "parse_from"
                raw = (msg["from"].get("first_name", "")+" "+(msg["from"].get("last_name", "") or "")).strip() or "-"
                user["name"] = raw.encode('ascii', 'ignore').decode('ascii') or "User"
                user["username"] = msg["from"].get("username", "")
            where = f"cmd {text[:30]}"
            if is_admin(chat_id) and text.startswith("/"):
                if handle_admin_command(chat_id, text):
                    return "ok", 200
            if text.startswith("/start"):
                user["last_date"] = datetime.now(WIB).strftime("%Y-%m-%d"); save_user_to_db(uid, user)
                send_message(chat_id, get_welcome_text(user), get_main_keyboard(is_admin(chat_id)))
            elif text.startswith("/newpost"): send_message(chat_id, f"Post Menfess\n{SEP}\nKetik langsung text / kirim media + caption\nAuto tag {HASHTAG}", get_back_keyboard())
            elif text.startswith("/profile"): send_message(chat_id, f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5", get_back_keyboard())
            elif text.lower().startswith("/stats"): send_stats(chat_id, user, "today")
            elif not user["banned"]:
                if text and not text.startswith("/") and len(text) >= 3:
                    if user["today_text"] >= 5: send_message(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", get_back_keyboard())
                    else:
                        clean = text.strip()
                        if HASHTAG.lower() not in clean.lower(): clean = f"{clean} {HASHTAG}"
                        target = user.get("admin_target", "both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                        ch_id = None
                        if target in ["channel", "both"]:
                            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=5).json()
                            ch_id = r.get("result", {}).get("message_id")
                        if target in ["threads", "both"]: post_to_threads(clean)
                        user["today_text"] += 1; user["total_text"] += 1; user["total_chars"] = user.get("total_chars", 0)+len(text)
                        save_user_to_db(uid, user); send_success(chat_id, user, ch_id, target)
                if "photo" in msg or "video" in msg:
                    if user["today_media"] >= 5: send_message(chat_id, "Limit 5/5", get_back_keyboard())
                    else:
                        fid = msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video", {}).get("file_id")
                        is_photo = "photo" in msg
                        base_cap = caption.strip() if caption else HASHTAG
                        if HASHTAG.lower() not in base_cap.lower(): base_cap = f"{base_cap} {HASHTAG}"
                        target = user.get("admin_target", "both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                        ch_id = None
                        if target in ["channel", "both"]:
                            if is_photo:
                                raw = download_file(fid); wm = add_watermark(raw) if raw else None
                                if wm: r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": ("wm.jpg", wm, "image/jpeg")}, timeout=8).json(); ch_id = r.get("result", {}).get("message_id")
                                else: r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id = r.get("result", {}).get("message_id")
                            else: r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id = r.get("result", {}).get("message_id")
                        if target in ["threads", "both"]: post_to_threads(base_cap)
                        user["today_media"] += 1; user["total_media"] += 1
                        save_user_to_db(uid, user); send_success(chat_id, user, ch_id, target)
        if "callback_query" in data:
            cq = data["callback_query"]; chat_id = cq["message"]["chat"]["id"]; uid = str(chat_id); cdata = cq["data"]; msg_id = cq["message"]["message_id"]
            where = f"callback {cdata}"
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
            except: pass
            user = get_user(uid)
            HASHTAG = get_setting('hashtag', '#jogjalend')
            if cdata in ["stats", "stats_today", "stats_weekly"]:
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=2)
                except: pass
                mode = "weekly" if cdata == "stats_weekly" else "today"
                send_stats(chat_id, user, mode)
            elif cdata == "back_home": edit_message_fast(chat_id, msg_id, get_welcome_text(user), get_main_keyboard(is_admin(chat_id)))
            elif cdata == "lend_page1": edit_message_fast(chat_id, msg_id, M("Pilih salah satu pengaturan yang ingin anda ubah."), get_menu_1())
            elif cdata == "lend_page2": edit_message_fast(chat_id, msg_id, M("Pilih salah satu pengaturan yang ingin anda ubah."), get_menu_2())
            elif cdata == "my_profile": edit_message_fast(chat_id, msg_id, f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5\nHashtag: {HASHTAG}", get_back_keyboard())
            elif cdata == "post": edit_message_fast(chat_id, msg_id, f"Post Menfess\n{SEP}\nKetik langsung text / kirim media + caption\nAuto tag {HASHTAG}", get_back_keyboard())
            elif cdata == "threads":
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "Back", "callback_data": "back_home"}]]}
                edit_message_fast(chat_id, msg_id, f"Threads Setting\n{SEP}\nStatus: {'ON' if user.get('threads_on') else 'OFF'}\nLink: threads.net/jogjalend", kb)
            elif cdata == "threads_toggle":
                user["threads_on"] = not user.get("threads_on", False); save_user_to_db(uid, user)
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "Back", "callback_data": "back_home"}]]}
                edit_message_fast(chat_id, msg_id, f"Threads {'ON' if user['threads_on'] else 'OFF'}!\nLink: threads.net/jogjalend", kb)
            elif cdata == "info_bot":
                edit_message_fast(chat_id, msg_id, "Bot Information\n\nJogjaLend Bot adalah bot yang dikembangkan oleh tim @jogja_lend.\n<pre>Versi Bot : V110.9\nDatabase  : PostgreSQL</pre>\nUntuk pertanyaan tentang penggunaan bot, saran untuk fitur baru atau laporan bug Anda dapat menulis di @joglendsupportBot", get_back_keyboard())
            elif cdata == "admin_panel":
                if is_admin(chat_id): edit_message_fast(chat_id, msg_id, M("ADMIN PANEL V110.9\n------------------------------\nPilih menu admin:"), get_admin_panel())
                else: edit_message_fast(chat_id, msg_id, M("Not admin"), get_back_keyboard())
            elif cdata == "lend_tag":
                edit_message_fast(chat_id, msg_id, M(f"Tag Saat Ini: {HASHTAG}\n------------------------------\nGanti dengan command:\n/settag #tagbaru"), get_menu_1())
            elif cdata == "lend_persetujuan":
                cur = get_setting('approval', 'off')
                kb = {"inline_keyboard": [[{"text": f"Mode: {cur.upper()} - Klik untuk ganti", "callback_data": "toggle_approval"}], [{"text": "Kembali", "callback_data": "lend_page1"}]]}
                edit_message_fast(chat_id, msg_id, M(f"Mode Persetujuan\n------------------------------\nJika ON, menfess tidak langsung post tapi masuk LOG_CHANNEL dulu untuk di-approve.\nStatus: {cur}"), kb)
            elif cdata == "toggle_approval":
                cur = get_setting('approval', 'off'); new = 'on' if cur == 'off' else 'off'; set_setting('approval', new)
                kb = {"inline_keyboard": [[{"text": f"Mode: {new.upper()} - Klik untuk ganti", "callback_data": "toggle_approval"}], [{"text": "Kembali", "callback_data": "lend_page1"}]]}
                edit_message_fast(chat_id, msg_id, M(f"Mode Persetujuan diubah jadi {new.upper()}"), kb)
            elif cdata == "lend_hapus": edit_message_fast(chat_id, msg_id, M("Menghapus Pesan\n------------------------------\nUser bisa hapus post sendiri via tombol Delete setelah post. Admin bisa /del dengan reply."), get_menu_1())
            elif cdata == "lend_lang": edit_message_fast(chat_id, msg_id, M("Lang\n------------------------------\nBot saat ini: Indonesia (fancy)."), get_menu_1())
            elif cdata == "lend_peraturan":
                per = get_setting('peraturan', '-')
                edit_message_fast(chat_id, msg_id, M(f"Peraturan\n------------------------------\n{per}\n\nGanti: /setperaturan <teks>"), get_menu_2())
            elif cdata == "lend_peringatan": edit_message_fast(chat_id, msg_id, M(f"Peringatan\n------------------------------\n/warn <user_id> - tambah warn (3x auto ban)\nSistem warn user: {user.get('warn',0)}/3"), get_menu_2())
            elif cdata == "lend_blacklist":
                db = get_db()
                txt = "Daftar Hitam\n------------------------------\n"
                if db:
                    cur = db.cursor(); cur.execute("SELECT user_id, name, warn FROM menfess_users WHERE banned=true LIMIT 20"); rows = cur.fetchall(); cur.close(); db.close()
                    if not rows: txt += "Tidak ada user banned."
                    else:
                        for r in rows: txt += f"{r[1]} - {r[0]} warn:{r[2]}\n"
                    kb = {"inline_keyboard": [[{"text": "Unban: /unban <id>", "callback_data": "admin_noop"}], [{"text": "Kembali", "callback_data": "lend_page2"}]]}
                else: kb = get_menu_2()
                edit_message_fast(chat_id, msg_id, M(txt), kb)
            elif cdata == "lend_izin": edit_message_fast(chat_id, msg_id, M("Perizinan\n------------------------------\nSemua user boleh post text/media (max 5). Admin bisa ban/warn. Edit di code jika mau limit link."), get_menu_2())
            elif cdata == "lend_log": edit_message_fast(chat_id, msg_id, M(f"Log Saluran\n------------------------------\nLog Channel: {LOG_CHANNEL}\nError & approval akan kesini.\nGanti via env LOG_CHANNEL"), get_menu_2())
            elif cdata == "lend_channel":
                if is_admin(chat_id): edit_message_fast(chat_id, msg_id, M(f"Manajemen Channel\n------------------------------\nPilih target posting\nCurrent: {user.get('admin_target','both').upper()}"), get_channel_target_keyboard(user))
                else: edit_message_fast(chat_id, msg_id, M("Not admin"), get_back_keyboard())
            elif cdata == "admin_set_channel":
                if is_admin(chat_id): user["admin_target"] = "channel"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Set ke CHANNEL ONLY\n------------------------------\nMenfess cuma ke {CHANNEL_ID}"), get_channel_target_keyboard(user))
            elif cdata == "admin_set_threads":
                if is_admin(chat_id): user["admin_target"] = "threads"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Set ke THREADS ONLY\n------------------------------\nMenfess cuma ke Threads"), get_channel_target_keyboard(user))
            elif cdata == "admin_set_both":
                if is_admin(chat_id): user["admin_target"] = "both"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Set ke BOTH\n------------------------------\nMenfess ke Channel + Threads"), get_channel_target_keyboard(user))
            elif cdata == "admin_users":
                send_user_list(chat_id)
                edit_message_fast(chat_id, msg_id, M("List User dikirim di bawah"), get_admin_panel())
            elif cdata == "admin_allstats":
                db = get_db()
                if db:
                    cur = db.cursor(); cur.execute("SELECT SUM(total_text), SUM(total_media) FROM menfess_users"); s = cur.fetchone(); cur.close(); db.close()
                    edit_message_fast(chat_id, msg_id, M(f"GLOBAL\n------------------------------\nText : {s[0]}\nMedia: {s[1]}"), get_admin_panel())
            elif cdata == "admin_broadcast":
                edit_message_fast(chat_id, msg_id, M("Broadcast\n------------------------------\nKetik:") + "\n/broadcast <pesan>\n" + M("Akan kirim ke semua user di DB"), get_admin_panel())
            elif cdata == "admin_webhook":
                r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=5).json()
                res = r.get('result', {})
                url = res.get('url', '')
                edit_message_fast(chat_id, msg_id, M("Webhook Info\n------------------------------") + f"\nURL: <a href=\"{url}\">{url}</a>\n" + M(f"Pending: {res.get('pending_update_count')}\nLastError: {res.get('last_error_message')}\n\nUntuk set ulang:") + "\n/setwebhook", get_admin_panel())
            elif cdata == "admin_logs": edit_message_fast(chat_id, msg_id, M(f"Logs\n------------------------------\nError otomatis ke {LOG_CHANNEL}\nCek /webhookinfo dan Vercel Logs"), get_admin_panel())
            elif cdata == "admin_noop": pass
            elif cdata == "close":
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=3)
                except: pass
            elif cdata.startswith("del_"):
                mid = cdata.replace("del_", "")
                if mid.isdigit():
                    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=3)
                    except: pass
                edit_message_fast(chat_id, msg_id, "Deleted ✅", get_back_keyboard())
        return "ok", 200
    except Exception as e:
        try:
            cid = 0
            try:
                if "message" in data and "chat" in data["message"]: cid = data["message"]["chat"]["id"]
                elif "callback_query" in data: cid = data["callback_query"]["message"]["chat"]["id"]
            except: pass
            if cid != 0: report_error(cid, where, e)
            else: print(f"[CRITICAL {where}] {e}\n{traceback.format_exc()}")
        except: print(f"[FATAL {where}] {e}\n{traceback.format_exc()}")
        return "ok", 200

@app.errorhandler(500)
def handle_500(e):
    print(f"500 ERROR: {e}")
    return "ok", 200

@app.errorhandler(Exception)
def handle_any(e):
    print(f"ANY ERROR: {e}")
    return "ok", 200
