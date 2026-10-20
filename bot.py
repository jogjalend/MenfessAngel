import tweepy
import telebot
from telebot import types
from datetime import datetime
import os

API_KEY = "768jbgLEYitCHJJpgbXyt5HFu"
API_SECRET = "KUHTW9hR5eZNyduB5kNKyUpfYSrL3H3Vt004wWaZll2OXmpYf3"
ACCESS_TOKEN = "2067954595218030592-unSaId3AulEGwb8nWLBUQsGeH0hwsY"
ACCESS_SECRET = "Tc5FYm5C5k8ES6cgNs6v7VFVlpTu2vGW79vd72yo1ezsC"
TELEGRAM_TOKEN = "8716061655:AAFHu13ziFLn3t528EeR5CQ45meda1K2zpk"
CHANNEL = "@menfessangel"
CHANNEL_LINK = "https://t.me/menfessangel"

print("CONNECT KE X...")
# Client v2 buat tweet
client_x = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_SECRET)
# API v1 buat upload media
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api_v1 = tweepy.API(auth)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_quota = {}

def get_quota(uid):
    today = datetime.now().strftime("%Y-%m-%d")
    if uid not in user_quota or user_quota[uid]['date'] != today:
        user_quota[uid] = {'date': today, 'text': 0, 'media': 0}
    return user_quota[uid]

@bot.message_handler(content_types=['text', 'photo', 'video'])
def all_handler(message):
    print(f"PESAN MASUK: {message.from_user.id} type={message.content_type}")
    if message.text and message.text.startswith('/start'):
        name = message.from_user.first_name or "kamu"
        uname = f"@{message.from_user.username}" if message.from_user.username else "tidak ada username"
        txt = f"halo,{name} !\n\nusername anda:{uname} .\n\nini adalah bot promote lend angel.\nanda bisa mengirimkan text beserta foto diri\nkalian disini, let's go!\n\n📣 Pertanyaan & dukungan: @jogja_lend"
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("👤 Profil", callback_data="profil"))
        kb.add(types.InlineKeyboardButton("📋 Informasi Bot", callback_data="info"))
        bot.send_message(message.chat.id, txt, reply_markup=kb)
        print("-> /start TERKIRIM")
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

    if "#jogjalend" not in base_text.lower():
        text = f"{base_text}\n\n#jogjalend"
    else:
        text = base_text

    # === UPLOAD MEDIA KE X ===
    media_ids = []
    tmp_path = None
    try:
        if is_media:
            if message.content_type == 'photo':
                file_id = message.photo[-1].file_id
            else:
                file_id = message.video.file_id
            
            file_info = bot.get_file(file_id)
            downloaded = bot.download_file(file_info.file_path)
            tmp_path = f"/tmp/{file_id}.jpg" if message.content_type == 'photo' else f"/tmp/{file_id}.mp4"
            with open(tmp_path, 'wb') as f:
                f.write(downloaded)
            
            print(f"-> UPLOAD MEDIA KE X: {tmp_path}")
            media = api_v1.media_upload(tmp_path)
            media_ids = [media.media_id]
    except Exception as e:
        print(f"-> GAGAL UPLOAD MEDIA X: {e}")

    try:
        if media_ids:
            tweet = client_x.create_tweet(text=text, media_ids=media_ids)
        else:
            tweet = client_x.create_tweet(text=text)
        tweet_id = tweet.data['id']
        print(f"-> SUKSES X: {tweet_id}")
    except Exception as e:
        print(f"-> GAGAL X: {e}")
        bot.reply_to(message, f"❌ Gagal ke X: {e}")
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return

    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)

    # === KIRIM KE CHANNEL TELEGRAM (PAKE FOTO/VIDEO) ===
    try:
        if message.content_type == 'photo':
            sent = bot.send_photo(CHANNEL, message.photo[-1].file_id, caption=text)
        elif message.content_type == 'video':
            sent = bot.send_video(CHANNEL, message.video.file_id, caption=text)
        else:
            sent = bot.send_message(CHANNEL, text)
        channel_url = f"{CHANNEL_LINK}/{sent.message_id}"
        ch_msg_id = sent.message_id
    except Exception as e:
        print(f"-> GAGAL Channel: {e}")
        channel_url = CHANNEL_LINK
        ch_msg_id = 0

    reply_text = f"Free Daily Quota\nText: {q['text']}/5\nMedia: {q['media']}/3\n\nBerhasil mengirim menfess\n\npertanyaan & aduan:\n@Jogja_Lend"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➡️ See Message", url=channel_url))
    markup.add(types.InlineKeyboardButton("🗑️ Delete Post", callback_data=f"del_{tweet_id}_{ch_msg_id}"))
    bot.reply_to(message, reply_text, reply_markup=markup)
    print("-> DONE POST TERKIRIM")

@bot.callback_query_handler(func=lambda call: True)
def all_callback(call):
    print(f"CALLBACK: {call.data}")
    if call.data in ["profil", "info"]:
        if call.data == "profil":
            bot.send_message(call.message.chat.id, f"👤 Profil\nNama: {call.from_user.first_name}\nUsername: @{call.from_user.username}\nID: {call.from_user.id}")
        else:
            bot.send_message(call.message.chat.id, "📋 Bot Menfess Angel\nFree Daily Quota: Text 50, Media 10\npertanyaan & aduan: @Jogja_Lend")
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
print("WEBHOOK BERSIH!")
print("BOT JALAN SAYANG😚 /start READY! AUTO #jogjalend ON! FOTO ON!")
bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=60)
