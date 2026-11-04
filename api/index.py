# api/index.py - JogjaLend Menfess Angel V110.8 Full
import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
BOT_VERSION = "V110.8"

API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

# ============ DB (in-memory fallback biar gak crash kalau DATABASE_URL kosong) ============
# Kalau pakai Postgres di Vercel, ganti bagian ini dengan psycopg2
# Untuk sekarang pakai dict biar bot langsung jalan, tidak 500
menfess_db = []
user_state = {}

def get_db():
    return menfess_db

# ============ HELPERS TELEGRAM ============
def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    if not BOT_TOKEN:
        return None
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{API}/sendMessage", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"send_message error: {e}")
        return None

def send_to_channel(text, reply_markup=None):
    if not CHANNEL_ID:
        return None
    return send_message(CHANNEL_ID, text, reply_markup)

def main_keyboard():
    return {
        "keyboard": [
            [{"text": "📝 Kirim Menfess"}],
            [{"text": "📊 Status"}, {"text": "❓ Help"}]
        ],
        "resize_keyboard": True
    }

def cancel_keyboard():
    return {
        "keyboard": [[{"text": "❌ Batal"}]],
        "resize_keyboard": True
    }

# ============ LOGIC BOT ============
def handle_update(update):
    if "message" not in update:
        return
    msg = update["message"]
    chat_id = msg.get("chat", {}).get("id")
    user_id = msg.get("from", {}).get("id")
    text = msg.get("text", "") or ""
    username = msg.get("from", {}).get("username", "anon")
    first_name = msg.get("from", {}).get("first_name", "Anon")

    if not chat_id:
        return

    # /start
    if text.startswith("/start"):
        send_message(chat_id,
            f"Hai <b>{first_name}</b> 👋\n\n"
            f"Selamat datang di <b>JogjaLend Menfess</b> ✨\n\n"
            f"Klik <b>📝 Kirim Menfess</b> untuk kirim menfess anonim ke channel.\n"
            f"Menfess kamu 100% anonim, admin tidak tau siapa pengirimnya.\n\n"
            f"Bot: <code>{BOT_VERSION}</code>",
            reply_markup=main_keyboard())
        user_state.pop(user_id, None)
        return

    # Batal
    if text == "❌ Batal":
        user_state.pop(user_id, None)
        send_message(chat_id, "Dibatalkan ✅ Balik ke menu.", reply_markup=main_keyboard())
        return

    # Menu Kirim Menfess
    if text == "📝 Kirim Menfess":
        user_state[user_id] = "waiting_menfess"
        send_message(chat_id,
            "Silahkan ketik menfess kamu sekarang 📝\n\n"
            "Contoh:\n"
            "<i>titip salam buat si dia yang di Kotagede, semangat yaa 🫶</i>\n\n"
            "Ketik <b>❌ Batal</b> untuk batal.",
            reply_markup=cancel_keyboard())
        return

    # Menu Status
    if text == "📊 Status":
        total = len(menfess_db)
        send_message(chat_id, f"📊 <b>Status Bot</b>\n\nBot: Aktif ✅\nVersi: <code>{BOT_VERSION}</code>\nTotal menfess terkirim: <b>{total}</b>", reply_markup=main_keyboard())
        return

    # Menu Help
    if text == "❓ Help" or text.startswith("/help"):
        send_message(chat_id,
            "❓ <b>Help JogjaLend</b>\n\n"
            "1. Klik 📝 Kirim Menfess\n"
            "2. Ketik isi menfess\n"
            "3. Menfess dikirim ke channel anonim\n\n"
            "Jangan kirim SARA, porn, dan doxing ya 🙏",
            reply_markup=main_keyboard())
        return

    # Lagi nunggu menfess -> kirim ke channel
    if user_state.get(user_id) == "waiting_menfess":
        if len(text) < 5:
            send_message(chat_id, "Menfess terlalu pendek, ketik yang lebih panjang yaa 🥺", reply_markup=cancel_keyboard())
            return
        # Simpan
        mid = len(menfess_db) + 1
        menfess_db.append({"id": mid, "text": text, "time": datetime.now().isoformat()})
        user_state.pop(user_id, None)

        # Kirim ke channel
        channel_text = (
            f"💌 <b>Menfess #{mid}</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"{text}\n"
            f"━━━━━━━━━━━━━━\n"
            f"<i>via @JogjaLendBot - Kirim menfess di bot ini yaa</i>"
        )
        res = send_to_channel(channel_text)
        if res:
            send_message(chat_id, f"Menfess kamu berhasil dikirim! ✅\n\nMenfess #{mid} udah tayang di channel 🎉", reply_markup=main_keyboard())
        else:
            # Kalau CHANNEL_ID belum di-set / salah, kasih tau user tapi tetap simpan
            send_message(chat_id, f"Menfess kamu diterima ✅ (Menfess #{mid})\n\n⚠️ Channel belum ke-set, hubungi admin untuk cek CHANNEL_ID di Vercel.", reply_markup=main_keyboard())
        return

    # Default - belum pilih menu
    send_message(chat_id, "Klik <b>📝 Kirim Menfess</b> dulu ya untuk kirim menfess ✨", reply_markup=main_keyboard())

# ============ ROUTES - INI YANG BIKIN 404 KEMARIN, SEKARANG SEMUA PATH MASUK KE 1 FUNGSI ============
@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
@app.route("/api/index/", methods=["GET", "POST"])
@app.route("/webhook", methods=["GET", "POST"])
@app.route("/flask", methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def webhook(path=None):
    if request.method == "GET":
        return jsonify({"status": "ok", "version": BOT_VERSION, "bot": "JogjaLend", "path": path or "/"})
    try:
        update = request.get_json(force=True, silent=True)
        if not update:
            return jsonify({"ok": True})
        handle_update(update)
        return jsonify({"ok": True})
    except Exception as e:
        print(f"webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 200

# Wajib untuk Vercel Flask
if __name__ == "__main__":
    app.run()