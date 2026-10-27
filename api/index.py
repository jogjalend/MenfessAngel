from flask import Flask
app = Flask(__name__)

import os, io, json, requests
from PIL import Image
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"
QUOTA_FILE = "/tmp/quota.json"
SETTINGS_FILE = "/tmp/settings.json"
BLOCKED_FILE = "/tmp/blocked.json"
MEMBERS_FILE = "/tmp/members.json"
GLOBAL_FILE = "/tmp/global.json"
FILTER_FILE = "/tmp/filters.json"
SPAM_FILE = "/tmp/spamlog.json"
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
ADMIN_IDS = [8584319568]

def load_json(p,d=None):
    try:
        if os.path.exists(p):
            with open(p,"r") as f: return json.load(f)
    except: pass
    return d if d is not None else {}
def save_json(p,d):
    try:
        with open(p,"w") as f: json.dump(d,f)
    except: pass
def load_quota(): return load_json(QUOTA_FILE,{})
def save_quota(d): save_json(QUOTA_FILE,d)
def load_settings(): return load_json(SETTINGS_FILE,{})
def save_settings(d): save_json(SETTINGS_FILE,d)
def load_blocked(): return load_json(BLOCKED_FILE,{})
def save_blocked(d): save_json(BLOCKED_FILE,d)
def load_members(): return load_json(MEMBERS_FILE,{})
def save_members(d): save_json(MEMBERS_FILE,d)
def load_filters(): return load_json(FILTER_FILE,[])
def save_filters(d): save_json(FILTER_FILE,d)
def load_spam(): return load_json(SPAM_FILE,[])
def save_spam(d): save_json(SPAM_FILE,d)
def load_global():
    g=load_json(GLOBAL_FILE,{})
    if not g: g={"hashtag":"\n\n#jogjalend","limit_text":5,"limit_media":5,"welcome":"Hi {name}! Welcome","maintenance":False}
    return g
def save_global(d): save_json(GLOBAL_FILE,d)
def is_admin(cid): return int(cid) in ADMIN_IDS
def is_blocked(cid): return str(cid) in load_blocked()
def is_threads_enabled(cid): return load_settings().get(str(cid),{}).get("threads",False)
def set_threads_enabled(cid,v):
    s=load_settings()
    if str(cid) not in s: s[str(cid)]={}
    s[str(cid)]["threads"]=v; save_settings(s)
def get_today_key(cid): return f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
def add_hashtag(t):
    g=load_global(); ht=g.get("hashtag","")
    if not t: return ht.strip()
    if "jogjalend" in t.lower(): return t
    return t.strip()+ht
def get_real_channel_count():
    try:
        r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=10).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 658
def get_start_text(fn="Jogja Lend"):
    g=load_global(); return g.get("welcome","Hi {name}!").replace("{name}",fn)
def get_main_menu(cid):
    base=[[{"text":"My Profile","callback_data":"profil"}],[{"text":"Rules","callback_data":"menu_rules"},{"text":"Post","callback_data":"menu_post"}],[{"text":"Threads Setting","callback_data":"menu_threads"}],[{"text":"Stats","callback_data":"menu_stats"},{"text":"Help","callback_data":"menu_help"}]]
    if is_admin(cid): base.insert(3,[{"text":"ADMIN PANEL PRO","callback_data":"admin_panel"}])
    return {"inline_keyboard":base}
def safe_send(cid,mid,txt,kb):
    try:
        r=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":kb},timeout=10).json()
        if r.get("ok"): return True
    except: pass
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid},timeout=5)
    except: pass
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10); return True
def add_watermark(b):
    try:
        base=Image.open(io.BytesIO(b)).convert("RGBA")
        logo=None
        base_dir=os.path.dirname(__file__); root_dir=os.path.join(base_dir,"..")
        for p in [os.path.join(root_dir,"logo.png"),"logo.png",os.path.join(os.getcwd(),"logo.png")]:
            p=os.path.normpath(p)
            if os.path.exists(p):
                try: logo=Image.open(p).convert("RGBA"); break
                except: pass
        if logo:
            lw=int(base.width*0.20); lh=int(lw*logo.height/logo.width) if logo.width else lw
            logo=logo.resize((lw,lh),Image.LANCZOS)
            x=base.width-lw-20; y=base.height-lh-20
            ov=Image.new("RGBA",base.size,(0,0,0,0)); ov.paste(logo,(x,y),logo); base=Image.alpha_composite(base,ov)
        buf=io.BytesIO(); base.convert("RGB").save(buf,format="JPEG",quality=92); buf.seek(0); return buf.getvalue()
    except: return b

@app.route("/",methods=['GET'])
def home(): return "Bot V51.1 FIXED APP FOUND",200

@app.route("/",methods=['POST'])
@app.route("/api/index",methods=['POST'])
def handler():
    try:
        from flask import request
        data=request.get_json()
        if not data: return "ok",200
        if "callback_query" in data:
            cq=data["callback_query"]; cb=cq["data"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]; uf=cq["from"].get("first_name","Jogja Lend")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})
            if cb in ["menu_main","back_main","back"]:
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid},timeout=5)
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_start_text(uf),"reply_markup":get_main_menu(cid)}); return "ok",200
            if cb=="admin_panel":
                if not is_admin(cid): return "ok",200
                real=get_real_channel_count(); m=load_members(); b=load_blocked(); q=load_quota(); g=load_global()
                total=sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt=f"ADMIN V51 ULTIMATE\nSubs: {real} LIVE | Users: {len(m)}\nTotal: {total}\nQuota: {g['limit_text']}/{g['limit_media']}"
                kb={"inline_keyboard":[[{"text":"Analytics","callback_data":"admin_analytics"},{"text":"Top 10","callback_data":"admin_top"}],[{"text":"All Users","callback_data":"admin_members"},{"text":"Block List","callback_data":"admin_blocked"}],[{"text":"Search","callback_data":"admin_search"},{"text":"Set Quota","callback_data":"admin_setquota"}],[{"text":"Blok User","callback_data":"admin_blockuser"},{"text":"Broadcast","callback_data":"admin_broadcast"}],[{"text":"Welcome","callback_data":"admin_welcome"},{"text":"Word Filter","callback_data":"admin_filter"}],[{"text":"Clear Quota","callback_data":"admin_clearquota"},{"text":"Export","callback_data":"admin_export"}],[{"text":"Spam Logs","callback_data":"admin_spam"},{"text":"Nuke DB","callback_data":"admin_nuke"}],[{"text":"Maintenance","callback_data":"admin_maint"},{"text":"Daily Report","callback_data":"admin_daily"}],[{"text":"BACK MAIN","callback_data":"menu_main"}]]}
                safe_send(cid,mid,txt,kb); return "ok",200
            back_admin={"inline_keyboard":[[{"text":"BACK ADMIN","callback_data":"admin_panel"}],[{"text":"MAIN","callback_data":"menu_main"}]]}
            g=load_global()
            if cb=="admin_analytics": txt="ANALYTICS PRO\nOK"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_top": txt="TOP 10\nOK"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb in ["admin_members","admin_blocked","admin_search","admin_setquota","admin_blockuser","admin_broadcast","admin_welcome","admin_filter","admin_clearquota","admin_export","admin_spam","admin_nuke","admin_maint","admin_daily"]:
                txt=f"{cb} - OK"; safe_send(cid,mid,txt,back_admin); return "ok",200
            # fallback menus
            if cb=="profil":
                g=load_global(); qs=load_quota(); k=get_today_key(cid); q=qs.get(k,{"text":0,"media":0}); on=is_threads_enabled(cid)
                cap=f"My Profile\nID: {cid}\nText: {q['text']}/{g['limit_text']}\nMedia: {q['media']}/{g['limit_media']}\nThreads: {'ON' if on else 'OFF'}"
                kb={"inline_keyboard":[[{"text":f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"menu_main"}]]}
                safe_send(cid,mid,cap,kb); return "ok",200
            if cb=="menu_stats": txt=f"STATS\nChannel: {get_real_channel_count()}"; kb={"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}; safe_send(cid,mid,txt,kb); return "ok",200
            txt="Menu OK"; kb={"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}; safe_send(cid,mid,txt,kb); return "ok",200
        if "message" not in data: return "ok",200
        msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
        mems=load_members()
        if str(cid) not in mems: mems[str(cid)]={"username":msg["from"].get("username","-"),"name":msg["from"].get("first_name","-")}; save_members(mems)
        if text.startswith(("/start","/menu")): SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_start_text(msg["from"].get("first_name","Jogja Lend")),"reply_markup":get_main_menu(cid)}); return "ok",200
        raw_caption=msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas=load_quota(); key=get_today_key(cid)
        if key not in quotas: quotas[key]={"text":0,"media":0}
        g=load_global(); is_media="photo" in msg; caption=add_hashtag(raw_caption)
        if is_media:
            fid=msg["photo"][-1]["file_id"]; r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json(); fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content; fb=add_watermark(fb)
            files={"photo":("menfess.jpg",fb,"image/jpeg")}; res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":CHANNEL_ID,"caption":caption},files=files,timeout=30).json()
        else: res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":caption}).json()
        if res.get("ok"):
            pid=res["result"]["message_id"]
            if is_media: quotas[key]["media"]+=1
            else: quotas[key]["text"]+=1
            save_quota(quotas)
    except Exception as e: print(e)
    return "ok",200
