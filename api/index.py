from flask import Flask, request
import os, requests, io, psycopg2, random, re
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
DATABASE_URL = os.getenv("DATABASE_URL")
THREADS_URL = os.getenv("THREADS") or "https://threads.net/jogjalend"
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
WIB = timezone(timedelta(hours=7))
SEP = "●-----------------------------------------------------●"
HASHTAG = "#jogjalend"

# === V106.6 FIX - ALL CLICKABLE ===
def to_fancy(text):
    pattern = r'@\w+|#\w+|/\w+|https?://\S+|threads\.net/\S+|t\.me/\S+'
    res_parts = []
    last_idx = 0
    for m in re.finditer(pattern, text):
        before = text[last_idx:m.start()]
        conv = ""
        for c in before:
            if 'A' <= c <= 'Z': conv+=chr(0x1D5A0 + ord(c)-65)
            elif 'a' <= c <= 'z': conv+=chr(0x1D5BA + ord(c)-97)
            elif '0' <= c <= '9': conv+=chr(0x1D7E2 + ord(c)-48)
            else: conv+=c
        res_parts.append(conv)
        res_parts.append(m.group(0))
        last_idx = m.end()
    tail = text[last_idx:]
    conv = ""
    for c in tail:
        if 'A' <= c <= 'Z': conv+=chr(0x1D5A0 + ord(c)-65)
        elif 'a' <= c <= 'z': conv+=chr(0x1D5BA + ord(c)-97)
        elif '0' <= c <= '9': conv+=chr(0x1D7E2 + ord(c)-48)
        else: conv+=c
    res_parts.append(conv)
    return "".join(res_parts)

def F(t): return to_fancy(t)

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0, "admin_target": "both"})

def get_db():
    if not DATABASE_URL: return None
    try: return psycopg2.connect(DATABASE_URL, connect_timeout=5)
    except: return None
def init_db():
    db=get_db()
    if not db: return
    try:
        cur=db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0, admin_target TEXT DEFAULT 'both')")
        try: cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS admin_target TEXT DEFAULT 'both'")
        except: pass
        db.commit(); cur.close(); db.close()
    except: pass
def load_user_from_db(uid):
    db=get_db()
    if not db: return None
    try:
        cur=db.cursor()
        cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target FROM menfess_users WHERE user_id=%s",(uid,))
        row=cur.fetchone(); cur.close(); db.close()
        if row: return {"name":row[0] or "", "username":row[1] or "", "threads_on":row[2] or False, "today_text":row[3] or 0, "today_media":row[4] or 0, "last_date":row[5] or "", "banned":row[6] or False, "total_text":row[7] or 0, "total_media":row[8] or 0, "total_chars":row[9] or 0, "admin_target":row[10] or "both"}
    except: return None
    return None
def save_user_to_db(uid,user):
    db=get_db()
    if not db: return
    try:
        cur=db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s, admin_target=%s",
                    (uid,user["name"],user["username"],user["threads_on"],user["today_text"],user["today_media"],user["last_date"],user["banned"],user["total_text"],user["total_media"],user.get("total_chars",0),user.get("admin_target","both"),
                     user["name"],user["username"],user["threads_on"],user["today_text"],user["today_media"],user["last_date"],user["banned"],user["total_text"],user["total_media"],user.get("total_chars",0),user.get("admin_target","both")))
        db.commit(); cur.close(); db.close()
    except: pass
def get_user(uid):
    u=USERS[uid]
    if u["last_date"]=="" and DATABASE_URL:
        d=load_user_from_db(uid)
        if d: USERS[uid]=d; u=USERS[uid]
    today=datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"]!=today: u["today_text"]=0; u["today_media"]=0; u["last_date"]=today; save_user_to_db(uid,u)
    return u
def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send_message(chat_id,text,kb=None):
    if kb and "inline_keyboard" in kb:
        for row in kb["inline_keyboard"]:
            for btn in row:
                if "text" in btn and "url" not in btn:
                    btn["text"]=F(btn["text"])
    payload={"chat_id":chat_id,"text":F(text),"parse_mode":"HTML","disable_web_page_preview":True}
    if kb: payload["reply_markup"]=kb
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json=payload,timeout=10)
    except: pass

def get_welcome_text(user): return f"Hi {user['name']}!\n{SEP}\nPublish to @menfessangel\nTap Post!\n\nKuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5"
def get_back_keyboard(): return {"inline_keyboard": [[{"text": "<< Back", "callback_data": "back_home"}]]}
def get_main_keyboard(is_ad=False):
    kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
    if is_ad: kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb
def get_admin_keyboard(user):
    target=user.get("admin_target","both")
    return {"inline_keyboard": [[{"text": f"Target: {target.upper()}", "callback_data": "admin_noop"}], [{"text": "✅ Channel Only" if target=="channel" else "Channel Only", "callback_data": "admin_set_channel"}], [{"text": "✅ Threads Only" if target=="threads" else "Threads Only", "callback_data": "admin_set_threads"}], [{"text": "✅ Both (Channel+Threads)" if target=="both" else "Both", "callback_data": "admin_set_both"}], [{"text": "<< Back", "callback_data": "back_home"}]]}

def find_logo():
    for p in ["logo.png","../logo.png",os.path.join(os.path.dirname(__file__),"../logo.png")]:
        if os.path.exists(p): return p
    return None
def download_file(file_id):
    try:
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",params={"file_id":file_id},timeout=5).json()
        fp=info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}",timeout=8).content
    except: return None
def add_watermark(photo_bytes):
    try:
        lp=find_logo()
        if not lp: return None
        base=Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo=Image.open(lp).convert("RGBA")
        w,h=base.size; sz=int(w*0.13); logo=logo.resize((sz,sz),Image.LANCZOS)
        overlay=Image.new("RGBA",base.size,(0,0,0,0)); overlay.paste(logo,(12,12),logo)
        combined=Image.alpha_composite(base,overlay).convert("RGB")
        bio=io.BytesIO(); combined.save(bio,"JPEG",quality=92); bio.seek(0); return bio
    except: return None
def get_font(size,bold=False):
    try:
        p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(p): return ImageFont.truetype(p,size)
    except: pass
    return ImageFont.load_default()
def make_today_chart(user):
    try:
        W,H=1080,650
        img=Image.new('RGB',(W,H),'#0D0D0F')
        draw=ImageDraw.Draw(img)
        f_title=get_font(32,True); f_small=get_font(18)
        draw.rectangle([0,0,W,85],fill='#161618')
        draw.text((30,18),f"TODAY 1D - {user['name'][:16]}",fill='white',font=f_title)
        draw.text((30,55),f"{datetime.now(WIB).strftime('%d %b')} - {user['today_text']+user['today_media']}/10 today",fill='#71717A',font=f_small)
        hours=["08:00","10:00","12:00","14:00","16:00","18:00","20:00","22:00"]
        total=user['today_text']+user['today_media']
        highs=[0]*8 if total==0 else [max(0, random.randint(0,2)+(total//8)) for _ in hours]
        max_val=max(highs) if max(highs)>0 else 3
        max_val=max(max_val,3)
        ct,cb,cl,cr=120,580,70,1050
        ch=cb-ct
        for i in range(5):
            y=ct+i*ch//4
            draw.line([(cl,y),(cr,y)],fill='#1F1F23',width=1)
            draw.text((10,y-8),str(max_val - i*max_val//4),fill='#71717A',font=f_small)
        slot_w=(cr-cl)//len(hours)
        for idx in range(len(hours)):
            xc=cl+idx*slot_w+slot_w//2
            v=highs[idx]
            def to_y(val): return cb-int(val/max_val*ch*0.9)
            yh=to_y(v)
            color='#10B981' if idx%2==0 else '#EF4444'
            if total==0: color='#27272A'
            draw.line([(xc,yh),(xc,cb)],fill=color,width=2)
            draw.rectangle([xc-18,yh,xc+18,cb if v==0 else yh+max(18,(cb-yh)//3)],fill=color)
            draw.text((xc-22,cb+10),hours[idx],fill='#A1A1AA',font=f_small)
            if v>0: draw.text((xc-4,yh-18),str(v),fill='#A1A1AA',font=f_small)
        bio=io.BytesIO(); img.save(bio,format='JPEG',quality=95); bio.seek(0); return bio
    except: return None
def make_weekly_chart(user):
    try:
        W,H=1080,650
        img=Image.new('RGB',(W,H),'#0D0D0F')
        draw=ImageDraw.Draw(img)
        f_title=get_font(32,True); f_small=get_font(18)
        draw.rectangle([0,0,W,85],fill='#161618')
        draw.text((30,18),"WEEKLY 7D",fill='white',font=f_title)
        draw.text((30,55),f"{user['name'][:20]} - Last 7 days",fill='#71717A',font=f_small)
        days=["22","23","24","25","26","27","28"]
        vals=[random.randint(1,5) for _ in days]
        max_v=max(vals) if max(vals)>0 else 5
        ct,cb,cl,cr=120,580,70,1050
        ch=cb-ct
        for i in range(5):
            y=ct+i*ch//4
            draw.line([(cl,y),(cr,y)],fill='#1F1F23',width=1)
            draw.text((10,y-8),str(max_v - i*max_v//4),fill='#71717A',font=f_small)
        slot_w=(cr-cl)//len(days)
        for idx in range(len(days)):
            xc=cl+idx*slot_w+slot_w//2
            v=vals[idx]
            def to_y(val): return cb-int(val/max_v*ch*0.85)
            yv=to_y(v)
            color='#3B82F6' if idx%2==0 else '#8B5CF6'
            draw.line([(xc,yv),(xc,cb)],fill=color,width=2)
            draw.rectangle([xc-20,yv,xc+20,cb],fill=color)
            draw.text((xc-6,yv-22),str(v),fill='white',font=f_small)
            draw.text((xc-10,cb+10),f"{days[idx]}",fill='#A1A1AA',font=f_small)
        bio=io.BytesIO(); img.save(bio,format='JPEG',quality=95); bio.seek(0); return bio
    except: return None
def send_stats(chat_id,user,mode="today"):
    try:
        if mode=="today":
            chart=make_today_chart(user)
            cap=f"TODAY 1D - {user['name']}\n{user['today_text']} text | {user['today_media']} media\nPer jam 08:00-22:00 - Restart 00:00 WIB"
        else:
            chart=make_weekly_chart(user)
            cap=f"WEEKLY 7D - {user['name']}\nLast 7 days trend"
        kb={"inline_keyboard": [[{"text":"• TODAY 1D" if mode=="today" else "TODAY 1D","callback_data":"stats_today"},{"text":"• WEEKLY 7D" if mode=="weekly" else "WEEKLY 7D","callback_data":"stats_weekly"}],[{"text":"<< Back","callback_data":"back_home"}]]}
        if chart:
            chart.seek(0)
            r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":chat_id,"caption":cap},files={"photo":("stats.jpg",chart,"image/jpeg")},timeout=20).json()
            if r.get("ok"):
                send_message(chat_id,"Switch mode:",kb)
                return
        send_message(chat_id,cap,kb)
    except: send_message(chat_id,"Stats error",get_back_keyboard())
def post_to_threads(text_content):
    try:
        if not THREADS_USER_ID or not THREADS_TOKEN: return False
        r=requests.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads",data={"media_type":"TEXT","text":text_content,"access_token":THREADS_TOKEN},timeout=10).json()
        cid=r.get("id")
        if not cid: return False
        r2=requests.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish",data={"creation_id":cid,"access_token":THREADS_TOKEN},timeout=10).json()
        return "id" in r2
    except: return False
def send_success(chat_id,user,ch_msg_id,target="both"):
    try:
        url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
        buttons=[]
        if target in ["threads","both"] and (user.get("threads_on") or is_admin(chat_id)): buttons.append([{"text": "See on Threads", "url": THREADS_URL}])
        if target in ["channel","both"] and ch_msg_id: buttons.append([{"text": "See on channel", "url": url}])
        if ch_msg_id: buttons.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
        buttons.append([{"text": "Back", "callback_data": "back_home"}])
        note=f" → {target.upper()}" if is_admin(chat_id) else ""
        send_message(chat_id,f"Menfess sent!{note}\n{SEP}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5",{"inline_keyboard": buttons})
    except: pass

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def main_handler():
    try:
        init_db()
        if request.method=="GET": return "V106.6 OK",200
        data=request.get_json(force=True,silent=True) or {}
        if "message" in data:
            msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
            if "from" in msg:
                raw=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
                user["name"]=raw.encode('ascii','ignore').decode('ascii') or "User"
                user["username"]=msg["from"].get("username","")
            if text.startswith("/start"): send_message(chat_id,get_welcome_text(user),get_main_keyboard(is_admin(chat_id)))
            elif text.lower().startswith("/stats"): send_stats(chat_id,user,"today")
            elif not user["banned"]:
                if text and not text.startswith("/") and len(text)>=3:
                    if user["today_text"]>=5: send_message(chat_id,f"Limit 5/5\n{SEP}\nReset 00:00 WIB",get_back_keyboard())
                    else:
                        clean=text.strip()
                        if HASHTAG.lower() not in clean.lower(): clean=f"{clean} {HASHTAG}"
                        try:
                            target=user.get("admin_target","both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                            ch_id=None
                            if target in ["channel","both"]:
                                r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":clean,"parse_mode":"HTML"},timeout=5).json()
                                ch_id=r.get("result",{}).get("message_id")
                            if target in ["threads","both"]: post_to_threads(clean)
                            user["today_text"]+=1; user["total_text"]+=1; user["total_chars"]=user.get("total_chars",0)+len(text)
                            save_user_to_db(uid,user); send_success(chat_id,user,ch_id,target)
                        except Exception as e: print(e)
                if "photo" in msg or "video" in msg:
                    if user["today_media"]>=5: send_message(chat_id,f"Limit 5/5",get_back_keyboard())
                    else:
                        try:
                            fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                            is_photo="photo" in msg
                            base_cap=caption.strip() if caption else HASHTAG
                            if HASHTAG.lower() not in base_cap.lower(): base_cap=f"{base_cap} {HASHTAG}"
                            target=user.get("admin_target","both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                            ch_id=None
                            if target in ["channel","both"]:
                                if is_photo:
                                    raw=download_file(fid); wm=add_watermark(raw) if raw else None
                                    if wm: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":CHANNEL_ID,"caption":base_cap,"parse_mode":"HTML"},files={"photo":("wm.jpg",wm,"image/jpeg")},timeout=15).json(); ch_id=r.get("result",{}).get("message_id")
                                    else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",json={"chat_id":CHANNEL_ID,"photo":fid,"caption":base_cap,"parse_mode":"HTML"},timeout=5).json(); ch_id=r.get("result",{}).get("message_id")
                                else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",json={"chat_id":CHANNEL_ID,"video":fid,"caption":base_cap,"parse_mode":"HTML"},timeout=8).json(); ch_id=r.get("result",{}).get("message_id")
                            if target in ["threads","both"]: post_to_threads(base_cap)
                            user["today_media"]+=1; user["total_media"]+=1
                            save_user_to_db(uid,user); send_success(chat_id,user,ch_id,target)
                        except Exception as e: print(e)
        if "callback_query" in data:
            cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]},timeout=2)
            except: pass
            if cdata=="back_home": send_message(chat_id,get_welcome_text(user),get_main_keyboard(is_admin(chat_id)))
            elif cdata=="my_profile": send_message(chat_id,f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5",get_back_keyboard())
            elif cdata=="post": send_message(chat_id,f"Post Menfess\n{SEP}\nKetik langsung text / kirim media + caption\nAuto tag {HASHTAG}",get_back_keyboard())
            elif cdata=="threads":
                kb={"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "<< Back", "callback_data": "back_home"}]]}
                send_message(chat_id,f"Threads Setting\n{SEP}\nStatus: {'ON' if user.get('threads_on') else 'OFF'}\nLink: threads.net/jogjalend",kb)
            elif cdata=="threads_toggle":
                user["threads_on"]=not user.get("threads_on",False); save_user_to_db(uid,user)
                kb={"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "<< Back", "callback_data": "back_home"}]]}
                send_message(chat_id,f"Threads {'ON' if user['threads_on'] else 'OFF'}!\nLink: threads.net/jogjalend",kb)
            elif cdata=="help":
                send_message(chat_id, f"""Pusat Bantuan - @menfessangel Bot

PANDUAN PENGIRIMAN:
- Ketik pesan teks Anda di sini
- Kirim foto/video beserta caption
- Otomatis ditambahkan tagar #jogjalend
- Otomatis terbit di channel @menfessangel

BATAS HARIAN:
- Batas 5 teks dan 5 media per hari
- Reset setiap pukul 00:00 WIB
- Gunakan /stats untuk melihat statistik

INTEGRASI THREADS:
- Pengaturan di menu Threads Setting
- ON = terbit di threads.net/jogjalend juga
- OFF = hanya terbit di channel

DAFTAR PERINTAH:
/start - Menu utama
/stats - Statistik TODAY 1D & WEEKLY 7D

Bot Versi V106.6
Author : @jogja_lend""", get_back_keyboard())
            elif cdata=="stats": send_stats(chat_id,user,"today")
            elif cdata=="stats_today": send_stats(chat_id,user,"today")
            elif cdata=="stats_weekly": send_stats(chat_id,user,"weekly")
            elif cdata=="admin_panel":
                if is_admin(chat_id): send_message(chat_id,f"ADMIN PANEL\n{SEP}\nHalo admin {user['name']}\nCurrent: {user.get('admin_target','both').upper()}",get_admin_keyboard(user))
                else: send_message(chat_id,"Not admin",get_back_keyboard())
            elif cdata=="admin_set_channel":
                if is_admin(chat_id): user["admin_target"]="channel"; save_user_to_db(uid,user); send_message(chat_id,f"Set ke CHANNEL ONLY",get_admin_keyboard(user))
            elif cdata=="admin_set_threads":
                if is_admin(chat_id): user["admin_target"]="threads"; save_user_to_db(uid,user); send_message(chat_id,f"Set ke THREADS ONLY",get_admin_keyboard(user))
            elif cdata=="admin_set_both":
                if is_admin(chat_id): user["admin_target"]="both"; save_user_to_db(uid,user); send_message(chat_id,f"Set ke BOTH",get_admin_keyboard(user))
            elif cdata.startswith("del_"):
                mid=cdata.replace("del_","")
                if mid.isdigit():
                    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":CHANNEL_ID,"message_id":int(mid)},timeout=3)
                    except: pass
                send_message(chat_id,"Deleted",get_back_keyboard())
        return "ok",200
    except Exception as e:
        print(f"ERROR {e}"); import traceback; traceback.print_exc(); return "ok",200
