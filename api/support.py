import os
from flask import Flask, request
import telebot

app = Flask(__name__)

TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
LOG_CHANNEL = os.getenv("LOG_CHANNEL", ADMIN_ID)

bot = telebot.TeleBot(TOKEN, threaded=False)

@app.route('/api/support', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    return 'no', 403

@bot.message_handler(commands=['start'])
def start(m):
    nama = m.from_user.first_name
    bot.send_message(m.chat.id,
        f"Halo {nama}! Selamat datang di dukungan @joglendfess.\n\n"
        "Aturan dukungan:\n"
        "• Tolong sampaikan permintaan Anda langsung tanpa sapaan\n"
        "• Jangan mengirim tautan tanpa izin\n"
        "• Jangan mengirim media (misalnya foto dan video) tanpa izin\n\n"
        "Melanggar aturan ini dapat mengakibatkan Anda diblokir oleh bot.\n\n"
        "⬇️ Ketik permintaan Anda dan tim dukungan akan merespon secepatnya."
    )

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    # kalau admin yang chat, jangan diterusin ke log
    if m.from_user.id == ADMIN_ID:
        return
        
    # terusin ke lu (admin) sebagai log
    try:
        username = f"@{m.from_user.username}" if m.from_user.username else "-"
        text_log = (
            f"📩 Support baru dari {m.from_user.first_name} {username} | ID: {m.from_user.id}\n\n"
            f"{m.text}"
        )
        bot.send_message(LOG_CHANNEL, text_log)
        bot.send_message(m.chat.id, "✅ Pesan Anda sudah terkirim ke tim dukungan. Mohon tunggu respon ya.")
    except Exception as e:
        print(f"Error: {e}")
