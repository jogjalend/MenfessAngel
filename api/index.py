import os
import telebot
import tweepy
from flask import Flask, request
from datetime import datetime
from PIL import Image

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")

client_x = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_SECRET)
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api_v1 = tweepy.API(auth)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
user_quota = {}

def get_quota(uid):
    today = datetime.now().strftime("%Y-%m-%d")
    if uid not in user_quota or user_quota[uid]['date'] != today:
        user_quota[uid] = {'date': today, 'text': 0, 'media': 0}
    return user_quota[uid]

def add_watermark_with_logo(base_path, logo_path="logo.png"):
    try:
        base = Image.open(base_path).convert("RGBA")
        # Coba cari logo.png di root, kalau gak ketemu coba di ../logo.png
        if not os.path.exists(logo_path):
            logo_path = "../logo.png"
        logo = Image.open(logo_path).convert("RGBA")
        logo_width = int(base.width * 0.20)
        ratio = logo_width / float(logo.width)
        logo_height = int(float(logo.height) * float(ratio))
        logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
        logo.putalpha(180)
        pos = (base.width - logo.width - 15, base.height - logo.height - 15)
        base.paste(logo, pos, logo)
        base.convert("RGB").save(base_path)
        return True
    except Exception as e:
        print(f"WATERMARK ERROR: {e}")
        return False

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def all_handler(message):
    if message.text and message.text.startswith('/start'):
        name = message.from_user.first_name or "kamu"
        txt = f"halo, {name} ! ini bot promote lend angel. kirim text/foto disini ya!\n\nSisa: Text {get_quota(message.from_user.id)['text']}/5, Media {get_quota(message.from_user.id)['media']}/3"
        bot.send_message(message.chat.id, txt)
        return
    q = get_quota(message.from_user.id)
    is_media = message.content_type in ['photo', 'video']
    if is_media:
        if q['media'] >= 3:
            bot.reply_to(message, "❌ Kuota Media habis (3/3)"); return
        q['media'] += 1
        base_text = message.caption if message.caption else " "
    else:
        if q['text'] >= 5:
            bot.reply_to(message, "❌ Kuota Text habis (5/5)"); return
        q['text'] += 1
        base_text = message.text or " "
    text = f"{base_text}\n\n#jogjalend" if "#jogjalend" not in base_text.lower() else base_text
    try:
        media_ids = []
        if is_media:
            file_id = message.photo[-1].file_id if message.content_type == 'photo' else message.video.file_id
            file_info = bot.get_file(file_id)
            downloaded = bot.download_file(file_info.file_path)
            temp_path = "/tmp/temp_media.jpg"
            with open(temp_path, "wb") as f:
                f.write(downloaded)
            add_watermark_with_logo(temp_path)
            media = api_v1.media_upload(temp_path)
            media_ids.append(media.media_id)
        if media_ids:
            client_x.create_tweet(text=text, media_ids=media_ids)
        else:
            client_x.create_tweet(text=text)
        bot.reply_to(message, f"✅ Terkirim! Sisa: Text {q['text']}/5, Media {q['media']}/3")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'OK'

@app.route('/')
def index():
    return 'BOT JALAN - MenfessAngel + WATERMARK LOGO'
