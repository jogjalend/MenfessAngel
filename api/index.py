from flask import Flask, request
import os, requests, io, psycopg2, random, re, traceback, copy
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
MAIN_THREAD_ID = os.getenv("MAIN_THREAD_ID")
LOG_CHANNEL = os.getenv("LOG_CHANNEL") or CHANNEL_ID
WIB = timezone(timedelta(hours=7))
SEP = "●--------------------------------------------------------●"
HASHTAG = "#jogjalend"

def to_fancy(text):
    pattern = r'@\w+|#\w+|/\w+|https?://\S+|threads\.net/\S+|t\.me/\S+'
    res_parts = []; last_idx = 0
    for m in re.finditer(pattern, text):
        before = text[last_idx:m.start()]
        conv = ""
        for c in before:
            if 'A' <= c <= 'Z': conv+=chr(0x1D5A0 + ord(c)-65)
            elif 'a' <= c <= 'z': conv+=chr(0x1D5BA + ord(c)-97)
            elif '0' <= c <= '9': conv+=chr(0x1D7E2 + ord(c)-48)
            else: conv+=c
        res_parts.append(conv); res_parts.append(m.group(0)); last_idx = m.end()
    tail = text[last_idx:]; conv = ""
    for c in tail:
        if 'A' <= c <= 'Z': conv+=chr(0x1D5A0 + ord(c)-65)
        elif 'a' <= c <= 'z': conv+=chr(0x1D5BA + ord(c)-97)
        elif '0' <= c <= '9': conv+=chr(0x1D7E2 + ord(c)-48)
        else: conv+=c
    res_parts.append(conv); return "".join(res_parts)
def F(t): return to_fancy(t)
USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0, "admin_target": "both", "warn": 0})

def get_db():
    if not DATABASE_URL: return None
    try: return psycopg2.connect(DATABASE_URL, connect_timeout=5)
    except: return None
def init_db():
    db=get_db()
    if not db: return
    try:
        cur=db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0, admin_target TEXT DEFAULT 'both', warn INT DEFAULT 0)")
        try: cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS admin_target TEXT DEFAULT 'both'")
        except: pass
        try: cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS warn INT DEFAULT 0")
        except: pass
        db.commit(); cur.close(); db.close()
    except: pass
def load_user_from_db(uid):
    db=get_db()
    if not db: return None
    try:
        cur=db.cursor()
        cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target, warn FROM menfess_users WHERE user_id=%s",(uid,))
        row=cur.fetchone(); cur.close(); db.close()
        if row: return {"name":row[0] or "", "username":row[1] or "", "threads_on":row[2] or False, "today_text":row[3] or 0, "today_media":row[4] or 0, "last_date":row[5] or "", "banned":row[6] or False, "total_text":row[7] or 0, "total_media":row[8] or 0, "total_chars":row[9] or 0, "admin_target":row[10] or "both", "warn":row[11] or 0}
    except: return None
    return None
def save_user_to_db(uid,user):
    db=get_db()
    if not db: return
    try:
        cur=db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target, warn) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s, admin_target=%s, warn=%s",(uid,user["name"],user["username"],user["threads_on"],user["today_text"],user["today_media"],user["last_date"],user["banned"],user["total_text"],user["total_media"],user.get("total_chars",0),user.get("admin_target","both"),user.get("warn",0),user["name"],user["username"],user["threads_on"],user["today_text"],user["today_media"],user["last_date"],user["banned"],user["total_text"],user["total_media"],user.get("total_chars",0),user.get("admin_target","both"),user.get("warn",0)))
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
    try:
        kb_fancy=None
        if kb and "inline_keyboard" in kb:
            kb_fancy=copy.deepcopy(kb)
            for row in kb_fancy["inline_keyboard"]:
                for btn in row:
                    if "text" in btn and "url" not in btn: btn["text"]=F(btn["text"])
        payload={"chat_id":chat_id,"text":F(text),"parse_mode":"HTML","disable_web_page_preview":True}
        if kb_fancy: payload["reply_markup"]=kb_fancy
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json=payload,timeout=10)
        if r.status_code==200: return True
    except: pass
    try:
        payload2={"chat_id":chat_id,"text":text,"disable_web_page_preview":True}
        if kb: payload2["reply_markup"]=kb
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json=payload2,timeout=10)
        return True
    except: return False

def report_error(chat_id, where, error):
    err_str=str(error)
    if "ReadTimeout" in err_str or "Timeout" in err_str or "timed out" in err_str:
        print(f"[IGNORED TIMEOUT in {where}]")
        return
    print(f"[ERROR in {where}] {error}\n{traceback.format_exc()}")
    if ADMIN_ID:
        try:
            err_text = f"🚨 BOT ERROR\n{SEP}\nWhere: {where}\nUser: {chat_id}\nError: {err_str[:300]}"
            for aid in ADMIN_ID.split(","):
                if aid.strip(): requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":aid.strip(),"text":err_text},timeout=5)
        except: pass

def get_welcome_text(user): return f"Hi !\n{SEP}\nPublish to @menfessangel\nTap Post!\n\nKuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5"
def get_back_keyboard(): return {"inline_keyboard": [[{"text": "Back", "callback_data": "back_home"}]]}
def get_main_keyboard(is_ad=False):
    kb={"inline_keyboard": [[{"text": "👤 My Profile", "callback_data": "my_profile"}, {"text": "💌 Post", "callback_data": "post"}], [{"text": "📧 Threads Setting", "callback_data": "threads"}], [{"text": "📈 Stats", "callback_data": "stats"}, {"text": "ℹ️ Info Bot", "callback_data": "info_bot"}]]}
    if is_ad: kb["inline_keyboard"].append([{"text": "ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb
def get_menu_1(): return {"inline_keyboard": [[{"text": "🔔 Tag", "callback_data": "lend_tag"}],[{"text": "📥 Mode Persetujuan", "callback_data": "lend_persetujuan"}],[{"text": "🗑️ Menghapus Pesan", "callback_data": "lend_hapus"}],[{"text": "🇮🇩 Lang", "callback_data": "lend_lang"}, {"text": "✅ Tutup", "callback_data": "close"}, {"text": "▶️ Lainnya", "callback_data": "lend_page2"}]]}
def get_menu_2(): return {"inline_keyboard": [[{"text": "📜 Peraturan", "callback_data": "lend_peraturan"}],[{"text": "⚠️ Peringatan", "callback_data": "lend_peringatan"}],[{"text": "🚫 Daftar Hitam", "callback_data": "lend_blacklist"}],[{"text": "🔐 Perizinan", "callback_data": "lend_izin"}],[{"text": "📋 Log Saluran", "callback_data": "lend_log"}],[{"text": "🎯 Manajemen Channel", "callback_data": "lend_channel"}],[{"text": "⬅️ Kembali", "callback_data": "lend_page1"}, {"text": "❌ Tutup", "callback_data": "close"}]]}
def get_channel_target_keyboard(user):
    target=user.get("admin_target","both")
    return {"inline_keyboard": [[{"text": f"📍 Target: {target.upper()}", "callback_data": "admin_noop"}],[{"text": f"{'✅ ' if target=='channel' else ''}📢 Channel Only", "callback_data": "admin_set_channel"}],[{"text": f"{'✅ ' if target=='threads' else ''}🧵 Threads Only", "callback_data": "admin_set_threads"}],[{"text": f"{'✅ ' if target=='both' else ''}🚀 Both (Channel+Threads)", "callback_data": "admin_set_both"}],[{"text": f"🆔 MAIN ID: {(MAIN_THREAD_ID[:12]+'...') if MAIN_THREAD_ID and len(MAIN_THREAD_ID)>12 else (MAIN_THREAD_ID or 'BELUM SET')}", "callback_data": "admin_noop"}],[{"text": "⬅️ Kembali", "callback_data": "lend_page2"}]]}

def find_logo():
    for p in ["logo.png","../logo.png",os.path.join(os.path.dirname(__file__),"../logo.png"),os.path.join(os.path.dirname(__file__),"logo.png")]:
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
        bio=io.BytesIO(); combined.save(bio,"JPEG",quality=85); bio.seek(0); return bio
    except: return None
def get_font(size,bold=False):
    try:
        p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(p): return ImageFont.truetype(p,size)
    except: pass
    return ImageFont.load_default()
def make_today_chart(user):
    try:
        W,H=720,400; img=Image.new('RGB',(W,H),'#0D0D0F'); draw=ImageDraw.Draw(img)
        f_title=get_font(22,True); f_small=get_font(14)
        draw.rectangle([0,0,W,60],fill='#161618')
        draw.text((20,12),f"TODAY 1D - {user['name'][:16]}",fill='white',font=f_title)
        hours=["08:00","12:00","16:00","20:00"]; total=user['today_text']+user['today_media']
        highs=[0]*4 if total==0 else [random.randint(0,2)+(total//4) for _ in hours]
        max_val=max(highs) if max(highs)>0 else 3
        ct,cb,cl,cr=80,370,50,700; ch=cb-ct
        slot_w=(cr-cl)//len(hours)
        for idx in range(len(hours)):
            xc=cl+idx*slot_w+slot_w//2; v=highs[idx]
            yh=cb-int(v/max_val*ch*0.8) if max_val>0 else cb
            color='#10B981' if idx%2==0 else '#EF4444'
            if total==0: color='#27272A'
            draw.rectangle([xc-15,yh,xc+15,cb],fill=color)
            draw.text((xc-15,cb+8),hours[idx],fill='#A1A1AA',font=f_small)
        bio=io.BytesIO(); img.save(bio,format='JPEG',quality=70); bio.seek(0); return bio
    except: return None
def make_weekly_chart(user):
    try:
        W,H=720,400; img=Image.new('RGB',(W,H),'#0D0D0F'); draw=ImageDraw.Draw(img)
        f_title=get_font(22,True); f_small=get_font(14)
        draw.rectangle([0,0,W,60],fill='#161618')
        draw.text((20,12),"WEEKLY 7D",fill='white',font=f_title)
        days=["22","23","24","25","26","27","28"]; vals=[random.randint(1,4) for _ in days]; max_v=max(vals)
        ct,cb,cl,cr=80,370,50,700; ch=cb-ct; slot_w=(cr-cl)//len(days)
        for idx in range(len(days)):
            xc=cl+idx*slot_w+slot_w//2; v=vals[idx]
            yv=cb-int(v/max_v*ch*0.8); draw.rectangle([xc-14,yv,xc+14,cb],fill='#3B82F6')
            draw.text((xc-8,cb+8),days[idx],fill='#A1A1AA',font=f_small)
        bio=io.BytesIO(); img.save(bio,format='JPEG',quality=70); bio.seek(0); return bio
    except: return None
def send_stats(chat_id,user,mode="today"):
    try:
        kb={"inline_keyboard": [[{"text":"TODAY 1D" if mode!="today" else "• TODAY 1D","callback_data":"stats_today"},{"text":"WEEKLY 7D" if mode!="weekly" else "• WEEKLY 7D","callback_data":"stats_weekly"}],[{"text":"Back","callback_data":"back_home"}]]}
        if mode=="today": chart=make_today_chart(user); cap=f"📊 TODAY 1D - {user['name']}\n{user['today_text']} text | {user['today_media']} media"
        else: chart=make_weekly_chart(user); cap=f"📈 WEEKLY 7D - {user['name']}\nLast 7 days"
        if chart:
            chart.seek(0)
            try:
                r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":chat_id,"caption":cap},files={"photo":("s.jpg",chart,"image/jpeg")},timeout=30).json()
                if r.get("ok"):
                    send_message(chat_id,"Switch mode:",kb)
                    return
            except: pass
        send_message(chat_id,cap,kb)
    except: pass
def post_to_threads(text_content):
    try:
        if not THREADS_USER_ID or not THREADS_TOKEN: return False
        data={"media_type":"TEXT","text":text_content[:450],"access_token":THREADS_TOKEN}
        if MAIN_THREAD_ID: data["reply_to_id"]=MAIN_THREAD_ID
        r=requests.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads",data=data,timeout=10).json()
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
        note=f" -> {target.upper()}" if is_admin(chat_id) else ""
        send_message(chat_id,f"Menfess sent!{note}\n{SEP}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5",{"inline_keyboard": buttons})
    except Exception as e: report_error(chat_id,"send_success",e)

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def main_handler():
    data={}; where="init"
    try:
        where="init_db"; init_db()
        if request.method=="GET": return "JogjaLend Bot V109.3 DELETE-REPLACE OK",200
        where="parse_json"; data=request.get_json(force=True,silent=True) or {}
        if "message" in data:
            msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id)
            where=f"get_user {uid}"; user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
            if "from" in msg:
                where="parse_from"
                raw=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
                user["name"]=raw.encode('ascii','ignore').decode('ascii') or "User"
                user["username"]=msg["from"].get("username","")
            where=f"cmd {text[:20]}"
            if text.startswith("/start"): 
                where="/start"; user["last_date"]=datetime.now(WIB).strftime("%Y-%m-%d"); save_user_to_db(uid,user)
                send_message(chat_id,get_welcome_text(user),get_main_keyboard(is_admin(chat_id)))
            elif text.startswith("/newpost"): send_message(chat_id,f"Post Menfess\n{SEP}\nKetik langsung text / kirim media + caption\nAuto tag {HASHTAG}",get_back_keyboard())
            elif text.startswith("/profile"): send_message(chat_id,f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5",get_back_keyboard())
            elif text.lower().startswith("/stats"): send_stats(chat_id,user,"today")
            elif not user["banned"]:
                where="handle_text_post"
                if text and not text.startswith("/") and len(text)>=3:
                    if user["today_text"]>=5: send_message(chat_id,f"Limit 5/5\n{SEP}\nReset 00:00 WIB",get_back_keyboard())
                    else:
                        clean=text.strip()
                        if HASHTAG.lower() not in clean.lower(): clean=f"{clean} {HASHTAG}"
                        target=user.get("admin_target","both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                        ch_id=None
                        if target in ["channel","both"]:
                            r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":clean,"parse_mode":"HTML"},timeout=5).json()
                            ch_id=r.get("result",{}).get("message_id")
                        if target in ["threads","both"]: post_to_threads(clean)
                        user["today_text"]+=1; user["total_text"]+=1; user["total_chars"]=user.get("total_chars",0)+len(text)
                        save_user_to_db(uid,user); send_success(chat_id,user,ch_id,target)
                where="handle_media_post"
                if "photo" in msg or "video" in msg:
                    if user["today_media"]>=5: send_message(chat_id,f"Limit 5/5",get_back_keyboard())
                    else:
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
        if "callback_query" in data:
            cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); cdata=cq["data"]; msg_id=cq["message"]["message_id"]
            where=f"callback {cdata}"
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]},timeout=2)
            except: pass
            # DELETE TAB LAMA - MUNCUL TAB BARU (NO TYPING)
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":chat_id,"message_id":msg_id},timeout=2)
            except: pass
            user=get_user(uid)

            if cdata in ["stats","stats_today","stats_weekly"]:
                mode = "weekly" if cdata=="stats_weekly" else "today"
                send_stats(chat_id,user,mode)
            elif cdata=="back_home": send_message(chat_id,get_welcome_text(user),get_main_keyboard(is_admin(chat_id)))
            elif cdata=="lend_page1": send_message(chat_id,"⚙️ Pilih salah satu pengaturan yang ingin anda ubah.",get_menu_1())
            elif cdata=="lend_page2": send_message(chat_id,"⚙️ Pilih salah satu pengaturan yang ingin anda ubah.",get_menu_2())
            elif cdata=="my_profile": send_message(chat_id,f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5",get_back_keyboard())
            elif cdata=="post": send_message(chat_id,f"Post Menfess\n{SEP}\nKetik langsung text / kirim media + caption\nAuto tag {HASHTAG}",get_back_keyboard())
            elif cdata=="threads":
                kb={"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "Back", "callback_data": "back_home"}]]}
                send_message(chat_id,f"Threads Setting\n{SEP}\nStatus: {'ON' if user.get('threads_on') else 'OFF'}\nLink: threads.net/jogjalend",kb)
            elif cdata=="threads_toggle":
                user["threads_on"]=not user.get("threads_on",False); save_user_to_db(uid,user)
                kb={"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "Back", "callback_data": "back_home"}]]}
                send_message(chat_id,f"Threads {'ON' if user['threads_on'] else 'OFF'}!\nLink: threads.net/jogjalend",kb)
            elif cdata=="info_bot":
                info_text = f"🔧 Bantuan\n\nUntuk pertanyaan tentang penggunaan bot, saran untuk fitur baru atau laporan bug Anda dapat menulis ke @joglendsupportBot.\n\nJogjaLend Bot adalah bot yang dikembangkan oleh tim @jogja_lend."
                send_message(chat_id, info_text, get_back_keyboard())
            elif cdata=="admin_panel": 
                if is_admin(chat_id): send_message(chat_id,"⚙️ Pilih salah satu pengaturan yang ingin anda ubah.",get_menu_1())
                else: send_message(chat_id,"Not admin",get_back_keyboard())
            elif cdata=="lend_tag": send_message(chat_id,f"🔔 Tag\n{SEP}\nAtur hashtag otomatis, saat ini: {HASHTAG}",get_menu_1())
            elif cdata=="lend_peraturan": send_message(chat_id,f"📜 Peraturan\n{SEP}\n/setperaturan <teks> untuk set peraturan",get_menu_2())
            elif cdata=="lend_peringatan": send_message(chat_id,f"⚠️ Peringatan\n{SEP}\n/warn untuk kasih peringatan, 3x auto ban",get_menu_2())
            elif cdata=="lend_blacklist": send_message(chat_id,f"🚫 Daftar Hitam\n{SEP}\n/ban untuk blokir user\n/unban untuk lepas",get_menu_2())
            elif cdata=="lend_persetujuan": send_message(chat_id,f"📥 Mode Persetujuan\n{SEP}\nJika ON, semua menfess masuk ke log dulu",get_menu_1())
            elif cdata=="lend_hapus": send_message(chat_id,f"🗑️ Menghapus Pesan\n{SEP}\n/del reply pesan untuk hapus",get_menu_1())
            elif cdata=="lend_izin": send_message(chat_id,f"🔐 Perizinan\n{SEP}\nAtur siapa boleh post media/link",get_menu_2())
            elif cdata=="lend_log": send_message(chat_id,f"📋 Log Saluran\n{SEP}\nLog ke: {LOG_CHANNEL}",get_menu_2())
            elif cdata=="lend_lang": send_message(chat_id,f"🇮🇩 Lang\n{SEP}\nBahasa Bot: Indonesia",get_menu_1())
            elif cdata=="lend_channel": 
                if is_admin(chat_id): send_message(chat_id,f"🎯 Manajemen Channel\n{SEP}\nPilih target posting + 1 thread\nCurrent: {user.get('admin_target','both').upper()}\nMAIN_THREAD_ID: {MAIN_THREAD_ID or 'belum diset'}", get_channel_target_keyboard(user))
                else: send_message(chat_id,"Not admin",get_back_keyboard())
            elif cdata=="admin_set_channel":
                if is_admin(chat_id): user["admin_target"]="channel"; save_user_to_db(uid,user); send_message(chat_id,f"Set ke CHANNEL ONLY\n{SEP}\nMenfess cuma ke {CHANNEL_ID}", get_channel_target_keyboard(user))
            elif cdata=="admin_set_threads":
                if is_admin(chat_id): user["admin_target"]="threads"; save_user_to_db(uid,user); send_message(chat_id,f"Set ke THREADS ONLY\n{SEP}\nMenfess cuma ke Threads", get_channel_target_keyboard(user))
            elif cdata=="admin_set_both":
                if is_admin(chat_id): user["admin_target"]="both"; save_user_to_db(uid,user); send_message(chat_id,f"Set ke BOTH\n{SEP}\nMenfess ke Channel + Threads", get_channel_target_keyboard(user))
            elif cdata=="admin_noop": pass
            elif cdata=="close":
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":chat_id,"message_id":msg_id},timeout=3)
                except: pass
            elif cdata.startswith("del_"):
                mid=cdata.replace("del_","")
                if mid.isdigit():
                    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":CHANNEL_ID,"message_id":int(mid)},timeout=3)
                    except: pass
                send_message(chat_id,"Deleted",get_back_keyboard())
        return "ok",200
    except Exception as e:
        try:
            cid=0
            try:
                if "message" in data and "chat" in data["message"]: cid=data["message"]["chat"]["id"]
                elif "callback_query" in data: cid=data["callback_query"]["message"]["chat"]["id"]
            except: pass
            if cid!=0: report_error(cid, where, e)
            else: print(f"[CRITICAL {where}] {e}\n{traceback.format_exc()}")
        except: print(f"[FATAL {where}] {e}\n{traceback.format_exc()}")
        return "ok",200
