# api/index.py - JogjaLend Bot Angel V117.2 - Perfeksionis + Bahasa Indonesia Formal + Ringan + Tanpa Bug
from flask import Flask, request, jsonify
import os, requests, io, re, traceback, copy, time, hmac, hashlib, base64, urllib.parse, secrets, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

try:
    import psycopg2
    from psycopg2 import pool
except:
    psycopg2 = None
    pool = None
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

X_API_KEY = os.getenv("X_API_KEY") or ""
X_API_SECRET = os.getenv("X_API_SECRET") or ""
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or ""
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET") or ""
QRIS_IMAGE_URL = os.getenv("QRIS_IMAGE_URL") or ""
QRIS_TEXT = os.getenv("QRIS_TEXT") or "QRIS a.n jogjaStore, silakan pindai kode QR di atas"
X_PRICE = os.getenv("X_PRICE") or "Rp 100.000 / 30 hari"
PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS") or "30")
RETWEET_HASHTAG = os.getenv("RETWEET_HASHTAG") or "#jogjalend"

TG = requests.Session()
TG.headers.update({"Connection": "keep-alive"})
BASE_TG = f"https://api.telegram.org/bot{BOT_TOKEN}"

SETTINGS_CACHE = {}
USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0, "admin_target": "both", "warn": 0, "waiting_proof": False, "x_premium_until": "", "x_auto": True})

_db_pool = None
def get_pool():
    global _db_pool
    if _db_pool or not DATABASE_URL or not pool:
        return _db_pool
    try:
        _db_pool = pool.SimpleConnectionPool(1, 5, DATABASE_URL, connect_timeout=2)
    except:
        _db_pool = None
    return _db_pool

def get_db():
    p = get_pool()
    if p:
        try: return p.getconn()
        except: return None
    if not DATABASE_URL or not psycopg2: return None
    try: return psycopg2.connect(DATABASE_URL, connect_timeout=2)
    except: return None

def release_db(db):
    if not db: return
    p = get_pool()
    try:
        if p: p.putconn(db)
        else: db.close()
    except: pass

_db_init_done = False
def init_db():
    global _db_init_done
    if _db_init_done: return
    _db_init_done = True
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0, admin_target TEXT DEFAULT 'both', warn INT DEFAULT 0)")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS x_premium_until TEXT DEFAULT ''")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS waiting_proof BOOLEAN DEFAULT FALSE")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS x_auto BOOLEAN DEFAULT TRUE")
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_posts (msg_id TEXT PRIMARY KEY, owner_id TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('hashtag', '#jogjalend') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('peraturan', '1. Dilarang SARA dan Pornografi\n2. Dilarang spam\n3. Maksimal 5 kiriman per hari') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('approval', 'off') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('x_auto_share', 'off') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('last_retweet_id', '0') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('x_retweet', 'on') ON CONFLICT (key) DO NOTHING")
        db.commit(); cur.close()
    except: pass
    finally: release_db(db)

try: init_db()
except: pass

def get_setting(k, default=""):
    if k in SETTINGS_CACHE:
        val, ts = SETTINGS_CACHE[k]
        if time.time() - ts < 60:
            return val
    db = get_db()
    if not db:
        return SETTINGS_CACHE.get(k, (default, 0))[0]
    try:
        cur = db.cursor(); cur.execute("SELECT value FROM bot_settings WHERE key=%s", (k,)); r = cur.fetchone(); cur.close()
        val = r[0] if r else default
        SETTINGS_CACHE[k] = (val, time.time())
        return val
    except: return SETTINGS_CACHE.get(k, (default, 0))[0]
    finally: release_db(db)

def set_setting(k, v):
    SETTINGS_CACHE[k] = (v, time.time())
    db = get_db()
    if not db: return
    try:
        cur = db.cursor(); cur.execute("INSERT INTO bot_settings (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=%s", (k, v, v)); db.commit(); cur.close()
    except: pass
    finally: release_db(db)

def delete_setting(k):
    SETTINGS_CACHE.pop(k, None)
    db = get_db()
    if not db: return
    try:
        cur = db.cursor(); cur.execute("DELETE FROM bot_settings WHERE key=%s", (k,)); db.commit(); cur.close()
    except: pass
    finally: release_db(db)

def _x_oauth_header(method, url, extra_params=None):
    if not X_API_KEY or not X_API_SECRET or not X_ACCESS_TOKEN or not X_ACCESS_SECRET:
        return None
    oauth = {
        "oauth_consumer_key": X_API_KEY,
        "oauth_nonce": base64.b64encode(os.urandom(32)).decode()[:32].replace("+","a").replace("/","b"),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": X_ACCESS_TOKEN,
        "oauth_version": "1.0",
    }
    all_params = dict(oauth)
    if extra_params:
        all_params.update(extra_params)
    sorted_params = sorted(all_params.items())
    param_str = "&".join(f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}" for k,v in sorted_params)
    base = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_str, safe='')}"
    signing_key = f"{urllib.parse.quote(X_API_SECRET, safe='')}&{urllib.parse.quote(X_ACCESS_SECRET, safe='')}"
    sig = base64.b64encode(hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    header = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k,v in sorted(oauth.items()))
    return header

def _x_upload_media(photo_bytes):
    try:
        url = "https://upload.twitter.com/1.1/media/upload.json"
        header = _x_oauth_header("POST", url)
        if not header: return None
        files = {"media": ("img.jpg", photo_bytes, "image/jpeg")}
        r = TG.post(url, headers={"Authorization": header}, files=files, timeout=10)
        j = r.json()
        return j.get("media_id_string")
    except Exception as e:
        print(f"X upload error: {e}")
        return None

def post_to_x(text_content, photo_bytes=None):
    try:
        if not X_API_KEY or not X_API_SECRET or not X_ACCESS_TOKEN or not X_ACCESS_SECRET:
            return False
        BAD = ["judol", "slot", "bokep", "porno", "togel", "gacor", "maxwin"]
        if any(b in (text_content or "").lower() for b in BAD):
            print("X blocked bad word")
            return False
        clean = re.sub(r"<[^>]+>", "", text_content or "").strip()
        if not clean:
            return False
        if len(clean) > 280:
            clean = clean[:277] + "..."
        media_id = None
        if photo_bytes:
            media_id = _x_upload_media(photo_bytes)
        url = "https://api.twitter.com/2/tweets"
        header = _x_oauth_header("POST", url, None)
        if not header: return False
        payload = {"text": clean}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}
        r = TG.post(url, headers={"Authorization": header, "Content-Type": "application/json"}, json=payload, timeout=10)
        print(f"X post: {r.status_code}")
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"X post error: {e}")
        return False

_X_MY_ID = None
def _x_get_my_id():
    global _X_MY_ID
    if _X_MY_ID: return _X_MY_ID
    try:
        url = "https://api.twitter.com/2/users/me"
        h = _x_oauth_header("GET", url)
        r = TG.get(url, headers={"Authorization": h}, timeout=10).json()
        _X_MY_ID = r.get("data", {}).get("id")
        return _X_MY_ID
    except: return None

def auto_retweet_hashtag():
    try:
        if not X_API_KEY or not X_ACCESS_TOKEN:
            return "Variabel lingkungan X belum diatur"
        last_id = get_setting('last_retweet_id', '0')
        my_id = _x_get_my_id()
        if not my_id: return "Gagal memperoleh ID Pengguna X"
        query = f"{RETWEET_HASHTAG} -is:retweet -is:reply -from:jogjalend"
        url = "https://api.twitter.com/2/tweets/search/recent"
        params = {"query": query, "max_results": 10, "tweet.fields": "author_id,created_at"}
        if last_id and last_id != "0":
            params["since_id"] = last_id
        h = _x_oauth_header("GET", url, params)
        r = TG.get(url, headers={"Authorization": h}, params=params, timeout=10)
        j = r.json()
        if r.status_code != 200:
            print(f"Search error: {r.status_code} {r.text[:300]}")
            return f"Pencarian gagal {r.status_code}"
        tweets = j.get("data", [])
        if not tweets:
            return "Tidak ada tweet baru"
        count = 0
        max_id = last_id
        for t in reversed(tweets):
            if count >= 5:
                break
            tid = t["id"]
            if str(t.get("author_id")) == str(my_id):
                if int(tid) > int(max_id or 0): max_id = tid
                continue
            retweet_url = f"https://api.twitter.com/2/users/{my_id}/retweets"
            h2 = _x_oauth_header("POST", retweet_url)
            rr = TG.post(retweet_url, headers={"Authorization": h2, "Content-Type": "application/json"}, json={"tweet_id": tid}, timeout=10)
            print(f"Retweet {tid}: {rr.status_code}")
            if rr.status_code in [200, 201]:
                count += 1
                if int(tid) > int(max_id or 0): max_id = tid
            elif rr.status_code == 403 and "already retweeted" in rr.text.lower():
                if int(tid) > int(max_id or 0): max_id = tid
        if str(max_id) != str(last_id):
            set_setting('last_retweet_id', str(max_id))
        return f"Berhasil me-retweet {count} dari {len(tweets)}"
    except Exception as e:
        print(f"Retweet error: {e}")
        return str(e)

def to_fancy(text):
    if not text: return ""
    pattern = r'<plain>.*?</plain>|<code>.*?</code>|<pre>.*?</pre>|<a[^>]*>.*?</a>|<[^>]+>|@\w+|#\w+|/\w+|https?://\S+|threads\.net/\S+|t\.me/\S+'
    res_parts = []; last_idx = 0
    for m in re.finditer(pattern, text, flags=re.DOTALL):
        before = text[last_idx:m.start()]
        conv = "".join(chr(0x1D5A0 + ord(c)-65) if 'A' <= c <= 'Z' else chr(0x1D5BA + ord(c)-97) if 'a' <= c <= 'z' else chr(0x1D7E2 + ord(c)-48) if '0' <= c <= '9' else c for c in before)
        res_parts.append(conv); res_parts.append(m.group(0)); last_idx = m.end()
    tail = text[last_idx:]
    conv = "".join(chr(0x1D5A0 + ord(c)-65) if 'A' <= c <= 'Z' else chr(0x1D5BA + ord(c)-97) if 'a' <= c <= 'z' else chr(0x1D7E2 + ord(c)-48) if '0' <= c <= '9' else c for c in tail)
    res_parts.append(conv); return "".join(res_parts)

def F(t): return to_fancy(t)
def M(t):
    t = str(t).replace("<", "[").replace(">", "]")
    out = []
    for line in t.split("\n"):
        if line.strip() == "": out.append("")
        elif "http" in line or "@" in line or "tg://" in line or line.strip().startswith("/"): out.append(line)
        else: out.append(f"<code>{line}</code>")
    return "\n".join(out)

def load_user_from_db(uid):
    db = get_db()
    if not db: return None
    try:
        cur = db.cursor()
        cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target, warn, x_premium_until, waiting_proof, x_auto FROM menfess_users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close()
        if row: return {"name": row[0] or "", "username": row[1] or "", "threads_on": row[2] or False, "today_text": row[3] or 0, "today_media": row[4] or 0, "last_date": row[5] or "", "banned": row[6] or False, "total_text": row[7] or 0, "total_media": row[8] or 0, "total_chars": row[9] or 0, "admin_target": row[10] or "both", "warn": row[11] or 0, "x_premium_until": row[12] or "", "waiting_proof": row[13] or False, "x_auto": row[14] if row[14] is not None else True}
    except: return None
    finally: release_db(db)
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target, warn, x_premium_until, waiting_proof, x_auto) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s, admin_target=%s, warn=%s, x_premium_until=%s, waiting_proof=%s, x_auto=%s", (uid, user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars", 0), user.get("admin_target", "both"), user.get("warn", 0), user.get("x_premium_until",""), user.get("waiting_proof", False), user.get("x_auto", True), user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars", 0), user.get("admin_target", "both"), user.get("warn", 0), user.get("x_premium_until",""), user.get("waiting_proof", False), user.get("x_auto", True)))
        db.commit(); cur.close()
    except: pass
    finally: release_db(db)

def get_user(uid):
    u = USERS[uid]
    if u["name"] == "" and DATABASE_URL:
        d = load_user_from_db(uid)
        if d: USERS[uid] = d; u = USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today:
        u["today_text"] = 0; u["today_media"] = 0; u["last_date"] = today
        if u["name"] != "":
            try: save_user_to_db(uid, u)
            except: pass
    return u

def is_admin(uid): return str(uid).strip() in [x.strip() for x in ADMIN_ID.split(",") if x.strip()] if ADMIN_ID else False

def is_premium_active(user):
    try:
        until = user.get("x_premium_until","") or ""
        if not until: return False
        dt = datetime.strptime(until, "%Y-%m-%d").replace(tzinfo=WIB)
        return datetime.now(WIB) <= dt + timedelta(days=1)
    except: return False

def save_post_owner(msg_id, owner_id):
    if not msg_id: return
    db = get_db()
    if not db: return
    try:
        cur = db.cursor(); cur.execute("INSERT INTO menfess_posts (msg_id, owner_id) VALUES (%s,%s) ON CONFLICT (msg_id) DO NOTHING", (str(msg_id), str(owner_id))); db.commit(); cur.close()
    except: pass
    finally: release_db(db)

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
        r = TG.post(f"{BASE_TG}/sendMessage", json=payload, timeout=3)
        return r.status_code == 200
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
        r = TG.post(f"{BASE_TG}/editMessageText", json=payload, timeout=3)
        if r.status_code == 200:
            return True
        return send_message(chat_id, text, kb)
    except:
        try: return send_message(chat_id, text, kb)
        except: return False

def send_qris(chat_id):
    if QRIS_IMAGE_URL:
        try:
            TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": chat_id, "photo": QRIS_IMAGE_URL, "caption": f"Silakan pindai kode QRIS ini untuk melakukan pembayaran X Premium\nHarga: {X_PRICE}"}, timeout=5)
            return True
        except: pass
    return False

def get_x_premium_keyboard(user=None):
    if user and is_premium_active(user):
        auto = "ON" if user.get("x_auto", True) else "OFF"
        return {"inline_keyboard": [[{"text": f"𝕏 X Auto Post: {auto}", "callback_data": "x_toggle_auto"}], [{"text": "Kembali", "callback_data": "back_home"}]]}
    return {"inline_keyboard": [[{"text": "💳 Saya Telah Transfer, Kirim Bukti", "callback_data": "x_pay_proof"}], [{"text": "Kembali", "callback_data": "back_home"}]]}

def get_welcome_text(user):
    hashtag = get_setting('hashtag', '#jogjalend')
    prem = " ✅ X Premium" if is_premium_active(user) else ""
    return f"Selamat Datang!{prem}\n{SEP}\nPublikasikan ke {CHANNEL_ID}\nSilakan ketuk tombol Post untuk mengirim.\n\nKuota\nMedia : {user['today_media']}/5\nTeks : {user['today_text']}/5\nTag: {hashtag}"

def get_back_keyboard(): return {"inline_keyboard": [[{"text": "Kembali", "callback_data": "back_home"}]]}
def get_main_keyboard(is_ad=False):
    kb = {"inline_keyboard": [[{"text": "👤 Profil Saya", "callback_data": "my_profile"}, {"text": "💌 Post", "callback_data": "post"}], [{"text": "📧 Pengaturan Threads", "callback_data": "threads"}], [{"text": "𝕏 X Premium", "callback_data": "x_premium"}], [{"text": "📈 Statistik", "callback_data": "stats"}, {"text": "ℹ️ Informasi Bot", "callback_data": "info_bot"}]]}
    if is_ad: kb["inline_keyboard"].append([{"text": "🔧 PANEL ADMIN", "callback_data": "admin_panel"}])
    return kb
def get_menu_1():
    return {"inline_keyboard": [[{"text": "🔔 Tag", "callback_data": "lend_tag"}], [{"text": "📥 Mode Persetujuan", "callback_data": "lend_persetujuan"}], [{"text": "🗑️ Hapus Pesan", "callback_data": "lend_hapus"}], [{"text": "🇮🇩 Bahasa", "callback_data": "lend_lang"}, {"text": "✅ Tutup", "callback_data": "close"}], [{"text": "▶️ Selengkapnya", "callback_data": "lend_page2"}]]}
def get_menu_2():
    return {"inline_keyboard": [[{"text": "📜 Peraturan", "callback_data": "lend_peraturan"}], [{"text": "⚠️ Peringatan", "callback_data": "lend_peringatan"}], [{"text": "🚫 Daftar Blokir", "callback_data": "lend_blacklist"}], [{"text": "🔐 Perizinan", "callback_data": "lend_izin"}, {"text": "📋 Log Channel", "callback_data": "lend_log"}], [{"text": "🎯 Pengelolaan Channel", "callback_data": "lend_channel"}], [{"text": "⬅️ Kembali", "callback_data": "lend_page1"}, {"text": "❌ Tutup", "callback_data": "close"}]]}

def get_admin_panel():
    x_on = get_setting('x_auto_share', 'off') == 'on'
    x_label = f"{'✅ ' if x_on else '❌ '}𝕏 Auto Share: {'ON' if x_on else 'OFF'}"
    rt_on = get_setting('x_retweet', 'on') == 'on'
    rt_label = f"{'✅ ' if rt_on else '❌ '}🔁 Auto Retweet {RETWEET_HASHTAG}: {'ON' if rt_on else 'OFF'}"
    return {"inline_keyboard": [
        [{"text": "👥 Daftar Pengguna", "callback_data": "admin_users"}, {"text": "📊 Seluruh Statistik", "callback_data": "admin_allstats"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}, {"text": "🚫 Ban/Unban", "callback_data": "lend_blacklist"}],
        [{"text": "🎯 Target Channel", "callback_data": "lend_channel"}],
        [{"text": x_label, "callback_data": "admin_x_toggle"}],
        [{"text": rt_label, "callback_data": "admin_rt_toggle"}],
        [{"text": "🧪 Uji Post ke X", "callback_data": "admin_x_test"}, {"text": "🔁 Uji Retweet", "callback_data": "admin_rt_test"}],
        [{"text": "🔗 Atur Webhook", "callback_data": "admin_webhook"}, {"text": "📋 Periksa Log", "callback_data": "admin_logs"}],
        [{"text": "⚙️ Pengaturan Bot", "callback_data": "lend_page1"}],
        [{"text": "⬅️ Kembali", "callback_data": "back_home"}]
    ]}

def get_channel_target_keyboard(user):
    target = user.get("admin_target", "both")
    return {"inline_keyboard": [[{"text": f"📍 Target: {target.upper()}", "callback_data": "admin_noop"}], [{"text": f"{'✅ ' if target=='channel' else ''}📢 Channel Saja", "callback_data": "admin_set_channel"}, {"text": f"{'✅ ' if target=='threads' else ''}🧵 Threads Saja", "callback_data": "admin_set_threads"}], [{"text": f"{'✅ ' if target=='both' else ''}🚀 Keduanya (Channel+Threads)", "callback_data": "admin_set_both"}], [{"text": "⬅️ Kembali", "callback_data": "admin_panel"}]]}

_LOGO_CACHED = None
def get_logo_cached():
    global _LOGO_CACHED
    if _LOGO_CACHED is not None: return _LOGO_CACHED
    base_dir = os.path.dirname(__file__)
    for p in [os.path.join(base_dir, "logo.png"), "logo.png", os.path.join(os.getcwd(), "api/logo.png")]:
        if os.path.exists(p):
            try:
                logo = Image.open(p).convert("RGBA")
                bbox = logo.getbbox()
                if bbox: logo = logo.crop(bbox)
                _LOGO_CACHED = logo
                return logo
            except: return None
    return None

def download_file(file_id):
    try:
        info = TG.get(f"{BASE_TG}/getFile", params={"file_id": file_id}, timeout=3).json()
        fp = info["result"]["file_path"]
        return TG.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=5).content
    except: return None

def add_watermark(photo_bytes):
    try:
        if not Image or not photo_bytes: return None
        logo_orig = get_logo_cached()
        if not logo_orig: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = logo_orig.copy()
        w, h = base.size
        target_w = int(w * 0.20); target_w = max(60, min(target_w, 400))
        target_h = int(target_w * logo.height / logo.width)
        max_h = int(h * 0.20)
        if target_h > max_h:
            target_h = max_h; target_w = int(target_h * logo.width / logo.height)
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        margin = max(10, int(w * 0.015))
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        overlay.paste(logo, (margin, margin), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO(); combined.save(bio, "JPEG", quality=82, optimize=True); bio.seek(0); return bio
    except Exception as e:
        print(f"watermark error: {e}"); return None

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
        draw.text((20, 12), f"HARI INI - {user['name'][:16]}", fill='white', font=f_title)
        total = user['today_text'] + user['today_media']
        hours = ["TOTAL", "TEKS", "MEDIA", "LIMIT"]
        vals = [total, user['today_text'], user['today_media'], 5]
        max_val = max(vals) if max(vals) > 0 else 3
        slot_w = (700-50)//len(hours)
        for idx in range(len(hours)):
            xc = 50+idx*slot_w+slot_w//2; v = vals[idx]
            yh = 370-int(v/max_val*250) if max_val > 0 else 370
            draw.rectangle([xc-15, yh, xc+15, 370], fill='#10B981')
            draw.text((xc-15, 378), hours[idx], fill='#A1A1AA', font=f_small)
            draw.text((xc-10, yh-20), str(v), fill='white', font=f_small)
        bio = io.BytesIO(); img.save(bio, format='JPEG', quality=70); bio.seek(0); return bio
    except: return None

def make_weekly_chart(user):
    try:
        if not Image: return None
        W, H = 720, 400; img = Image.new('RGB', (W, H), '#0D0D0F'); draw = ImageDraw.Draw(img)
        f_title = get_font(22, True); f_small = get_font(14)
        draw.rectangle([0, 0, W, 60], fill='#161618')
        draw.text((20, 12), f"TOTAL MINGGUAN - {user['name'][:16]}", fill='white', font=f_title)
        total = user['total_text'] + user['total_media']
        draw.text((20, 150), f"Total Keseluruhan: {total} kiriman", fill='white', font=f_title)
        draw.text((20, 200), f"Teks: {user['total_text']} | Media: {user['total_media']}", fill='#A1A1AA', font=f_small)
        bio = io.BytesIO(); img.save(bio, format='JPEG', quality=70); bio.seek(0); return bio
    except: return None

def send_stats(chat_id, user, mode="today"):
    try:
        kb = {"inline_keyboard": [[{"text": "HARI INI" if mode != "today" else "• HARI INI", "callback_data": "stats_today"}, {"text": "MINGGUAN 7D" if mode != "weekly" else "• MINGGUAN 7D", "callback_data": "stats_weekly"}], [{"text": "Kembali", "callback_data": "back_home"}]]}
        if mode == "today": chart = make_today_chart(user); cap = f"📊 HARI INI - {user['name']}\n{user['today_text']} teks | {user['today_media']} media"
        else: chart = make_weekly_chart(user); cap = f"📈 MINGGUAN 7D - {user['name']}\n7 hari terakhir"
        if chart:
            chart.seek(0)
            try:
                r = TG.post(f"{BASE_TG}/sendPhoto", data={"chat_id": chat_id, "caption": cap}, files={"photo": ("s.jpg", chart, "image/jpeg")}, timeout=5).json()
                if r.get("ok"):
                    send_message(chat_id, "Silakan pilih mode:", kb); return
            except: pass
        send_message(chat_id, cap, kb)
    except: pass

def post_to_threads(text_content):
    try:
        if not THREADS_USER_ID or not THREADS_TOKEN: return False
        data = {"media_type": "TEXT", "text": text_content[:450], "access_token": THREADS_TOKEN}
        if MAIN_THREAD_ID: data["reply_to_id"] = MAIN_THREAD_ID
        r = TG.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads", data=data, timeout=3).json()
        cid = r.get("id")
        if not cid: return False
        r2 = TG.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish", data={"creation_id": cid, "access_token": THREADS_TOKEN}, timeout=3).json()
        return "id" in r2
    except: return False

def send_success(chat_id, user, ch_msg_id, target="both"):
    try:
        url = f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
        buttons = []
        if target in ["threads", "both"] and (user.get("threads_on") or is_admin(chat_id)): buttons.append([{"text": "Lihat di Threads", "url": THREADS_URL}])
        if target in ["channel", "both"] and ch_msg_id: buttons.append([{"text": "Lihat di Channel", "url": url}])
        if ch_msg_id: buttons.append([{"text": "Hapus", "callback_data": f"del_{ch_msg_id}"}])
        buttons.append([{"text": "Kembali", "callback_data": "back_home"}])
        note = f" -> {target.upper()}" if is_admin(chat_id) else ""
        if is_premium_active(user) and user.get("x_auto", True) and get_setting('x_auto_share', 'off') == 'on':
            note += " + X"
        if is_admin(chat_id) and get_setting('x_auto_share', 'off') == 'on':
            if " + X" not in note: note += " + X"
        send_message(chat_id, f"Menfess berhasil dikirim!{note}\n{SEP}\nMedia : {user['today_media']}/5\nTeks : {user['today_text']}/5", {"inline_keyboard": buttons})
    except Exception as e: print(f"send_success error: {e}")

def send_user_list(chat_id):
    db = get_db()
    if not db:
        send_message(chat_id, "Basis data belum tersambung."); return
    try:
        cur = db.cursor()
        cur.execute("SELECT user_id, name, username, total_text+total_media as total, banned, x_premium_until FROM menfess_users ORDER BY total DESC")
        rows = cur.fetchall(); cur.close()
        back_kb = {"inline_keyboard": [[{"text": "Kembali", "callback_data": "admin_panel"}]]}
        if not rows:
            send_message(chat_id, M("Belum ada pengguna."), back_kb); return
        header = M(f"Total Pengguna: {len(rows)}\n------------------------------\nSeluruh Anggota:")
        txt = header + "\n"
        for i, r in enumerate(rows, 1):
            status = " DIBLOKIR" if r[4] else ""
            prem = " 👑" if r[5] else ""
            display = f"<a href=\"tg://user?id={r[0]}\">@{r[2]}</a>" if r[2] else f"<a href=\"tg://user?id={r[0]}\">{r[0]}</a>"
            line = f"{i}. {display} - {r[0]} ({r[3]}){status}{prem}\n"
            if len(txt) + len(line) > 3200:
                send_message(chat_id, txt, back_kb)
                txt = M(f"Lanjutan ({i}/{len(rows)}):") + "\n"
            txt += line
        send_message(chat_id, txt, back_kb)
    except Exception as e:
        send_message(chat_id, f"Gagal memperoleh daftar pengguna: {e}")
    finally: release_db(db)

def handle_admin_command(chat_id, text):
    if text.startswith("/clearmenu"):
        TG.post(f"{BASE_TG}/setChatMenuButton", json={"menu_button": {"type": "default"}}, timeout=3)
        TG.post(f"{BASE_TG}/deleteMyCommands", json={}, timeout=3)
        send_message(chat_id, "Tombol menu dan perintah telah dibersihkan."); return True
    if text.startswith("/ban"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1].strip()
            if not target.isdigit():
                send_message(chat_id, M("ID harus berupa angka. Contoh: /ban 123456789")); return True
            tu = get_user(target); tu["banned"] = True; save_user_to_db(target, tu); send_message(chat_id, M(f"Pengguna {target} telah DIBLOKIR."))
        return True
    if text.startswith("/unban"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1].strip()
            if not target.isdigit():
                send_message(chat_id, M("ID harus berupa angka. Contoh: /unban 123456789")); return True
            tu = get_user(target); tu["banned"] = False; tu["warn"] = 0; save_user_to_db(target, tu); send_message(chat_id, M(f"Pengguna {target} telah DIBUKA BLOKIRNYA."))
        return True
    if text.startswith("/warn"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1].strip()
            if not target.isdigit():
                send_message(chat_id, M("ID harus berupa angka. Contoh: /warn 123456789")); return True
            tu = get_user(target); tu["warn"] = tu.get("warn", 0)+1
            if tu["warn"] >= 3: tu["banned"] = True
            save_user_to_db(target, tu); send_message(chat_id, M(f"Peringatan untuk {target} = {tu['warn']}/3 {'+ OTOMATIS DIBLOKIR' if tu['banned'] else ''}"))
        return True
    if text.startswith("/settag"):
        nt = text.replace("/settag", "").strip()
        if nt: set_setting('hashtag', nt); send_message(chat_id, M(f"Hashtag telah diubah menjadi {nt}"))
        return True
    if text.startswith("/setperaturan"):
        nt = text.replace("/setperaturan", "").strip()
        if nt: set_setting('peraturan', nt); send_message(chat_id, M("Peraturan telah diperbarui."))
        return True
    if text.startswith("/x_test"):
        ok = post_to_x(f"Uji JogjaLend Bot - X Auto Share ON {datetime.now(WIB).strftime('%H:%M')}")
        send_message(chat_id, M(f"Uji X: {'BERHASIL ✅' if ok else 'GAGAL ❌ - Silakan periksa variabel lingkungan X di Vercel / Log'}"))
        return True
    if text.startswith("/rt_test"):
        res = auto_retweet_hashtag()
        send_message(chat_id, M(f"Uji Retweet: {res}"))
        return True
    if text.startswith("/broadcast"):
        btext = text.replace("/broadcast", "").strip()
        if not btext:
            send_message(chat_id, "Silakan ketik: /broadcast [pesan Anda]", get_back_keyboard())
            return True
        dedup_key = f"bc_{hashlib.md5(btext.encode()).hexdigest()[:12]}"
        old = get_setting(dedup_key, "")
        if old:
            try:
                old_ts = float(old)
                if time.time() - old_ts < 300:
                    send_message(chat_id, "Broadcast ini telah dikirim dalam 5 menit terakhir. Mohon tunggu 5 menit agar tidak terjadi pengiriman ganda.", get_admin_panel())
                    return True
            except: pass
        db = get_db()
        if not db:
            send_message(chat_id, "Basis data belum tersambung. Broadcast gagal.", get_back_keyboard())
            return True
        try:
            cur = db.cursor(); cur.execute("SELECT user_id FROM menfess_users WHERE banned=FALSE"); rows = cur.fetchall(); cur.close()
        except Exception as e:
            send_message(chat_id, f"Gagal memperoleh daftar pengguna: {e}", get_back_keyboard())
            return True
        finally: release_db(db)
        if len(rows) > 80:
            send_message(chat_id, f"Jumlah pengguna terlalu banyak ({len(rows)}). Maksimal 80 per broadcast agar tidak terjadi timeout Vercel. Silakan bagi menjadi 2 kali broadcast.", get_admin_panel())
            return True
        set_setting(dedup_key, str(time.time()))
        sukses = 0; gagal = 0
        for r in rows:
            if send_message(r[0], f"📢 BROADCAST\n{SEP}\n{btext}"): sukses += 1
            else: gagal += 1
            time.sleep(0.05)
        send_message(chat_id, f"✅ Broadcast Terkirim!\n{SEP}\nPesan: {btext[:100]}\n\nBerhasil dikirim kepada: {sukses} anggota\nGagal: {gagal} anggota (memblokir bot / akun telah dihapus)\nTotal: {len(rows)} anggota", get_admin_panel())
        return True
    if text.startswith("/users"):
        send_user_list(chat_id); return True
    if text.startswith("/setwebhook"):
        host = request.host_url.rstrip('/'); wh = f"{host}/api/index"
        r = TG.get(f"{BASE_TG}/setWebhook", params={"url": wh}, timeout=3).json()
        send_message(chat_id, M(f"Webhook: {wh}\nHasil: {r}")); return True
    return False

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    try:
        host = request.host_url.rstrip('/')
        webhook_url = f"{host}/api/index"
        custom = os.getenv("WEBHOOK_URL")
        if custom: webhook_url = custom
        r = TG.get(f"{BASE_TG}/setWebhook", params={"url": webhook_url}, timeout=3).json()
        return f"Webhook set to {webhook_url}<br>{r}", 200
    except Exception as e:
        return f"Error setting webhook: {e}", 500

@app.route("/webhookinfo", methods=["GET"])
def webhook_info():
    try:
        r = TG.get(f"{BASE_TG}/getWebhookInfo", timeout=3).json()
        return jsonify(r), 200
    except Exception as e:
        return str(e), 500

@app.route("/api/cron_retweet", methods=["GET"])
def cron_retweet():
    if get_setting('x_retweet', 'on') != 'on':
        return "Retweet OFF", 200
    res = auto_retweet_hashtag()
    return res, 200

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def main_handler():
    data = {}; where = "init"
    try:
        if request.method == "GET": return "JogjaLend Bot V117.2 OK", 200
        where = "parse_json"; data = request.get_json(force=True, silent=True) or {}
        upd_id = data.get("update_id")
        if upd_id is not None:
            upd_key = f"upd_{upd_id}"
            if get_setting(upd_key, "") == "done":
                return "ok", 200
            set_setting(upd_key, "done")
        if "message" in data:
            msg = data["message"]; chat_id = msg["chat"]["id"]; uid = str(chat_id)
            where = f"get_user {uid}"; user = get_user(uid); text = msg.get("text", ""); caption = msg.get("caption", "")
            HASHTAG = get_setting('hashtag', '#jogjalend')
            if "from" in msg:
                raw = (msg["from"].get("first_name", "")+" "+(msg["from"].get("last_name", "") or "")).strip() or "-"
                user["name"] = raw.encode('ascii', 'ignore').decode('ascii') or "Pengguna"
                user["username"] = msg["from"].get("username", "")
            if is_admin(chat_id) and text.startswith("/"):
                if handle_admin_command(chat_id, text):
                    return "ok", 200
            if user.get("banned") and not is_admin(chat_id):
                send_message(chat_id, f"Anda telah DIBLOKIR.\n{SEP}\nPeringatan: {user.get('warn',0)}/3\nSilakan hubungi administrator.", get_back_keyboard())
                return "ok", 200
            if text.startswith("/start"):
                save_user_to_db(uid, user)
                send_message(chat_id, get_welcome_text(user), get_main_keyboard(is_admin(chat_id)))
            elif text.startswith("/newpost"): send_message(chat_id, f"Post Menfess\n{SEP}\nSilakan ketik teks Anda secara langsung, atau kirim media beserta keterangan.\nHashtag akan ditambahkan secara otomatis: {HASHTAG}", get_back_keyboard())
            elif text.startswith("/profile"): send_message(chat_id, f"Profil Saya\n{SEP}\nNama: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Teks: {user['today_text']}/5\nX Premium: {'AKTIF hingga '+user.get('x_premium_until','') if is_premium_active(user) else 'Belum aktif'}", get_back_keyboard())
            elif text.lower().startswith("/stats"): send_stats(chat_id, user, "today")
            elif text.startswith("/") and text.split()[0] not in ["/start", "/newpost", "/profile", "/stats"] and not is_admin(chat_id):
                send_message(chat_id, f"Perintah tidak dikenali: {text}\n{SEP}\nSilakan ketik /start untuk membuka menu.", get_back_keyboard())
            elif not user["banned"]:
                if user.get("waiting_proof") and ("photo" in msg or "video" in msg):
                    user["waiting_proof"] = False
                    save_user_to_db(uid, user)
                    fid = msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video", {}).get("file_id")
                    send_message(chat_id, f"Bukti Diterima! ✅\n{SEP}\nPembayaran Anda sedang diverifikasi oleh administrator. Anda akan menerima pemberitahuan setelah disetujui.", get_back_keyboard())
                    for adm in ADMIN_ID.split(","):
                        adm = adm.strip()
                        if not adm: continue
                        try:
                            TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": adm, "photo": fid, "caption": f"💰 PEMBAYARAN X PREMIUM\nPengguna: {user['name']} (@{user['username']})\nID: {uid}\nHarga: {X_PRICE}"}, timeout=5)
                            send_message(adm, "Apakah Anda ingin menyetujui pengguna ini?", {"inline_keyboard": [[{"text": "✅ Setujui 30 Hari", "callback_data": f"x_approve_{uid}"}, {"text": "❌ Tolak", "callback_data": f"x_reject_{uid}"}]]})
                        except: pass
                    return "ok", 200
                if text and not text.startswith("/") and len(text) >= 3:
                    if user["today_text"] >= 5: send_message(chat_id, f"Batas Tercapai 5/5\n{SEP}\nKuota akan diatur ulang pada pukul 00:00 WIB", get_back_keyboard())
                    else:
                        clean = text.strip()
                        if HASHTAG.lower() not in clean.lower(): clean = f"{clean} {HASHTAG}"
                        if get_setting('approval', 'off') == 'on' and not is_admin(chat_id):
                            pid = secrets.token_hex(8)
                            pkey = f"pending_{pid}"
                            set_setting(pkey, json.dumps({"type": "text", "owner": uid, "text": clean, "name": user['name'], "username": user['username']}, ensure_ascii=False))
                            kb_appr = {"inline_keyboard": [[{"text": "✅ Setujui", "callback_data": f"appr_{pid}"}, {"text": "❌ Tolak", "callback_data": f"rej_{pid}"}]]}
                            send_message(LOG_CHANNEL, f"📥 MENFESS MENUNGGU PERSETUJUAN\nDari: {user['name']} (@{user['username']})\nID: {pid}\n{SEP}\n{clean}", kb_appr)
                            send_message(chat_id, f"Menfess Anda telah masuk ke antrean persetujuan administrator.\n{SEP}\nMohon menunggu.", get_back_keyboard())
                            return "ok", 200
                        target = user.get("admin_target", "both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                        ch_id = None
                        if target in ["channel", "both"]:
                            r = TG.post(f"{BASE_TG}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=3).json()
                            ch_id = r.get("result", {}).get("message_id")
                            save_post_owner(ch_id, uid)
                        if target in ["threads", "both"]: post_to_threads(clean)
                        if (is_admin(chat_id) or (is_premium_active(user) and user.get("x_auto", True))) and get_setting('x_auto_share', 'off') == 'on':
                            post_to_x(clean)
                        user["today_text"] += 1; user["total_text"] += 1; user["total_chars"] = user.get("total_chars", 0)+len(text)
                        save_user_to_db(uid, user); send_success(chat_id, user, ch_id, target)
                if "photo" in msg or "video" in msg:
                    if caption and any(w in caption.lower() for w in ["bukti", "transfer", "tf ", "qris", "struk", "receipt"]):
                        send_message(chat_id, "Pesan ini terdeteksi sebagai bukti pembayaran, bukan menfess. Bukti pembayaran tidak akan dipublikasikan ke channel. Silakan kirim melalui menu X Premium.", get_back_keyboard())
                        return "ok", 200
                    if user["today_media"] >= 5: send_message(chat_id, "Batas Tercapai 5/5", get_back_keyboard())
                    else:
                        fid = msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video", {}).get("file_id")
                        is_photo = "photo" in msg
                        base_cap = caption.strip() if caption else HASHTAG
                        if HASHTAG.lower() not in base_cap.lower(): base_cap = f"{base_cap} {HASHTAG}"
                        if get_setting('approval', 'off') == 'on' and not is_admin(chat_id):
                            pid = secrets.token_hex(8)
                            pkey = f"pending_{pid}"
                            set_setting(pkey, json.dumps({"type": "video" if not is_photo else "photo", "owner": uid, "file_id": fid, "caption": base_cap, "name": user['name'], "username": user['username']}, ensure_ascii=False))
                            kb_appr = {"inline_keyboard": [[{"text": "✅ Setujui", "callback_data": f"appr_{pid}"}, {"text": "❌ Tolak", "callback_data": f"rej_{pid}"}]]}
                            try:
                                if is_photo: TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": LOG_CHANNEL, "photo": fid, "caption": f"📥 MEDIA MENUNGGU PERSETUJUAN\nDari: {user['name']} (@{user['username']})\nID: {pid}\n{SEP}\n{base_cap}"}, timeout=5)
                                else: TG.post(f"{BASE_TG}/sendVideo", json={"chat_id": LOG_CHANNEL, "video": fid, "caption": f"📥 MEDIA MENUNGGU PERSETUJUAN\nDari: {user['name']} (@{user['username']})\nID: {pid}\n{SEP}\n{base_cap}"}, timeout=5)
                            except: pass
                            send_message(LOG_CHANNEL, f"📥 MEDIA MENUNGGU PERSETUJUAN - ID: {pid}\nDari: {user['name']} (@{user['username']})", kb_appr)
                            send_message(chat_id, "Media Anda telah masuk ke antrean persetujuan administrator.\nMohon menunggu.", get_back_keyboard())
                            return "ok", 200
                        target = user.get("admin_target", "both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                        ch_id = None
                        wm_bytes = None
                        if target in ["channel", "both"]:
                            if is_photo:
                                raw = download_file(fid); wm = add_watermark(raw) if raw else None
                                if wm:
                                    wm.seek(0); wm_bytes = wm.read(); wm.seek(0)
                                    r = TG.post(f"{BASE_TG}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": ("wm.jpg", wm, "image/jpeg")}, timeout=5).json(); ch_id = r.get("result", {}).get("message_id")
                                else:
                                    r = TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=3).json(); ch_id = r.get("result", {}).get("message_id")
                            else:
                                r = TG.post(f"{BASE_TG}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id = r.get("result", {}).get("message_id")
                            save_post_owner(ch_id, uid)
                        if target in ["threads", "both"]: post_to_threads(base_cap)
                        if (is_admin(chat_id) or (is_premium_active(user) and user.get("x_auto", True))) and get_setting('x_auto_share', 'off') == 'on':
                            if is_photo and wm_bytes:
                                post_to_x(base_cap, wm_bytes)
                            elif not is_photo:
                                post_to_x(base_cap)
                        user["today_media"] += 1; user["total_media"] += 1
                        save_user_to_db(uid, user); send_success(chat_id, user, ch_id, target)
        if "callback_query" in data:
            cq = data["callback_query"]; chat_id = cq["message"]["chat"]["id"]; uid = str(chat_id); cdata = cq["data"]; msg_id = cq["message"]["message_id"]
            where = f"callback {cdata}"
            try: TG.post(f"{BASE_TG}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
            except: pass
            user = get_user(uid)
            HASHTAG = get_setting('hashtag', '#jogjalend')
            if user.get("banned") and not is_admin(chat_id):
                edit_message_fast(chat_id, msg_id, "Anda telah DIBLOKIR.", get_back_keyboard())
                return "ok", 200
            if cdata in ["stats", "stats_today", "stats_weekly"]:
                try: TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=2)
                except: pass
                mode = "weekly" if cdata == "stats_weekly" else "today"
                send_stats(chat_id, user, mode)
            elif cdata == "back_home": edit_message_fast(chat_id, msg_id, get_welcome_text(user), get_main_keyboard(is_admin(chat_id)))
            elif cdata == "lend_page1": edit_message_fast(chat_id, msg_id, M("Silakan pilih pengaturan yang ingin diubah."), get_menu_1())
            elif cdata == "lend_page2": edit_message_fast(chat_id, msg_id, M("Silakan pilih pengaturan yang ingin diubah."), get_menu_2())
            elif cdata == "my_profile": edit_message_fast(chat_id, msg_id, f"Profil Saya\n{SEP}\nNama: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Teks: {user['today_text']}/5\nHashtag: {HASHTAG}\nX Premium: {'AKTIF hingga '+user.get('x_premium_until','') if is_premium_active(user) else 'Belum aktif'}", get_back_keyboard())
            elif cdata == "post": edit_message_fast(chat_id, msg_id, f"Post Menfess\n{SEP}\nSilakan ketik teks Anda secara langsung, atau kirim media beserta keterangan.\nHashtag akan ditambahkan secara otomatis: {HASHTAG}", get_back_keyboard())
            elif cdata == "threads":
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "Kembali", "callback_data": "back_home"}]]}
                edit_message_fast(chat_id, msg_id, f"Pengaturan Threads\n{SEP}\nStatus: {'ON' if user.get('threads_on') else 'OFF'}\nTautan: threads.net/jogjalend", kb)
            elif cdata == "threads_toggle":
                user["threads_on"] = not user.get("threads_on", False); save_user_to_db(uid, user)
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "Kembali", "callback_data": "back_home"}]]}
                edit_message_fast(chat_id, msg_id, f"Threads {'ON' if user['threads_on'] else 'OFF'}!\nTautan: threads.net/jogjalend", kb)
            elif cdata == "info_bot":
                edit_message_fast(chat_id, msg_id, "Informasi Bot\n\nJogjaLend Bot merupakan bot yang dikembangkan oleh tim @jogja_lend.\n<pre>Versi Bot : V117.2\nBasis Data  : PostgreSQL</pre>\nUntuk pertanyaan mengenai penggunaan bot, saran fitur, atau laporan bug, silakan hubungi @joglendsupportBot", get_back_keyboard())
            elif cdata == "x_premium":
                if is_premium_active(user):
                    auto = "ON" if user.get("x_auto", True) else "OFF"
                    edit_message_fast(chat_id, msg_id, f"🎉 X Premium AKTIF ✅\n{SEP}\nBerlaku Hingga: {user.get('x_premium_until','')}\nStatus Posting Otomatis: {auto}\nMenfess Anda akan otomatis dipublikasikan ke X apabila diaktifkan.", get_x_premium_keyboard(user))
                else:
                    send_qris(chat_id)
                    edit_message_fast(chat_id, msg_id, f"𝕏 X Premium 🔒\n{SEP}\nAktifkan posting otomatis menfess Anda ke X.\n\nHarga: {X_PRICE}\n{QRIS_TEXT}\n\nPetunjuk:\n1. Silakan transfer sesuai nominal.\n2. Ketuk 'Saya Telah Transfer'.\n3. Kirim foto bukti transfer di sini.\n4. Mohon menunggu persetujuan administrator.", get_x_premium_keyboard(user))
            elif cdata == "x_pay_proof":
                user["waiting_proof"] = True; save_user_to_db(uid, user)
                edit_message_fast(chat_id, msg_id, f"Kirim Bukti Transfer\n{SEP}\nSilakan kirim FOTO bukti transfer QRIS Anda di sini.\nMohon untuk tidak mengirim menfess terlebih dahulu, kirimkan hanya bukti transfer.", get_back_keyboard())
            elif cdata == "x_toggle_auto":
                if is_premium_active(user):
                    user["x_auto"] = not user.get("x_auto", True); save_user_to_db(uid, user)
                    auto = "ON" if user.get("x_auto", True) else "OFF"
                    edit_message_fast(chat_id, msg_id, f"🎉 X Premium AKTIF ✅\n{SEP}\nBerlaku Hingga: {user.get('x_premium_until','')}\nStatus Posting Otomatis: {auto}", get_x_premium_keyboard(user))
            elif cdata.startswith("x_approve_"):
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
                else:
                    target_id = cdata.replace("x_approve_", "")
                    tu = get_user(target_id)
                    until = (datetime.now(WIB) + timedelta(days=PREMIUM_DAYS)).strftime("%Y-%m-%d")
                    tu["x_premium_until"] = until; tu["x_auto"] = True; save_user_to_db(target_id, tu)
                    edit_message_fast(chat_id, msg_id, f"✅ Disetujui! Pengguna {target_id} aktif hingga {until}", get_admin_panel())
                    send_message(target_id, f"🎉 X Premium DIAKTIFKAN!\n{SEP}\nBerlaku Hingga: {until}\nMenfess Anda sekarang akan otomatis dipublikasikan ke X. Anda dapat mengaktifkan atau menonaktifkan fitur ini pada menu X Premium.", get_back_keyboard())
            elif cdata.startswith("x_reject_"):
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
                else:
                    target_id = cdata.replace("x_reject_", "")
                    edit_message_fast(chat_id, msg_id, f"❌ Ditolak. Pengguna {target_id}", get_admin_panel())
                    send_message(target_id, f"❌ Pembayaran X Premium Anda ditolak.\n{SEP}\nSilakan hubungi administrator apabila Anda meyakini telah menyelesaikan transfer.", get_back_keyboard())
            elif cdata.startswith("appr_") or cdata.startswith("rej_"):
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
                else:
                    pid = cdata.split("_", 1)[1]
                    pkey = f"pending_{pid}"
                    raw_pending = get_setting(pkey, "")
                    if not raw_pending:
                        edit_message_fast(chat_id, msg_id, "Pengajuan ini telah diproses atau telah kedaluwarsa.", get_admin_panel())
                    else:
                        try: pend = json.loads(raw_pending)
                        except: pend = {"type": "text", "text": raw_pending, "owner": ""}
                        delete_setting(pkey)
                        owner_id = pend.get("owner", "")
                        if cdata.startswith("appr_"):
                            if pend.get("type") == "text":
                                txt = pend.get("text", "")
                                rr = TG.post(f"{BASE_TG}/sendMessage", json={"chat_id": CHANNEL_ID, "text": txt, "parse_mode": "HTML"}, timeout=3).json()
                                ch_mid = rr.get("result", {}).get("message_id")
                                save_post_owner(ch_mid, owner_id)
                                try:
                                    ou = get_user(str(owner_id)); ou["today_text"] += 1; ou["total_text"] += 1; save_user_to_db(str(owner_id), ou)
                                except: pass
                                if owner_id: send_message(owner_id, f"Menfess Anda telah disetujui dan dipublikasikan.\n{SEP}\n{txt[:100]}", get_back_keyboard())
                            else:
                                fid2 = pend.get("file_id", ""); cap2 = pend.get("caption", "")
                                if pend.get("type") == "photo":
                                    rr = TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid2, "caption": cap2, "parse_mode": "HTML"}, timeout=5).json()
                                else:
                                    rr = TG.post(f"{BASE_TG}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid2, "caption": cap2, "parse_mode": "HTML"}, timeout=5).json()
                                ch_mid = rr.get("result", {}).get("message_id")
                                save_post_owner(ch_mid, owner_id)
                                try:
                                    ou = get_user(str(owner_id)); ou["today_media"] += 1; ou["total_media"] += 1; save_user_to_db(str(owner_id), ou)
                                except: pass
                                if owner_id: send_message(owner_id, "Media Anda telah disetujui dan dipublikasikan.", get_back_keyboard())
                            edit_message_fast(chat_id, msg_id, "Telah disetujui dan dipublikasikan ke channel.", get_admin_panel())
                        else:
                            edit_message_fast(chat_id, msg_id, "Ditolak.", get_admin_panel())
                            if owner_id: send_message(owner_id, "Menfess Anda ditolak oleh administrator.", get_back_keyboard())
            elif cdata == "admin_panel":
                if is_admin(chat_id): edit_message_fast(chat_id, msg_id, M("PANEL ADMIN V117.2\n------------------------------\nSilakan pilih menu administrator:"), get_admin_panel())
                else: edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
            elif cdata == "admin_x_toggle":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
                else:
                    cur = get_setting('x_auto_share', 'off')
                    new = 'on' if cur == 'off' else 'off'
                    set_setting('x_auto_share', new)
                    edit_message_fast(chat_id, msg_id, M(f"X Auto Share: {new.upper()}\n------------------------------\n{'Kiriman administrator dan pengguna Premium sekarang akan otomatis dibagikan ke X.' if new=='on' else 'Pembagian otomatis ke X telah dinonaktifkan.'}"), get_admin_panel())
            elif cdata == "admin_rt_toggle":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
                else:
                    cur = get_setting('x_retweet', 'on')
                    new = 'on' if cur == 'off' else 'off'
                    set_setting('x_retweet', new)
                    edit_message_fast(chat_id, msg_id, M(f"Auto Retweet {RETWEET_HASHTAG}: {new.upper()}"), get_admin_panel())
            elif cdata == "admin_x_test":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
                else:
                    ok = post_to_x(f"Uji JogjaLend Bot X Auto Share {datetime.now(WIB).strftime('%H:%M')}")
                    edit_message_fast(chat_id, msg_id, M(f"Uji X: {'BERHASIL ✅ - Silakan periksa akun X Anda' if ok else 'GAGAL ❌ - Silakan periksa variabel lingkungan X / Paket Basic / Log Vercel'}"), get_admin_panel())
            elif cdata == "admin_rt_test":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
                else:
                    res = auto_retweet_hashtag()
                    edit_message_fast(chat_id, msg_id, M(f"Uji Retweet: {res}"), get_admin_panel())
            elif cdata == "lend_tag":
                edit_message_fast(chat_id, msg_id, M(f"Tag Saat Ini: {HASHTAG}\n------------------------------\nUntuk mengubahnya, gunakan perintah:\n/settag #tagbaru"), get_menu_1())
            elif cdata == "lend_persetujuan":
                cur = get_setting('approval', 'off')
                kb = {"inline_keyboard": [[{"text": f"Mode: {cur.upper()} - Ketuk untuk mengubah", "callback_data": "toggle_approval"}], [{"text": "Kembali", "callback_data": "lend_page1"}]]}
                edit_message_fast(chat_id, msg_id, M(f"Mode Persetujuan\n------------------------------\nApabila AKTIF, menfess tidak akan langsung dipublikasikan. Menfess akan dikirim ke LOG_CHANNEL untuk persetujuan terlebih dahulu.\nStatus: {cur}"), kb)
            elif cdata == "toggle_approval":
                cur = get_setting('approval', 'off'); new = 'on' if cur == 'off' else 'off'; set_setting('approval', new)
                kb = {"inline_keyboard": [[{"text": f"Mode: {new.upper()} - Ketuk untuk mengubah", "callback_data": "toggle_approval"}], [{"text": "Kembali", "callback_data": "lend_page1"}]]}
                edit_message_fast(chat_id, msg_id, M(f"Mode Persetujuan telah diubah menjadi {new.upper()}"), kb)
            elif cdata == "lend_hapus": edit_message_fast(chat_id, msg_id, M("Hapus Pesan\n------------------------------\nPengguna dapat menghapus kirimannya sendiri menggunakan tombol Hapus setelah mengirim."), get_menu_1())
            elif cdata == "lend_lang": edit_message_fast(chat_id, msg_id, M("Bahasa\n------------------------------\nBahasa bot saat ini: Bahasa Indonesia."), get_menu_1())
            elif cdata == "lend_peraturan":
                per = get_setting('peraturan', '-')
                edit_message_fast(chat_id, msg_id, M(f"Peraturan\n------------------------------\n{per}\n\nUntuk mengubah: /setperaturan [teks]"), get_menu_2())
            elif cdata == "lend_peringatan": edit_message_fast(chat_id, msg_id, M(f"Peringatan\n------------------------------\n/warn [user_id] - Tambah peringatan (3 peringatan = otomatis diblokir)\nPeringatan Anda saat ini: {user.get('warn',0)}/3"), get_menu_2())
            elif cdata == "lend_blacklist":
                db = get_db()
                txt = "Daftar Blokir\n------------------------------\n"
                if db:
                    cur = db.cursor(); cur.execute("SELECT user_id, name, warn FROM menfess_users WHERE banned=true LIMIT 20"); rows = cur.fetchall(); cur.close(); release_db(db)
                    if not rows: txt += "Tidak ada pengguna yang diblokir."
                    else:
                        for r in rows: txt += f"{r[1]} - {r[0]} warn:{r[2]}\n"
                    kb = {"inline_keyboard": [[{"text": "Unban: /unban [id]", "callback_data": "admin_noop"}], [{"text": "Kembali", "callback_data": "lend_page2"}]]}
                else: kb = get_menu_2()
                edit_message_fast(chat_id, msg_id, M(txt), kb)
            elif cdata == "lend_izin": edit_message_fast(chat_id, msg_id, M("Perizinan\n------------------------------\nSeluruh pengguna dapat mengirim teks/media (maksimal 5). Administrator dapat memblokir atau memberi peringatan kepada pengguna."), get_menu_2())
            elif cdata == "lend_log": edit_message_fast(chat_id, msg_id, M(f"Log Channel\n------------------------------\nLog Channel: {LOG_CHANNEL}\nKesalahan dan persetujuan akan dikirim ke sini."), get_menu_2())
            elif cdata == "lend_channel":
                if is_admin(chat_id): edit_message_fast(chat_id, msg_id, M(f"Pengelolaan Channel\n------------------------------\nSilakan pilih target publikasi.\nSaat Ini: {user.get('admin_target','both').upper()}"), get_channel_target_keyboard(user))
                else: edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
            elif cdata == "admin_set_channel":
                if is_admin(chat_id): user["admin_target"] = "channel"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Diatur ke CHANNEL SAJA\n------------------------------\nMenfess hanya akan dikirim ke {CHANNEL_ID}"), get_channel_target_keyboard(user))
            elif cdata == "admin_set_threads":
                if is_admin(chat_id): user["admin_target"] = "threads"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Diatur ke THREADS SAJA\n------------------------------\nMenfess hanya akan dikirim ke Threads"), get_channel_target_keyboard(user))
            elif cdata == "admin_set_both":
                if is_admin(chat_id): user["admin_target"] = "both"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Diatur ke KEDUANYA\n------------------------------\nMenfess akan dikirim ke Channel + Threads"), get_channel_target_keyboard(user))
            elif cdata == "admin_users":
                send_user_list(chat_id)
                edit_message_fast(chat_id, msg_id, M("Daftar pengguna telah dikirim di bawah."), get_admin_panel())
            elif cdata == "admin_allstats":
                db = get_db()
                if db:
                    cur = db.cursor(); cur.execute("SELECT SUM(total_text), SUM(total_media) FROM menfess_users"); s = cur.fetchone(); cur.close(); release_db(db)
                    edit_message_fast(chat_id, msg_id, M(f"STATISTIK GLOBAL\n------------------------------\nTeks : {s[0]}\nMedia: {s[1]}"), get_admin_panel())
            elif cdata == "admin_broadcast":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Akses ditolak. Khusus administrator."), get_back_keyboard())
                else:
                    edit_message_fast(chat_id, msg_id, "📢 BROADCAST\n------------------------------\nSilakan ketik:\n/broadcast [pesan Anda]\n\nContoh:\n/broadcast Halo semuanya, besok tersedia stok baru\n\nPesan akan dikirim kepada seluruh pengguna di basis data.", get_back_keyboard())
            elif cdata == "admin_webhook":
                r = TG.get(f"{BASE_TG}/getWebhookInfo", timeout=3).json()
                res = r.get('result', {})
                url = res.get('url', '')
                edit_message_fast(chat_id, msg_id, M("Informasi Webhook\n------------------------------") + f"\nURL: <a href=\"{url}\">{url}</a>\n" + M(f"Pending: {res.get('pending_update_count')}\nKesalahan Terakhir: {res.get('last_error_message')}\n\nUntuk mengatur ulang:") + "\n/setwebhook", get_admin_panel())
            elif cdata == "admin_logs": edit_message_fast(chat_id, msg_id, M(f"Log\n------------------------------\nKesalahan akan otomatis dikirim ke {LOG_CHANNEL}\nSilakan periksa /webhookinfo dan Log Vercel."), get_admin_panel())
            elif cdata == "admin_noop": pass
            elif cdata == "close":
                try: TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=2)
                except: pass
            elif cdata.startswith("del_"):
                mid = cdata.replace("del_", "")
                allowed = is_admin(chat_id)
                if not allowed and mid.isdigit():
                    db = get_db()
                    if db:
                        try:
                            cur = db.cursor(); cur.execute("SELECT owner_id FROM menfess_posts WHERE msg_id=%s", (mid,)); r = cur.fetchone(); cur.close()
                            if r and str(r[0]) == str(uid): allowed = True
                        except: pass
                        finally: release_db(db)
                if not allowed:
                    edit_message_fast(chat_id, msg_id, "Anda bukan pemilik kiriman ini.", get_back_keyboard())
                else:
                    if mid.isdigit():
                        try: TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=2)
                        except: pass
                    edit_message_fast(chat_id, msg_id, "Berhasil Dihapus ✅", get_back_keyboard())
        return "ok", 200
    except Exception as e:
        try: print(f"[CRITICAL {where}] {e}\n{traceback.format_exc()}")
        except: pass
        return "ok", 200