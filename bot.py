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
