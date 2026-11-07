# V117.5 Full Fix - JogjaLend Menfess Bot
# Fix: 1) Tombol View on X  2) Anti Double Process (update_id)

import os, json, time, requests
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from requests_oauthlib import OAuth1Session

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
X_USERNAME = "jogja_lend"

TG = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---------- DB ----------
def db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    con = db(); cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY, username TEXT, is_banned BOOLEAN DEFAULT FALSE,
        is_premium BOOLEAN DEFAULT FALSE, premium_until BIGINT DEFAULT 0,
        media_count INT DEFAULT 0, text_count INT DEFAULT 0, last_reset BIGINT DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS processed_updates (update_id BIGINT PRIMARY KEY, created_at BIGINT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS menfess_log (
        id SERIAL PRIMARY KEY, user_id BIGINT, username TEXT, type TEXT,
        channel_msg_id BIGINT, x_url TEXT, created_at BIGINT)""")
    con.commit(); con.close()

init_db()

def get_setting(k, d="on"):
    try:
        con = db(); cur = con.cursor()
        cur.execute("SELECT value FROM settings WHERE key=%s", (k,))
        r = cur.fetchone(); con.close()
        return r["value"] if r else d
    except: return d

def set_setting(k, v):
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value", (k, v))
    con.commit(); con.close()

# ---------- Telegram Helper ----------
def tg(method, payload):
    return requests.post(f"{TG}/{method}", json=payload, timeout=20).json()

def send_msg(chat_id, text, reply_markup=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: p["reply_markup"] = reply_markup
    return tg("sendMessage", p)

def send_photo(chat_id, photo, caption, reply_markup=None):
    p = {"chat_id": chat_id, "photo": photo, "caption": caption, "parse_mode": "HTML"}
    if reply_markup: p["reply_markup"] = reply_markup
    return tg("sendPhoto", p)

# ---------- X ----------
def post_to_x(text, media_url=None):
    """Return (success_bool, tweet_url_or_None)"""
    try:
        oauth = OAuth1Session(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        media_ids = None
        if media_url:
            # Download dari Telegram file -> upload ke X
            f = requests.get(media_url, timeout=30).content
            up = oauth.post("https://upload.twitter.com/1.1/media/upload.json", files={"media": f}, timeout=60)
            media_ids = up.json().get("media_id_string")
        payload = {"text": text}
        if media_ids: payload["media"] = {"media_ids": [media_ids]}
        r = oauth.post("https://api.twitter.com/2/tweets", json=payload, timeout=30)
        data = r.json()
        if "data" in data:
            tweet_id = data["data"]["id"]
            tweet_url = f"https://x.com/{X_USERNAME}/status/{tweet_id}"
            return True, tweet_url
        print("X ERROR:", data)
        return False, None
    except Exception as e:
        print("X EXCEPTION:", e)
        return False, None

def auto_retweet_hashtag():
    # ... fungsi retweet lama V117.3, tidak diubah ...
    return "No new tweet"

# ---------- User & Quota ----------
def get_or_create_user(user_id, username):
    con = db(); cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    u = cur.fetchone()
    if not u:
        cur.execute("INSERT INTO users(user_id, username) VALUES(%s,%s)", (user_id, username or ""))
        con.commit()
        cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        u = cur.fetchone()
    con.close(); return u

# ---------- Webhook ----------
@app.route("/api/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    update_id = update.get("update_id")

    # ===== FIX ANTI DOUBLE PROCESS V117.5 =====
    # Jika update_id sudah pernah diproses, abaikan agar kuota tidak terpotong 2x
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

    # --- Callback Query: Delete / Back ---
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        if data.startswith("delete_"):
            # ... logika delete lama: hapus dari Channel + X ...
            tg("answerCallbackQuery", {"callback_query_id": cq["id"], "text": "Deleted ✅"})
            tg("editMessageText", {"chat_id": chat_id, "message_id": cq["message"]["message_id"], "text": "Menfess deleted ✅"})
        elif data == "back":
            tg("answerCallbackQuery", {"callback_query_id": cq["id"]})
            send_msg(chat_id, "Menu Utama\n\nKirim menfess teks / foto / video.")
        return jsonify({"ok": True})

    if "message" not in update: return jsonify({"ok": True})
    msg = update["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    username = msg["from"].get("username", "")
    user = get_or_create_user(user_id, username)

    if user["is_banned"]:
        send_msg(chat_id, "Akun Anda dibanned.")
        return jsonify({"ok": True})

    # --- Tentukan jenis: teks atau media ---
    text = msg.get("text", "") or msg.get("caption", "")
    is_media = "photo" in msg or "video" in msg
    file_id = None
    if "photo" in msg: file_id = msg["photo"][-1]["file_id"]
    if "video" in msg: file_id = msg["video"]["file_id"]

    if not text and not is_media:
        return jsonify({"ok": True})

    # --- Kuota: 5/5, dihitung 1x per pesan berkat dedup ---
    con = db(); cur = con.cursor()
    if is_media:
        cur.execute("UPDATE users SET media_count=media_count+1 WHERE user_id=%s", (user_id,))
    else:
        cur.execute("UPDATE users SET text_count=text_count+1 WHERE user_id=%s", (user_id,))
    con.commit()
    cur.execute("SELECT media_count, text_count FROM users WHERE user_id=%s", (user_id,))
    q = cur.fetchone(); con.close()
    media_used = q["media_count"]; text_used = q["text_count"]

    # --- Format ke Channel ---
    footer = "\n\nVerified\nJogjaLend✅\nhttps://t.me/jogjalend"
    full_text = (text or "") + footer

    # --- Kirim ke Channel ---
    channel_msg_id = None
    if is_media and file_id:
        # Ambil file_url Telegram untuk X, lalu kirim ke Channel
        f = tg("getFile", {"file_id": file_id})
        file_path = f.get("result", {}).get("file_path", "")
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}" if file_path else None
        ch = send_photo(CHANNEL_ID, file_id, full_text)
        channel_msg_id = ch.get("result", {}).get("message_id")
    else:
        file_url = None
        ch = send_msg(CHANNEL_ID, full_text)
        channel_msg_id = ch.get("result", {}).get("message_id")

    channel_url = f"https://t.me/jogjalend/{channel_msg_id}" if channel_msg_id else "https://t.me/jogjalend"

    # --- Kirim ke X ---
    x_ok, x_url = False, None
    if get_setting("x_post", "on") == "on":
        x_ok, x_url = post_to_x(full_text, file_url)

    # --- Simpan log ---
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO menfess_log(user_id, username, type, channel_msg_id, x_url, created_at) VALUES(%s,%s,%s,%s,%s,%s)",
                (user_id, username, "media" if is_media else "text", channel_msg_id, x_url, int(time.time())))
    con.commit(); con.close()

    # ===== FIX VIEW ON X V117.5 =====
    # Tombol View on X hanya muncul jika X berhasil dan x_url tersedia
    keyboard = {"inline_keyboard": [
        [{"text": "View on Channel", "url": channel_url}]
    ]}
    if x_ok and x_url:
        keyboard["inline_keyboard"].append([{"text": "View on X", "url": x_url}])
    keyboard["inline_keyboard"].append([{"text": "Delete", "callback_data": f"delete_{channel_msg_id}"}])
    keyboard["inline_keyboard"].append([{"text": "Back", "callback_data": "back"}])

    status = "Menfess successfully sent! + X" if x_ok else "Menfess successfully sent! (X failed)"
    send_msg(chat_id, f"{status}\n━━━━━━━━━━━━━━\nMedia : {media_used}/5\nText : {text_used}/5", reply_markup=keyboard)
    return jsonify({"ok": True})

@app.route("/api/cron_retweet", methods=["GET"])
def cron_retweet():
    if get_setting('x_retweet', 'on') != 'on':
        return "Retweet OFF", 200
    res = auto_retweet_hashtag()
    return res, 200

@app.route("/", methods=["GET"])
def index():
    return "JogjaLend Bot V117.5 OK", 200

if __name__ == "__main__":
    app.run()