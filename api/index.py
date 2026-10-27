import os, json, requests, tempfile
from flask import Flask, request
from datetime import datetime, timezone, timedelta
app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
BASE_ADMIN = [8584319568]

FILES = {
 "quota":"/tmp/quota.json","members":"/tmp/members.json",
 "blocked":"/tmp/blocked.json","global":"/tmp/global.json"
}

def load(p,d=None):
 try:
  if os.path.exists(p):
   with open(p,"r") as f: return json.load(f)
 except: pass
 return d if d is not None else {}

def save(p,d):
 try:
  dn=os.path.dirname(p); fd,tmp=tempfile.mkstemp(dir=dn)
  with os.fdopen(fd,'w') as f: json.dump(d,f)
  os.replace(tmp,p)
 except:
  try:
   with open(p,"w") as f: json.dump(d,f)
  except: pass

def get_global():
 g=load(FILES["global"],{})
 if not g or not isinstance(g,dict): g={}
 g.setdefault("limit_text",5); g.setdefault("limit_media",5)
 g.setdefault("welcome","Hi {name}!\nPromote your account here!\n______________________________________\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend")
 g.setdefault("hashtag","\n\n#jogjalend")
 return g

def is_admin(cid): return int(cid) in BASE_ADMIN

def get_real_count():
 try:
  r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=10).json()
  if r.get("ok"): return r.get("result",0)
 except: pass
 return 0

# FIX UTAMA: 1 fungsi handle GET dan POST
@app.route("/", methods=['GET','POST'])
@app.route("/api/index.py", methods=['GET','POST'])
def handler():
 if request.method == 'GET':
  return "Bot V52 Fixed Method Not Allowed - Khusus Admin 8584319568 - Welcome Editable",200

 try:
  data=request.get_json()
  if not data: return "ok",200
  if "callback_query" in data:
   cq=data["callback_query"]; cb=cq["data"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]
   fn=cq["from"].get("first_name","Bos")
   SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})
   if cb=="main":
    g=get_global(); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":g.get("welcome","Hi").replace("{name}",fn),"reply_markup":{"inline_keyboard":[[{"text":"Admin Panel","callback_data":"admin"}]]}})
    return "ok",200
   if not is_admin(cid): return "ok",200
   members=load(FILES["members"],{}); blocked=load(FILES["blocked"],{}); quota=load(FILES["quota"],{}); g=get_global()
   if cb=="admin":
    real=get_real_count(); total=sum(v.get("text",0)+v.get("media",0) for v in quota.values())
    txt=f"👑 ADMIN PANEL - KHUSUS LU\n______________________________________\n\n📢 Subs: {real} LIVE\n👥 Users: {len(members)}\n🚫 Blocked: {len(blocked)}\n📊 Posts: {total}\n\nID: {cid}"
    kb={"inline_keyboard":[[{"text":"📢 Real Count","callback_data":"admin"},{"text":"👥 All Users","callback_data":"all"}],[{"text":"🚫 Blocked","callback_data":"blocked"},{"text":"🔍 Search","callback_data":"s_info"}],[{"text":"⛔ Blok","callback_data":"b_info"},{"text":"✅ Unblok","callback_data":"ub_info"}],[{"text":"🗑️ Hapus","callback_data":"h_info"},{"text":"🔄 Reset","callback_data":"r_info"}],[{"text":"✏️ Edit Welcome","callback_data":"e_welcome"}],[{"text":"⬅️ Back","callback_data":"main"}]]}
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":kb}); return "ok",200
   if cb=="all":
    txt="ALL USERS\n"+"\n".join([f"{v.get('name','-')} {k}" for k,v in list(members.items())[-20:]]) or "0"
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin"}]]}}); return "ok",200
   infos={"blocked":f"BLOCKED {len(blocked)}\n"+"\n".join(blocked.keys()) or "0","s_info":"Kirim: /search ID","b_info":"Kirim: /block ID","ub_info":"Kirim: /unblock ID","h_info":"Kirim: /deluser ID","r_info":"Kirim: /resetquota ID atau all","e_welcome":f"EDIT WELCOME\n______________________________________\n/setwelcome teks baru pakai {{name}}\n\nSekarang:\n{g.get('welcome','')}"}
   if cb in infos: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":infos[cb],"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin"}]]}}); return "ok",200

  if "message" not in data: return "ok",200
  msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
  members=load(FILES["members"],{})
  if str(cid) not in members: members[str(cid)]={"name":msg["from"].get("first_name","-")}; save(FILES["members"],members)

  if is_admin(cid) and text.startswith("/"):
   if text.startswith("/setwelcome "): w=text.replace("/setwelcome ",""); g=get_global(); g["welcome"]=w; save(FILES["global"],g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"✅ Welcome updated!\n\n{w}"}); return "ok",200
   if text.startswith("/block "): t=text.split()[1]; b=load(FILES["blocked"],{}); b[t]="x"; save(FILES["blocked"],b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{t} blocked"}); return "ok",200
   if text.startswith("/unblock "): t=text.split()[1]; b=load(FILES["blocked"],{}); b.pop(t,None); save(FILES["blocked"],b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{t} unblocked"}); return "ok",200
   if text.startswith("/search "): t=text.split()[1]; m=load(FILES["members"],{}); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":str(m.get(t,"Not found"))}); return "ok",200
   if text.startswith("/resetquota "): t=text.split()[1]; q=load(FILES["quota"],{}); 
    if t=="all": q={}
    else: [q.pop(k) for k in list(q.keys()) if k.startswith(t+"_")]
    save(FILES["quota"],q); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Quota reset"}); return "ok",200

  if text.startswith(("/start","/menu")):
   g=get_global(); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":g.get("welcome","Hi").replace("{name}",msg["from"].get("first_name","Bos")),"reply_markup":{"inline_keyboard":[[{"text":"Admin Panel","callback_data":"admin"}]] if is_admin(cid) else []}}); return "ok",200

  quota=load(FILES["quota"],{}); key=f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"; 
  if key not in quota: quota[key]={"text":0,"media":0}
  g=get_global(); lt=g.get("limit_text",5); lm=g.get("limit_media",5)
  is_media="photo" in msg; raw=msg.get("caption") or msg.get("text") or ""
  if not raw and not is_media: return "ok",200
  if is_media and quota[key].get("media",0)>=lm: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Limit {lm}/hari"}); return "ok",200
  if not is_media and quota[key].get("text",0)>=lt: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Limit {lt}/hari"}); return "ok",200
  caption=raw+(g.get("hashtag","") if "jogjalend" not in raw.lower() else "")
  if is_media:
   fid=msg["photo"][-1]["file_id"]; r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
   if not r.get("ok"): return "ok",200
   fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
   res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":CHANNEL_ID,"caption":caption},files={"photo":("a.jpg",fb,"image/jpeg")}).json()
  else: res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":caption}).json()
  if res.get("ok"):
   if is_media: quota[key]["media"]=quota[key].get("media",0)+1
   else: quota[key]["text"]=quota[key].get("text",0)+1
   save(FILES["quota"],quota)
   SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"✅ Sent {quota[key].get('text',0)}/{lt} text {quota[key].get('media',0)}/{lm} media"})
 except Exception as e: print(e)
 return "ok",200