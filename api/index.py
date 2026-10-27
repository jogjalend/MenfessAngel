import os, json, requests, tempfile, time
from flask import Flask, request
from datetime import datetime, timezone, timedelta
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
BASE_ADMIN = [8584319568] # KHUSUS LU

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
 g.setdefault("welcome","Hi {name}!\nPromote your account here!\n______________________________________\n\nPublish to:\n- Channel -> @menfessangel")
 g.setdefault("hashtag","\n\n#jogjalend")
 return g

# FIX Copilot: is_admin aman
def is_admin(cid):
 try:
  cid=int(cid)
  return cid in BASE_ADMIN
 except:
  return False

def is_blocked(cid):
 b=load(FILES["blocked"],{})
 return str(cid) in b

def get_real_count():
 # FIX Copilot: validasi token dulu
 if not BOT_TOKEN: return 0
 try:
  r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=10).json()
  if r.get("ok"): return r.get("result",0)
  else: print(f"getChatCount fail: {r}")
 except Exception as e: print(f"real_count error {e}")
 return 0

def tg_post(method,payload,files=None,retries=1):
 # FIX Copilot: handle rate limit & error
 if not BOT_TOKEN: 
  print("BOT_TOKEN kosong!")
  return {"ok":False}
 url=f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
 for _ in range(retries+1):
  try:
   if files: res=SESSION.post(url,data=payload,files=files,timeout=30)
   else: res=SESSION.post(url,json=payload,timeout=15)
   j=res.json()
   if j.get("ok"): return j
   # kalau rate limit 429 tunggu
   if j.get("error_code")==429:
    time.sleep(j.get("parameters",{}).get("retry_after",2))
    continue
   print(f"TG error {method}: {j}")
   return j
  except Exception as e:
   print(f"TG exception {method}: {e}")
   time.sleep(1)
 return {"ok":False}

@app.route("/", methods=['GET','POST'])
@app.route("/api/index.py", methods=['GET','POST'])
def handler():
 # FIX utama Method Not Allowed
 if request.method=='GET':
  if not BOT_TOKEN: return "BOT_TOKEN belum di set di Vercel ENV!",500
  return f"Bot V53 Lolos Copilot - Khusus {BASE_ADMIN[0]} - Welcome Editable - {get_real_count()} subs LIVE",200

 try:
  data=request.get_json()
  if not data: return "ok",200
  
  # FIX Copilot: proteksi chat type - cuma terima private & callback
  if "callback_query" in data:
   cq=data["callback_query"]; cb=cq["data"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]
   fn=cq["from"].get("first_name","Bos")
   tg_post("answerCallbackQuery",{"callback_query_id":cq["id"]})
   
   if cb=="main":
    g=get_global()
    tg_post("sendMessage",{"chat_id":cid,"text":g.get("welcome","Hi").replace("{name}",fn),"reply_markup":{"inline_keyboard":[[{"text":"Admin Panel","callback_data":"admin"}]]}})
    return "ok",200

   if not is_admin(cid): return "ok",200
   
   members=load(FILES["members"],{}); blocked=load(FILES["blocked"],{}); quota=load(FILES["quota"],{}); g=get_global()
   
   if cb=="admin":
    real=get_real_count(); total=sum(v.get("text",0)+v.get("media",0) for v in quota.values())
    txt=f"👑 ADMIN PANEL - KHUSUS LU\n______________________________________\n\n📢 Subs: {real} LIVE\n👥 Users: {len(members)}\n🚫 Blocked: {len(blocked)}\n📊 Posts: {total}\n\nID: {cid} - Full Akses!\nToken: {'OK' if BOT_TOKEN else 'KOSONG!'}"
    kb={"inline_keyboard":[[{"text":"📢 Real Count","callback_data":"admin"},{"text":"👥 All Users","callback_data":"all"}],[{"text":"🚫 Blocked","callback_data":"blocked"},{"text":"🔍 Search","callback_data":"s_info"}],[{"text":"⛔ Blok","callback_data":"b_info"},{"text":"✅ Unblok","callback_data":"ub_info"}],[{"text":"🗑️ Hapus","callback_data":"h_info"},{"text":"🔄 Reset Quota","callback_data":"r_info"}],[{"text":"✏️ Edit Welcome","callback_data":"e_welcome"}],[{"text":"⬅️ Back","callback_data":"main"}]]}
    tg_post("editMessageText",{"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":kb}); return "ok",200
   
   if cb=="all":
    txt="ALL USERS 20 terbaru\n"+"\n".join([f"{v.get('name','-')} {k}" for k,v in list(members.items())[-20:]]) or "0"
    tg_post("editMessageText",{"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin"}]]}}); return "ok",200
   
   infos={
    "blocked":f"BLOCKED {len(blocked)}\n"+"\n".join(list(blocked.keys())[:30]) or "0",
    "s_info":"Kirim: /search ID",
    "b_info":"Kirim: /block ID\nContoh: /block 123",
    "ub_info":"Kirim: /unblock ID",
    "h_info":"Kirim: /deluser ID",
    "r_info":"Kirim: /resetquota ID atau /resetquota all",
    "e_welcome":f"EDIT WELCOME KHUSUS LU\n______________________________________\nKirim:\n/setwelcome teks baru\nPakai {{name}} untuk nama user\n\nWelcome sekarang:\n{g.get('welcome','')[:1000]}"
   }
   if cb in infos:
    tg_post("editMessageText",{"chat_id":cid,"message_id":mid,"text":infos[cb],"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin"}]]}}); return "ok",200

  if "message" not in data: return "ok",200
  msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
  
  # FIX Copilot: chat type - tolak grup/channel, cuma private
  chat_type=msg["chat"].get("type","")
  if chat_type!="private": return "ok",200

  # FIX Copilot: cek blocked di awal handler pesan (bukan cuma di admin)
  if is_blocked(cid) and not is_admin(cid):
   tg_post("sendMessage",{"chat_id":cid,"text":"⛔ You are blocked"}); return "ok",200

  members=load(FILES["members"],{})
  if str(cid) not in members:
   members[str(cid)]={"name":msg["from"].get("first_name","-"),"username":msg["from"].get("username","-")}; save(FILES["members"],members)

  if is_admin(cid) and text.startswith("/"):
   if text.startswith("/setwelcome "):
    w=text.replace("/setwelcome ","",1); g=get_global(); g["welcome"]=w; save(FILES["global"],g)
    tg_post("sendMessage",{"chat_id":cid,"text":f"✅ Welcome updated!\n\n{w}"}); return "ok",200
   if text.startswith("/block "):
    try: t=text.split()[1]; b=load(FILES["blocked"],{}); b[str(t)]="blocked"; save(FILES["blocked"],b); tg_post("sendMessage",{"chat_id":cid,"text":f"{t} diblokir"})
    except: pass
    return "ok",200
   if text.startswith("/unblock "):
    try: t=text.split()[1]; b=load(FILES["blocked"],{}); b.pop(str(t),None); save(FILES["blocked"],b); tg_post("sendMessage",{"chat_id":cid,"text":f"{t} di-unblok"})
    except: pass
    return "ok",200
   if text.startswith("/search "):
    try: t=text.split()[1]; m=load(FILES["members"],{}); tg_post("sendMessage",{"chat_id":cid,"text":str(m.get(str(t),"Not found"))})
    except: pass
    return "ok",200
   if text.startswith("/resetquota "):
    try:
     t=text.split()[1]; q=load(FILES["quota"],{})
     if t=="all": q={}
     else: [q.pop(k) for k in list(q.keys()) if k.startswith(str(t)+"_")]
     save(FILES["quota"],q); tg_post("sendMessage",{"chat_id":cid,"text":"✅ Quota reset"})
    except: pass
    return "ok",200

  if text.startswith(("/start","/menu")):
   g=get_global(); tg_post("sendMessage",{"chat_id":cid,"text":g.get("welcome","Hi").replace("{name}",msg["from"].get("first_name","Bos")),"reply_markup":{"inline_keyboard":[[{"text":"Admin Panel","callback_data":"admin"}]] if is_admin(cid) else []}}); return "ok",200

  # MENFESS LOGIC
  quota=load(FILES["quota"],{}); key=f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
  if key not in quota: quota[key]={"text":0,"media":0}
  g=get_global(); lt=g.get("limit_text",5); lm=g.get("limit_media",5)
  is_media="photo" in msg; raw=msg.get("caption") or msg.get("text") or ""
  if not raw and not is_media: return "ok",200
  if is_media and quota[key].get("media",0)>=lm: tg_post("sendMessage",{"chat_id":cid,"text":f"Limit media {lm}/hari tercapai"}); return "ok",200
  if not is_media and quota[key].get("text",0)>=lt: tg_post("sendMessage",{"chat_id":cid,"text":f"Limit text {lt}/hari tercapai"}); return "ok",200
  
  caption=raw+(g.get("hashtag","") if "jogjalend" not in raw.lower() else "")
  if is_media:
   fid=msg["photo"][-1]["file_id"]
   rf=tg_post("getFile",{"file_id":fid})
   if not rf.get("ok"): return "ok",200
   fp=rf["result"]["file_path"]
   try:
    fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}",timeout=20).content
    res=tg_post("sendPhoto",{"chat_id":CHANNEL_ID,"caption":caption},{"photo":("a.jpg",fb,"image/jpeg")})
   except: res={"ok":False}
  else: res=tg_post("sendMessage",{"chat_id":CHANNEL_ID,"text":caption})

  if res.get("ok"):
   if is_media: quota[key]["media"]=quota[key].get("media",0)+1
   else: quota[key]["text"]=quota[key].get("text",0)+1
   save(FILES["quota"],quota)
   tg_post("sendMessage",{"chat_id":cid,"text":f"✅ Sent! {quota[key].get('text',0)}/{lt} text, {quota[key].get('media',0)}/{lm} media"})
 except Exception as e: print(f"ERR: {e}")
 return "ok",200