import tweepy
import telebot
from telebot import types
from datetime import datetime
import os
import io

# === IMPORT ANTI-CRASH ===
try:
    from PIL import Image
    PIL_AVAILABLE = True
    print("PIL OK")
except:
    PIL_AVAILABLE = False
    print("PIL belum ada - watermark off sementara")

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

def kasih_watermark(file_bytes):
    if not PIL_AVAILABLE:
        return file_bytes
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
        out.seek(
