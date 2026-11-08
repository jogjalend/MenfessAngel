# api/index.py - JogjaLend Bot V117.6 - NO THREADS - Channel + X Fail-Safe (X Banned Tetap Share ke Channel) + Button 2x2 + X @jogcorp
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
LOG_CHANNEL = os.getenv("LOG_CHANNEL") or CHANNEL_ID
WIB = timezone(timedelta(hours=7))
SEP = "●-----------------------------------------------------●"

X_API_KEY = os.getenv("X_API_KEY") or ""
X_API_SECRET = os.getenv("X_API_SECRET") or ""
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or ""
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET") or ""
QRIS_IMAGE_URL = os.getenv("QRIS_IMAGE_URL") or ""
QRIS_TEXT = os.getenv("QRIS_TEXT") or "QRIS a.n jogjaStore, please scan the QR code above"
X_PRICE = os.getenv("X_PRICE") or "Rp 100.000 / 30 days"
PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS") or "30")
RETWEET_HASHTAG = os.getenv("RETWEET_HASHTAG") or "#jogjalend"
# Akun X resmi: https://x.com/jogcorp
X_USERNAME = os.getenv("X_USERNAME") or "jogcorp"

TG = requests.Session()
TG.headers.update({"Connection": "keep-alive"})
BASE_TG = f"https://api.telegram.org/bot{BOT_TOKEN}"

SETTINGS_CACHE = {}
USERS = defaultdict(lambda: {"name": "", "username": "", "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0, "warn": 0, "waiting_proof": False, "x_premium_until": "", "x_auto": True})

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
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0, warn INT DEFAULT 0)")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS x_premium_until TEXT DEFAULT ''")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS waiting_proof BOOLEAN DEFAULT FALSE")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS x_auto BOOLEAN DEFAULT TRUE")
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_posts (msg_id TEXT PRIMARY KEY, owner_id TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('hashtag', '#jogjalend') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('peraturan', '1. No SARA & Pornography\n2. No spam\n3. Maximum 5 posts per day') ON CONFLICT (key) DO NOTHING")
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

def _x_upload_media(photo_bytes, is_video=False):
    try:
        if not photo_bytes: return None
        if is_video:
            url_init = "https://upload.twitter.com/1.1/media/upload.json"
            h = _x_oauth_header("POST", url_init)
            r = TG.post(url_init, headers={"Authorization": h}, data={"command": "INIT", "total_bytes": len(photo_bytes), "media_type": "video/mp4", "media_category": "tweet_video"}, timeout=15)
            j = r.json()
            media_id = j.get("media_id_string")
            if not media_id:
                print(f"X video INIT failed: {j}")
                return None
            chunk_size = 1024 * 1024
            for idx in range(0, len(photo_bytes), chunk_size):
                chunk = photo_bytes[idx:idx+chunk_size]
                h2 = _x_oauth_header("POST", url_init)
                files = {"media": ("video.mp4", chunk, "video/mp4")}
                rr = TG.post(url_init, headers={"Authorization": h2}, data={"command": "APPEND", "media_id": media_id, "segment_index": idx // chunk_size}, files=files, timeout=20)
                print(f"X video APPEND {idx//chunk_size}: {rr.status_code}")
            h3 = _x_oauth_header("POST", url_init)
            rf = TG.post(url_init, headers={"Authorization": h3}, data={"command": "FINALIZE", "media_id": media_id}, timeout=15)
            print(f"X video FINALIZE: {rf.status_code} {rf.text[:200]}")
            for _ in range(10):
                h4 = _x_oauth_header("GET", url_init, {"command": "STATUS", "media_id": media_id})
                rs = TG.get(url_init, headers={"Authorization": h4}, params={"command": "STATUS", "media_id": media_id}, timeout=10)
                st = rs.json().get("processing_info", {}).get("state")
                print(f"X video STATUS: {st}")
                if st == "succeeded": break
                if st == "failed": return None
                time.sleep(2)
            return media_id
        url = "https://upload.twitter.com/1.1/media/upload.json"
        header = _x_oauth_header("POST", url)
        if not header: return None
        files = {"media": ("img.jpg", photo_bytes, "image/jpeg")}
        r = TG.post(url, headers={"Authorization": header}, files=files, timeout=15)
        j = r.json()
        print(f"X photo upload: {r.status_code} {str(j)[:200]}")
        return j.get("media_id_string")
    except Exception as e:
        print(f"X upload error: {e}")
        return None

def post_to_x(text_content, photo_bytes=None, is_video=False):
    try:
        if not X_API_KEY or not X_API_SECRET or not X_ACCESS_TOKEN or not X_ACCESS_SECRET:
            return False, None
        BAD = ["judol", "slot", "bokep", "porno", "togel", "gacor", "maxwin"]
        if any(b in (text_content or "").lower() for b in BAD):
            print("X blocked bad word")
            return False, None
        clean = re.sub(r"<[^>]+>", "", text_content or "").strip()
        if not clean:
            return False, None
        if len(clean) > 280:
            clean = clean[:277] + "..."
        media_id = None
        if photo_bytes:
            media_id = _x_upload_media(photo_bytes, is_video=is_video)
        url = "https://api.twitter.com/2/tweets"
        header = _x_oauth_header("POST", url, None)
        if not header: return False, None
        payload = {"text": clean}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}
        r = TG.post(url, headers={"Authorization": header, "Content-Type": "application/json"}, json=payload, timeout=10)
        print(f"X post: {r.status_code}")
        if r.status_code in [200, 201]:
            try:
                tweet_id = r.json().get("data", {}).get("id")
                if tweet_id:
                    return True, f"https://x.com/i/status/{tweet_id}"
            except:
                pass
            return True, None
        # 401 / 403 = token invalid / akun ke-banned / suspended - jangan lempar error
        print(f"X post failed {r.status_code}: {r.text[:300]}")
        return False, None
    except Exception as e:
        print(f"X post error (ditahan, channel tetap jalan): {e}")
        return False, None

# V117.6 - FAIL-SAFE WRAPPER: X gagal apapun alasannya, JANGAN PERNAH gagalkan Channel
def safe_post_to_x(text_content, photo_bytes=None, is_video=False):
    try:
        if get_setting('x_auto_share', 'off') != 'on':
            return False, None
        ok, url = post_to_x(text_content, photo_bytes, is_video)
        return ok, url
    except Exception as e:
        print(f"safe_post_to_x ditahan: {e}")
        return False, None

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
            return "X ENV not configured"
        last_id = get_setting('last_retweet_id', '0')
        my_id = _x_get_my_id()
        if not my_id: return "Failed to get my X user ID"
        query = f"{RETWEET_HASHTAG} -is:retweet -is:reply -from:{X_USERNAME}"
        url = "https://api.twitter.com/2/tweets/search/recent"
        params = {"query": query, "max_results": 10, "tweet.fields": "author_id,created_at"}
        if last_id and last_id != "0":
            params["since_id"] = last_id
        h = _x_oauth_header("GET", url, params)
        r = TG.get(url, headers={"Authorization": h}, params=params, timeout=10)
        j = r.json()
        if r.status_code != 200:
            print(f"Search error: {r.status_code} {r.text[:300]}")
            return f"Search failed {r.status_code}"
        tweets = j.get("data", [])
        if not tweets:
            return "No new tweet"
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
        return f"Retweeted {count} / {len(tweets)}"
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
        cur.execute("SELECT name, username, today_text, today_media, last_date, banned, total_text, total_media, total_chars, warn, x_premium_until, waiting_proof, x_auto FROM menfess_users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close()
        if row: return {"name": row[0] or "", "username": row[1] or "", "today_text": row[2] or 0, "today_media": row[3] or 0, "last_date": row[4] or "", "banned": row[5] or False, "total_text": row[6] or 0, "total_media": row[7] or 0, "total_chars": row[8] or 0, "warn": row[9] or 0, "x_premium_until": row[10] or "", "waiting_proof": row[11] or False, "x_auto": row[12] if row[12] is not None else True}
    except: return None
    finally: release_db(db)
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, today_text, today_media, last_date, banned, total_text, total_media, total_chars, warn, x_premium_until, waiting_proof, x_auto) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s, warn=%s, x_premium_until=%s, waiting_proof=%s, x_auto=%s", (uid, user["name"], user["username"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars", 0), user.get("warn", 0), user.get("x_premium_until",""), user.get("waiting_proof", False), user.get("x_auto", True), user["name"], user["username"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars", 0), user.get("warn", 0), user.get("x_premium_until",""), user.get("waiting_proof", False), user.get("x_auto", True)))
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
            TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": chat_id, "photo": QRIS_IMAGE_URL, "caption": f"Please scan this QRIS to pay for X Premium\nPrice: {X_PRICE}"}, timeout=5)
            return True
        except: pass
    return False

def get_x_premium_keyboard(user=None):
    if user and is_premium_active(user):
        auto = "ON" if user.get("x_auto", True) else "OFF"
        return {"inline_keyboard": [[{"text": f"𝕏 X Auto Post: {auto}", "callback_data": "x_toggle_auto"}], [{"text": "Back", "callback_data": "back_home"}]]}
    return {"inline_keyboard": [[{"text": "💳 I Have Transferred, Send Receipt", "callback_data": "x_pay_proof"}], [{"text": "Back", "callback_data": "back_home"}]]}

def get_welcome_text(user):
    hashtag = get_setting('hashtag', '#jogjalend')
    prem = " ✅ X Premium" if is_premium_active(user) else ""
    return f"Welcome !{prem}\n{SEP}\nPublish to {CHANNEL_ID}\nPlease tap Post to submit.\n\nQuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5\nTag: {hashtag}"

def get_back_keyboard(): return {"inline_keyboard": [[{"text": "Back", "callback_data": "back_home"}]]}
def get_main_keyboard(is_ad=False):
    kb = {"inline_keyboard": [[{"text": "👤 My Profile", "callback_data": "my_profile"}, {"text": "💌 Post", "callback_data": "post"}], [{"text": "𝕏 X Premium", "callback_data": "x_premium"}], [{"text": "📈 Stats", "callback_data": "stats"}, {"text": "ℹ️ Bot Info", "callback_data": "info_bot"}]]}
    if is_ad: kb["inline_keyboard"].append([{"text": "🔧 ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb
def get_menu_1():
    return {"inline_keyboard": [[{"text": "🔔 Tag", "callback_data": "lend_tag"}], [{"text": "📥 Approval Mode", "callback_data": "lend_persetujuan"}], [{"text": "🗑️ Delete Message", "callback_data": "lend_hapus"}], [{"text": "🇮🇩 Language", "callback_data": "lend_lang"}, {"text": "✅ Close", "callback_data": "close"}], [{"text": "▶️ More", "callback_data": "lend_page2"}]]}
def get_menu_2():
    return {"inline_keyboard": [[{"text": "📜 Rules", "callback_data": "lend_peraturan"}], [{"text": "⚠️ Warnings", "callback_data": "lend_peringatan"}], [{"text": "🚫 Blacklist", "callback_data": "lend_blacklist"}], [{"text": "🔐 Permissions", "callback_data": "lend_izin"}, {"text": "📋 Channel Log", "callback_data": "lend_log"}], [{"text": "⬅️ Back", "callback_data": "lend_page1"}, {"text": "❌ Close", "callback_data": "close"}]]}

def get_admin_panel():
    x_on = get_setting('x_auto_share', 'off') == 'on'
    x_label = f"{'✅ ' if x_on else '❌ '}𝕏 Auto Share: {'ON' if x_on else 'OFF'}"
    rt_on = get_setting('x_retweet', 'on') == 'on'
    rt_label = f"{'✅ ' if rt_on else '❌ '}🔁 Auto Retweet {RETWEET_HASHTAG}: {'ON' if rt_on else 'OFF'}"
    return {"inline_keyboard": [
        [{"text": "👥 User List", "callback_data": "admin_users"}, {"text": "📊 All Stats", "callback_data": "admin_allstats"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}, {"text": "🚫 Ban/Unban", "callback_data": "lend_blacklist"}],
        [{"text": x_label, "callback_data": "admin_x_toggle"}],
        [{"text": rt_label, "callback_data": "admin_rt_toggle"}],
        [{"text": "🧪 Test Post to X", "callback_data": "admin_x_test"}, {"text": "🔁 Test Retweet", "callback_data": "admin_rt_test"}],
        [{"text": "🔗 Set Webhook", "callback_data": "admin_webhook"}, {"text": "📋 Check Logs", "callback_data": "admin_logs"}],
        [{"text": "⚙️ Bot Settings", "callback_data": "lend_page1"}],
        [{"text": "⬅️ Back", "callback_data": "back_home"}]
    ]}

_LOGO_CACHED = None
def get_logo_cached():
    global _LOGO_CACHED
    if _LOGO_CACHED is not None: return _LOGO_CACHED
    base_dir = os.path.dirname(__file__)
    root_dir = os.path.dirname(base_dir)
    candidates = [
        os.path.join(base_dir, "logo.png"),
        os.path.join(root_dir, "logo.png"),
        os.path.join(os.getcwd(), "logo.png"),
        os.path.join(os.getcwd(), "api/logo.png"),
        "logo.png",
        "api/logo.png",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                logo = Image.open(p).convert("RGBA")
                bbox = logo.getbbox()
                if bbox: logo = logo.crop(bbox)
                if logo.width > 300:
                    logo = logo.resize((300, int(300 * logo.height / logo.width)), Image.LANCZOS)
                _LOGO_CACHED = logo
                print(f"Logo found at: {p}")
                return logo
            except Exception as e:
                print(f"logo load error {p}: {e}")
                return None
    print("logo.png NOT FOUND di api/ maupun di root")
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
        w, h = base.size
        target_w = max(60, min(int(w * 0.18), 300))
        logo = logo_orig.resize((target_w, int(target_w * logo_orig.height / logo_orig.width)), Image.LANCZOS)
        margin = max(10, int(w * 0.015))
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        overlay.paste(logo, (margin, margin), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO()
        combined.save(bio, "JPEG", quality=80, optimize=True)
        bio.seek(0)
        return bio
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
        total = user['today_text'] + user['today_media']
        hours = ["TOTAL", "TEXT", "MEDIA", "LIMIT"]
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
        draw.text((20, 12), f"WEEKLY TOTAL - {user['name'][:16]}", fill='white', font=f_title)
        total = user['total_text'] + user['total_media']
        draw.text((20, 150), f"Total All Time: {total} posts", fill='white', font=f_title)
        draw.text((20, 200), f"Text: {user['total_text']} | Media: {user['total_media']}", fill='#A1A1AA', font=f_small)
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
                r = TG.post(f"{BASE_TG}/sendPhoto", data={"chat_id": chat_id, "caption": cap}, files={"photo": ("s.jpg", chart, "image/jpeg")}, timeout=5).json()
                if r.get("ok"):
                    send_message(chat_id, "Please select a mode:", kb); return
            except: pass
        send_message(chat_id, cap, kb)
    except: pass

# V117.6 - Sukses 2x2, X gagal tetap tampil Channel, ada keterangan X Failed buat admin
def send_success(chat_id, user, ch_msg_id, target="channel", x_url=None, x_failed=False):
    try:
        url = f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
        row1 = []
        if ch_msg_id:
            row1.append({"text": "View Channel", "url": url})
        if x_url:
            row1.append({"text": "View X", "url": x_url})
        row2 = []
        if ch_msg_id:
            row2.append({"text": "Delete", "callback_data": f"del_{ch_msg_id}"})
        row2.append({"text": "Back", "callback_data": "back_home"})
        buttons = []
        if row1: buttons.append(row1)
        if row2: buttons.append(row2)
        note = ""
        if x_url:
            note += " + X"
        elif x_failed:
            # X gagal / banned, tapi Channel tetap sukses - jangan bikin user panik, cuma info kecil
            note += " (X Failed, Channel OK)"
        send_message(chat_id, f"Menfess successfully sent!{note}\n{SEP}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5", {"inline_keyboard": buttons})
    except Exception as e: print(f"send_success error: {e}")

def send_user_list(chat_id):
    db = get_db()
    if not db:
        send_message(chat_id, "Database is not connected."); return
    try:
        cur = db.cursor()
        cur.execute("SELECT user_id, name, username, total_text+total_media as total, banned, x_premium_until FROM menfess_users ORDER BY total DESC")
        rows = cur.fetchall(); cur.close()
        back_kb = {"inline_keyboard": [[{"text": "Back", "callback_data": "admin_panel"}]]}
        if not rows:
            send_message(chat_id, M("No users yet."), back_kb); return
        header = M(f"Total Users: {len(rows)}\n------------------------------\nAll Members:")
        txt = header + "\n"
        for i, r in enumerate(rows, 1):
            status = " BANNED" if r[4] else ""
            prem = " 👑" if r[5] else ""
            display = f"<a href=\"tg://user?id={r[0]}\">@{r[2]}</a>" if r[2] else f"<a href=\"tg://user?id={r[0]}\">{r[0]}</a>"
            line = f"{i}. {display} - {r[0]} ({r[3]}){status}{prem}\n"
            if len(txt) + len(line) > 3200:
                send_message(chat_id, txt, back_kb)
                txt = M(f"Continued ({i}/{len(rows)}):") + "\n"
            txt += line
        send_message(chat_id, txt, back_kb)
    except Exception as e:
        send_message(chat_id, f"Failed to retrieve user list: {e}")
    finally: release_db(db)

def handle_admin_command(chat_id, text):
    if text.startswith("/clearmenu"):
        TG.post(f"{BASE_TG}/setChatMenuButton", json={"menu_button": {"type": "default"}}, timeout=3)
        TG.post(f"{BASE_TG}/deleteMyCommands", json={}, timeout=3)
        send_message(chat_id, "Menu button and commands have been cleared."); return True
    if text.startswith("/ban"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1].strip()
            if not target.isdigit():
                send_message(chat_id, M("ID must be numeric. Example: /ban 123456789")); return True
            tu = get_user(target); tu["banned"] = True; save_user_to_db(target, tu); send_message(chat_id, M(f"User {target} has been BANNED."))
        return True
    if text.startswith("/unban"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1].strip()
            if not target.isdigit():
                send_message(chat_id, M("ID must be numeric. Example: /unban 123456789")); return True
            tu = get_user(target); tu["banned"] = False; tu["warn"] = 0; save_user_to_db(target, tu); send_message(chat_id, M(f"User {target} has been UNBANNED."))
        return True
    if text.startswith("/warn"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1].strip()
            if not target.isdigit():
                send_message(chat_id, M("ID must be numeric. Example: /warn 123456789")); return True
            tu = get_user(target); tu["warn"] = tu.get("warn", 0)+1
            if tu["warn"] >= 3: tu["banned"] = True
            save_user_to_db(target, tu); send_message(chat_id, M(f"Warning for {target} = {tu['warn']}/3 {'+ AUTO BANNED' if tu['banned'] else ''}"))
        return True
    if text.startswith("/settag"):
        nt = text.replace("/settag", "").strip()
        if nt: set_setting('hashtag', nt); send_message(chat_id, M(f"Hashtag has been changed to {nt}"))
        return True
    if text.startswith("/setperaturan"):
        nt = text.replace("/setperaturan", "").strip()
        if nt: set_setting('peraturan', nt); send_message(chat_id, M("Rules have been updated."))
        return True
    if text.startswith("/x_test"):
        ok, _x_url = post_to_x(f"Test JogjaLend Bot - X Auto Share ON {datetime.now(WIB).strftime('%H:%M')}")
        send_message(chat_id, M(f"X Test: {'SUCCESSFUL ✅' if ok else 'FAILED ❌ - Please check the X ENV in Vercel / Logs - Channel tetap jalan, X saja yang gagal'}"))
        return True
    if text.startswith("/rt_test"):
        res = auto_retweet_hashtag()
        send_message(chat_id, M(f"Retweet Test: {res}"))
        return True
    if text.startswith("/broadcast"):
        btext = text.replace("/broadcast", "").strip()
        if not btext:
            send_message(chat_id, "Please type: /broadcast [your message]", get_back_keyboard())
            return True
        dedup_key = f"bc_{hashlib.md5(btext.encode()).hexdigest()[:12]}"
        old = get_setting(dedup_key, "")
        if old:
            try:
                old_ts = float(old)
                if time.time() - old_ts < 300:
                    send_message(chat_id, "This broadcast has already been sent within the last 5 minutes. Please wait 5 minutes to prevent duplication.", get_admin_panel())
                    return True
            except: pass
        db = get_db()
        if not db:
            send_message(chat_id, "Database is not connected. Broadcast failed.", get_back_keyboard())
            return True
        try:
            cur = db.cursor(); cur.execute("SELECT user_id FROM menfess_users WHERE banned=FALSE"); rows = cur.fetchall(); cur.close()
        except Exception as e:
            send_message(chat_id, f"Failed to get user list: {e}", get_back_keyboard())
            return True
        finally: release_db(db)
        if len(rows) > 80:
            send_message(chat_id, f"Too many users ({len(rows)}). Maximum is 80 per broadcast to prevent Vercel timeout. Please split the broadcast.", get_admin_panel())
            return True
        set_setting(dedup_key, str(time.time()))
        sukses = 0; gagal = 0
        for r in rows:
            if send_message(r[0], f"📢 BROADCAST\n{SEP}\n{btext}"): sukses += 1
            else: gagal += 1
            time.sleep(0.05)
        send_message(chat_id, f"✅ Broadcast Sent!\n{SEP}\nMessage: {btext[:100]}\n\nSuccessfully sent to: {sukses} members\nFailed: {gagal} members (blocked bot / deleted account)\nTotal: {len(rows)} members", get_admin_panel())
        return True
    if text.startswith("/users"):
        send_user_list(chat_id); return True
    if text.startswith("/setwebhook"):
        host = request.host_url.rstrip('/'); wh = f"{host}/api/index"
        r = TG.get(f"{BASE_TG}/setWebhook", params={"url": wh}, timeout=3).json()
        send_message(chat_id, M(f"Webhook: {wh}\nResult: {r}")); return True
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
@app.route("/api/index.py", methods=["GET", "POST"])
@app.route("/api/webhook", methods=["GET", "POST"])
@app.route("/webhook", methods=["GET", "POST"])
def main_handler():
    data = {}; where = "init"
    try:
        if request.method == "GET": return "JogjaLend Bot V117.6 OK", 200
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
                user["name"] = raw.encode('ascii', 'ignore').decode('ascii') or "User"
                user["username"] = msg["from"].get("username", "")
            if is_admin(chat_id) and text.startswith("/"):
                if handle_admin_command(chat_id, text):
                    return "ok", 200
            if user.get("banned") and not is_admin(chat_id):
                send_message(chat_id, f"You are BANNED.\n{SEP}\nWarnings: {user.get('warn',0)}/3\nPlease contact the administrator.", get_back_keyboard())
                return "ok", 200
            if text.startswith("/start"):
                save_user_to_db(uid, user)
                send_message(chat_id, get_welcome_text(user), get_main_keyboard(is_admin(chat_id)))
            elif text.startswith("/newpost"): send_message(chat_id, f"Post Menfess\n{SEP}\nPlease type your text directly, or send media with a caption.\nHashtag will be added automatically: {HASHTAG}", get_back_keyboard())
            elif text.startswith("/profile"): send_message(chat_id, f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5\nX Premium: {'ACTIVE until '+user.get('x_premium_until','') if is_premium_active(user) else 'Not active'}", get_back_keyboard())
            elif text.lower().startswith("/stats"): send_stats(chat_id, user, "today")
            elif text.startswith("/") and text.split()[0] not in ["/start", "/newpost", "/profile", "/stats"] and not is_admin(chat_id):
                send_message(chat_id, f"Unknown command: {text}\n{SEP}\nPlease type /start to open the menu.", get_back_keyboard())
            elif not user["banned"]:
                if user.get("waiting_proof") and ("photo" in msg or "video" in msg):
                    user["waiting_proof"] = False
                    save_user_to_db(uid, user)
                    fid = msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video", {}).get("file_id")
                    send_message(chat_id, f"Receipt Received! ✅\n{SEP}\nYour payment is currently being verified by the admin. You will receive a notification once it has been approved.", get_back_keyboard())
                    for adm in ADMIN_ID.split(","):
                        adm = adm.strip()
                        if not adm: continue
                        try:
                            TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": adm, "photo": fid, "caption": f"💰 X PREMIUM PAYMENT\nUser: {user['name']} (@{user['username']})\nID: {uid}\nPrice: {X_PRICE}"}, timeout=5)
                            send_message(adm, "Would you like to approve this user?", {"inline_keyboard": [[{"text": "✅ Approve for 30 Days", "callback_data": f"x_approve_{uid}"}, {"text": "❌ Reject", "callback_data": f"x_reject_{uid}"}]]})
                        except: pass
                    return "ok", 200
                if text and not text.startswith("/") and len(text) >= 3:
                    if user["today_text"] >= 5: send_message(chat_id, f"Limit Reached 5/5\n{SEP}\nQuota will reset at 00:00 WIB", get_back_keyboard())
                    else:
                        clean = text.strip()
                        if HASHTAG.lower() not in clean.lower(): clean = f"{clean} {HASHTAG}"
                        if get_setting('approval', 'off') == 'on' and not is_admin(chat_id):
                            pid = secrets.token_hex(8)
                            pkey = f"pending_{pid}"
                            set_setting(pkey, json.dumps({"type": "text", "owner": uid, "text": clean, "name": user['name'], "username": user['username']}, ensure_ascii=False))
                            kb_appr = {"inline_keyboard": [[{"text": "✅ Approve", "callback_data": f"appr_{pid}"}, {"text": "❌ Reject", "callback_data": f"rej_{pid}"}]]}
                            send_message(LOG_CHANNEL, f"📥 PENDING MENFESS\nFrom: {user['name']} (@{user['username']})\nKey: {pid}\n{SEP}\n{clean}", kb_appr)
                            send_message(chat_id, f"Your menfess has been submitted for administrator approval.\n{SEP}\nPlease wait for confirmation.", get_back_keyboard())
                            return "ok", 200
                        # V117.6 - URUTAN WAJIB: 1. Channel dulu, 2. X terakhir + fail-safe
                        ch_id = None
                        x_url = None
                        x_failed = False
                        should_post_x = (is_admin(chat_id) or (is_premium_active(user) and user.get("x_auto", True)))
                        # 1. CHANNEL - TIDAK PERNAH DIBATALKAN OLEH X
                        try:
                            r = TG.post(f"{BASE_TG}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=3).json()
                            ch_id = r.get("result", {}).get("message_id")
                            save_post_owner(ch_id, uid)
                        except Exception as e:
                            print(f"Channel text failed: {e}")
                        # 2. X - KALAU GAGAL / BANNED, CUMA TANDAI, JANGAN GAGALKAN CHANNEL
                        if should_post_x:
                            _ok_x, x_url = safe_post_to_x(clean)
                            if not _ok_x and get_setting('x_auto_share', 'off') == 'on':
                                x_failed = True
                        user["today_text"] += 1; user["total_text"] += 1; user["total_chars"] = user.get("total_chars", 0)+len(text)
                        save_user_to_db(uid, user); send_success(chat_id, user, ch_id, "channel", x_url, x_failed)
                if "photo" in msg or "video" in msg:
                    if caption and any(w in caption.lower() for w in ["bukti", "transfer", "tf ", "qris", "struk", "receipt"]):
                        send_message(chat_id, "This appears to be a payment receipt, not a menfess. Payment receipts will not be published to the channel. Please submit your receipt through the X Premium menu.", get_back_keyboard())
                        return "ok", 200
                    if user["today_media"] >= 5: send_message(chat_id, "Limit Reached 5/5", get_back_keyboard())
                    else:
                        fid = msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video", {}).get("file_id")
                        is_photo = "photo" in msg
                        base_cap = caption.strip() if caption else HASHTAG
                        if HASHTAG.lower() not in base_cap.lower(): base_cap = f"{base_cap} {HASHTAG}"
                        if get_setting('approval', 'off') == 'on' and not is_admin(chat_id):
                            pid = secrets.token_hex(8)
                            pkey = f"pending_{pid}"
                            set_setting(pkey, json.dumps({"type": "video" if not is_photo else "photo", "owner": uid, "file_id": fid, "caption": base_cap, "name": user['name'], "username": user['username']}, ensure_ascii=False))
                            kb_appr = {"inline_keyboard": [[{"text": "✅ Approve", "callback_data": f"appr_{pid}"}, {"text": "❌ Reject", "callback_data": f"rej_{pid}"}]]}
                            try:
                                if is_photo: TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": LOG_CHANNEL, "photo": fid, "caption": f"📥 PENDING MENFESS\nFrom: {user['name']} (@{user['username']})\nKey: {pid}\n{SEP}\n{base_cap}"}, timeout=5)
                                else: TG.post(f"{BASE_TG}/sendVideo", json={"chat_id": LOG_CHANNEL, "video": fid, "caption": f"📥 PENDING MENFESS\nFrom: {user['name']} (@{user['username']})\nKey: {pid}\n{SEP}\n{base_cap}"}, timeout=5)
                            except: pass
                            send_message(LOG_CHANNEL, f"📥 PENDING MENFESS - Key: {pid}\nFrom: {user['name']} (@{user['username']})", kb_appr)
                            send_message(chat_id, "Your media has been submitted for administrator approval.\nPlease wait for confirmation.", get_back_keyboard())
                            return "ok", 200
                        # V117.6 - URUTAN WAJIB MEDIA: 1. Channel dulu, 2. X terakhir + fail-safe
                        ch_id = None
                        wm_bytes = None
                        x_url = None
                        x_failed = False
                        raw = None
                        should_post_x = (is_admin(chat_id) or (is_premium_active(user) and user.get("x_auto", True)))
                        if is_photo:
                            raw = download_file(fid)
                            wm = add_watermark(raw) if raw else None
                            if wm:
                                wm.seek(0); wm_bytes = wm.read(); wm.seek(0)
                                print("Logo berhasil nempel")
                            else:
                                print("Logo gagal nempel, pakai foto asli, tetap share ke X")
                                wm_bytes = raw
                        # 1. CHANNEL
                        try:
                            if is_photo:
                                if wm_bytes:
                                    r = TG.post(f"{BASE_TG}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": ("wm.jpg", io.BytesIO(wm_bytes), "image/jpeg")}, timeout=5).json(); ch_id = r.get("result", {}).get("message_id")
                                else:
                                    r = TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=3).json(); ch_id = r.get("result", {}).get("message_id")
                            else:
                                r = TG.post(f"{BASE_TG}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id = r.get("result", {}).get("message_id")
                            save_post_owner(ch_id, uid)
                        except Exception as e:
                            print(f"Channel media failed: {e}")
                        # 2. X - FAIL-SAFE
                        if should_post_x:
                            if is_photo:
                                _ok_x, x_url = safe_post_to_x(base_cap, wm_bytes, is_video=False)
                            else:
                                try:
                                    video_bytes = download_file(fid)
                                    if video_bytes:
                                        _ok_x, x_url = safe_post_to_x(base_cap, video_bytes, is_video=True)
                                    else:
                                        _ok_x, x_url = safe_post_to_x(base_cap)
                                except Exception as e:
                                    print(f"X video fail-safe: {e}")
                                    _ok_x, x_url = False, None
                            if not _ok_x and get_setting('x_auto_share', 'off') == 'on':
                                x_failed = True
                        user["today_media"] += 1; user["total_media"] += 1
                        save_user_to_db(uid, user); send_success(chat_id, user, ch_id, "channel", x_url, x_failed)
        if "callback_query" in data:
            cq = data["callback_query"]; chat_id = cq["message"]["chat"]["id"]; uid = str(chat_id); cdata = cq["data"]; msg_id = cq["message"]["message_id"]
            where = f"callback {cdata}"
            try: TG.post(f"{BASE_TG}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
            except: pass
            user = get_user(uid)
            HASHTAG = get_setting('hashtag', '#jogjalend')
            if user.get("banned") and not is_admin(chat_id):
                edit_message_fast(chat_id, msg_id, "You are BANNED.", get_back_keyboard())
                return "ok", 200
            if cdata in ["stats", "stats_today", "stats_weekly"]:
                try: TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=2)
                except: pass
                mode = "weekly" if cdata == "stats_weekly" else "today"
                send_stats(chat_id, user, mode)
            elif cdata == "back_home": edit_message_fast(chat_id, msg_id, get_welcome_text(user), get_main_keyboard(is_admin(chat_id)))
            elif cdata == "close":
                try: TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=2)
                except: pass
            elif cdata == "admin_noop": pass
            elif cdata == "lend_page1": edit_message_fast(chat_id, msg_id, M("Please select one of the settings you would like to change."), get_menu_1())
            elif cdata == "lend_page2": edit_message_fast(chat_id, msg_id, M("Please select one of the settings you would like to change."), get_menu_2())
            elif cdata == "my_profile": edit_message_fast(chat_id, msg_id, f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5\nHashtag: {HASHTAG}\nX Premium: {'ACTIVE until '+user.get('x_premium_until','') if is_premium_active(user) else 'Not active'}", get_back_keyboard())
            elif cdata == "post": edit_message_fast(chat_id, msg_id, f"Post Menfess\n{SEP}\nPlease type your text directly, or send media with a caption.\nHashtag will be added automatically: {HASHTAG}", get_back_keyboard())
            elif cdata == "info_bot":
                edit_message_fast(chat_id, msg_id, "Bot Information\n\nJogjaLend Bot is a bot developed by the @jogja_lend team.\n<pre>Bot Version : V117.6\nDatabase  : PostgreSQL</pre>\nFor questions regarding bot usage, feature suggestions, or bug reports, please contact @joglendsupportBot", get_back_keyboard())
            elif cdata == "x_premium":
                if is_premium_active(user):
                    auto = "ON" if user.get("x_auto", True) else "OFF"
                    edit_message_fast(chat_id, msg_id, f"🎉 X Premium ACTIVE ✅\n{SEP}\nValid Until: {user.get('x_premium_until','')}\nAutomatic Posting Status: {auto}\nYour menfess will be automatically posted to X when enabled.", get_x_premium_keyboard(user))
                else:
                    send_qris(chat_id)
                    edit_message_fast(chat_id, msg_id, f"𝕏 X Premium 🔒\n{SEP}\nEnable automatic posting of your menfess to X.\n\nPrice: {X_PRICE}\n{QRIS_TEXT}\n\nInstructions:\n1. Please transfer the exact amount.\n2. Tap 'I Have Transferred'.\n3. Send a photo of your transfer receipt here.\n4. Please wait for admin approval.", get_x_premium_keyboard(user))
            elif cdata == "x_pay_proof":
                user["waiting_proof"] = True; save_user_to_db(uid, user)
                edit_message_fast(chat_id, msg_id, f"Submit Transfer Receipt\n{SEP}\nPlease send a PHOTO of your QRIS transfer receipt here.\nPlease do not send a menfess yet, send only the receipt photo.", get_back_keyboard())
            elif cdata == "x_toggle_auto":
                if is_premium_active(user):
                    user["x_auto"] = not user.get("x_auto", True); save_user_to_db(uid, user)
                    auto = "ON" if user.get("x_auto", True) else "OFF"
                    edit_message_fast(chat_id, msg_id, f"🎉 X Premium ACTIVE ✅\n{SEP}\nValid Until: {user.get('x_premium_until','')}\nAutomatic Posting Status: {auto}", get_x_premium_keyboard(user))
            elif cdata.startswith("x_approve_"):
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    target_id = cdata.replace("x_approve_", "")
                    tu = get_user(target_id)
                    until = (datetime.now(WIB) + timedelta(days=PREMIUM_DAYS)).strftime("%Y-%m-%d")
                    tu["x_premium_until"] = until; tu["x_auto"] = True; save_user_to_db(target_id, tu)
                    edit_message_fast(chat_id, msg_id, f"✅ Approved! User {target_id} is now active until {until}", get_admin_panel())
                    send_message(target_id, f"🎉 X Premium ACTIVATED!\n{SEP}\nValid Until: {until}\nYour menfess will now be automatically posted to X. You may enable or disable this feature in the X Premium menu.", get_back_keyboard())
            elif cdata.startswith("x_reject_"):
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    target_id = cdata.replace("x_reject_", "")
                    edit_message_fast(chat_id, msg_id, f"❌ Rejected. User {target_id}", get_admin_panel())
                    send_message(target_id, f"❌ Your X Premium payment was rejected.\n{SEP}\nPlease contact the admin if you believe you have completed the transfer.", get_back_keyboard())
            elif cdata.startswith("appr_") or cdata.startswith("rej_"):
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    pid = cdata.split("_", 1)[1]
                    pkey = f"pending_{pid}"
                    raw_pending = get_setting(pkey, "")
                    if not raw_pending:
                        edit_message_fast(chat_id, msg_id, "This pending item has already been processed or has expired.", get_admin_panel())
                    else:
                        try: pend = json.loads(raw_pending)
                        except: pend = {"type": "text", "text": raw_pending, "owner": ""}
                        delete_setting(pkey)
                        owner_id = pend.get("owner", "")
                        if cdata.startswith("appr_"):
                            x_url_appr = None
                            if pend.get("type") == "text":
                                txt = pend.get("text", "")
                                # V117.6 - Approval juga: Channel dulu, X fail-safe
                                try:
                                    rr = TG.post(f"{BASE_TG}/sendMessage", json={"chat_id": CHANNEL_ID, "text": txt, "parse_mode": "HTML"}, timeout=3).json()
                                    ch_mid = rr.get("result", {}).get("message_id")
                                    save_post_owner(ch_mid, owner_id)
                                except Exception as e:
                                    print(f"Approval channel failed: {e}")
                                    ch_mid = None
                                _ok_appr, x_url_appr = safe_post_to_x(txt)
                                try:
                                    ou = get_user(str(owner_id)); ou["today_text"] += 1; ou["total_text"] += 1; save_user_to_db(str(owner_id), ou)
                                except: pass
                                if owner_id:
                                    row1_appr = []
                                    if ch_mid: row1_appr.append({"text": "View Channel", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_mid}"})
                                    if x_url_appr: row1_appr.append({"text": "View X", "url": x_url_appr})
                                    kb_owner = {"inline_keyboard": [row1_appr, [{"text": "Back", "callback_data": "back_home"}]]} if row1_appr else {"inline_keyboard": [[{"text": "Back", "callback_data": "back_home"}]]}
                                    send_message(owner_id, f"Your menfess has been approved and published.\n{SEP}\n{txt[:100]}", kb_owner)
                            else:
                                fid2 = pend.get("file_id", ""); cap2 = pend.get("caption", "")
                                media_for_x = None
                                ch_mid = None
                                try:
                                    if pend.get("type") == "photo":
                                        raw2 = download_file(fid2)
                                        wm2 = add_watermark(raw2) if raw2 else None
                                        if wm2:
                                            wm2.seek(0); media_for_x = wm2.read()
                                            rr = TG.post(f"{BASE_TG}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": cap2, "parse_mode": "HTML"}, files={"photo": ("wm.jpg", io.BytesIO(media_for_x), "image/jpeg")}, timeout=5).json()
                                        else:
                                            media_for_x = raw2
                                            rr = TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid2, "caption": cap2, "parse_mode": "HTML"}, timeout=5).json()
                                    else:
                                        rr = TG.post(f"{BASE_TG}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid2, "caption": cap2, "parse_mode": "HTML"}, timeout=5).json()
                                    ch_mid = rr.get("result", {}).get("message_id")
                                    save_post_owner(ch_mid, owner_id)
                                except Exception as e:
                                    print(f"Approval channel media failed: {e}")
                                # X fail-safe
                                try:
                                    if pend.get("type") == "photo":
                                        _ok_appr, x_url_appr = safe_post_to_x(cap2, media_for_x, is_video=False)
                                    else:
                                        vbytes = download_file(fid2)
                                        if vbytes:
                                            _ok_appr, x_url_appr = safe_post_to_x(cap2, vbytes, is_video=True)
                                        else:
                                            _ok_appr, x_url_appr = safe_post_to_x(cap2)
                                except Exception as e:
                                    print(f"Approval X fail-safe: {e}")
                                    x_url_appr = None
                                try:
                                    ou = get_user(str(owner_id)); ou["today_media"] += 1; ou["total_media"] += 1; save_user_to_db(str(owner_id), ou)
                                except: pass
                                if owner_id:
                                    row1_appr = []
                                    if ch_mid: row1_appr.append({"text": "View Channel", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_mid}"})
                                    if x_url_appr: row1_appr.append({"text": "View X", "url": x_url_appr})
                                    kb_owner = {"inline_keyboard": [row1_appr, [{"text": "Back", "callback_data": "back_home"}]]} if row1_appr else {"inline_keyboard": [[{"text": "Back", "callback_data": "back_home"}]]}
                                    send_message(owner_id, "Your media has been approved and published.", kb_owner)
                            edit_message_fast(chat_id, msg_id, "Approved and published to the channel.", get_admin_panel())
                        else:
                            edit_message_fast(chat_id, msg_id, "Rejected.", get_admin_panel())
                            if owner_id: send_message(owner_id, "Your menfess was rejected by the administrator.", get_back_keyboard())
            elif cdata == "admin_panel":
                if is_admin(chat_id): edit_message_fast(chat_id, msg_id, M("ADMIN PANEL V117.6\n------------------------------\nPlease select an admin menu:"), get_admin_panel())
                else: edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
            elif cdata == "admin_users":
                send_user_list(chat_id)
            elif cdata == "admin_allstats":
                db = get_db()
                if db:
                    try:
                        cur = db.cursor(); cur.execute("SELECT COUNT(*), COALESCE(SUM(total_text),0), COALESCE(SUM(total_media),0) FROM menfess_users"); r = cur.fetchone(); cur.close()
                        edit_message_fast(chat_id, msg_id, f"All Stats\n{SEP}\nTotal Users: {r[0]}\nTotal Text: {r[1]}\nTotal Media: {r[2]}", get_admin_panel())
                    except: edit_message_fast(chat_id, msg_id, "Failed to load stats.", get_admin_panel())
                    finally: release_db(db)
                else: edit_message_fast(chat_id, msg_id, "Database is not connected.", get_admin_panel())
            elif cdata == "admin_broadcast":
                edit_message_fast(chat_id, msg_id, "Broadcast\n------------------------------\nType: /broadcast [your message]", get_admin_panel())
            elif cdata == "admin_webhook":
                host = request.host_url.rstrip('/'); wh = f"{host}/api/index"
                r = TG.get(f"{BASE_TG}/setWebhook", params={"url": wh}, timeout=3).json()
                edit_message_fast(chat_id, msg_id, f"Webhook: {wh}\nResult: {r}", get_admin_panel())
            elif cdata == "admin_logs":
                edit_message_fast(chat_id, msg_id, f"Check Logs\n------------------------------\nLog Channel: {LOG_CHANNEL}\nPlease check Vercel Logs for errors.", get_admin_panel())
            elif cdata == "admin_x_toggle":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    cur = get_setting('x_auto_share', 'off')
                    new = 'on' if cur == 'off' else 'off'
                    set_setting('x_auto_share', new)
                    edit_message_fast(chat_id, msg_id, M(f"X Auto Share: {new.upper()}\n------------------------------\n{'Posts from admin and Premium users will now be automatically shared to X.' if new=='on' else 'Automatic sharing to X has been disabled.'}"), get_admin_panel())
            elif cdata == "admin_rt_toggle":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    cur = get_setting('x_retweet', 'on')
                    new = 'on' if cur == 'off' else 'off'
                    set_setting('x_retweet', new)
                    edit_message_fast(chat_id, msg_id, M(f"Auto Retweet {RETWEET_HASHTAG}: {new.upper()}"), get_admin_panel())
            elif cdata == "admin_x_test":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    ok, _x_url_test = post_to_x(f"Test JogjaLend Bot X Auto Share {datetime.now(WIB).strftime('%H:%M')}")
                    edit_message_fast(chat_id, msg_id, M(f"X Test: {'SUCCESSFUL ✅ - Please check your X account' if ok else 'FAILED ❌ - Please check the X ENV / Basic Plan / Vercel Logs - Channel tetap jalan'}"), get_admin_panel())
            elif cdata == "admin_rt_test":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    res = auto_retweet_hashtag()
                    edit_message_fast(chat_id, msg_id, M(f"Retweet Test: {res}"), get_admin_panel())
            elif cdata == "lend_tag":
                edit_message_fast(chat_id, msg_id, M(f"Current Tag: {HASHTAG}\n------------------------------\nTo change it, use the command:\n/settag #newtag"), get_menu_1())
            elif cdata == "lend_persetujuan":
                cur = get_setting('approval', 'off')
                kb = {"inline_keyboard": [[{"text": f"Mode: {cur.upper()} - Tap to change", "callback_data": "toggle_approval"}], [{"text": "Back", "callback_data": "lend_page1"}]]}
                edit_message_fast(chat_id, msg_id, M(f"Approval Mode\n------------------------------\nIf ON, menfess will not be posted immediately. It will be sent to the LOG_CHANNEL for approval first.\nStatus: {cur}"), kb)
            elif cdata == "toggle_approval":
                cur = get_setting('approval', 'off'); new = 'on' if cur == 'off' else 'off'; set_setting('approval', new)
                kb = {"inline_keyboard": [[{"text": f"Mode: {new.upper()} - Tap to change", "callback_data": "toggle_approval"}], [{"text": "Back", "callback_data": "lend_page1"}]]}
                edit_message_fast(chat_id, msg_id, M(f"Approval Mode has been changed to {new.upper()}"), kb)
            elif cdata == "lend_hapus": edit_message_fast(chat_id, msg_id, M("Delete Message\n------------------------------\nUsers may delete their own posts using the Delete button after posting."), get_menu_1())
            elif cdata == "lend_lang": edit_message_fast(chat_id, msg_id, M("Language\n------------------------------\nCurrent bot language: English (Formal)."), get_menu_1())
            elif cdata == "lend_peraturan":
                per = get_setting('peraturan', '-')
                edit_message_fast(chat_id, msg_id, M(f"Rules\n------------------------------\n{per}\n\nTo change: /setperaturan [text]"), get_menu_2())
            elif cdata == "lend_peringatan": edit_message_fast(chat_id, msg_id, M(f"Warnings\n------------------------------\n/warn [user_id] - Add a warning (3 warnings = auto ban)\nYour current warnings: {user.get('warn',0)}/3"), get_menu_2())
            elif cdata == "lend_blacklist":
                db = get_db()
                txt = "Blacklist\n------------------------------\n"
                if db:
                    cur = db.cursor(); cur.execute("SELECT user_id, name, warn FROM menfess_users WHERE banned=true LIMIT 20"); rows = cur.fetchall(); cur.close(); release_db(db)
                    if not rows: txt += "There are no banned users."
                    else:
                        for r in rows: txt += f"{r[1]} - {r[0]} warn:{r[2]}\n"
                    kb = {"inline_keyboard": [[{"text": "Unban: /unban [id]", "callback_data": "admin_noop"}], [{"text": "Back", "callback_data": "lend_page2"}]]}
                else: kb = get_menu_2()
                edit_message_fast(chat_id, msg_id, M(txt), kb)
            elif cdata == "lend_izin": edit_message_fast(chat_id, msg_id, M("Permissions\n------------------------------\nAll users may post text/media (maximum 5). Admins may ban or warn users."), get_menu_2())
            elif cdata == "lend_log": edit_message_fast(chat_id, msg_id, M(f"Channel Log\n------------------------------\nLog Channel: {LOG_CHANNEL}\nErrors and approvals will be sent here."), get_menu_2())
            elif cdata.startswith("del_"):
                try:
                    mid = int(cdata.replace("del_", ""))
                    db = get_db()
                    owner = None
                    if db:
                        cur = db.cursor(); cur.execute("SELECT owner_id FROM menfess_posts WHERE msg_id=%s", (str(mid),)); rr = cur.fetchone(); cur.close(); release_db(db)
                        if rr: owner = rr[0]
                    if owner and str(owner) != uid and not is_admin(chat_id):
                        edit_message_fast(chat_id, msg_id, "You can only delete your own post.", get_back_keyboard())
                    else:
                        TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": mid}, timeout=2)
                        edit_message_fast(chat_id, msg_id, "Post deleted.", get_back_keyboard())
                except Exception as e:
                    edit_message_fast(chat_id, msg_id, f"Failed to delete: {e}", get_back_keyboard())
    except Exception as e:
        print(f"ERROR {where}: {e}\n{traceback.format_exc()}")
        try:
            if "message" in data:
                send_message(data["message"]["chat"]["id"], "An error occurred. Please try again.", get_back_keyboard())
        except: pass
    return "ok", 200

@app.route("/<path:path>", methods=["GET", "POST"])
def catch_all(path):
    if request.method == "POST":
        try:
            data = request.get_json(force=True, silent=True) or {}
            if "update_id" in data or "message" in data or "callback_query" in data:
                return main_handler()
        except:
            pass
        return main_handler()
    return "JogjaLend Bot V117.6 OK", 200

if __name__ == "__main__":
    app.run()