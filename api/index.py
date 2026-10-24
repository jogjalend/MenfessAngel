import os, io, json, requests, traceback
from flask import Flask, request
from PIL import Image
import tweepy
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID") or "8584319568")
except:
    ADMIN_ID = 8584319568

HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))

BROADCAST_TEXT = """👼 HALO ANGEL!

Jangan lupa follow & join ya 🤍

FOLLOW:
• Channel: @menfessangel
• Grup: @jogjalend
• X: x.com/jogjalendpm

Kirim menfess kalian disini, auto-post 24 jam!"""

BROADCAST_KB = {
    "inline_keyboard": [
        [{"text": "📢 Channel", "url": "https://t.me/menfessangel"}, {"text": "💬 Grup", "url": "https://t.me/jogjalend"}],
        [{"text": "🐦 X / Twitter", "url": "https://x.com/jogjalendpm"}]
    ]
}

def load_quota():
    try:
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_quota(data):
    try:
        with open(QUOTA_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

def get_today_key(chat_id):
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    return f"{chat_id}_{today}"

def add_hashtag(text):
    if not text:
        return HASHTAG.strip()
    if "#jogjalend" in text.lower():
        return text
    return text.strip() + HASHTAG

def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png", "api/logo
