# api/index.py - JogjaLend Bot Angel V110.9 Full FIX 500
import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
WEBHOOK_URL = "https://menfess-angel.vercel.app/api/index"
BOT_VERSION = "V110.9"

API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

menfess_db = []
user_state = {}

# ============ HELPERS ============
def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    if not BOT_TOKEN:
        return None
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        return requests.post(f"{API}/sendMessage", json=payload, timeout=10).json()
    except Exception as e:
        print(f"send_message error: {e}")
        return None

def send_to_channel(text, reply_markup=None):
    if not CHANNEL_ID:
        return None
    return send_message(CHANNEL_ID, text, reply_markup)

# ============ KEYBOARDS ============
def main_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "👤 My Profile", "callback_data": "profile"}, {"text": "💌 Post", "callback_data": "post"}],
            [{"text": "🧵 Threads Setting", "callback_data": "threads"}],
            [{"text": "📈 Stats", "callback_data": "stats"}, {"text": "ℹ️ Info Bot", "callback_data": "info"}],
            [{"text": "ADMIN PANEL", "callback_data": "admin"}],
        ]
    }

def admin_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🔔 Tag", "callback_data": "admin_tag"}],
            [{"text": "📥 Mode Persetujuan", "callback_data": "admin_approve"}],
            [{"text": "🗑️ Menghapus Pesan", "callback_data": "admin_delete"}],
            [{"text": "🇮🇩 Lang", "callback_data": "admin_lang"}, {"text": "✅ Tutup", "callback_data": "close"}],
            [{"text": "▶️ Lainnya", "callback_data": "admin_more"}],
        ]
    }

def system_tools_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🔗 Set Webhook", "callback_data": "set_webhook"}],
            [{"text": "🛰️ Webhook Info", "callback_data": "webhook_info"}],
            [{"text": "🗑️ Delete Webhook", "callback_data": "delete_webhook"}],
            [{"text": "⬅️ Kembali", "callback_data": "admin"}],
        ]
    }

def back_keyboard():
    return {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu", "callback_data": "back_menu"}]]}

# ============ LOGIC ============
def handle_update(update):
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        try:
            requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": cb["id"]}, timeout=5)
        except:
            pass

        if data == "back_menu":
            send_message(chat_id, "✨ <b>JogjaLend Bot Angel</b> ✨\n\nSelamat datang di JogjaLend Menfess!\nKirim menfess anonim kamu lewat tombol di bawah 👇", reply_markup=main_menu_keyboard())
            return

        if data == "profile":
            send_message(chat_id, f"👤 <b>My Profile</b>\n━━━━━━━━━━━━━━\nID: <code>{chat_id}</code>\nStatus: Member ✅\nTotal menfess: <b>{len(menfess_db)}</b>", reply_markup=back_keyboard())
            return

        if data == "post":
            user_state[chat_id] = "waiting_menfess"
            send_message(chat_id, "Hi !\n━━━━━━━━━━━━━━━━━━━━\nPublish to @menfessangel\nTap Post!\n\nKuota\nMedia : 0/5\nText : 0/5\n\nKetik menfess kamu sekarang 📝", reply_markup=back_keyboard())
            return

        if data == "threads":
            send_message(chat_id, "🧵 <b>Threads Setting</b>\n━━━━━━━━━━━━━━\nThreads kamu belum di-set.\nHubungi admin untuk setting threads.", reply_markup=back_keyboard())
            return

        if data == "stats":
            send_message(chat_id, f"📈 <b>Stats</b>\n━━━━━━━━━━━━━━\nTotal menfess: <b>{len(menfess_db)}</b>\nBot: Aktif ✅\nVersi: {BOT_VERSION}", reply_markup=back_keyboard())
            return

        if data == "info":
            send_message(chat_id, "ℹ️ <b>Info Bot</b>\n━━━━━━━━━━━━━━\n<b>JogjaLend Bot Angel</b>\nBot menfess anonim Jogja.\nKirim menfess tanpa ketahuan siapa kamu.", reply_markup=back_keyboard())
            return

        if data == "admin":
            send_message(chat_id, "⚙️ <b>Pilih salah satu pengaturan yang ingin anda ubah.</b>", reply_markup=admin_keyboard())
            return

        if data == "close":
            send_message(chat_id, "Ditutup ✅", reply_markup=main_menu_keyboard())
            return

        if data == "admin_tag":
            send_message(chat_id, "🔔 <b>Tag</b>\n━━━━━━━━━━━━━━\nFitur Tag belum diaktifkan.\nHubungi admin.", reply_markup=admin_keyboard())
            return

        if data == "admin_approve":
            send_message(chat_id, "📥 <b>Mode Persetujuan</b>\n━━━━━━━━━━━━━━\nSaat ini: Otomatis ✅\nSemua menfess langsung tayang tanpa persetujuan.", reply_markup=admin_keyboard())
            return

        if data == "admin_delete":
            send_message(chat_id, "🗑️ <b>Menghapus Pesan</b>\n━━━━━━━━━━━━━━\nKirim ID menfess yang mau dihapus.\nContoh: /del 1", reply_markup=admin_keyboard())
            return

        if data == "admin_lang":
            send_message(chat_id, "🇮🇩 <b>Lang</b>\n━━━━━━━━━━━━━━\nBahasa: Indonesia ✅", reply_markup=admin_keyboard())
            return

        if data == "admin_more":
            send_message(chat_id, "⚙️ <b>System Tools</b>\n━━━━━━━━━━━━━━━━━━━━\nWebhook: " + WEBHOOK_URL + "\nKelola bot tanpa buka Vercel", reply_markup=system_tools_keyboard())
            return

        if data == "set_webhook":
            try:
                r = requests.get(f"{API}/setWebhook", params={"url": WEBHOOK_URL}, timeout=10).json()
                if r.get("ok"):
                    send_message(chat_id, f"✅ <b>Webhook berhasil di-set!</b>\n\nURL: {WEBHOOK_URL}", reply_markup=system_tools_keyboard())
                else:
                    send_message(chat_id, f"❌ Gagal set webhook: {r}", reply_markup=system_tools_keyboard())
            except Exception as e:
                send_message(chat_id, f"❌ Error: {e}", reply_markup=system_tools_keyboard())
            return

        if data == "webhook_info":
            try:
                r = requests.get(f"{API}/getWebhookInfo", timeout=10).json()
                info = r.get("result", {})
                send_message(chat_id, "🛰️ <b>Webhook Info</b>\n━━━━━━━━━━━━━━━━━━━━\nURL: <code>" + str(info.get('url','-')) + "</code>\nPending: " + str(info.get('pending_update_count',0)) + "\nError: " + str(info.get('last_error_message','-')), reply_markup=system_tools_keyboard())
            except Exception as e:
                send_message(chat_id, f"❌ Error: {e}", reply_markup=system_tools_keyboard())
            return

        if data == "delete_webhook":
            try:
                requests.get(f"{API}/deleteWebhook", params={"drop_pending_updates": "true"}, timeout=10)
                send_message(chat_id, "🗑️ Webhook dihapus! ✅\n\nBot bakal berhenti bales sampai kamu Set Webhook lagi.", reply_markup=system_tools_keyboard())
            except Exception as e:
                send_message(chat_id, f"❌ Error: {e}", reply_markup=system_tools_keyboard())
            return

        send_message(chat_id, f"Menu <b>{data}</b> belum di-set.", reply_markup=admin_keyboard())
        return

    if "message" not in update:
        return
    msg = update["message"]
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "") or ""
    if not chat_id:
        return

    if text.startswith("/start"):
        send_message(chat_id, "✨ <b>JogjaLend Bot Angel</b> ✨\n\nSelamat datang di JogjaLend Menfess!\nKirim menfess anonim kamu lewat tombol di bawah 👇", reply_markup=main_menu_keyboard())
        return

    if text.startswith("/del"):
        try:
            mid = int(text.split()[1])
            menfess_db[:] = [m for m in menfess_db if m["id"] != mid]
            send_message(chat_id, f"Menfess #{mid} dihapus ✅", reply_markup=main_menu_keyboard())
        except:
            send_message(chat_id, "Format salah. Contoh: /del 1", reply_markup=main_menu_keyboard())
        return

    if user_state.get(chat_id) == "waiting_menfess":
        if len(text) < 3:
            send_message(chat_id, "Menfess terlalu pendek, ketik yang lebih panjang yaa 🥺")
            return
        mid = len(menfess_db) + 1
        menfess_db.append({"id": mid, "text": text, "time": datetime.now().isoformat()})
        user_state.pop(chat_id, None)
        send_to_channel(f"💌 <b>Menfess #{mid}</b>\n━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━\n<i>via @JogjaLendBot</i>")
        send_message(chat_id, f"Menfess #{mid} berhasil dikirim! ✅", reply_markup=main_menu_keyboard())
        return

    send_message(chat_id, "Klik tombol di bawah ya 👇", reply_markup=main_menu_keyboard())

# ============ ROUTES ============
@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
@app.route("/api/index/", methods=["GET", "POST"])
@app.route("/webhook", methods=["GET", "POST"])
@app.route("/flask", methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def webhook(path=None):
    if request.method == "GET":
        return jsonify({"status": "ok", "version": BOT_VERSION, "bot": "JogjaLend"})
    try:
        update = request.get_json(force=True, silent=True)
        if not update:
            return jsonify({"ok": True})
        handle_update(update)
        return jsonify({"ok": True})
    except Exception as e:
        print(f"webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 200

if __name__ == "__main__":
    app.run()