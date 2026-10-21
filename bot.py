import tweepy
import telebot
from telebot import types
from datetime import datetime
import os
import io
from PIL import Image

# === TOKEN AMAN DARI ENV ===
API_KEY = os.getenv("768jbgLEYitCHJJpgbXyt5HFu")
API_SECRET = os.getenv("KUHTW9hR5eZNyduB5kNKyUpfYSrL3H3Vt004wWaZll2OXmpYf3")
ACCESS_TOKEN = os.getenv("2067954595218030592-unSaId3AulEGwb8nWLBUQsGeH0hwsY")
ACCESS_SECRET = os.getenv("Tc5FYm5C5k8ES6cgNs6v7VFVlpTu2vGW79vd72yo1ezsC")
TELEGRAM_TOKEN = os.getenv("8716061655:AAFHu13ziFLn3t528EeR5CQ45meda1K2zpk")
CHANNEL = "@menfessangel"
CHANNEL_LINK = "https://t.me/menfessangel"

print("CONNECT KE X...")
client_x = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_SECRET)
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api_v1 = tweepy.API(auth)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_quota = {}

# === WATERMARK LEND ANGEL KIRI ATAS ===
def kasih_watermark(file_bytes):
    try:
        base = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
        W, H = base.size
        logo = Image.open("logo.png").convert("RGBA")
        logo_w = int(W * 0.18)
        logo_h = int(logo.size[1] * logo_w / logo.size[0])
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        base.paste(logo, (25, 25), logo)
        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=92)
        out.seek(0)
        return out.getvalue()
    except Exception as e:
        print(f"Watermark error: {e}")
        return file_bytes

def get_quota(uid):
    today = datetime.now().strftime("%Y-%m-%d")
    if uid not in user_quota or user_quota[uid]['date'] != today:
        user_quota[uid] = {'date': today, 'text': 0, 'media': 0}
    return user_quota[uid]

@bot.message_handler(content_types=['text', 'photo', 'video'])
def all_handler(message):
    if message.text and message.text.startswith('/start'):
        name = message.from_user.first_name or "kamu"
        uname = f"@{message.from_user.username}" if message.from_user.username else "tidak ada username"
        txt = f"halo,{name} !\n\nusername anda:{uname} .\n\nini adalah bot promote lend angel.\nanda bisa mengirimkan text beserta foto diri\nkalian disini, let's go!\n\n📣 Pertanyaan & dukungan: @jogja_lend"
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("👤 Profil", callback_data="profil"))
        kb.add(types.InlineKeyboardButton("📋 Informasi Bot", callback_data="info"))
        bot.send_message(message.chat.id, txt, reply_markup=kb)
        return

    q = get_quota(message.from_user.id)
    is_media = message.content_type in ['photo', 'video']
    
    if is_media:
        if q['media'] >= 3:
            bot.reply_to(message, "❌ Kuota Media habis (3/3)")
            return
        q['media'] += 1
        base_text = message.caption if message.caption else " "
    else:
        if q['text'] >= 5:
            bot.reply_to(message, "❌ Kuota Text habis (5/5)")
            return
        q['text'] += 1
        base_text = message.text or " "

    text = base_text if "#jogjalend" in base_text.lower() else f"{base_text}\n\n#jogjalend"

    media_ids = []
    tmp_path = None
    downloaded_bytes = None
    try:
        if is_media:
            file_id = message.photo[-1].file_id if message.content_type == 'photo' else message.video.file_id
            file_info = bot.get_file(file_id)
            downloaded_bytes = bot.download_file(file_info.file_path)
            tmp_path = f"/tmp/{file_id}.jpg" if message.content_type == 'photo' else f"/tmp/{file_id}.mp4"
            with open(tmp_path, 'wb') as f:
                f.write(downloaded_bytes)
            media = api_v1.media_upload(tmp_path)
            media_ids = [media.media_id]
    except Exception as e:
        print(f"GAGAL MEDIA X: {e}")

    try:
        if media_ids:
            tweet = client_x.create_tweet(text=text, media_ids=media_ids)
        else:
            tweet = client_x.create_tweet(text=text)
        tweet_id = tweet.data['id']
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal ke X: {e}")
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return

    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)

    try:
        if message.content_type == 'photo':
            wm_bytes = kasih_watermark(downloaded_bytes)
            sent = bot.send_photo(CHANNEL, wm_bytes, caption=text)
        elif message.content_type == 'video':
            sent = bot.send_video(CHANNEL, message.video.file_id, caption=text)
        else:
            sent = bot.send_message(CHANNEL, text)
        channel_url = f"{CHANNEL_LINK}/{sent.message_id}"
        ch_msg_id = sent.message_id
    except Exception as e:
        print(f"GAGAL Channel: {e}")
        channel_url = CHANNEL_LINK
        ch_msg_id = 0

    # === BALASAN BARU + TOMBOL TETEP ADA ===
    reply_text = f"👸Menfess terkirim!\n\nSisa kuota hari ini:\n📝 Text : {q['text']}/5\n📸 Media : {q['media']}/3\n\nMenfes terkirim ke :\n@menfessangel\nx.com/jogjalendpm"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➡️ See Message", url=channel_url))
    markup.add(types.InlineKeyboardButton("🗑️ Delete Post", callback_data=f"del_{tweet_id}_{ch_msg_id}"))
    bot.reply_to(message, reply_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def all_callback(call):
    if call.data in ["profil", "info"]:
        if call.data == "profil":
            bot.send_message(call.message.chat.id, f"👤 Profil\nNama: {call.from_user.first_name}\nUsername: @{call.from_user.username}\nID: {call.from_user.id}")
        else:
            bot.send_message(call.message.chat.id, "📋 Bot Menfess Angel\nFree Daily Quota: Text 5, Media 3\npertanyaan & aduan: @Jogja_Lend")
        bot.answer_callback_query(call.id)
    elif call.data.startswith('del_'):
        try:
            _, tweet_id, ch_msg_id = call.data.split('_')
            client_x.delete_tweet(tweet_id)
            if ch_msg_id != "0":
                bot.delete_message(CHANNEL, int(ch_msg_id))
            bot.edit_message_text("🗑️ Post berhasil dihapus", call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "✅ Dihapus!")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Gagal: {e}")

print("MENGHAPUS WEBHOOK...")
bot.remove_webhook()
bot.delete_webhook(drop_pending_updates=True)
print("BOT JALAN FINAL! WATERMARK + BALASAN BARU + TOMBOL ON!")
bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=60)
