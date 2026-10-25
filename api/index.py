import os, time, requests
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")

app = Flask(__name__)
SESSION = requests.Session()

def upload_catbox(file_bytes):
    try:
        r = SESSION.post("https://catbox.moe/user/api.php", 
            data={"reqtype":"fileupload"}, 
            files={"fileToUpload": ("img.jpg", file_bytes)})
        return r.text.strip() if r.ok and "http" in r.text else None
    except: return None

def post_to_threads(text, img_bytes=None):
    if not THREADS_TOKEN or not THREADS_USER_ID: return
    try:
        if img_bytes:
            url = upload_catbox(img_bytes)
            if not url: return
            payload = {"media_type":"IMAGE","image_url":url,"text":text,"access_token":THREADS_TOKEN}
        else:
            payload = {"media_type":"TEXT","text":text,"access_token":THREADS_TOKEN}
        
        c = SESSION.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads", data=payload).json()
        cid = c.get("id")
        if not cid: 
            print("Threads container error:", c)
            return
        time.sleep(6)
        SESSION.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish", 
                     data={"creation_id":cid,"access_token":THREADS_TOKEN})
    except Exception as e:
        print("Threads err:", e)

# ... sisa code handler lu tetep, tinggal di bawah sendPhoto tambahin:
# post_to_threads(caption, fb if is_media else None)
