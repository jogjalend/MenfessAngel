import os, json, requests, tempfile, time
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
 "blocked":"/tmp/blocked.json","global":"/tmp/global.json",
 "settings":"/tmp/settings.json"
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
  with open(p,"w") as f: json.dump(d,f)

def get_global():
 g=load(FILES["global"],{})
 if not g or not isinstance(g,dict): g={}
 g.setdefault("limit_text",5); g.setdefault("limit_media",5)
 g.setdefault("hashtag","\n\n#jogjalend")
 g.setdefault("welcome","Hi {name}!\nPromote your account here!\n______________________________________\n\nPublish to:\n• Channel → @menfessangel\n• Threads → @jogjalend [optional]\n• X → @jogjalendpm [maintenance]\n\nTap Post to start!")
 return g

def is_admin(cid):
 try: return int(cid) in BASE_ADMIN
 except: return False

def is_blocked(cid):
 return str(cid) in load(FILES["blocked"],{})

def is_threads_enabled(cid):
 return load(FILES["settings"],{}).get(str(cid),{}).get("threads",False)

def set_threads(cid,v):
 s=load(FILES["settings"],{}); 
 if str(cid) not in s: s[str(cid)]={}
 s[str(cid)]["threads"]=v; save(FILES["settings"],s)

def get_real_count():
 if not BOT_TOKEN: return 0
 try:
  r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=10).json()
  if r.get("ok"): return r.get("result",0)
 except: pass
 return 0

def tg(method,payload,files=None):
 if not BOT_TOKEN: return {"ok":False}
 url=f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
 try:
  if files: return SESSION.post(url,data=payload,files=files,timeout=30).json()
  return SESSION.post(url,json=payload,timeout=15).json()
 except: return {"ok":False}

def get_main_menu(cid):
 # Layout persis screenshot lu
 btns=[
  [{"text":"My Profile","callback_data":"profil"}],
  [{"text":"Rules","callback_data":"rules"},{"text":"Post","callback_data":"post"}],
  [{"text":"Threads Setting","callback_data":"threads"}],
 ]
 if is_admin(cid): btns.append([{"text":"Admin Panel 👑","callback_data":"admin"}])
 btns.append([{"text":"Stats","callback_data":"stats"},{"text":"Help","callback_data":"help"}])
 return {"inline_keyboard":btns}

def get_admin_menu():
 return {"inline_keyboard":[
  [{"text":"📢 Real Count","callback_data":"admin"},{"text":"👥 All Users","callback_data":"all"}],
  [{"text":"🚫 Blocked List","callback_data":"blocked"},{"text":"🔍 Search","callback_data":"s_info"}],
  [{"text":"⛔ Blok User","callback_data":"b_info"},{"text":"✅ Unblok","callback_data":"ub_info"}],
  [{"text":"🗑️ Hapus User","callback_data":"h_info"},{"text":"🔄 Reset Quota","callback_data":"r_info"}],
  [{"text":"✏️ Edit Welcome","callback_data":"e_welcome"},{"text":"📜 Edit Rules","callback_data":"e_rules"}],
  [{"text":"⬅️ Back","callback_data":"main"}]
 ]}

@app.route("/", methods=['GET','POST'])
@app.route("/api/index.py", methods=['GET','POST'])
def handler():
 if request.method=='GET':
  return f"Bot V54 Layout Screenshot - Khusus 8584319568 - {get_real_count()} LIVE",200

 try:
  data=request.get_json()
  if not data: return "ok",200
  
  if "callback_query" in data:
   cq=data["callback_query"]; cb=cq["data"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]
   fn=cq["from"].get("first_name","Bos")
   tg("answerCallbackQuery",{"callback_query_id":cq["id"]})
   
   if cb=="main":
    g=get_global()
    tg("sendMessage",{"chat_id":cid,"text":g.get("welcome","Hi").replace("{name}",fn),"reply_markup":get_main_menu(cid)})
    return "ok",200
   
   if cb=="profil":
    g=get_global(); q=load(FILES["quota"],{}); key=f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
    qq=q.get(key,{"text":0,"media":0}); th="ON" if is_threads_enabled(cid) else "OFF"
    txt=f"My Profile\n______________________________________\n\nID: {cid}\nName: {fn}\nThreads: {th}\n\nQuota hari ini:\nText: {qq['text']}/{g.get('limit_text',5)}\nMedia: {qq['media']}/{g.get('limit_media',5)}"
    tg("editMessageText",{"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":f"Threads: {th}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"main"}]]}})
    return "ok",200

   if cb=="toggle_threads":
    set_threads(cid, not is_threads_enabled(cid))
    return handler.__wrapped__ if False else (tg("answerCallbackQuery",{"callback_query_id":cq["id"]}), None)[1] or "ok",200

   if cb in ["rules","stats","help","post","threads"]:
    g=get_global()
    if cb=="rules": txt=g.get("rules","1. No Spam\n2. No SARA\n3. No Porn")
    elif cb=="stats": txt=f"STATS\n______________________________________\n\nChannel: {get_real_count()} LIVE\nUsers: {len(load(FILES['members'],{}))}\nBlocked: {len(load(FILES['blocked'],{}))}"
    elif cb=="help": txt="Help\n______________________________________\nKirim text/foto/video, nanti auto post ke @menfessangel\nLimit 5 text + 5 media /hari"
    elif cb=="post": txt="Kirim menfess kamu sekarang:\n\nBisa text, foto, video\nAuto pakai hashtag #jogjalend"
    else: 
     th="ON" if is_threads_enabled(cid) else "OFF"
     txt=f"Threads Setting: {th}\n\nKalau ON, menfess mu juga dipublish ke Threads @jogjalend (optional)"
    tg("editMessageText",{"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
    return "ok",200

   if not is_admin(cid): return "ok",200
   members=load(FILES["members"],{}); blocked=load(FILES["blocked"],{}); quota=load(FILES["quota"],{}); g=get_global()
   if cb=="admin":
    real=get_real_count(); total=sum(v.get("text",0)+v.get("media",0) for v in quota.values())
    txt=f"👑 ADMIN PANEL - KHUSUS LU 8584319568\n______________________________________\n\n📢 Subs: {real} LIVE\n👥 Users: {len(members)}\n🚫 Blocked: {len(blocked)}\n📊 Posts: {total}"
    tg("editMessageText",{"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":get_admin_menu()}); return "ok",200
   if cb=="all":
    txt="ALL USERS\n"+"\n".join([f"{v.get('name','-')} {k}" for k,v in list(members.items())[-20:]]) or "0"
    tg("editMessageText",{"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin"}]]}}); return "ok",200
   infos={"blocked":f"BLOCKED {len(blocked)}\n"+"\n".join(blocked.keys()) or "0","s_info":"Kirim: /search ID","b_info":"Kirim: /block ID","ub_info":"Kirim: /unblock ID","h_info":"Kirim: /deluser ID","r_info":"Kirim: /resetquota ID atau all","e_welcome":f"EDIT WELCOME\nKirim:\n/setwelcome teks baru pakai {{name}}\n\nSekarang:\n{g.get('welcome','')[:1000]}","e_rules":"Kirim: /setrules teks baru"}
   if cb in infos:
    tg("editMessageText",{"chat_id":cid,"message_id":mid,"text":infos[cb],"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin"}]]}}); return "ok",200

  if "message" not in data: return "ok",200
  msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
  if msg["chat"].get("type")!="private": return "ok",200
  if is_blocked(cid) and not is_admin(cid): tg("sendMessage",{"chat_id":cid,"text":"You are blocked"}); return "ok",200
  
  members=load(FILES["members"],{})
  if str(cid) not in members: members[str(cid)]={"name":msg["from"].get("first_name","-")}; save(FILES["members"],members)

  if is_admin(cid) and text.startswith("/"):
   if text.startswith("/setwelcome "):
    w=text.replace("/setwelcome ","",1); g=get_global(); g["welcome"]=w; save(FILES["global"],g)
    tg("sendMessage",{"chat_id":cid,"text":f"✅ Welcome updated!\n\n{w}"}); return "ok",200
   if text.startswith("/setrules "):
    r=text.replace("/setrules ","",1); g=get_global(); g["rules"]=r; save(FILES["global"],g)
    tg("sendMessage",{"chat_id":cid,"text":"Rules updated"}); return "ok",200
   if text.startswith("/block "): t=text.split()[1]; b=load(FILES["blocked"],{}); b[str(t)]="x"; save(FILES["blocked"],b); tg("sendMessage",{"chat_id":cid,"text":f"{t} blocked"}); return "ok",200
   if text.startswith("/unblock "): t=text.split()[1]; b=load(FILES["blocked"],{}); b.pop(str(t),None); save(FILES["blocked"],b); tg("sendMessage",{"chat_id":cid,"text":f"{t} unblocked"}); return "ok",200
   if text.startswith("/search "): t=text.split()[1]; m=load(FILES["members"],{}); tg("sendMessage",{"chat_id":cid,"text":str(m.get(str(t),"Not found"))}); return "ok",200
   if text.startswith("/resetquota "): t=text.split()[1]; q=load(FILES["quota"],{}); 
    if t=="all": q={}
    else: [q.pop(k) for k in list(q.keys()) if k.startswith(str(t)+"_")]
    save(FILES["quota"],q); tg("sendMessage",{"chat_id":cid,"text":"Quota reset"}); return "ok",200

  if text.startswith(("/start","/menu")):
   g=get_global()
   tg("sendMessage",{"chat_id":cid,"text":g.get("welcome","Hi {name}!").replace("{name}",msg["from"].get("first_name","Bos")),"reply_markup":get_main_menu(cid)})
   return "ok",200

  # Menfess
  quota=load(FILES["quota"],{}); key=f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
  if key not in quota: quota[key]={"text":0,"media":0}
  g=get_global(); lt=g.get("limit_text",5); lm=g.get("limit_media",5)
  is_media="photo" in msg; raw=msg.get("caption") or msg.get("text") or ""
  if not raw and not is_media: return "ok",200
  if is_media and quota[key].get("media",0)>=lm: tg("sendMessage",{"chat_id":cid,"text":f"Limit {lm}/hari"}); return "ok",200
  if not is_media and quota[key].get("text",0)>=lt: tg("sendMessage",{"chat_id":cid,"text":f"Limit {lt}/hari"}); return "ok",200
  caption=raw+(g.get("hashtag","") if "jogjalend" not in raw.lower() else "")
  if is_media:
   fid=msg["photo"][-1]["file_id"]; rf=tg("getFile",{"file_id":fid})
   if not rf.get("ok"): return "ok",200
   fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{rf['result']['file_path']}",timeout=20).content
   res=tg("sendPhoto",{"chat_id":CHANNEL_ID,"caption":caption},{"photo":("a.jpg",fb,"image/jpeg")})
  else: res=tg("sendMessage",{"chat_id":CHANNEL_ID,"text":caption})
  if res.get("ok"):
   if is_media: quota[key]["media"]=quota[key].get("media",0)+1
   else: quota[key]["text"]=quota[key].get("text",0)+1
   save(FILES["quota"],quota)
   tg("sendMessage",{"chat_id":cid,"text":f"✅ Sent {quota[key].get('text',0)}/{lt} text"})
 except Exception as e: print(e)
 return "ok",200