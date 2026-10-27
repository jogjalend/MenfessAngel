import os, io, json, requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta
app = Flask(__name__)
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
    if not g: g={"hashtag":"\n\n#jogjalend","limit_text":5,"limit_media":5,"welcome":"Hi {name}! Welcome to Menfess","maintenance":False}
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
def home(): return "Bot V51.1 FIXED",200
@app.route("/",methods=['POST'])
@app.route("/api/index.py",methods=['POST'])
def handler():
    try:
        data=request.get_json()
        if not data: return "ok",200
        if "callback_query" in data:
            cq=data["callback_query"]; cb=cq["data"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]; uf=cq["from"].get("first_name","Jogja Lend")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})
            if cb in ["menu_main","back_main","back"]:
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid},timeout=5)
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_start_text(uf),"reply_markup":get_main_menu(cid)}); return "ok",200
            if cb=="profil":
                g=load_global(); qs=load_quota(); k=get_today_key(cid); q=qs.get(k,{"text":0,"media":0}); on=is_threads_enabled(cid); mems=load_members(); inf=mems.get(str(cid),{})
                cap=f"My Profile\nName: {inf.get('name',uf)}\nID: {cid}\nUsername: @{inf.get('username','-')}\nText: {q['text']}/{g['limit_text']}\nMedia: {q['media']}/{g['limit_media']}\nThreads: {'ON' if on else 'OFF'}"
                kb={"inline_keyboard":[[{"text":f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"menu_main"}]]}
                safe_send(cid,mid,cap,kb); return "ok",200
            if cb=="toggle_threads": set_threads_enabled(cid,not is_threads_enabled(cid)); 
            if cb=="toggle_threads":
                g=load_global(); qs=load_quota(); k=get_today_key(cid); q=qs.get(k,{"text":0,"media":0}); on=is_threads_enabled(cid)
                cap=f"My Profile\nThreads: {'ON' if on else 'OFF'}\nText: {q['text']}/{g['limit_text']}\nMedia: {q['media']}/{g['limit_media']}"
                kb={"inline_keyboard":[[{"text":f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"menu_main"}]]}
                safe_send(cid,mid,cap,kb); return "ok",200
            if cb=="menu_threads":
                on=is_threads_enabled(cid); txt=f"Threads Setting\nStatus: {'ON' if on else 'OFF'}"; kb={"inline_keyboard":[[{"text":f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"menu_main"}]]}; safe_send(cid,mid,txt,kb); return "ok",200
            if cb=="menu_rules": txt="Rules\n1. No Spam\n2. No SARA\n3. No Doxxing\n4. No Promosi Ilegal\n5. No Porn"; kb={"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}; safe_send(cid,mid,txt,kb); return "ok",200
            if cb=="menu_post": txt="Post Menfess\nJust send text or photo!\nAuto watermark logo + #jogjalend"; kb={"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}; safe_send(cid,mid,txt,kb); return "ok",200
            if cb=="menu_help": txt="Help\n/start - Menu\nKirim text/photo - Post\nQuota 5/5 per hari"; kb={"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}; safe_send(cid,mid,txt,kb); return "ok",200
            if cb=="menu_stats":
                real=get_real_channel_count(); m=load_members(); b=load_blocked(); q=load_quota(); total=sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt=f"STATS\nChannel Subs: {real}\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}"; kb={"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}; safe_send(cid,mid,txt,kb); return "ok",200
            if cb=="admin_panel":
                if not is_admin(cid): return "ok",200
                real=get_real_channel_count(); m=load_members(); b=load_blocked(); q=load_quota(); g=load_global(); filt=load_filters(); spam=load_spam()
                total=sum(v.get("text",0)+v.get("media",0) for v in q.values()); today=datetime.now(WIB).strftime('%Y-%m-%d'); today_posts=sum(v.get("text",0)+v.get("media",0) for k,v in q.items() if today in k)
                txt=f"ADMIN V51 ULTIMATE\nSubs: {real} LIVE | Users: {len(m)}\nTotal: {total} | Today: {today_posts}\nBlock: {len(b)} | Filter: {len(filt)} | Spam: {len(spam)}\nQuota: {g['limit_text']}/{g['limit_media']} | {datetime.now(WIB).strftime('%d-%m %H:%M')} WIB"
                kb={"inline_keyboard":[
                    [{"text":"Analytics","callback_data":"admin_analytics"},{"text":"Top 10","callback_data":"admin_top"}],
                    [{"text":"All Users","callback_data":"admin_members"},{"text":"Block List","callback_data":"admin_blocked"}],
                    [{"text":"Search","callback_data":"admin_search"},{"text":"Set Quota","callback_data":"admin_setquota"}],
                    [{"text":"Blok User","callback_data":"admin_blockuser"},{"text":"Broadcast","callback_data":"admin_broadcast"}],
                    [{"text":"Welcome","callback_data":"admin_welcome"},{"text":"Word Filter","callback_data":"admin_filter"}],
                    [{"text":"Clear Quota","callback_data":"admin_clearquota"},{"text":"Export","callback_data":"admin_export"}],
                    [{"text":"Spam Logs","callback_data":"admin_spam"},{"text":"Nuke DB","callback_data":"admin_nuke"}],
                    [{"text":"Maintenance","callback_data":"admin_maint"},{"text":"Daily Report","callback_data":"admin_daily"}],
                    [{"text":"BACK MAIN","callback_data":"menu_main"}]
                ]}; safe_send(cid,mid,txt,kb); return "ok",200
            back_admin={"inline_keyboard":[[{"text":"BACK ADMIN","callback_data":"admin_panel"}],[{"text":"MAIN","callback_data":"menu_main"}]]}
            g=load_global()
            if cb=="admin_analytics":
                q=load_quota(); m=load_members(); today=datetime.now(WIB).strftime('%Y-%m-%d')
                today_c=sum(v.get("text",0)+v.get("media",0) for k,v in q.items() if today in k)
                txt=f"ANALYTICS PRO\nToday: {today_c} post\nTotal: {sum(v.get('text',0)+v.get('media',0) for v in q.values())}\nUsers: {len(m)}"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_top":
                q=load_quota(); top=sorted(q.items(),key=lambda x:x[1].get('text',0)+x[1].get('media',0),reverse=True)[:10]
                txt="TOP 10 POSTERS\n"+"\n".join([f"{i+1}. {k.split('_')[0]} = {v.get('text',0)+v.get('media',0)}" for i,(k,v) in enumerate(top)]) or "Belum ada"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_members": m=load_members(); txt="All Users (20)\n"+"\n".join([f"{v.get('name','-')} {k} @{v.get('username','-')}" for k,v in list(m.items())[-20:]]) or "0"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_blocked": b=load_blocked(); txt=f"Blocked {len(b)}\n"+"\n".join(list(b.keys())[:20]) or "Kosong"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_search": txt="Search\nKetik:\n/search 123456\n/search @username"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_setquota": txt=f"Set Quota Now {g['limit_text']}/{g['limit_media']}\nKetik:\n/setquota 5 5"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_blockuser": txt="Blok User\nKetik:\n/block @username\n/unblock @username"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_broadcast": txt="Broadcast PRO\nKetik:\n/broadcast Pesan"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_welcome": txt=f"Welcome Msg\nNow:\n{g.get('welcome','')}\nKetik:\n/setwelcome Hi {{name}}!"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_filter": filt=load_filters(); txt=f"WORD FILTER ({len(filt)})\n"+"\n".join(filt) or "Kosong\n/addfilter kata\n/delfilter kata"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_clearquota": save_quota({}); txt="QUOTA CLEARED!"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_export": m=load_members(); txt=f"EXPORT Users: {len(m)}\nKetik /export"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_spam": spam=load_spam(); txt=f"SPAM LOGS ({len(spam)})\n"+"\n".join(spam[-15:]) or "Bersih"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_nuke": txt="NUKE DB\nKetik:\n/nuke confirm"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_maint":
                g=load_global(); g["maintenance"]=not g.get("maintenance",False); save_global(g)
                txt=f"MAINTENANCE: {'ON' if g['maintenance'] else 'OFF'}"; safe_send(cid,mid,txt,back_admin); return "ok",200
            elif cb=="admin_daily":
                q=load_quota(); today=datetime.now(WIB).strftime('%Y-%m-%d'); m=load_members()
                today_posts=sum(v.get("text",0)+v.get("media",0) for k,v in q.items() if today in k)
                txt=f"DAILY REPORT {today}\nPosts Today: {today_posts}\nTotal Users: {len(m)}\nChannel: {get_real_channel_count()} subs"; safe_send(cid,mid,txt,back_admin); return "ok",200

        if "message" not in data: return "ok",200
        msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
        mems=load_members()
        if str(cid) not in mems:
            mems[str(cid)]={"username":msg["from"].get("username","-"),"name":msg["from"].get("first_name","-"),"joined":datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}; save_members(mems)
        g=load_global()
        if g.get("maintenance") and not is_admin(cid) and not text.startswith("/start"):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Bot maintenance, coba lagi nanti!"}); return "ok",200
        if is_blocked(cid) and not is_admin(cid): SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"You are blocked"}); return "ok",200
        if is_admin(cid) and text.startswith("/"):
            if text.startswith("/block "):
                target=text.split()[1].replace("@",""); blocked=load_blocked(); members=load_members()
                if not target.isdigit():
                    for uid,info in members.items():
                        if info.get("username","").lower()==target.lower() or target.lower() in info.get("username","").lower():
                            blocked[uid]=f"@{info.get('username','-')}"; save_blocked(blocked); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Blocked {uid}"}); return "ok",200
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"@{target} not found"}); return "ok",200
                else: blocked[target]="ID"; save_blocked(blocked); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{target} blocked"}); return "ok",200
            if text.startswith("/unblock "):
                target=text.split()[1].replace("@",""); blocked=load_blocked(); members=load_members()
                if not target.isdigit():
                    rm=[]
                    for uid,info in members.items():
                        if target.lower() in info.get("username","").lower(): rm.append(uid)
                    for uid in rm: blocked.pop(uid,None)
                    save_blocked(blocked); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Unblocked {len(rm)}"}); return "ok",200
                else: blocked.pop(target,None); save_blocked(blocked); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{target} unblocked"}); return "ok",200
            if text.startswith("/setquota "):
                try: p=text.split(); g=load_global(); g["limit_text"]=int(p[1]); g["limit_media"]=int(p[2]); save_global(g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Quota {p[1]}/{p[2]}"}); return "ok",200
                except: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Format: /setquota 5 5"}); return "ok",200
            if text.startswith("/setwelcome "): w=text.replace("/setwelcome ","").strip(); g=load_global(); g["welcome"]=w; save_global(g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Welcome set:\n{w}"}); return "ok",200
            if text.startswith("/search "): q=text.split()[1]; m=load_members(); f=[f"{v.get('name','-')} {k} @{v.get('username','-')}" for k,v in m.items() if q in k or q.lower() in v.get('username','').lower()]; txt="Hasil:\n"+"\n".join(f[:20]) if f else "Not found"; SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":txt}); return "ok",200
            if text.startswith("/broadcast "): pesan=text.replace("/broadcast ",""); m=load_members(); cnt=0; 
                for uid in m.keys():
                    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":uid,"text":f"Broadcast:\n{pesan}"},timeout=5); cnt+=1
                    except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Broadcast ke {cnt} selesai"}); return "ok",200
            if text.startswith("/addfilter "): w=text.replace("/addfilter ","").lower().strip(); f=load_filters(); 
                if w not in f: f.append(w); save_filters(f); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Filter added: {w}"})
                return "ok",200
            if text.startswith("/delfilter "): w=text.replace("/delfilter ","").lower().strip(); f=load_filters(); 
                if w in f: f.remove(w); save_filters(f); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Filter deleted: {w}"})
                return "ok",200
            if text=="/filters": f=load_filters(); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Filters ({len(f)}):\n"+"\n".join(f) or "Kosong"}); return "ok",200
            if text=="/clearquota": save_quota({}); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Quota cleared"}); return "ok",200
            if text=="/export": m=load_members(); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Export {len(m)} users"}); return "ok",200
            if text=="/nuke confirm": save_json(QUOTA_FILE,{}); save_json(BLOCKED_FILE,{}); save_json(FILTER_FILE,[]); save_json(SPAM_FILE,[]); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"ALL DB NUKED"}); return "ok",200

        if text.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_start_text(msg["from"].get("first_name","Jogja Lend")),"reply_markup":get_main_menu(cid)}); return "ok",200
        raw_caption=msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        filters=load_filters()
        for bad in filters:
            if bad in raw_caption.lower():
                spam=load_spam(); spam.append(f"{cid} : {raw_caption[:50]} [{bad}]"); save_spam(spam[-100:])
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Diblokir kata terlarang: {bad}","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}}); return "ok",200
        quotas=load_quota(); key=get_today_key(cid)
        if key not in quotas: quotas[key]={"text":0,"media":0}
        g=load_global(); is_media="photo" in msg; caption=add_hashtag(raw_caption)
        if is_media and quotas[key]["media"]>=g["limit_media"]: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Limit {g['limit_media']}/hari","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}}); return "ok",200
        if not is_media and quotas[key]["text"]>=g["limit_text"]: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Limit {g['limit_text']}/hari","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}}); return "ok",200
        if is_media:
            fid=msg["photo"][-1]["file_id"]; r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json(); fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content; fb=add_watermark(fb)
            files={"photo":("menfess.jpg",fb,"image/jpeg")}; res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":CHANNEL_ID,"caption":caption},files=files,timeout=30).json()
        else: res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":caption}).json()
        if res.get("ok"):
            pid=res["result"]["message_id"]
            if is_media: quotas[key]["media"]+=1
            else: quotas[key]["text"]+=1
            save_quota(quotas); tl=f"https://t.me/{CHANNEL_USERNAME}/{pid}"; btn={"inline_keyboard":[[{"text":"See on channel","url":tl}],[{"text":"Back","callback_data":"menu_main"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Menfess sent! Quota {quotas[key]['text']}/{g['limit_text']} {quotas[key]['media']}/{g['limit_media']}","reply_markup":btn})
    except Exception as e: print(e)
    return "ok",200
