import os, requests, io
from PIL import Image
import tweepy

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

def add_watermark(base_image_bytes):
    base = Image.open(io.BytesIO(base_image_bytes)).convert("RGBA")
    # cari logo.png
    logo_path = "logo.png"
    if not os.path.exists(logo_path):
        logo_path = "api/logo.png"
    if not os.path.exists(logo_path):
        return base_image_bytes # kalau gak ada logo, post polosan
    
    logo = Image.open(logo_path).convert("RGBA")
    # resize logo 15% dari lebar foto
    w, h = base.size
    logo_size = int(w * 0.15)
    logo.thumbnail((logo_size, logo_size))
    
    # taruh pojok kanan bawah dengan margin 20px
    x = w - logo.width - 20
    y = h - logo.height - 20
    
    base.paste(logo, (x, y), logo)
    
    out = io.BytesIO()
    base.convert("RGB").save(out, format="JPEG", quality=95)
    out.seek(0)
    return out.getvalue()

def handler(request):
    try:
        data = request.get_json() if hasattr(request, 'get_json') else request.json
        if not data or "message" not in data:
            return {"statusCode": 200}
        
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        
        if "photo" not in msg:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": "Kirim FOTO + caption bos! Contoh: kirim foto terus tulis caption 'spill jogja'"})
            return {"statusCode": 200}
        
        caption = msg.get("caption", "") or "menfess"
        photo = msg["photo"][-1] # ambil resolusi terbesar
        file_id = photo["file_id"]
        
        # get file path telegram
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_path = r["result"]["file_path"]
        file_bytes = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}").content
        
        # watermark
        watermarked = add_watermark(file_bytes)
        
        # post ke X
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
                                access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        
        # upload media dulu
        # save temp
        with open("/tmp/post.jpg", "wb") as f:
            f.write(watermarked)
        
        media = api.media_upload("/tmp/post.jpg")
        client.create_tweet(text=caption, media_ids=[media.media_id])
        
        # bales di telegram
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": f"✅ BERHASIL POST KE X @jogjalend!\n\nCaption: {caption}"})
            
    except Exception as e:
        print(f"ERROR: {e}")
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": f"❌ Gagal: {e}"})
        except: pass
    
    return {"statusCode": 200}

# buat Vercel python
def app(environ, start_response):
    from werkzeug.wrappers import Request, Response
    request = Request(environ)
    result = handler(request)
    response = Response(status=result["statusCode"])
    return response(environ, start_response)
