import os, json, requests, time
from flask import Flask, request
from datetime import datetime, timezone, timedelta
app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
START_TIME = time.time()
# KHUSUS LU DOANG
BASE_ADMIN = [8584319568]
FILES = {
 "quota":"/tmp/quota.json","settings":"/tmp/settings.json",
 "blocked":"/tmp/blocked.json","members":"/tmp/members.json",
 "global":"/tmp/global.json","words":"/tmp/words.json"
}
def load(p,d={}):
 try:
  if os.path.exists(p):
   with open(p,"r") as f: return json.load(f)
 except: pass
 return d
def save(p,d):
 try:
  with open(p,"w") as f: json.dump(d,f)
 except: pass
def get_global():
 g=load(FILES["global"])
 if not g: g={"limit_text":5,"limit_media":5,"welcome":"Hi {name}!\nPromote your account here!\n______________________________________\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend","rules":"1. No Spam\n2. No SARA","hashtag":"\n\n#jogjalend"}
 return g
def is_admin(cid): return int(cid) in BASE_ADMIN
def get_real_count():
 try:
  r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=10).json()
  if r.get("ok"): return r["result"]
 except: pass
 return 0
def get_admin_menu():
 return {"inline_keyboard":[
  [{"text":"📢 Real Count","callback_data":"real_count"},{"text":"👥 All Users","callback_data":"all_users"}],
  [{"text":"🚫 Blocked List","callback_data":"blocked_list"},{"text":"🔍 Search User","callback_data":"search_info"}],
  [{"text":"⛔ Blok User","callback_data":"blok_info"},{"text":"✅ Unblok User","callback_data":"unblok_info"}],
  [{"text":"🗑️ Hapus User","callback_data":"hapus_info"},{"text":"🔄 Reset Quota","callback_data":"reset_info"}],
  [{"text":"✏️ Edit Welcome","callback_data":"edit_welcome"},{"text":"📜 Edit Rules","callback_data":"edit_rules"}],
  [{"text":"⚙️ Set Quota","callback_data":"set_quota"},{"text":"📢 Broadcast","callback_data":"broadcast_info"}],
  [{"text":"📤 Export","callback_data":"export_users"},{"text":"⬅️ Back","callback_data":"menu_main"}]
 ]}

@app.route("/", methods=['GET'])
def home(): return "Bot V49 Khusus Admin 8584319568 + Welcome Edit",200

@app.route("/", methods=['POST'])
@app.route("/api/index.py", methods=['POST'])
def handler():
 try:
  data=request.get_json()
  if not data: return "ok",200
  if "callback_query" in data:
   cq=data["callback_query"]; cb=cq["data"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]
   fn=cq["from"].get("first_name","Bos")
   SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})
   if cb=="menu_main":
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":get_global()["welcome"].replace("{name}",fn),"reply_markup":{"inline_keyboard":[[{"text":"Admin Panel","callback_data":"admin_panel"}]]}})
    return "ok",200
   if not is_admin(cid): return "ok",200
   members=load(FILES["members"],{}); blocked=load(FILES["blocked"],{}); quota=load(FILES["quota"],{}); g=get_global()
   if cb=="admin_panel" or cb=="real_count":
    real=get_real_count()
    txt=f"👑 ADMIN PANEL - KHUSUS LU\n______________________________________\n\n📢 Channel Subs: {real} (LIVE)\n👥 Bot Users: {len(members)}\n🚫 Blocked: {len(blocked)}\n📊 Total Posts: {sum(v.get('text',0)+v.get('media',0) for v in quota.values())}\n\nID Admin: {cid}\nAkses Full!"
    if cb=="real_count": txt=f"Real Count @{CHANNEL_ID}: {real} subs (LIVE dari Telegram)"
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":get_admin_menu()})
    return "ok",200
   if cb=="all_users":
    txt=f"ALL USERS {len(members)}\n______________________________________\n"+"\n".join([f"{v.get('name','-')} - {k}" for k,v in list(members.items())[-20:]]) or "0"
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
    return "ok",200
   if cb=="blocked_list":
    txt=f"BLOCKED {len(blocked)}\n______________________________________\n"+"\n".join(blocked.keys()) or "0"
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
    return "ok",200
   # INFO TOMBOL
   infos={
    "search_info":"Kirim: /search USER_ID\nContoh: /search 123456789",
    "blok_info":"Kirim: /block USER_ID\nContoh: /block 123456789",
    "unblok_info":"Kirim: /unblock USER_ID\nContoh: /unblock 123456789",
    "hapus_info":"Kirim: /deluser USER_ID",
    "reset_info":"Kirim: /resetquota USER_ID atau /resetquota all",
    "edit_welcome":"FITUR EDIT WELCOME KHUSUS LU\n______________________________________\n\nKirim:\n/setwelcome Pesan baru lu\n\nBisa pakai {name} buat nama user\nContoh:\n/setwelcome Hi {name}! Welcome di JogjaLend\n\nWelcome sekarang:\n"+g["welcome"][:500],
    "edit_rules":"Kirim: /setrules 1. No spam...",
    "set_quota":"Kirim: /setquota 10 10\n(10 text, 10 media per hari)",
    "broadcast_info":"Kirim: /broadcast all Pesan lu akan dikirim ke semua user"
   }
   if cb in infos:
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":infos[cb],"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
    return "ok",200
   if cb=="export_users":
    csv_data="id,username,name\n"+"\n".join([f"{k},{v.get('username','-')},{v.get('name','-')}" for k,v in members.items()])
    files={"document":("users.csv",csv_data.encode(),"text/csv")}
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",data={"chat_id":cid,"caption":f"Export {len(members)} users"},files=files)
    return "ok",200

  if "message" not in data: return "ok",200
  msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
  members=load(FILES["members"],{})
  if str(cid) not in members:
   members[str(cid)]={"username":msg["from"].get("username","-"),"name":msg["from"].get("first_name","-")}; save(FILES["members"],members)
  
  # COMMAND KHUSUS ADMIN LU
  if is_admin(cid) and text.startswith("/"):
   if text.startswith("/setwelcome "):
    w=text.replace("/setwelcome ",""); g=get_global(); g["welcome"]=w; save(FILES["global"],g)
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Welcome updated!\n\n{w}"})
    return "ok",200
   if text.startswith("/setrules "):
    r=text.replace("/setrules ",""); g=get_global(); g["rules"]=r; save(FILES["global"],g)
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Rules updated!"})
    return "ok",200
   if text.startswith("/setquota "):
    try:
     lt=int(text.split()[1]); lm=int(text.split()[2]); g=get_global(); g["limit_text"]=lt; g["limit_media"]=lm; save(FILES["global"],g)
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Quota set {lt} text / {lm} media"})
    except: pass
    return "ok",200
   if text.startswith("/search "): 
    t=text.split()[1]; m=load(FILES["members"],{}); info=m.get(t)
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Found: {info}" if info else "Not found"})
    return "ok",200
   if text.startswith("/block "): t=text.split()[1]; b=load(FILES["blocked"],{}); b[t]="blocked"; save(FILES["blocked"],b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{t} diblokir"}); return "ok",200
   if text.startswith("/unblock "): t=text.split()[1]; b=load(FILES["blocked"],{}); b.pop(t,None); save(FILES["blocked"],b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{t} di-unblok"}); return "ok",200
   if text.startswith("/deluser "): t=text.split()[1]; m=load(FILES["members"],{}); m.pop(t,None); save(FILES["members"],m); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{t} dihapus"}); return "ok",200
   if text.startswith("/resetquota "): 
    t=text.split()[1]
    if t=="all": save(FILES["quota"],{})
    else: q=load(FILES["quota"],{}); [q.pop(k) for k in list(q.keys()) if k.startswith(t+"_")]; save(FILES["quota"],q)
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Quota reset"}); return "ok",200
   if text.startswith("/broadcast all "): bc=text.replace("/broadcast all ",""); m=load(FILES["members"],{}); c=0;
    for uid in m.keys():
     try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":uid,"text":f"BROADCAST\n\n{bc}"}); c+=1
     except: pass
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Broadcast ke {c} users"}); return "ok",200

  if text.startswith(("/start","/menu")):
   g=get_global()
   SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":g["welcome"].replace("{name}",msg["from"].get("first_name","Bos")),"reply_markup":{"inline_keyboard":[[{"text":"Admin Panel","callback_data":"admin_panel"}]]}})
   return "ok",200

  # MENFESS BIASA
  quota=load(FILES["quota"],{}); key=f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
  if key not in quota: quota[key]={"text":0,"media":0}
  g=get_global(); is_media="photo" in msg; raw=msg.get("caption") or msg.get("text") or ""
  caption=raw+(g.get("hashtag","") if "jogjalend" not in raw.lower() else "")
  if is_media:
   fid=msg["photo"][-1]["file_id"]; r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json(); fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
   res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":CHANNEL_ID,"caption":caption},files={"photo":("a.jpg",fb,"image/jpeg")}).json()
  else:
   res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":caption}).json()
  if res.get("ok"):
   if is_media: quota[key]["media"]+=1
   else: quota[key]["text"]+=1
   save(FILES["quota"],quota)
   SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Sent! {quota[key]['text']}/{g['limit_text']} text, {quota[key]['media']}/{g['limit_media']} media"})
 except Exception as e: print(e)
 return "ok",200
