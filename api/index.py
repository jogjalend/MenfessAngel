from flask import Flask, request
import os, requests, io, psycopg2, random
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
DATABASE_URL = os.getenv("DATABASE_URL")
THREADS_URL = os.getenv("THREADS") or os.getenv("THREADS_URL") or "https://www.threads.net/@jogjalend"
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
WIB = timezone(timedelta(hours=7))
SEP = "-------------------------------------------"
HASHTAG = "#jogjalend"

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0})

def get_db():
    if not DATABASE_URL: return None
    try: return psycopg2.connect(DATABASE_URL, connect_timeout=5)
    except: return None

def init_db():
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0)")
        db.commit(); cur.close(); db.close()
    except Exception as e: print(f"db init {e}")

def load_user_from_db(uid):
    db = get_db()
    if not db: return None
    try:
        cur = db.cursor()
        cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars FROM menfess_users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close(); db.close()
        if row: return {"name":row[0] or "", "username":row[1] or "", "threads_on":row[2] or False, "today_text":row[3] or 0, "today_media":row[4] or 0, "last_date":row[5] or "", "banned":row[6] or False, "total_text":row[7] or 0, "total_media":row[8] or 0, "total_chars":row[9] or 0}
    except: return None
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s",
                    (uid, user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars",0),
                     user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars",0)))
        db.commit(); cur.close(); db.close()
    except Exception as e: print(f"save {e}")

def get_user(uid):
    u = USERS[uid]
    if u["last_date"] == "" and DATABASE_URL:
        d = load_user_from_db(uid)
        if d: USERS[uid]=d; u=USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today: u["today_text"]=0; u["today_media"]=0; u["last_date"]=today; save_user_to_db(uid, u)
    return u

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send(chat_id, text, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)
    except Exception as e: print(f"send {e}")

def welcome_text(user): return f"Hi {user['name']}!\n{SEP}\nPublish to @menfessangel\nTap Post!\n\nKuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5"

def back_kb(): return {"inline_keyboard": [[{"text": "<< Back", "callback_data": "back_home"}]]}
def main_kb(is_ad=False):
    kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
    if is_ad: kb["inline_keyboard"].append([{"text": "ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb

def find_logo():
    for p in ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "../logo.png")]:
        if os.path.exists(p): return p
    return None

def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=5).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=8).content
    except: return None

def add_watermark(photo_bytes):
    try:
        lp = find_logo()
        if not lp: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(lp).convert("RGBA")
        w,h = base.size; sz = int(w*0.13); logo = logo.resize((sz,sz), Image.LANCZOS)
        overlay = Image.new("RGBA", base.size, (0,0,0,0)); overlay.paste(logo, (12, 12), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO(); combined.save(bio, "JPEG", quality=92); bio.seek(0); return bio
    except: return None

def get_font(size, bold=False):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in paths:
        try:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

def make_intraday_chart(user):
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
        if total==0:
            highs=[0]*8
        else:
            base=[random.randint(0,2) for _ in hours]
            s=sum(base) or 1
            base=[int(b/s*total) for b in base]
            highs=[max(0,b+random.randint(0,1)) for b in base]
        max_val=max(highs) if highs and max(highs)>0 else 3
        max_val=max(max_val,3)
        chart_top,chart_bottom,chart_left,chart_right=120,580,70,1050
        chart_h=chart_bottom-chart_top
        for i in range(5):
            y=chart_top+i*chart_h//4
            draw.line([(chart_left,y),(chart_right,y)],fill='#1F1F23',width=1)
            val=max_val - i*max_val//4
            draw.text((10,y-8),str(val),fill='#71717A',font=f_small)
        slot_w=(chart_right-chart_left)//len(hours)
        for idx in range(len(hours)):
            x_center=chart_left+idx*slot_w+slot_w//2
            v=highs[idx]
            def to_y(val): return chart_bottom-int(val/max_val*chart_h*0.9)
            y_h=to_y(v)
            y_l=chart_bottom
            color='#10B981' if idx%2==0 else '#EF4444'
            if total==0: color='#27272A'
            draw.line([(x_center,y_h),(x_center,y_l)],fill=color,width=2)
            top_h = y_h
            bottom_h = chart_bottom if v==0 else y_h+max(18, (chart_bottom-y_h)//3)
            draw.rectangle([x_center-18,top_h,x_center+18,bottom_h],fill=color)
            draw.text((x_center-22,chart_bottom+10),hours[idx],fill='#A1A1AA',font=f_small)
            if v>0: draw.text((x_center-4,y_h-18),str(v),fill='#A1A1AA',font=f_small)
        bio=io.BytesIO(); img.save(bio,format='JPEG',quality=95); bio.seek(0); return bio
    except Exception as e:
        print(f"candle {e}"); import traceback; traceback.print_exc(); return None

def make_overall_chart(user):
    try:
        W,H=1080,650
        img=Image.new('RGB',(W,H),'#0D0D0F')
        draw=ImageDraw.Draw(img)
        f_title=get_font(32,True); f_label=get_font(20); f_small=get_font(18); f_num=get_font(56,True)
        draw.rectangle([0,0,W,85],fill='#161618')
        draw.text((30,18),"OVERALL - All Time",fill='white',font=f_title)
        draw.text((30,55),f"{user['name'][:20]} - {user['total_text']+user['total_media']} posts",fill='#71717A',font=f_small)
        boxes=[
            (30,110,520,300,"TOTAL TEXT",str(user['total_text']),f"{user.get('total_chars',0)} chars",'#8B5CF6'),
            (560,110,1050,300,"TOTAL MEDIA",str(user['total_media']),"All time",'#F59E0B'),
            (30,330,520,620,"TODAY",str(user['today_text']+user['today_media']),f"{user['today_text']}T {user['today_media']}M /10",'#3B82F6'),
            (560,330,1050,620,"AVG / DAY",str((user['total_text']+user['total_media'])//7 if user['total_text']>0 else 0),"Est per day",'#10B981'),
        ]
        for x1,y1,x2,y2,label,num,small,color in boxes:
            draw.rectangle([x1,y1,x2,y2],fill='#1C1C1F',outline='#27272A',width=2)
            draw.rectangle([x1,y1,x2,y1+6],fill=color)
            draw.text((x1+25,y1+20),label,fill='#A1A1AA',font=f_label)
            draw.text((x1+25,y1+55),num,fill='white',font=f_num)
            draw.text((x1+25,y1+155),small,fill=color,font=f_small)
        bio=io.BytesIO(); img.save(bio,format='JPEG',quality=95); bio.seek(0); return bio
    except Exception as e: print(e); return None

def make_weekly_chart(user):
    try:
        W,H=1080,550
        img=Image.new('RGB',(W,H),'#0D0D0F')
        draw=ImageDraw.Draw(img)
        f_title=get_font(30,True); f_small=get_font(18)
        draw.rectangle([0,0,W,80],fill='#161618')
        draw.text((30,18),"WEEKLY 7D",fill='white',font=f_title)
        days=["22","23","24","25","26","27","28"]
        vals=[random.randint(0,4) for _ in days]
        if user['total_text']>0:
            vals=[min(5, max(0, user['total_text']//7 + random.randint(-1,2))) for _ in days]
        max_v=max(vals) if max(vals)>0 else 5
        max_v=max(max_v,1)
        chart_top,chart_bottom,chart_left,chart_right=110,480,70,1050
        chart_h=chart_bottom-chart_top
        for i in range(5):
            y=chart_top+i*chart_h//4
            draw.line([(chart_left,y),(chart_right,y)],fill='#1F1F23',width=1)
        slot_w=(chart_right-chart_left)//len(days)
        for idx,d in enumerate(days):
            x_center=chart_left+idx*slot_w+slot_w//2
            v=vals[idx]
            def to_y(val): return chart_bottom-int(val/max_v*chart_h*0.85)
            y_v=to_y(v)
            draw.rectangle([x_center-22,y_v,x_center+22,chart_bottom],fill='#3B82F6')
            draw.text((x_center-8,y_v-20),str(v),fill='white',font=f_small)
            draw.text((x_center-10,chart_bottom+10),d,fill='#A1A1AA',font=f_small)
        bio=io.BytesIO(); img.save(bio,format='JPEG',quality=95); bio.seek(0); return bio
    except Exception as e: print(e); return None

def send_stats(chat_id, user, mode="today"):
    try:
        if mode=="today": chart=make_intraday_chart(user); cap=f"TODAY 1D - {user['name']}\n{user['today_text']} text | {user['today_media']} media today\nChart per jam 08:00-22:00 - Restart tiap hari"
        elif mode=="overall": chart=make_overall_chart(user); cap=f"OVERALL - {user['name']}\nTotal {user['total_text']} text {user['total_media']} media\nKinerja keseluruhan (gak restart)"
        else: chart=make_weekly_chart(user); cap=f"WEEKLY 7D - {user['name']}\nLast 7 days trend"
        kb={"inline_keyboard": [[{"text":"• TODAY" if mode=="today" else "TODAY 1D","callback_data":"stats_today"},{"text":"• OVERALL" if mode=="overall" else "OVERALL","callback_data":"stats_overall"},{"text":"• WEEKLY" if mode=="weekly" else "WEEKLY 7D","callback_data":"stats_weekly"}],[{"text":"<< Back","callback_data":"back_home"}]]}
        if chart:
            chart.seek(0)
            r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":chat_id,"caption":cap},files={"photo":("stats.jpg",chart,"image/jpeg")},timeout=20).json()
            print(f"sendPhoto {r}")
            if r.get("ok"):
                send(chat_id,"Pilih mode:",kb)
                return
        send(chat_id,cap,kb)
    except Exception as e:
        print(f"send_stats {e}"); import traceback; traceback.print_exc()
        send(chat_id,"Stats error",back_kb())

def post_to_threads_auto(text_content):
    try:
        if not THREADS_USER_ID or not THREADS_TOKEN: return False
        url_create = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        r = requests.post(url_create, data={"media_type": "TEXT", "text": text_content, "access_token": THREADS_TOKEN}, timeout=10).json()
        creation_id = r.get("id")
        if not creation_id: return False
        url_pub = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
        r2 = requests.post(url_pub, data={"creation_id": creation_id, "access_token": THREADS_TOKEN}, timeout=10).json()
        return "id" in r2
    except: return False

def send_success(chat_id, user, ch_msg_id):
    try:
        url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
        buttons=[]
        if user.get("threads_on"): buttons.append([{"text": "See on Threads", "url": THREADS_URL}])
        buttons.append([{"text": "See on channel", "url": url}])
        buttons.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
        buttons.append([{"text": "Back", "callback_data": "back_home"}])
        send(chat_id, f"Menfess sent!\n{SEP}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5", {"inline_keyboard": buttons})
    except: pass

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    try:
        init_db()
        if request.method=="GET": return f"V104 TODAY+OVERALL OK - {THREADS_URL}",200
        data = request.get_json(force=True, silent=True) or {}
        if "message" in data:
            msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
            if "from" in msg:
                raw = (msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
                user["name"] = raw.encode('ascii','ignore').decode('ascii') or "User"
                user["username"]=msg["from"].get("username","")
            if text.startswith("/start"): send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
            elif text.lower().startswith("/stats"): send_stats(chat_id, user, "today")
            elif text.lower().startswith("/profile") or text.lower().startswith("/me"): send(chat_id, f"My Profile\n{SEP}\nName: {user['name']}\nMedia: {user['today_media']}/5\nText: {user['today_text']}/5", back_kb())
            elif not user["banned"]:
                if text and not text.startswith("/") and len(text)>=3:
                    if user["today_text"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                    else:
                        clean=text.strip()
                        if HASHTAG.lower() not in clean.lower(): clean=f"{clean} {HASHTAG}"
                        try:
                            r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=5).json()
                            ch_id=r.get("result",{}).get("message_id")
                            if user.get("threads_on"): post_to_threads_auto(clean)
                            user["today_text"]+=1; user["total_text"]+=1; user["total_chars"]=user.get("total_chars",0)+len(text)
                            save_user_to_db(uid, user); send_success(chat_id, user, ch_id)
                        except Exception as e: print(e)
                if "photo" in msg or "video" in msg:
                    if user["today_media"]>=5: send(chat_id, f"Limit 5/5", back_kb())
                    else:
                        try:
                            fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                            is_photo="photo" in msg
                            base_cap=caption.strip() if caption else HASHTAG
                            if HASHTAG.lower() not in base_cap.lower(): base_cap=f"{base_cap} {HASHTAG}"
                            ch_id=None
                            if is_photo:
                                raw=download_file(fid); wm=add_watermark(raw) if raw else None
                                if wm: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": ("wm.jpg", wm, "image/jpeg")}, timeout=15).json(); ch_id=r.get("result",{}).get("message_id")
                                else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id=r.get("result",{}).get("message_id")
                            else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=8).json(); ch_id=r.get("result",{}).get("message_id")
                            if user.get("threads_on"): post_to_threads_auto(base_cap)
                            user["today_media"]+=1; user["total_media"]+=1
                            save_user_to_db(uid, user); send_success(chat_id, user, ch_id)
                        except Exception as e: print(e)
        if "callback_query" in data:
            cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
            except: pass
            if cdata=="stats": send_stats(chat_id, user, "today")
            elif cdata=="stats_today": send_stats(chat_id, user, "today")
            elif cdata=="stats_overall": send_stats(chat_id, user, "overall")
            elif cdata=="stats_weekly": send_stats(chat_id, user, "weekly")
            elif cdata=="back_home": send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
            elif cdata.startswith("del_"):
                mid=cdata.replace("del_","")
                if mid.isdigit():
                    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=3)
                    except: pass
                send(chat_id, "Deleted", back_kb())
            elif cdata in ["my_profile","post","threads","help"]:
                send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
        return "ok",200
    except Exception as e:
        print(f"GLOBAL {e}"); import traceback; traceback.print_exc(); return "ok",200