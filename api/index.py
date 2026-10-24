import os, io, json, requests, traceback, logging
from flask import Flask, request
from PIL import Image
import tweepy
from datetime import datetime
from upstash_redis import Redis

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("angel")

# --- ENV CHECK (fail fast) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN belum di-set di Vercel")
if not REDIS_URL or not REDIS_TOKEN: raise RuntimeError("UPSTASH_REDIS belum di-set")
if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
    raise RuntimeError("X API keys belum lengkap di Vercel")

CHANNEL_USERNAME = "menfessangel"
HASHTAG = "\n\n#jogjalend"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5

# --- REDIS PERSISTENT ---
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)

def get_today_key(chat_id):
    today = datetime.now().strftime("%Y-%m-%d")
    return f"quota:{chat_id}:{today}"

def load_quota(chat_id):
    key = get_today_key(chat_id)
    try:
        data = redis.get(key)
        if data:
            return json.loads(data) if isinstance(data, str) else data
    except Exception as e:
        logger.error(f"Redis get error: {e}")
    return {"text":0,"media":0}

def save_quota(chat_id, data):
    key = get_today_key(chat_id)
    try:
        redis.set(key, json.dumps(data), ex=172800) # auto hapus 2 hari
    except Exception as e:
        logger.error(f"Redis set error: {e}")

def add_hashtag(text):
    if not text: return HASHTAG.strip()
    if "#jogjalend" in text.lower(): return text
    return text.strip() + HASHTAG

def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png","api/logo.png"]:
            if os.path.exists(p):
                logo = Image.open(p).convert("RGBA")
                w,h = base.size
                size = int(w*0.15)
                logo.thumbnail((size,size), Image.LANCZOS)
                # bikin putih
                datas = []
                for r,g,bl,a in logo.getdata():
                    datas.append((255,255,255,230) if a>20 else (255,255,255,0))
                logo.putdata(datas)
                px = w - logo.width - 35
                py = h - logo.height - 55
                base.paste(logo, (px, py), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=95)
                return out.getvalue()
    except Exception as e:
        logger.warning(f"Watermark fail: {e}")
    return b

def tg_post(method, payload, timeout=10):
    # WAJIB timeout biar gak hang di Vercel
    try:
        return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload, timeout=timeout)
    except requests.exceptions.Timeout:
        logger.error(f"TG timeout {method}")
    except Exception as e:
        logger.error(f"TG error {method}: {e}")
    return None

@app.route("/")
@app.route("/<path:path>", methods=['GET','POST'])
def handler(path=None):
    if request.method == 'GET': return "Bot Active @jogja_lend - Redis ON", 200
    chat_id = None
    try:
        data = request.get_json(silent=True)
        if not data: return "ok",200

        # --- CALLBACK ---
        if "callback_query" in data:
            cq = data["callback_query"]
            cb_data = cq.get("data","")
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            
            if cb_data == "profil":
                tg_post("answerCallbackQuery", {"callback_query_id":cq["id"]})
                q = load_quota(chat_id)
                txt = f"👤 Profile\nID: {chat_id}\nToday Usage\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}"
                tg_post("sendMessage", {"chat_id":chat_id,"text":txt})
                return "ok",200

            if cb_data == "info_bot":
                tg_post("answerCallbackQuery", {"callback_query_id":cq["id"]})
                tg_post("sendMessage", {"chat_id":chat_id,"text":"📋 Angel Menfess Bot\nFree Daily Quota: Text 5, Media 5\nQuestions & Support: @Jogja_Lend"})
                return "ok",200

            if cb_data.startswith("delete|"):
                parts = cb_data.split("|")
                if len(parts) != 3:
                    logger.warning(f"Invalid delete callback: {cb_data}")
                    tg_post("answerCallbackQuery", {"callback_query_id":cq["id"],"text":"❌ Invalid data"})
                    return "ok",200
                _, tweet_id, ch_msg_id = parts
                if not tweet_id.isdigit() or not ch_msg_id.isdigit():
                    logger.warning(f"Invalid ID in callback: {cb_data}")
                    return "ok",200
                try:
                    client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
                    client.delete_tweet(tweet_id)
                except Exception as e:
                    logger.error(f"Delete tweet fail: {e}")
                try:
                    tg_post("deleteMessage", {"chat_id":CHANNEL_ID,"message_id":int(ch_msg_id)})
                except: pass
                tg_post("answerCallbackQuery", {"callback_query_id":cq["id"],"text":"✅ Post deleted!"})
                tg_post("editMessageText", {"chat_id":chat_id,"message_id":msg_id,"text":"🗑️ Post successfully deleted!"})
                return "ok",200

        # --- MESSAGE ---
        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg and msg["text"].startswith("/start"):
            first_name = msg.get("from", {}).get("first_name","you")
            username = msg.get("from", {}).get("username","jogja