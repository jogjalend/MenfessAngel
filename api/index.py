import os
import json
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@menfessangel"
LIMIT_TEXT = 3
LIMIT_MEDIA = 3
QUOTA_FILE = "/tmp/quota.json"

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False

def load_quota():
    try:
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, "r") as f:
                return json.load(f)
    except: pass
    return {}

def save_quota(data):
    try:
        with open(QUOTA_FILE, "w") as f:
            json.dump(data, f)
    except: pass

def get_today_key(chat_id):
    return f"{chat_id}_{datetime.now
