import os, json, requests
from flask import Flask, request
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
LOGS_FILE = "/tmp/logs.json"
WORDS_FILE = "/tmp/words.json"
WARNS_FILE = "/tmp/warns.json"
ADMINS_FILE = "/tmp/admins.json"
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
BASE_ADMIN = [8584319568]

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
def load_quota(): return load_json(QUOTA_FILE, {})
def save_quota(d): save_json(QUOTA_FILE, d)
def load_settings(): return load_json(SETTINGS_FILE, {})
def save_settings(d): save_json(SETTINGS_FILE, d)
def load_blocked(): return load_json(BLOCKED_FILE, {})
def save_blocked(d): save_json(BLOCKED_FILE, d)
def load_members(): return load_json(MEMBERS_FILE, {})
def save_members(d): save_json(MEMBERS_FILE, d)
def load_global():
    g=load_json(GLOBAL_FILE, {})
    if not g: g={"hashtag":"\n\n#jogjalend","limit_text":5,"limit_media":5,"maintenance":False,"flood":True}
    return g
def save_global(d): save_json(GLOBAL_FILE, d)
def load_logs(): return load_json(LOGS_FILE, [])
def save_logs(d): save_json(LOGS_FILE, d)
def load_words(): return load_json(WORDS_FILE, [])
def save_words(d): save_json(WORDS_FILE, d)
def load_warns(): return load_json(WARNS_FILE, {})
def save_warns(d): save_json(WARNS_FILE, d)
def load_admins():
    a=load_json(ADMINS_FILE, [])
    if not a: return BASE_ADMIN
    return list(set(BASE_ADMIN+a))

def is_admin(c): return int(c) in load_admins()
def is_blocked(c): return str(c) in load_blocked()
def is_threads_enabled(c): return load_settings().get(str(c),{}).get("threads", False)
def set_threads_enabled(c,v):
    s=load_settings()
    if str(c) not in s: s[str(c)]={}
    s[str(c)]["threads"]=v
    save_settings(s)
def get_today_key(c): return f"{c}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
def add_hashtag(t):
    g=load_global(); ht=g.get("hashtag","")
    if not t: return ht.strip()
    if "jogjalend" in t.lower(): return t
    return t.strip()+ht
def get_real_channel_count():
    try:
        r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}", timeout=10).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 0
def add_log(uid,name,typ):
    logs=load_logs(); logs.append({"uid":str(uid),"name":name,"type":typ,"time":datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}); save_logs(logs[-200:])

def get_start_text(fn="Jogja Lend"):
    return f"Hi {fn}!\nPromote your account here!\n______________________________________\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend [optional]\nTap Post to start!"

def get_main_menu(cid):
    btns=[[{"text":"My Profile","callback_data":"profil"}],[{"text":"Rules","callback_data":"menu_rules"},{"text":"Post","callback_data":"menu_post"}],[{"text":"Threads Setting","callback_data":"menu_threads"}]]
    if is_admin(cid): btns.append([{"text":"Admin Panel","callback_data":"admin_panel"}])
    btns.append([{"text":"Stats","callback_data":"menu_stats"},{"text":"Help","callback_data":"menu_help"}])
    return {"inline_keyboard":btns}

def get_admin_menu():
    g=load_global()
    maint="ON" if g.get("maintenance") else "OFF"
    flood="ON" if g.get("flood") else "OFF"
    return {"inline_keyboard":[
        [{"text":"Dashboard","callback_data":"admin_panel"},{"text":"Real Count","callback_data":"admin_real_count"}],
        [{"text":"All Users","callback_data":"admin_members_0"},{"text":"Top / Low","callback_data":"admin_top"}],
        [{"text":"Blocked List","callback_data":"admin_blocked"},{"text":"Search User","callback_data":"admin_search"}],
        [{"text":"Blok User","callback_data":"admin_blok_info"},{"text":"Unblok User","callback_data":"admin_unblok_info"}],
        [{"text":"Hapus User","callback_data":"admin_hapus_info"},{"text":"Reset Quota","callback_data":"admin_reset_info"}],
        [{"text":"Broadcast All","callback_data":"admin_broadcast"},{"text":"Word Filter","callback_data":"admin_words"}],
        [{"text":"Logs","callback_data":"admin_logs"},{"text":"Warns","callback_data":"admin_warns"}],
        [{"text":f"Maint: {maint}","callback_data":"admin_toggle_maint"},{"text":f"Flood: {flood}","callback_data":"admin_toggle_flood"}],
        [{"text":"Export CSV","callback_data":"admin_export"},{"text":"Backup JSON","callback_data":"admin_backup"}],
        [{"text":"Back","callback_data":"menu_main"}]
    ]}

def delete_and_send_menu(cid,mid,fn):
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":cid,"message_id":mid}, timeout=5)
    except: pass
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":get_start_text(fn),"reply_markup":get_main_menu(cid)})

@app.route("/", methods=['GET'])
def home(): return "Bot V47.3 Text Only + Admin Full",200
@app.route("/", methods=['POST'])
@app.route("/api/index.py", methods=['POST'])
def handler():
    try:
        data=request.get_json()
        if not data: return "ok",200
        if "callback_query" in data:
            cq=data["callback_query"]; cb=cq["data"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]; user_first=cq["from"].get("first_name","Jogja Lend")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
            if cb in ["menu_main"]: delete_and_send_menu(cid,mid,user_first); return "ok",200
            if cb in ["profil","toggle_threads","menu_threads"]:
                if cb=="toggle_threads": set_threads_enabled(cid, not is_threads_enabled(cid))
                g=load_global(); quotas=load_quota(); key=get_today_key(cid); q=quotas.get(key,{"text":0,"media":0}); on=is_threads_enabled(cid); members=load_members(); info=members.get(str(cid),{})
                txt=f"My Profile\n______________________________________\n\nName: {info.get('name',user_first)}\nID: {cid}\nUsername: @{info.get('username','-')}\n\nText: {q['text']}/{g['limit_text']}\nMedia: {q['media']}/{g['limit_media']}\nThreads: {'ON' if on else 'OFF'}"
                kb={"inline_keyboard":[[{"text":f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":kb}); return "ok",200
            if cb=="menu_stats":
                real=get_real_channel_count(); m=load_members(); b=load_blocked(); q=load_quota(); total=sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt=f"STATS\n______________________________________\n\nChannel Subs: {real}\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}}); return "ok",200
            if cb=="admin_panel":
                if not is_admin(cid): return "ok",200
                real=get_real_channel_count(); m=load_members(); b=load_blocked(); q=load_quota(); g=load_global(); total=sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt=f"ADMIN PANEL - KHUSUS LU\n______________________________________\n\nChannel Subs: {real}\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}\n\nID Admin: {cid}\nAkses Full!"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":get_admin_menu()}); return "ok",200
            if cb=="admin_real_count":
                real=get_real_channel_count(); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":f"Real Count @{CHANNEL_USERNAME}: {real} subs","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}}); return "ok",200
            if cb.startswith("admin_members_"):
                if not is_admin(cid): return "ok",200
                page=int(cb.split("_")[-1]); members=load_members(); keys=list(members.keys())[::-1]; per=10; total_pages=(len(keys)+per-1)//per; start=page*per; chunk=keys[start:start+per]
                txt=f"ALL USERS {len(members)} - Page {page+1}/{max(total_pages,1)}\n______________________________________\n"
                kb=[]
                for uid in chunk:
                    info=members[uid]; name=info.get('name','-')[:14]; txt+=f"- {name} {uid}\n"; kb.append([{"text":f"{name} ({uid})","callback_data":f"admin_view_{uid}"}])
                nav=[]
                if page>0: nav.append({"text":"Prev","callback_data":f"admin_members_{page-1}"})
                if page < total_pages-1: nav.append({"text":"Next","callback_data":f"admin_members_{page+1}"})
                if nav: kb.append(nav)
                kb.append([{"text":"Back","callback_data":"admin_panel"}])
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":kb}}); return "ok",200
            if cb.startswith("admin_view_"):
                if not is_admin(cid): return "ok",200
                target=cb.replace("admin_view_",""); members=load_members(); info=members.get(target,{}); quota=load_quota(); warns=load_warns(); blocked=load_blocked()
                user_posts=sum(v.get("text",0)+v.get("media",0) for k,v in quota.items() if k.startswith(target+"_"))
                txt=f"USER DETAIL\n______________________________________\n\nID: {target}\nName: {info.get('name','-')}\nUsername: @{info.get('username','-')}\nTotal Posts: {user_posts}\nWarns: {warns.get(target,0)}/3\nBlocked: {'YES' if target in blocked else 'NO'}"
                kb={"inline_keyboard":[[{"text":"Blok User","callback_data":f"admin_block_{target}"},{"text":"Unblok User","callback_data":f"admin_unblock_{target}"}],[{"text":"Hapus User","callback_data":f"admin_del_{target}"},{"text":"Reset Quota","callback_data":f"admin_reset_{target}"}],[{"text":"Back","callback_data":"admin_members_0"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":kb}); return "ok",200
            if cb.startswith("admin_block_") or cb.startswith("admin_unblock_") or cb.startswith("admin_del_") or cb.startswith("admin_reset_"):
                if not is_admin(cid): return "ok",200
                if cb.startswith("admin_block_"): t=cb.replace("admin_block_",""); b=load_blocked(); b[t]="blocked"; save_blocked(b); txt=f"{t} diblokir"
                elif cb.startswith("admin_unblock_"): t=cb.replace("admin_unblock_",""); b=load_blocked(); b.pop(t,None); save_blocked(b); txt=f"{t} di-unblok"
                elif cb.startswith("admin_del_"): t=cb.replace("admin_del_",""); m=load_members(); m.pop(t,None); save_members(m); txt=f"{t} dihapus"
                else: t=cb.replace("admin_reset_",""); q=load_quota(); [q.pop(k) for k in list(q.keys()) if k.startswith(t+"_")]; save_quota(q); txt=f"Quota {t} direset"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}}); return "ok",200
            # info buttons
            if cb in ["admin_blok_info","admin_unblok_info","admin_hapus_info","admin_reset_info","admin_search","admin_broadcast","admin_words","admin_logs","admin_warns","admin_export","admin_backup","admin_toggle_maint","admin_toggle_flood","admin_top","admin_blocked"]:
                if not is_admin(cid): return "ok",200
                if cb=="admin_search": txt="Search User\nKirim /search ID"
                elif cb=="admin_blok_info": txt="Blok User\nKirim /block ID"
                elif cb=="admin_unblok_info": txt="Unblok User\nKirim /unblock ID"
                elif cb=="admin_hapus_info": txt="Hapus User\nKirim /deluser ID"
                elif cb=="admin_reset_info": txt="Reset Quota\nKirim /resetquota ID atau /resetquota all"
                elif cb=="admin_top": quota=load_quota(); members=load_members(); totals={}; 
                else: txt="Fitur ini pakai command"
                if cb=="admin_top":
                    for k,v in quota.items(): uid=k.split("_")[0]; totals[uid]=totals.get(uid,0)+v.get("text",0)+v.get("media",0)
                    top=sorted(totals.items(), key=lambda x:x[1], reverse=True)[:10]; txt="TOP 10 ACTIVE\n______________________________________\n"; 
                    for i,(uid,tot) in enumerate(top,1): txt+=f"{i}. {members.get(uid,{}).get('name','-')[:12]} {uid} - {tot}\n"
                if cb=="admin_blocked":
                    blocked=load_blocked(); txt=f"BLOCKED {len(blocked)}\n"+"\n".join(blocked.keys())
                if cb=="admin_words":
                    words=load_words(); txt=f"WORD FILTER {len(words)}\n{', '.join(words) or 'empty'}\n\n/addword kata\n/delword kata"
                if cb=="admin_logs":
                    logs=load_logs()[-20:][::-1]; txt="LOGS\n______________________________________\n"; 
                    for l in logs: txt+=f"{l['time']} {l['uid']} {l['type']}\n"
                if cb=="admin_warns":
                    warns=load_warns(); txt="WARNS\n"; 
                    for uid,c in warns.items(): txt+=f"{uid} - {c}/3\n"
                if cb=="admin_export":
                    members=load_members(); csv_data="id,username,name\n"; 
                    for uid,info in members.items(): csv_data+=f"{uid},{info.get('username','-')},{info.get('name','-')}\n"
                    files={"document":("users.csv",csv_data.encode(),"text/csv")}; SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument", data={"chat_id":cid,"caption":f"Export {len(members)}"}, files=files); return "ok",200
                if cb=="admin_broadcast": txt="Broadcast\nKirim /broadcast all pesan lu"
                if cb=="admin_backup":
                    data_all={"members":load_members(),"quota":load_quota(),"blocked":load_blocked()}; files={"document":("backup.json",json.dumps(data_all, indent=2).encode(),"application/json")}; SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument", data={"chat_id":cid,"caption":"Backup"}, files=files); return "ok",200
                if cb=="admin_toggle_maint": g=load_global(); g["maintenance"]=not g.get("maintenance",False); save_global(g); txt=f"Maintenance {g['maintenance']}"
                if cb=="admin_toggle_flood": g=load_global(); g["flood"]=not g.get("flood",True); save_global(g); txt=f"Flood {g['flood']}"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}}); return "ok",200
            txts={"menu_post":"Post Menfess\nJust send text or photo!","menu_rules":"Rules:\n1. No Spam\n2. No SARA","menu_help":"Help /start"}
            txt=txts.get(cb,"Menu")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}}); return "ok",200
        if "message" not in data: return "ok",200
        msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
        members=load_members()
        if str(cid) not in members:
            members[str(cid)]={"username":msg["from"].get("username","-"),"name":msg["from"].get("first_name","-"),"joined":datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}; save_members(members)
        g=load_global()
        if g.get("maintenance") and not is_admin(cid): SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":"Bot maintenance"}); return "ok",200
        if is_blocked(cid) and not is_admin(cid): SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":"You are blocked"}); return "ok",200
        if not is_admin(cid):
            words=load_words(); low=(text+" "+msg.get("caption","")).lower()
            for w in words:
                if w.lower() in low: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Blocked word: {w}"}); return "ok",200
        if text.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":get_start_text(msg["from"].get("first_name","Jogja Lend")),"reply_markup":get_main_menu(cid)}); return "ok",200
        if is_admin(cid) and text.startswith("/"):
            if text.startswith("/broadcast all "): bc=text.replace("/broadcast all ",""); m=load_members(); c=0; 
                for uid in m.keys():
                    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":uid,"text":f"BROADCAST\n______________________________________\n\n{bc}"}); c+=1
                    except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Broadcast ke {c} users"}); return "ok",200
            if text.startswith("/setquota "): 
                try: lt=int(text.split()[1]); lm=int(text.split()[2]); g=load_global(); g["limit_text"]=lt; g["limit_media"]=lm; save_global(g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Quota {lt}/{lm}"})
                except: pass
                return "ok",200
            if text.startswith("/block "): t=text.split()[1]; b=load_blocked(); b[t]="blocked"; save_blocked(b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"{t} diblokir"}); return "ok",200
            if text.startswith("/unblock "): t=text.split()[1]; b=load_blocked(); b.pop(t,None); save_blocked(b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"{t} di-unblok"}); return "ok",200
            if text.startswith("/search "): t=text.split()[1]; m=load_members(); info=m.get(t); 
                if info: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Found: {info}","reply_markup":{"inline_keyboard":[[{"text":"Detail","callback_data":f"admin_view_{t}"}]]}})
                else: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":"Not found"}); return "ok",200
            if text.startswith("/deluser "): t=text.split()[1]; m=load_members(); m.pop(t,None); save_members(m); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"{t} dihapus"}); return "ok",200
            if text.startswith("/addword "): w=text.replace("/addword ","").lower().strip(); words=load_words(); 
                if w not in words: words.append(w); save_words(words); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Word {w} added"}); return "ok",200
            if text.startswith("/delword "): w=text.replace("/delword ","").lower().strip(); words=load_words(); 
                if w in words: words.remove(w); save_words(words); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Word {w} removed"}); return "ok",200
        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas=load_quota(); key=get_today_key(cid)
        if key not in quotas: quotas[key]={"text":0,"media":0}
        g=load_global(); is_media="photo" in msg; caption=add_hashtag(raw_caption)
        if is_media and quotas[key]["media"] >= g["limit_media"]: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Limit reached"}); return "ok",200
        if not is_media and quotas[key]["text"] >= g["limit_text"]: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Limit reached"}); return "ok",200
        if is_media:
            fid=msg["photo"][-1]["file_id"]; r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json(); fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
            files={"photo":("menfess.jpg",fb,"image/jpeg")}; res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=30).json()
        else:
            res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption}).json()
        if res.get("ok"):
            pid=res["result"]["message_id"]
            if is_media: quotas[key]["media"]+=1
            else: quotas[key]["text"]+=1
            save_quota(quotas); add_log(cid, msg["from"].get("first_name","-"), "photo" if is_media else "text")
            tl=f"https://t.me/{CHANNEL_USERNAME}/{pid}"; btn={"inline_keyboard":[[{"text":"See on channel","url":tl}],[{"text":"Back to Menu","callback_data":"menu_main"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"Menfess sent! Quota {quotas[key]['text']}/{g['limit_text']} {quotas[key]['media']}/{g['limit_media']}","reply_markup":btn})
    except Exception as e: print(e)
    return "ok",200
