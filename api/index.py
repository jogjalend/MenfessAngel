import os, io, json, requests, sys, time
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
LOGS_FILE = "/tmp/logs.json"
WORDS_FILE = "/tmp/words.json"
WARNS_FILE = "/tmp/warns.json"
ADMINS_FILE = "/tmp/admins.json"
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
START_TIME = time.time()
BASE_ADMIN = [8584319568]

def load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path,"r") as f: return json.load(f)
    except: pass
    return default if default is not None else {}
def save_json(path, d):
    try:
        with open(path,"w") as f: json.dump(d,f)
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
    g = load_json(GLOBAL_FILE, {})
    if not g: g = {"hashtag":"\n\n#jogjalend","limit_text":5,"limit_media":5,"maintenance":False,"flood":True,"welcome":"","rules":"1. No Spam\n2. No SARA\n3. No Doxxing"}
    return g
def save_global(d): save_json(GLOBAL_FILE, d)
def load_logs(): return load_json(LOGS_FILE, [])
def save_logs(d): save_json(LOGS_FILE, d)
def load_words(): return load_json(WORDS_FILE, [])
def save_words(d): save_json(WORDS_FILE, d)
def load_warns(): return load_json(WARNS_FILE, {})
def save_warns(d): save_json(WARNS_FILE, d)
def load_admins():
    a = load_json(ADMINS_FILE, [])
    if not a: return BASE_ADMIN
    return list(set(BASE_ADMIN + a))

def is_admin(chat_id): return int(chat_id) in load_admins()
def is_blocked(chat_id): return str(chat_id) in load_blocked()
def is_threads_enabled(chat_id): return load_settings().get(str(chat_id),{}).get("threads", False)
def set_threads_enabled(chat_id, v):
    s = load_settings()
    if str(chat_id) not in s: s[str(chat_id)] = {}
    s[str(chat_id)]["threads"] = v
    save_settings(s)
def get_today_key(chat_id): return f"{chat_id}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
def add_hashtag(text):
    g = load_global()
    ht = g.get("hashtag","")
    if not text: return ht.strip()
    if "jogjalend" in text.lower(): return text
    return text.strip() + ht
def get_real_channel_count():
    try:
        r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}", timeout=10).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 0
def add_log(uid, name, typ):
    logs = load_logs()
    logs.append({"uid":str(uid),"name":name,"type":typ,"time":datetime.now(WIB).strftime("%Y-%m-%d %H:%M")})
    save_logs(logs[-200:])

def get_start_text(first_name="Jogja Lend"):
    g = load_global()
    custom = g.get("welcome")
    if custom: return custom.replace("{name}", first_name)
    return f"Hi {first_name}!\nPromote your account here!\n______________________________________\n\nPublish to:\n• Channel → @menfessangel\n• Threads → @jogjalend [optional]\nTap Post to start!"

def get_main_menu(chat_id):
    btns = [
        [{"text":"My Profile","callback_data":"profil"}],
        [{"text":"Rules","callback_data":"menu_rules"}, {"text":"Post","callback_data":"menu_post"}],
        [{"text":"Threads Setting","callback_data":"menu_threads"}],
    ]
    if is_admin(chat_id): btns.append([{"text":"Admin Panel","callback_data":"admin_panel"}])
    btns.append([{"text":"Stats","callback_data":"menu_stats"}, {"text":"Help","callback_data":"menu_help"}])
    return {"inline_keyboard": btns}

def get_admin_menu():
    g = load_global()
    maint = "ON" if g.get("maintenance") else "OFF"
    flood = "ON" if g.get("flood") else "OFF"
    return {"inline_keyboard": [
        [{"text":"Dashboard","callback_data":"admin_panel"}, {"text":"Real Count","callback_data":"admin_real_count"}],
        [{"text":"All Users","callback_data":"admin_members_0"}, {"text":"Top / Low","callback_data":"admin_top"}],
        [{"text":"Blocked","callback_data":"admin_blocked"}, {"text":"Warns","callback_data":"admin_warns"}],
        [{"text":"Logs","callback_data":"admin_logs"}, {"text":"Clear Logs","callback_data":"admin_clear_logs"}],
        [{"text":"Broadcast All","callback_data":"admin_broadcast"}, {"text":"Broadcast Active","callback_data":"admin_broadcast_active"}],
        [{"text":"Word Filter","callback_data":"admin_words"}, {"text":f"Flood: {flood}","callback_data":"admin_toggle_flood"}],
        [{"text":f"Quota {g['limit_text']}/{g['limit_media']}","callback_data":"admin_set_quota"}, {"text":"Hashtag","callback_data":"admin_set_hashtag"}],
        [{"text":f"Maint: {maint}","callback_data":"admin_toggle_maint"}, {"text":"Sys Info","callback_data":"admin_sysinfo"}],
        [{"text":"Rules & Welcome","callback_data":"admin_edit_texts"}, {"text":"Admins","callback_data":"admin_list_admins"}],
        [{"text":"Export CSV","callback_data":"admin_export"}, {"text":"Backup JSON","callback_data":"admin_backup"}],
        [{"text":"Reset All","callback_data":"admin_reset"}, {"text":"Back","callback_data":"menu_main"}]
    ]}

def delete_and_send_menu(chat_id, msg_id, first_name):
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id}, timeout=5)
    except: pass
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(first_name),"reply_markup":get_main_menu(chat_id)})

def make_avatar_bytes(name):
    try:
        initial = (name or "J")[0].upper()
        img = Image.new('RGB', (800, 800), color=(29, 155, 240))
        draw = ImageDraw.Draw(img)
        draw.ellipse((100, 100, 700, 700), fill=(255,255,255))
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 350)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), initial, font=font)
        w = bbox[2]-bbox[0]; h = bbox[3]-bbox[1]
        draw.text(((800-w)/2, (800-h)/2 - 20), initial, fill=(29,155,240), font=font)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=90)
        buf.seek(0)
        return buf.getvalue()
    except:
        return None

def send_profile_with_photo(chat_id, msg_id, user_first):
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id})
    except: pass
    g = load_global()
    quotas = load_quota()
    key = get_today_key(chat_id)
    q = quotas.get(key, {"text":0,"media":0})
    on = is_threads_enabled(chat_id)
    members = load_members()
    info = members.get(str(chat_id), {})
    caption = f"My Profile\n______________________________________\n\nName: {info.get('name', user_first)}\nID: {chat_id}\nUsername: @{info.get('username','-')}\n\nText: {q['text']}/{g['limit_text']}\nMedia: {q['media']}/{g['limit_media']}\nThreads: {'ON' if on else 'OFF'}"
    kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"menu_main"}]]}
    photo_bytes = None
    try:
        r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos?user_id={chat_id}&limit=1", timeout=10).json()
        if r.get("ok") and r["result"]["total_count"] > 0:
            file_id = r["result"]["photos"][0][-1]["file_id"]
            rf = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            if rf.get("ok"):
                photo_bytes = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{rf['result']['file_path']}", timeout=15).content
    except: pass
    if not photo_bytes:
        photo_bytes = make_avatar_bytes(user_first or info.get('name','J'))
    if photo_bytes:
        files = {"photo": ("profile.jpg", photo_bytes, "image/jpeg")}
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":chat_id,"caption":caption,"reply_markup":json.dumps(kb)}, files=files, timeout=20)
    else:
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":kb})

@app.route("/", methods=['GET'])
def home(): return "Bot V47.1 Ultimate Admin + Photo",200
@app.route("/", methods=['POST'])
@app.route("/api/index.py", methods=['POST'])
def handler():
    try:
        data = request.get_json()
        if not data: return "ok",200
        if "callback_query" in data:
            cq = data["callback_query"]; cb_data = cq["data"]; chat_id = cq["message"]["chat"]["id"]; msg_id = cq["message"]["message_id"]; user_first = cq["from"].get("first_name","Jogja Lend")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
            if cb_data.startswith("delete_post_"):
                try:
                    tid = int(cb_data.replace("delete_post_",""))
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":tid})
                    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id})
                    except: pass
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"Post deleted","reply_markup":{"inline_keyboard":[[{"text":"Back to Menu","callback_data":"menu_main"}]]}})
                except: pass
                return "ok",200
            if cb_data.startswith("admin_view_"):
                if not is_admin(chat_id): return "ok",200
                target = cb_data.replace("admin_view_",""); members = load_members(); blocked = load_blocked(); quota = load_quota(); warns = load_warns()
                info = members.get(target, {}); user_posts = sum(v.get("text",0)+v.get("media",0) for k,v in quota.items() if k.startswith(target+"_"))
                today_key = f"{target}_{datetime.now(WIB).strftime('%Y-%m-%d')}"; today_q = quota.get(today_key, {"text":0,"media":0})
                txt = f"USER DETAIL\n______________________________________\n\nID: {target}\nName: {info.get('name','-')}\nUsername: @{info.get('username','-')}\nJoined: {info.get('joined','-')}\nBlocked: {'YES' if target in blocked else 'NO'}\nWarns: {warns.get(target,0)}/3\nToday: {today_q['text']}/{today_q['media']}\nTotal: {user_posts}"
                kb = {"inline_keyboard": [[{"text":"Warn +1","callback_data":f"admin_warn_{target}"}, {"text":"Blok","callback_data":f"admin_block_{target}"}],[{"text":"Unblok","callback_data":f"admin_unblock_{target}"}, {"text":"Reset Warn","callback_data":f"admin_unwarn_{target}"}],[{"text":"Hapus Data","callback_data":f"admin_del_{target}"}, {"text":"Reset Quota","callback_data":f"admin_reset_{target}"}],[{"text":"Back","callback_data":"admin_members_0"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200
            if cb_data.startswith("admin_block_") or cb_data.startswith("admin_unblock_") or cb_data.startswith("admin_del_") or cb_data.startswith("admin_reset_") or cb_data.startswith("admin_warn_") or cb_data.startswith("admin_unwarn_"):
                if not is_admin(chat_id): return "ok",200
                if cb_data.startswith("admin_block_"):
                    t=cb_data.replace("admin_block_",""); b=load_blocked(); b[t]=f"blocked by {chat_id}"; save_blocked(b); txt=f"{t} diblokir"
                elif cb_data.startswith("admin_unblock_"):
                    t=cb_data.replace("admin_unblock_",""); b=load_blocked(); b.pop(t,None); save_blocked(b); txt=f"{t} di-unblok"
                elif cb_data.startswith("admin_del_"):
                    t=cb_data.replace("admin_del_",""); m=load_members(); m.pop(t,None); save_members(m); txt=f"{t} dihapus"
                elif cb_data.startswith("admin_reset_"):
                    t=cb_data.replace("admin_reset_",""); q=load_quota(); [q.pop(k) for k in list(q.keys()) if k.startswith(t+"_")]; save_quota(q); txt=f"Quota {t} direset"
                elif cb_data.startswith("admin_warn_"):
                    t=cb_data.replace("admin_warn_",""); w=load_warns(); w[t]=w.get(t,0)+1; save_warns(w)
                    if w[t]>=3: b=load_blocked(); b[t]="3 warns"; save_blocked(b); txt=f"{t} warn {w[t]}/3 AUTO BLOCK"
                    else: txt=f"{t} warn {w[t]}/3"
                else:
                    t=cb_data.replace("admin_unwarn_",""); w=load_warns(); w.pop(t,None); save_warns(w); txt=f"Warn {t} direset"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            if cb_data in ["menu_main"]:
                delete_and_send_menu(chat_id, msg_id, user_first); return "ok",200
            if cb_data in ["profil","toggle_threads","menu_threads"]:
                if cb_data=="toggle_threads": set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                send_profile_with_photo(chat_id, msg_id, user_first); return "ok",200
            if cb_data=="menu_stats":
                real = get_real_channel_count(); m = load_members(); b = load_blocked(); q = load_quota()
                total = sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt = f"STATS\n______________________________________\n\nChannel Subs: {real}\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}\nDate: {datetime.now(WIB).strftime('%Y-%m-%d')}"
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id})
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}})
                return "ok",200
            if cb_data=="admin_panel":
                if not is_admin(chat_id): return "ok",200
                real=get_real_channel_count(); m=load_members(); b=load_blocked(); q=load_quota(); g=load_global(); logs=load_logs()
                total=sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt=f"ADMIN PANEL ULTIMATE\n______________________________________\n\nChannel: {real} subs\nUsers: {len(m)}\nBlocked: {len(b)}\nPosts: {total}\nLogs: {len(logs)}\nWarns: {len(load_warns())}\nWords Filter: {len(load_words())}\nMaint: {'ON' if g.get('maintenance') else 'OFF'}\nFlood: {'ON' if g.get('flood') else 'OFF'}\nQuota: {g['limit_text']}/{g['limit_media']}\nHashtag: {g['hashtag'].strip()}"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":get_admin_menu()})
                return "ok",200
            if cb_data=="admin_real_count":
                if not is_admin(chat_id): return "ok",200
                real=get_real_channel_count()
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"REAL COUNT\n@{CHANNEL_USERNAME}: {real} subs\n{datetime.now(WIB)}","reply_markup":{"inline_keyboard":[[{"text":"Refresh","callback_data":"admin_real_count"}],[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            if cb_data.startswith("admin_members_"):
                if not is_admin(chat_id): return "ok",200
                try: page=int(cb_data.split("_")[-1])
                except: page=0
                members=load_members(); keys=list(members.keys())[::-1]; per=10; total_pages=(len(keys)+per-1)//per
                start=page*per; chunk=keys[start:start+per]
                txt=f"ALL USERS {len(members)} - Page {page+1}/{max(total_pages,1)}\n______________________________________\n"
                kb=[]
                for uid in chunk:
                    info=members[uid]; name=info.get('name','-')[:14]; txt+=f"- {name} {uid}\n"; kb.append([{"text":f"{name} ({uid})","callback_data":f"admin_view_{uid}"}])
                nav=[]
                if page>0: nav.append({"text":"Prev","callback_data":f"admin_members_{page-1}"})
                if page < total_pages-1: nav.append({"text":"Next","callback_data":f"admin_members_{page+1}"})
                if nav: kb.append(nav)
                kb.append([{"text":"Back","callback_data":"admin_panel"}])
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":kb}})
                return "ok",200
            if cb_data=="admin_top":
                if not is_admin(chat_id): return "ok",200
                quota=load_quota(); members=load_members(); totals={}
                for k,v in quota.items():
                    uid=k.split("_")[0]; totals[uid]=totals.get(uid,0)+v.get("text",0)+v.get("media",0)
                top=sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
                low=sorted(totals.items(), key=lambda x: x[1])[:10]
                txt="TOP 10 ACTIVE\n______________________________________\n"
                for i,(uid,tot) in enumerate(top,1): txt+=f"{i}. {members.get(uid,{}).get('name','-')[:12]} {uid} - {tot}\n"
                txt+="\nLOW 10\n______________________________________\n"
                for i,(uid,tot) in enumerate(low,1): txt+=f"{i}. {members.get(uid,{}).get('name','-')[:12]} {uid} - {tot}\n"
                if not top: txt="Belum ada data"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            if cb_data=="admin_logs":
                if not is_admin(chat_id): return "ok",200
                logs=load_logs()[-20:][::-1]
                txt="RECENT LOGS\n______________________________________\n"
                for l in logs: txt+=f"{l['time']} {l['name'][:10]} {l['uid']} {l['type']}\n"
                if not logs: txt="No logs"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            if cb_data=="admin_clear_logs":
                if not is_admin(chat_id): return "ok",200
                save_logs([]); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Logs cleared","reply_markup":get_admin_menu()}); return "ok",200
            if cb_data=="admin_blocked":
                if not is_admin(chat_id): return "ok",200
                blocked=load_blocked()
                kb=[[ {"text":f"Unblok {uid}","callback_data":f"admin_unblock_{uid}"} ] for uid in list(blocked.keys())[:15]]
                kb.append([{"text":"Back","callback_data":"admin_panel"}])
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"BLOCKED {len(blocked)}","reply_markup":{"inline_keyboard":kb}})
                return "ok",200
            if cb_data=="admin_warns":
                if not is_admin(chat_id): return "ok",200
                warns=load_warns(); txt="WARNS\n______________________________________\n"
                for uid,c in warns.items(): txt+=f"{uid} - {c}/3\n"
                if not warns: txt="No warns"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            if cb_data=="admin_words":
                if not is_admin(chat_id): return "ok",200
                words=load_words(); txt=f"WORD FILTER {len(words)}\n______________________________________\n{', '.join(words[:30]) or 'empty'}\n\nCommand:\n/addword kata\n/delword kata\n/listwords"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            if cb_data=="admin_broadcast" or cb_data=="admin_broadcast_active":
                if not is_admin(chat_id): return "ok",200
                typ = "active today" if "active" in cb_data else "all"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"BROADCAST {typ}\n______________________________________\nKirim: /broadcast {typ} pesan lu","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            if cb_data=="admin_export":
                if not is_admin(chat_id): return "ok",200
                members=load_members(); csv_data="id,username,name,joined\n"
                for uid,info in members.items(): csv_data+=f"{uid},{info.get('username','-')},{info.get('name','-')},{info.get('joined','-')}\n"
                files={"document":("users.csv",csv_data.encode(),"text/csv")}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument", data={"chat_id":chat_id,"caption":f"Export {len(members)}"}, files=files); return "ok",200
            if cb_data=="admin_backup":
                if not is_admin(chat_id): return "ok",200
                data_all={"members":load_members(),"quota":load_quota(),"blocked":load_blocked(),"global":load_global(),"words":load_words(),"warns":load_warns()}
                files={"document":("backup.json",json.dumps(data_all, indent=2).encode(),"application/json")}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument", data={"chat_id":chat_id,"caption":"Backup JSON"}, files=files); return "ok",200
            if cb_data=="admin_set_quota":
                if not is_admin(chat_id): return "ok",200
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"SET QUOTA\nKirim /setquota 10 10","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}}); return "ok",200
            if cb_data=="admin_set_hashtag":
                if not is_admin(chat_id): return "ok",200
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"SET HASHTAG\nKirim /sethashtag #newtag atau /sethashtag off","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}}); return "ok",200
            if cb_data=="admin_toggle_maint":
                if not is_admin(chat_id): return "ok",200
                g=load_global(); g["maintenance"]=not g.get("maintenance",False); save_global(g)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"Maintenance {g['maintenance']}","reply_markup":get_admin_menu()}); return "ok",200
            if cb_data=="admin_toggle_flood":
                if not is_admin(chat_id): return "ok",200
                g=load_global(); g["flood"]=not g.get("flood",True); save_global(g)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"Flood {g['flood']}","reply_markup":get_admin_menu()}); return "ok",200
            if cb_data=="admin_sysinfo":
                if not is_admin(chat_id): return "ok",200
                uptime=int(time.time()-START_TIME); g=load_global()
                txt=f"SYS INFO\n______________________________________\nUptime {uptime//3600}h {(uptime%3600)//60}m\nPython {sys.version.split()[0]}\nMembers {len(load_members())}\nQuota {len(load_quota())}\nBlocked {len(load_blocked())}\nLogs {len(load_logs())}\nMaint {g.get('maintenance')} Flood {g.get('flood')}"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}}); return "ok",200
            if cb_data=="admin_edit_texts":
                if not is_admin(chat_id): return "ok",200
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"EDIT TEXTS\n______________________________________\n/setwelcome Hi {name} welcome!\n/setrules 1. No spam\n/resetwelcome","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}}); return "ok",200
            if cb_data=="admin_list_admins":
                if not is_admin(chat_id): return "ok",200
                admins=load_admins(); txt="ADMINS\n______________________________________\n"+"\n".join(map(str,admins))+"\n\n/addadmin ID\n/deladmin ID"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}}); return "ok",200
            if cb_data=="admin_reset":
                if not is_admin(chat_id): return "ok",200
                save_quota({}); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"All quota reset","reply_markup":get_admin_menu()}); return "ok",200
            txts={"menu_post":"Post Menfess\nJust send text or photo!","menu_rules":load_global().get("rules","Rules"),"menu_help":"Help /start"}
            txt=txts.get(cb_data,"Menu")
            try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}})
            except: delete_and_send_menu(chat_id, msg_id, user_first)
            return "ok",200

        if "message" not in data: return "ok",200
        msg=data["message"]; chat_id=msg["chat"]["id"]; text=msg.get("text","")
        members=load_members()
        if str(chat_id) not in members:
            members[str(chat_id)]={"username":msg["from"].get("username","-"),"name":msg["from"].get("first_name","-"),"joined":datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}; save_members(members)
        g=load_global()
        if g.get("maintenance") and not is_admin(chat_id):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"Bot maintenance"}); return "ok",200
        if is_blocked(chat_id) and not is_admin(chat_id):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"You are blocked"}); return "ok",200
        if not is_admin(chat_id):
            words=load_words()
            low=(msg.get("text","")+" "+msg.get("caption","")).lower()
            for w in words:
                if w.lower() in low:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Blocked word: {w}"}); return "ok",200
        if is_admin(chat_id):
            if text.startswith("/broadcast "):
                parts=text.split()
                if len(parts)>=3 and parts[1] in ["all","active"]:
                    mode=parts[1]; bc_text=text.replace(f"/broadcast {mode} ","")
                else:
                    mode="all"; bc_text=text.replace("/broadcast ","")
                members=load_members(); quota=load_quota(); today=datetime.now(WIB).strftime('%Y-%m-%d')
                count=0
                for uid in members.keys():
                    if mode=="active" and not any(today in k for k in quota.keys() if k.startswith(uid+"_")): continue
                    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":uid,"text":f"BROADCAST\n______________________________________\n\n{bc_text}"}, timeout=5); count+=1
                    except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Broadcast {mode} ke {count} users"}); return "ok",200
            if text.startswith("/setquota "):
                try: lt=int(text.split()[1]); lm=int(text.split()[2]); g=load_global(); g["limit_text"]=lt; g["limit_media"]=lm; save_global(g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Quota {lt}/{lm}"})
                except: pass
                return "ok",200
            if text.startswith("/sethashtag "):
                ht=text.replace("/sethashtag ","").strip(); g=load_global(); g["hashtag"]="" if ht.lower()=="off" else "\n\n"+ht; save_global(g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Hashtag {g['hashtag']}"}); return "ok",200
            if text.startswith("/setwelcome "):
                w=text.replace("/setwelcome ",""); g=load_global(); g["welcome"]=w; save_global(g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"Welcome updated"}); return "ok",200
            if text.startswith("/setrules "):
                r=text.replace("/setrules ",""); g=load_global(); g["rules"]=r; save_global(g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"Rules updated"}); return "ok",200
            if text.startswith("/resetwelcome"): g=load_global(); g["welcome"]=""; save_global(g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"Welcome reset"}); return "ok",200
            if text.startswith("/addword "):
                w=text.replace("/addword ","").lower().strip(); words=load_words(); 
                if w not in words: words.append(w); save_words(words)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Word {w} added"}); return "ok",200
            if text.startswith("/delword "):
                w=text.replace("/delword ","").lower().strip(); words=load_words(); 
                if w in words: words.remove(w); save_words(words)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Word {w} removed"}); return "ok",200
            if text.startswith("/listwords"):
                words=load_words(); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Words: {', '.join(words) or 'empty'}"}); return "ok",200
            if text.startswith("/warn "):
                t=text.split()[1]; w=load_warns(); w[t]=w.get(t,0)+1; save_warns(w); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"{t} warn {w[t]}/3"}); return "ok",200
            if text.startswith("/addadmin "):
                t=text.split()[1]; extra=load_json(ADMINS_FILE, []); if int(t) not in extra: extra.append(int(t)); save_json(ADMINS_FILE, extra); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Admin {t} added"}); return "ok",200
            if text.startswith("/deladmin "):
                t=int(text.split()[1]); extra=load_json(ADMINS_FILE, []); extra=[x for x in extra if int(x)!=t]; save_json(ADMINS_FILE, extra); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Admin {t} removed"}); return "ok",200
            if text.startswith("/block "):
                t=text.split()[1]; b=load_blocked(); b[t]="blocked"; save_blocked(b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"{t} diblokir"}); return "ok",200
            if text.startswith("/unblock "):
                t=text.split()[1]; b=load_blocked(); b.pop(t,None); save_blocked(b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"{t} di-unblok"}); return "ok",200
            if text.startswith("/search "):
                t=text.split()[1]; m=load_members(); info=m.get(t); 
                if info: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Found: {info}","reply_markup":{"inline_keyboard":[[{"text":"Detail","callback_data":f"admin_view_{t}"}]]}})
                else: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"Not found"})
                return "ok",200
            if text.startswith("/deluser "):
                t=text.split()[1]; m=load_members(); m.pop(t,None); save_members(m); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"{t} dihapus"}); return "ok",200
        if text.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(msg["from"].get("first_name","Jogja Lend")),"reply_markup":get_main_menu(chat_id)}); return "ok",200
        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas=load_quota(); key=get_today_key(chat_id)
        if key not in quotas: quotas[key]={"text":0,"media":0}
        g=load_global()
        is_media="photo" in msg
        caption=add_hashtag(raw_caption)
        if is_media and quotas[key]["media"] >= g["limit_media"]:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached","reply_markup":{"inline_keyboard":[[{"text":"Back to Menu","callback_data":"menu_main"}]]}}); return "ok",200
        if not is_media and quotas[key]["text"] >= g["limit_text"]:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached","reply_markup":{"inline_keyboard":[[{"text":"Back to Menu","callback_data":"menu_main"}]]}}); return "ok",200
        if is_media:
            fid=msg["photo"][-1]["file_id"]; r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
            files={"photo":("menfess.jpg",fb,"image/jpeg")}
            res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=30).json()
        else:
            res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption}).json()
        if res.get("ok"):
            pid=res["result"]["message_id"]
            if is_media: quotas[key]["media"]+=1
            else: quotas[key]["text"]+=1
            save_quota(quotas); add_log(chat_id, msg["from"].get("first_name","-"), "photo" if is_media else "text")
            tl=f"https://t.me/{CHANNEL_USERNAME}/{pid}"
            btn={"inline_keyboard": [[{"text":"See on channel","url":tl}],[{"text":"Delete","callback_data":f"delete_post_{pid}"}],[{"text":"Back to Menu","callback_data":"menu_main"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Menfess sent! Quota {quotas[key]['text']}/{g['limit_text']} {quotas[key]['media']}/{g['limit_media']}","reply_markup":btn})
    except Exception as e: print(e)
    return "ok",200
