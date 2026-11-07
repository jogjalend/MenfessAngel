# V117.7 Full Code Fix - JogjaLend Menfess Bot + Fitur Baru X
# Fix: Vercel Routing, 404 /, 404 /api/index, ModuleNotFound, Duplicate __main__

import os, time, requests, textwrap
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

try:
    from requests_oauthlib import OAuth1Session
except Exception:
    OAuth1Session = None

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or 0)
X_USERNAME = "jogja_lend"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ================= DB - LAZY INIT AGAR TIDAK CRASH SAAT COLD START =================
_DB_INITIALIZED = False

def db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    con = db(); cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY, username TEXT DEFAULT '',
        is_banned BOOLEAN DEFAULT FALSE, is_premium BOOLEAN DEFAULT FALSE,
        premium_until BIGINT DEFAULT 0,
        media_count INT DEFAULT 0, text_count INT DEFAULT 0, last_reset BIGINT DEFAULT 0)""")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS processed_updates (update_id BIGINT PRIMARY KEY, created_at BIGINT)")
    cur.execute("""CREATE TABLE IF NOT EXISTS menfess_log (
        id SERIAL PRIMARY KEY, user_id BIGINT, username TEXT, type TEXT,
        channel_msg_id BIGINT, x_url TEXT, x_id TEXT, x_status TEXT DEFAULT 'pending', created_at BIGINT)""")
    cur.execute("CREATE TABLE IF NOT EXISTS retweeted (tweet_id TEXT PRIMARY KEY, created_at BIGINT)")
    con.commit(); con.close()

def ensure_db():
    global _DB_INITIALIZED
    if not _DB_INITIALIZED and DATABASE_URL:
        try:
            init_db()
            _DB_INITIALIZED = True
        except Exception as e:
            print("INIT DB ERROR:", e)

def get_setting(k, d="on"):
    try:
        con = db(); cur = con.cursor()
        cur.execute("SELECT value FROM settings WHERE key=%s", (k,))
        r = cur.fetchone(); con.close()
        return r["value"] if r else d
    except: return d

def set_setting(k, v):
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value", (k, str(v)))
    con.commit(); con.close()

# ================= TELEGRAM =================
def tg(method, payload):
    try:
        return requests.post(f"{TG}/{method}", json=payload, timeout=25).json()
    except Exception as e:
        print("TG ERROR:", e); return {}

def send_msg(chat_id, text, reply_markup=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: p["reply_markup"] = reply_markup
    return tg("sendMessage", p)

def send_photo(chat_id, photo, caption, reply_markup=None):
    p = {"chat_id": chat_id, "photo": photo, "caption": caption, "parse_mode": "HTML"}
    if reply_markup: p["reply_markup"] = reply_markup
    return tg("sendPhoto", p)

def edit_msg(chat_id, msg_id, text, reply_markup=None):
    p = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: p["reply_markup"] = reply_markup
    return tg("editMessageText", p)

def answer_cq(cq_id, text=""):
    return tg("answerCallbackQuery", {"callback_query_id": cq_id, "text": text})

# ================= X =================
def x_oauth():
    if OAuth1Session is None:
        raise Exception("requests_oauthlib not installed")
    return OAuth1Session(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)

def x_upload_media(oauth, media_url):
    if not media_url: return None
    f = requests.get(media_url, timeout=30).content
    up = oauth.post("https://upload.twitter.com/1.1/media/upload.json", files={"media": f}, timeout=60)
    return up.json().get("media_id_string")

def x_post_single(oauth, text, media_id=None, reply_to=None):
    payload = {"text": text}
    if media_id: payload["media"] = {"media_ids": [media_id]}
    if reply_to: payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    r = oauth.post("https://api.twitter.com/2/tweets", json=payload, timeout=30)
    data = r.json()
    if "data" in data:
        return data["data"]["id"]
    print("X POST ERROR:", data)
    return None

def post_to_x_thread(text, media_url=None, reply_to=None):
    try:
        oauth = x_oauth()
        media_id = x_upload_media(oauth, media_url) if media_url else None
        chunks = textwrap.wrap(text, width=270, break_long_words=False, break_on_hyphens=False) or [text]
        first_id = None
        last_id = reply_to
        for i, chunk in enumerate(chunks):
            suffix = f" ({i+1}/{len(chunks)})" if len(chunks) > 1 else ""
            mid = media_id if i == 0 else None
            tid = x_post_single(oauth, chunk + suffix, mid, last_id)
            if not tid: return False, None, None
            if i == 0: first_id = tid
            last_id = tid
        url = f"https://x.com/{X_USERNAME}/status/{first_id}"
        return True, url, first_id
    except Exception as e:
        print("X THREAD ERROR:", e)
        return False, None, None

def delete_from_x(x_url=None, x_id=None):
    try:
        tid = x_id
        if not tid and x_url and "/status/" in x_url:
            tid = x_url.split("/status/")[-1].split("?")[0].strip()
        if not tid: return
        oauth = x_oauth()
        oauth.delete(f"https://api.twitter.com/2/tweets/{tid}", timeout=20)
    except Exception as e:
        print("DELETE X ERROR:", e)

def check_x_status():
    try:
        oauth = x_oauth()
        r = oauth.get("https://api.twitter.com/2/users/me", timeout=20)
        if r.status_code == 200:
            d = r.json().get("data", {})
            return True, f"X Terhubung ✅\n@{d.get('username','-')} | ID: {d.get('id','-')}"
        return False, f"X Error ❌\nStatus: {r.status_code}\n{r.text[:200]}"
    except Exception as e:
        return False, f"X Error ❌\n{e}"

def auto_retweet_hashtag():
    try:
        oauth = x_oauth()
        me = oauth.get("https://api.twitter.com/2/users/me", timeout=20).json()
        my_id = me.get("data", {}).get("id")
        if not my_id: return "Retweet gagal: tidak dapat ambil my_id"
        r = oauth.get("https://api.twitter.com/2/tweets/search/recent", params={"query": "#jogjalend -from:jogja_lend", "max_results": 10}, timeout=30)
        tweets = r.json().get("data", [])
        if not tweets: return "No new tweet"
        con = db(); cur = con.cursor()
        count = 0
        for t in tweets:
            tid = t["id"]
            cur.execute("SELECT 1 FROM retweeted WHERE tweet_id=%s", (tid,))
            if cur.fetchone(): continue
            rr = oauth.post(f"https://api.twitter.com/2/users/{my_id}/retweets", json={"tweet_id": tid}, timeout=20)
            if rr.status_code in (200, 201):
                cur.execute("INSERT INTO retweeted(tweet_id, created_at) VALUES(%s,%s)", (tid, int(time.time())))
                count += 1
        con.commit(); con.close()
        return f"Retweeted {count} tweet(s)"
    except Exception as e:
        print("RETWEET ERROR:", e)
        return f"Retweet error: {e}"

def x_stats():
    con = db(); cur = con.cursor()
    cur.execute("SELECT COUNT(*) as c FROM menfess_log WHERE x_status='success'"); ok = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM menfess_log WHERE x_status='failed'"); fail = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM retweeted"); rt = cur.fetchone()["c"]
    con.close()
    return ok, fail, rt

# ================= USER =================
def get_or_create_user(user_id, username):
    con = db(); cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    u = cur.fetchone()
    if not u:
        cur.execute("INSERT INTO users(user_id, username) VALUES(%s,%s)", (user_id, username or ""))
        con.commit()
        cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        u = cur.fetchone()
    else:
        if username and u["username"] != username:
            cur.execute("UPDATE users SET username=%s WHERE user_id=%s", (username, user_id))
            con.commit()
    con.close(); return u

def reset_quota_if_needed(user):
    now_wib = int(time.time()) + 7*3600
    today = now_wib // 86400
    if (user["last_reset"] or 0) != today:
        con = db(); cur = con.cursor()
        cur.execute("UPDATE users SET media_count=0, text_count=0, last_reset=%s WHERE user_id=%s", (today, user["user_id"]))
        con.commit(); con.close()
        user["media_count"] = 0; user["text_count"] = 0
    return user

# ================= ADMIN PANEL =================
def admin_keyboard():
    x_post = get_setting("x_post", "on")
    x_rt = get_setting("x_retweet", "on")
    return {"inline_keyboard": [
        [{"text": "𝕏 X Menu", "callback_data": "admin_xmenu"}],
        [{"text": f"X Post: {'ON ✅' if x_post=='on' else 'OFF ❌'}", "callback_data": "admin_toggle_xpost"}],
        [{"text": f"Retweet: {'ON ✅' if x_rt=='on' else 'OFF ❌'}", "callback_data": "admin_toggle_rt"}],
        [{"text": "📊 Statistik", "callback_data": "admin_stats"}],
        [{"text": "👥 Daftar User", "callback_data": "admin_users"}],
        [{"text": "⭐ Premium", "callback_data": "admin_premium"}],
        [{"text": "🚫 Banned", "callback_data": "admin_banned"}],
        [{"text": "📈 Activity Monitor", "callback_data": "admin_activity"}],
        [{"text": "⬅️ Back", "callback_data": "back_main"}],
    ]}

def admin_text():
    return f"<b>ADMIN PANEL - JogjaLend</b>\n━━━━━━━━━━━━━━\nX Post: {get_setting('x_post','on')}\nRetweet: {get_setting('x_retweet','on')}\n\nPilih menu di bawah:"

def x_menu_keyboard():
    return {"inline_keyboard": [
        [{"text": "🔍 Check X Status", "callback_data": "admin_xcheck"}],
        [{"text": "📊 X Stats", "callback_data": "admin_xstats"}],
        [{"text": "🔁 Retweet Sekarang", "callback_data": "admin_xretweet_now"}],
        [{"text": "⬅️ Kembali ke Admin", "callback_data": "admin_panel"}],
    ]}

def handle_admin_callback(cq, data, chat_id, msg_id):
    if cq["from"]["id"] != ADMIN_ID:
        answer_cq(cq["id"], "Bukan admin!"); return
    if data == "admin_panel":
        edit_msg(chat_id, msg_id, admin_text(), admin_keyboard()); answer_cq(cq["id"])
    elif data == "admin_toggle_xpost":
        cur = "off" if get_setting("x_post", "on") == "on" else "on"
        set_setting("x_post", cur)
        edit_msg(chat_id, msg_id, admin_text(), admin_keyboard()); answer_cq(cq["id"], f"X Post {cur}")
    elif data == "admin_toggle_rt":
        cur = "off" if get_setting("x_retweet", "on") == "on" else "on"
        set_setting("x_retweet", cur)
        edit_msg(chat_id, msg_id, admin_text(), admin_keyboard()); answer_cq(cq["id"], f"Retweet {cur}")
    elif data == "admin_xmenu":
        edit_msg(chat_id, msg_id, "<b>𝕏 X MENU</b>\n━━━━━━━━━━━━━━\nKelola seluruh fitur X dari sini.", x_menu_keyboard()); answer_cq(cq["id"])
    elif data == "admin_xcheck":
        ok, msgx = check_x_status()
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke X Menu", "callback_data": "admin_xmenu"}]]}
        edit_msg(chat_id, msg_id, f"<b>X STATUS</b>\n━━━━━━━━━━━━━━\n{msgx}", kb); answer_cq(cq["id"])
    elif data == "admin_xstats":
        ok, fail, rt = x_stats()
        txt = f"<b>𝕏 X STATS</b>\n━━━━━━━━━━━━━━\nBerhasil ke X: {ok}\nGagal ke X: {fail}\nTotal Retweet: {rt}\n"
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke X Menu", "callback_data": "admin_xmenu"}]]}
        edit_msg(chat_id, msg_id, txt, kb); answer_cq(cq["id"])
    elif data == "admin_xretweet_now":
        res = auto_retweet_hashtag()
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke X Menu", "callback_data": "admin_xmenu"}]]}
        edit_msg(chat_id, msg_id, f"<b>RETWEET MANUAL</b>\n━━━━━━━━━━━━━━\n{res}", kb); answer_cq(cq["id"])
    elif data == "admin_stats":
        con = db(); cur2 = con.cursor()
        cur2.execute("SELECT COUNT(*) as c FROM users"); total = cur2.fetchone()["c"]
        cur2.execute("SELECT COUNT(*) as c FROM users WHERE is_premium=TRUE"); prem = cur2.fetchone()["c"]
        cur2.execute("SELECT COUNT(*) as c FROM users WHERE is_banned=TRUE"); banned = cur2.fetchone()["c"]
        cur2.execute("SELECT COUNT(*) as c FROM menfess_log"); total_m = cur2.fetchone()["c"]
        con.close()
        txt = f"<b>STATISTIK</b>\n━━━━━━━━━━━━━━\nTotal User: {total}\nPremium: {prem}\nBanned: {banned}\nTotal Menfess: {total_m}\n"
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Admin", "callback_data": "admin_panel"}]]}
        edit_msg(chat_id, msg_id, txt, kb); answer_cq(cq["id"])
    elif data == "admin_users":
        con = db(); cur2 = con.cursor()
        cur2.execute("SELECT user_id, username, is_premium, is_banned, media_count, text_count FROM users ORDER BY user_id DESC LIMIT 10")
        rows = cur2.fetchall(); con.close()
        txt = "<b>10 USER TERBARU</b>\n━━━━━━━━━━━━━━\n"
        for r in rows:
            txt += f"@{r['username'] or '-'} | ID:{r['user_id']} | {'⭐' if r['is_premium'] else ''}{'🚫' if r['is_banned'] else ''} | M:{r['media_count']} T:{r['text_count']}\n"
        txt += "\n/ban [id]\n/unban [id]\n/premium [id] [hari]\n/unpremium [id]"
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Admin", "callback_data": "admin_panel"}]]}
        edit_msg(chat_id, msg_id, txt, kb); answer_cq(cq["id"])
    elif data == "admin_premium":
        con = db(); cur2 = con.cursor()
        cur2.execute("SELECT user_id, username FROM users WHERE is_premium=TRUE LIMIT 10")
        rows = cur2.fetchall(); con.close()
        txt = "<b>USER PREMIUM</b>\n━━━━━━━━━━━━━━\n"
        for r in rows: txt += f"@{r['username'] or '-'} | ID:{r['user_id']}\n"
        if not rows: txt += "Belum ada user premium.\n"
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Admin", "callback_data": "admin_panel"}]]}
        edit_msg(chat_id, msg_id, txt, kb); answer_cq(cq["id"])
    elif data == "admin_banned":
        con = db(); cur2 = con.cursor()
        cur2.execute("SELECT user_id, username FROM users WHERE is_banned=TRUE LIMIT 10")
        rows = cur2.fetchall(); con.close()
        txt = "<b>USER BANNED</b>\n━━━━━━━━━━━━━━\n"
        for r in rows: txt += f"@{r['username'] or '-'} | ID:{r['user_id']}\n"
        if not rows: txt += "Tidak ada user banned.\n"
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Admin", "callback_data": "admin_panel"}]]}
        edit_msg(chat_id, msg_id, txt, kb); answer_cq(cq["id"])
    elif data == "admin_activity":
        con = db(); cur2 = con.cursor()
        cur2.execute("SELECT username, type, x_url, created_at FROM menfess_log ORDER BY id DESC LIMIT 10")
        rows = cur2.fetchall(); con.close()
        txt = "<b>ACTIVITY MONITOR - 10 TERAKHIR</b>\n━━━━━━━━━━━━━━\n"
        for r in rows:
            tm = time.strftime("%d/%m %H:%M", time.gmtime(r["created_at"]+7*3600))
            txt += f"{tm} | @{r['username'] or '-'} | {r['type']} | {'X ✅' if r['x_url'] else 'X ❌'}\n"
        if not rows: txt += "Belum ada aktivitas.\n"
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Admin", "callback_data": "admin_panel"}]]}
        edit_msg(chat_id, msg_id, txt, kb); answer_cq(cq["id"])

# ================= WEBHOOK - FIX ROUTING VERCEL =================
@app.route("/api/webhook", methods=["POST"])
@app.route("/webhook", methods=["POST"])
@app.route("/api/index", methods=["POST"])
def webhook():
    ensure_db()
    update = request.get_json(force=True, silent=True) or {}
    update_id = update.get("update_id")
    if update_id is not None:
        try:
            con = db(); cur = con.cursor()
            cur.execute("SELECT 1 FROM processed_updates WHERE update_id=%s", (update_id,))
            if cur.fetchone():
                con.close(); return jsonify({"ok": True, "duplicate": True})
            cur.execute("INSERT INTO processed_updates(update_id, created_at) VALUES(%s,%s)", (update_id, int(time.time())))
            con.commit(); con.close()
        except Exception as e:
            print("DEDUP ERROR:", e)

    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        msg_id = cq["message"]["message_id"]
        if data.startswith("admin_"):
            handle_admin_callback(cq, data, chat_id, msg_id)
            return jsonify({"ok": True})
        if data.startswith("delete_"):
            try:
                ch_msg_id = int(data.split("_")[1])
                tg("deleteMessage", {"chat_id": CHANNEL_ID, "message_id": ch_msg_id})
                con = db(); cur = con.cursor()
                cur.execute("SELECT x_url, x_id FROM menfess_log WHERE channel_msg_id=%s ORDER BY id DESC LIMIT 1", (ch_msg_id,))
                row = cur.fetchone(); con.close()
                if row:
                    delete_from_x(row["x_url"], row["x_id"])
                answer_cq(cq["id"], "Deleted ✅ (Channel + X)")
                edit_msg(chat_id, msg_id, "Menfess deleted ✅\nChannel + X sudah dihapus.")
            except Exception as e:
                print("DELETE ERROR:", e); answer_cq(cq["id"], "Gagal hapus")
            return jsonify({"ok": True})
        if data in ("back", "back_main"):
            answer_cq(cq["id"])
            kb = {"inline_keyboard": [[{"text": "⚙️ Admin Panel", "callback_data": "admin_panel"}]]} if cq["from"]["id"] == ADMIN_ID else None
            edit_msg(chat_id, msg_id, "Menu Utama\n\nKirim menfess teks / foto / video.\n\nPerintah:\n/admin - Panel Admin\n/start - Menu Utama", kb)
            return jsonify({"ok": True})
        answer_cq(cq["id"]); return jsonify({"ok": True})

    if "message" not in update: return jsonify({"ok": True})
    msg = update["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    username = msg["from"].get("username", "")
    text_in = msg.get("text", "") or ""

    if text_in.startswith("/"):
        parts = text_in.split(); cmd = parts[0].lower()
        if cmd == "/start":
            kb = {"inline_keyboard": [[{"text": "⚙️ Admin Panel", "callback_data": "admin_panel"}]]} if user_id == ADMIN_ID else None
            send_msg(chat_id, "Selamat datang di JogjaLend Menfess Bot!\n\nKirim teks / foto / video untuk menfess.\n\nFooter otomatis:\nVerified JogjaLend✅", reply_markup=kb)
            return jsonify({"ok": True})
        if cmd == "/admin":
            if user_id != ADMIN_ID:
                send_msg(chat_id, "Hanya admin yang dapat mengakses."); return jsonify({"ok": True})
            send_msg(chat_id, admin_text(), reply_markup=admin_keyboard()); return jsonify({"ok": True})
        if user_id == ADMIN_ID and cmd in ("/ban", "/unban", "/premium", "/unpremium", "/xcheck"):
            if cmd == "/xcheck":
                ok, msgx = check_x_status(); send_msg(chat_id, msgx); return jsonify({"ok": True})
            if len(parts) < 2:
                send_msg(chat_id, "Format: /ban [id]\n/premium [id] [hari]"); return jsonify({"ok": True})
            try:
                target = int(parts[1]); con = db(); cur = con.cursor()
                if cmd == "/ban": cur.execute("UPDATE users SET is_banned=TRUE WHERE user_id=%s", (target,)); send_msg(chat_id, f"User {target} dibanned.")
                elif cmd == "/unban": cur.execute("UPDATE users SET is_banned=FALSE WHERE user_id=%s", (target,)); send_msg(chat_id, f"User {target} di-unban.")
                elif cmd == "/premium":
                    days = int(parts[2]) if len(parts) > 2 else 30
                    until = int(time.time()) + days*86400
                    cur.execute("UPDATE users SET is_premium=TRUE, premium_until=%s WHERE user_id=%s", (until, target)); send_msg(chat_id, f"User {target} jadi premium {days} hari.")
                elif cmd == "/unpremium": cur.execute("UPDATE users SET is_premium=FALSE, premium_until=0 WHERE user_id=%s", (target,)); send_msg(chat_id, f"Premium user {target} dicabut.")
                con.commit(); con.close()
            except Exception as e: send_msg(chat_id, f"Error: {e}")
            return jsonify({"ok": True})
        return jsonify({"ok": True})

    user = get_or_create_user(user_id, username)
    user = reset_quota_if_needed(user)
    if user["is_banned"]:
        send_msg(chat_id, "Akun Anda dibanned."); return jsonify({"ok": True})

    text = msg.get("text", "") or msg.get("caption", "")
    is_media = "photo" in msg or "video" in msg
    file_id = None
    if "photo" in msg: file_id = msg["photo"][-1]["file_id"]
    if "video" in msg: file_id = msg["video"]["file_id"]
    if not text and not is_media: return jsonify({"ok": True})

    limit = 5 if user["is_premium"] else 1
    if is_media and user["media_count"] >= limit:
        send_msg(chat_id, f"Kuota media habis ({user['media_count']}/{limit})."); return jsonify({"ok": True})
    if not is_media and user["text_count"] >= limit:
        send_msg(chat_id, f"Kuota teks habis ({user['text_count']}/{limit})."); return jsonify({"ok": True})

    con = db(); cur = con.cursor()
    if is_media: cur.execute("UPDATE users SET media_count=media_count+1 WHERE user_id=%s", (user_id,))
    else: cur.execute("UPDATE users SET text_count=text_count+1 WHERE user_id=%s", (user_id,))
    con.commit()
    cur.execute("SELECT media_count, text_count FROM users WHERE user_id=%s", (user_id,))
    q = cur.fetchone(); con.close()
    media_used = q["media_count"]; text_used = q["text_count"]

    footer = "\n\nVerified\nJogjaLend✅\nhttps://t.me/jogjalend"
    full_text = (text or "") + footer

    channel_msg_id = None; file_url = None
    if is_media and file_id:
        f = tg("getFile", {"file_id": file_id})
        fp = f.get("result", {}).get("file_path", "")
        if fp: file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
        ch = send_photo(CHANNEL_ID, file_id, full_text)
        channel_msg_id = ch.get("result", {}).get("message_id")
    else:
        ch = send_msg(CHANNEL_ID, full_text)
        channel_msg_id = ch.get("result", {}).get("message_id")

    channel_url = f"https://t.me/jogjalend/{channel_msg_id}" if channel_msg_id else "https://t.me/jogjalend"

    x_ok, x_url, x_id = False, None, None
    if get_setting("x_post", "on") == "on":
        x_ok, x_url, x_id = post_to_x_thread(full_text, file_url)

    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO menfess_log(user_id, username, type, channel_msg_id, x_url, x_id, x_status, created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (user_id, username, "media" if is_media else "text", channel_msg_id, x_url, x_id, "success" if x_ok else "failed", int(time.time())))
    con.commit(); con.close()

    kb = {"inline_keyboard": [[{"text": "View on Channel", "url": channel_url}]]}
    if x_ok and x_url:
        kb["inline_keyboard"].append([{"text": "View on X", "url": x_url}])
    kb["inline_keyboard"].append([{"text": "Delete", "callback_data": f"delete_{channel_msg_id}"}])
    kb["inline_keyboard"].append([{"text": "Back", "callback_data": "back"}])

    status = "Menfess successfully sent! + X" if x_ok else "Menfess successfully sent! (X failed)"
    if x_ok and len(full_text) > 280:
        status += "\n(Thread otomatis di X)"
    send_msg(chat_id, f"{status}\n━━━━━━━━━━━━━━\nMedia : {media_used}/{limit}\nText : {text_used}/{limit}", reply_markup=kb)
    return jsonify({"ok": True})

@app.route("/api/cron_retweet", methods=["GET"])
@app.route("/cron_retweet", methods=["GET"])
def cron_retweet():
    ensure_db()
    if get_setting("x_retweet", "on") != "on": return "Retweet OFF", 200
    return auto_retweet_hashtag(), 200

# FIX 404 di halaman utama - Vercel memetakan api/index.py ke /api/index
@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET"])
@app.route("/api", methods=["GET"])
def index():
    return "JogjaLend Bot V117.7 OK", 200

if __name__ == "__main__":
    app.run()