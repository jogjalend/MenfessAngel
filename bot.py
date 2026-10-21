import telebot
from telebot import types
import tweepy, os, io
from datetime import datetime

try:
    from PIL import Image
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False
    Image = None

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@menfessangel"
CHANNEL_LINK = "https://t.me/menfessangel"

print("INIT BOT...")
client_x = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_SECRET)
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api_v1 = tweepy.API(auth)

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
user_quota = {}

def get_quota(uid):
    today = datetime.now().strftime("%Y-%m-%d")
    if uid not in user_quota or user_quota[uid]['date'] != today:
        user_quota[uid] = {'date': today, 'text': 0, 'media': 0}
    return user_quota[uid]

@bot.message_handler(commands=['start'])
def start(m):
    name = m.from_user.first_name
    txt = f"halo,{name} ! bot udah aktif lagi!\n\nkirim text / foto + caption sekarang"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("👤 Profil", callback_data="profil"))
    kb.add(types.InlineKeyboardButton("📋 Info", callback_data="info"))
    bot.send_message(m.chat.id, txt, reply_markup=kb)
    print(f"START dari {m.from_user.id}")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle(m):
    try:
        q = get_quota(m.from_user.id)
        is_media = m.content_type in ['photo','video']
        if is_media:
            if q['media'] >= 3:
                bot.reply_to(m, "❌ Kuota Media habis")
                return
            q['media'] += 1
            base_text = m.caption or " "
        else:
            if q['text'] >=5:
                bot.reply_to(m, "❌ Kuota Text habis")
                return
            q['text'] += 1
            base_text = m.text or " "
        
        text = base_text if "#jogjalend" in base_text.lower() else f"{base_text}\n\n#jogjalend"
        
        # POST KE X
        media_ids = []
        if is_media:
            file_id = m.photo[-1].file_id if m.content_type == 'photo' else m.video.file_id
            f_info = bot.get_file(file_id)
            f_bytes = bot.download_file(f_info.file_path)
            tmp = f"/tmp/{file_id}.jpg"
            with open(tmp, 'wb') as f: f.write(f_bytes)
            media = api_v1.media_upload(tmp)
            media_ids = [media.media_id]
            os.remove(tmp)
        
        if media_ids:
            tw = client_x.create_tweet(text=text, media_ids=media_ids)
        else:
            tw = client_x.create_tweet(text=text)
        
        reply = f"👸Menfess terkirim!\nSisa: Text {q['text']}/5, Media {q['media']}/3"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➡️ See Message", url=CHANNEL_LINK))
        bot.reply_to(m, reply, reply_markup=markup)
        print("SUKSES POST")
    except Exception as e:
        print(f"ERROR HANDLE: {e}")
        bot.reply_to(m, f"Error: {e}")

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    bot.answer_callback_query(c.id, "OK")
    bot.send_message(c.message.chat.id, f"Tombol {c.data} dipencet")

print("HAPUS WEBHOOK...")
bot.remove_webhook()
import time
time.sleep(2)
bot.delete_webhook(drop_pending_updates=True)
print("BOT POLLING MULAI...")
bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
