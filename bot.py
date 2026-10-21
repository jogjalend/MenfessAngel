import os
import telebot
from telebot import types
import tweepy
from datetime import datetime

print("CONNECT KE X...")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")

# Client v2 buat tweet
client_x = tweepy.Client(
    consumer_key=API_KEY, 
    consumer_secret=API_SECRET, 
    access_token=ACCESS_TOKEN, 
    access_token_secret=ACCESS_SECRET
)
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
        txt = f"halo, {name} !\n\nusername anda: {uname} .\n\nini adalah bot promote lend angel.\nanda bisa mengirimkan text beserta foto diri\nkalian disini, let's go!\n\n📣 Pertanyaan & dukungan: @jogja_lend"
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

    # --- INI YANG KEMARIN KURANG BOS ---
    try:
        media_ids = []
        if is_media:
            print("-> DOWNLOAD MEDIA...")
            file_info = bot.get_file(message.photo[-1].file_id if message.content_type == 'photo' else message.video.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open("temp_media.jpg", "wb") as f:
                f.write(downloaded)
            # Upload ke X pake v1
            media = api_v1.media_upload("temp_media.jpg")
            media_ids.append(media.media_id)
            print(f"-> MEDIA UPLOADED: {media.media_id}")

        # Tweet pake v2
        print(f"-> POSTING: {text[:50]}...")
        if media_ids:
            client_x.create_tweet(text=text, media_ids=media_ids)
        else:
            client_x.create_tweet(text=text)
            
        bot.reply_to(message, f"✅ Terkirim! Sisa kuota: Text {q['text']}/5, Media {q['media']}/3")
        print("-> SUKSES POSTING")
        
    except Exception as e:
        print(f"ERROR: {e}")
        bot.reply_to(message, f"❌ Error: {e}\n\nCoba cek token X kamu bos, ini biasanya 401 karena token gak sinkron")

print("BOT JALAN...")
bot.infinity_polling()
