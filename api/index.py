from flask import Flask, request
import os, requests, io, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image, ImageDraw

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
WIB = timezone(timedelta(hours=7))
SEP = "────────────────────────"
HASHTAG = "#jogjalend"

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0})

def get_user(uid):
    u = USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today:
        u["today_text"]=0; u["today_media"]=0; u["last_date"]=today
    return u

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send(chat_id, text, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=4)
    except: pass

def welcome_text(user):
    # 1 GARIS DOANG - FINAL
    return f"""Hi {user['name']}!
{SEP}
Publish to @menfessangel
Tap Post!

Kuota Post
Media : {user['today_media']}/5
Text : {user['today_text']}/5"""

def find_logo():
    for p in ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "../logo.png")]:
        if os.path.exists(p): return p
    return None

def get_profile_photo_id(user_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos", params={"user_id": user_id, "limit": 1}, timeout=4).json()
        if r.get("result", {}).get("total_count", 0) > 0:
            return r["result"]["photos"][0][-1]["file_id"]
    except: pass
    return None

def get_channel_info():
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat", params={"chat_id": CHANNEL_ID}, timeout=4).json()
        chat = r.get("result", {})
        photo_file_id = chat.get("photo", {}).get("big_file_id")
        title = chat.get("title", "menfessangel")
        try:
            rc = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount", params={"chat_id": CHANNEL_ID}, timeout=4).json()
            members = rc.get("result", 0)
        except: members = 0
        return photo_file_id, members, title
    except: return None, 0, "menfessangel"

def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=4).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=6).content
    except: return None

def add_watermark(photo_bytes):
    try:
        lp = find_logo()
        if not lp: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(lp).convert("RGBA")
        w,h = base.size; sz = int(w*0.13)
        logo = logo.resize((sz,sz), Image.LANCZOS)
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        overlay.paste(logo, (12, 12), logo) # KIRI ATAS JELAS 13%
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO(); combined.save(bio, "JPEG", quality=92); bio.seek(0)
        return bio
    except: return None

def create_stats_chart(members, today_t, today_m, total_t, total_m):
    W,H = 800, 450; img = Image.new("RGB", (W,H), "#0f0f0f"); draw = ImageDraw.Draw(img)
    data = [("Today T", today_t), ("Today M", today_m), ("Total T", total_t), ("Total M", total_m), ("Members", members)]
    max_val = max([v for _,v in data] + [1]); bar_w = 110; gap = 30; start_x = 50; base_y = 350
    colors = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#f9ca24", "#6c5ce7"]
    for i, (label, val) in enumerate(data):
        h = int((val / max_val) * 250) if max_val>0 else 0
        x = start_x + i*(bar_w+gap); y = base_y - h
        draw.rectangle([x, y, x+bar_w, base_y], fill=colors[i])
        draw.text((x+10, base_y+10), label, fill="white"); draw.text((x+10, y-25), str(val), fill="white")
    draw.text((30, 20), f"STATS REALTIME - {datetime.now(WIB).strftime('%H:%M WIB')}", fill="white")
    bio = io.BytesIO(); img.save(bio, "PNG"); bio.seek(0); return bio

def back_kb(): return {"inline_keyboard": [[{"text": "« Back", "callback_data": "back_home"}]]}
def main_kb(is_admin_user=False):
    kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
    if is_admin_user: kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb

def send_success(chat_id, user, ch_msg_id):
    url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
    kb=[[{"text": "See on channel", "url": url}], [{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}], [{"text": "« Back", "callback_data": "back_home"}]]
    send(chat_id, f"Menfess sent!\n{SEP}\nRemaining\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5", {"inline_keyboard": kb})

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "V86.4 1 GARIS FINAL LIVE",200
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            user["name"]=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
            user["username"]=msg["from"].get("username","")
        if text.startswith("/start"):
            send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
        elif not user["banned"]:
            if text and not text.startswith("/") and len(text)>=3:
                if user["today_text"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    clean=text.strip()
                    if HASHTAG.lower() not in clean.lower(): clean=f"{clean} {HASHTAG}"
                    r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=5).json()
                    ch_id=r.get("result",{}).get("message_id"); user["today_text"]+=1; user["total_text"]+=1; send_success(chat_id, user, ch_id)
            if "photo" in msg or "video" in msg:
                if user["today_media"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                    is_photo="photo" in msg
                    base_cap=caption.strip() if caption else HASHTAG
                    if HASHTAG.lower() not in base_cap.lower(): base_cap=f"{base_cap} {HASHTAG}"
                    ch_id=None
                    if is_photo:
                        raw=download_file(fid); wm=add_watermark(raw) if raw else None
                        if wm: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": wm}, timeout=8).json(); ch_id=r.get("result",{}).get("message_id")
                        else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id=r.get("result",{}).get("message_id")
                    else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=8).json(); ch_id=r.get("result",{}).get("message_id")
                    user["today_media"]+=1; user["total_media"]+=1; send_success(chat_id, user, ch_id)

    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
        except: pass

        if cdata=="my_profile":
            photo_id=get_profile_photo_id(chat_id)
            txt=f"My Profile\n{SEP}\nName: {user['name']}\nID: {uid}\nUsername: @{user['username'] or '-'}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5\nThreads: {'ON' if user['threads_on'] else 'OFF'}"
            if photo_id:
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": chat_id, "photo": photo_id, "caption": txt, "parse_mode": "HTML", "reply_markup": back_kb()}, timeout=5)
                except: send(chat_id, txt, back_kb())
            else: send(chat_id, txt, back_kb())
        elif cdata=="stats":
            _, members, title = get_channel_info()
            today_t = sum(u["today_text"] for u in USERS.values()); today_m = sum(u["today_media"] for u in USERS.values())
            all_t = sum(u["total_text"] for u in USERS.values()); all_m = sum(u["total_media"] for u in USERS.values())
            chart = create_stats_chart(members, today_t, today_m, all_t, all_m)
            caption_txt = f"Stats - {title}\n\nMembers: {members}+\nToday: {today_t}T {today_m}M\nTotal: {all_t}T {all_m}M\nYour: {user['today_text']}/5 T, {user['today_media']}/5 M"
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": caption_txt, "parse_mode": "HTML", "reply_markup": json.dumps(back_kb())}, files={"photo": chart}, timeout=8)
            except: send(chat_id, caption_txt, back_kb())
        elif cdata=="back_home":
            send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Threads Setting\n{SEP}\nStatus: {'ON' if user['threads_on'] else 'OFF'}", kb)
        elif cdata=="threads_on": user["threads_on"]=True; send(chat_id, f"Threads: ON ✅\n{SEP}\nEnabled", back_kb())
        elif cdata=="threads_off": user["threads_on"]=False; send(chat_id, f"Threads: OFF ❌\n{SEP}\nDisabled", back_kb())
        elif cdata in ["verification", "rules"]: send(chat_id, f"Verification\n{SEP}\nContact @jogja_lend", back_kb())
        elif cdata=="post": send(chat_id, f"Post Menfess\n{SEP}\nKirim text/foto/video\nWatermark kiri atas + {HASHTAG}", back_kb())
        elif cdata=="help": send(chat_id, f"Help\n{SEP}\nChannel: @menfessangel", back_kb())
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit():
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=3)
                except: pass
            send(chat_id, f"Deleted\n{SEP}\nRemoved", back_kb())
        elif cdata=="admin_panel" and is_admin(chat_id):
            total_t=sum(u["today_text"] for u in USERS.values()); total_m=sum(u["today_media"] for u in USERS.values())
            kb={"inline_keyboard": [[{"text": f"👥 {len(USERS)} Users", "callback_data": "admin_users"}, {"text": f"📈 {total_t}T {total_m}M", "callback_data": "admin_stats"}], [{"text": "🔄 Reset Limits", "callback_data": "admin_reset"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"🔐 ADMIN PANEL\n{SEP}\nUsers: {len(USERS)}\nToday: {total_t}T {total_m}M", kb)
        elif cdata.startswith("admin_") and is_admin(chat_id):
            if cdata=="admin_reset":
                for u in USERS.values(): u["today_text"]=0; u["today_media"]=0
                send(chat_id, f"Reset done\n{SEP}\nAll limits 0", back_kb())
            else: send(chat_id, f"Admin {cdata}\n{SEP}\nDone", back_kb())
    return "ok",200
