from flask import Flask, request
import os, json, requests, re
from datetime import datetime, timezone, timedelta
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
BASE_ADMIN = [8584319568]

FILES = {"quota":"/tmp/quota.json","members":"/tmp/members.json","blocked":"/tmp/blocked.json","global":"/tmp/global.json"}

def load(p,d=None):
 try:
  if os.path.exists(p):
   with open(p,"r") as f: return json.load(f)
 except: pass
 return d if d is not None else {}
def save(p,d):
 try:
  with open(p,"w") as f: json.dump(d,f)
 except: pass
def clean(s):
  if not s: return "Kamu"
  c = re.sub(r'[^A-Za-z0-9 ]','',str(s)).strip()[:15]
  return c if len(c)>=2 else "Kamu"
def get_global():
 g=load(FILES["global"],{})
 if not g: g={"limit_text":5,"limit_media":5,"hashtag":"\n\n#jogjalend","rules":"1. No spam\n2. No SARA\n3. Max 5/hari","threads_enabled":False,"threads_user":"@jogjalend"}; save(FILES["global"],g)
 if "threads_enabled" not in g: g["threads_enabled"]=False
 if "threads_user" not in g: g["threads_user"]="@jogjalend"
 return g
def is_admin(cid):
 try: return int(cid) in BASE_ADMIN
 except: return False
def get_real():
 try:
  r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}",timeout=10).json()
  if r.get("ok"): return r["result"]
 except: pass
 return 659
def main_menu(cid):
 btn=[[{"text":"My Profile","callback_data":"profil"}],[{"text":"Rules","callback_data":"rules"},{"text":"Post","callback_data":"post"}],[{"text":"Threads Setting","callback_data":"threads"}]]
 if is_admin(cid): btn.append([{"text":"Admin Panel","callback_data":"admin"}])
 btn.append([{"text":"Stats","callback_data":"stats"},{"text":"Help","callback_data":"help"}])
 return {"inline_keyboard":btn}
def welcome_msg(name): return f"Hi {name}!\nPromote your account here!\n______________________________________\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend [optional]\n- X -> @jogjalendpm [maintenance]\n\nTap Post to start!"

@app.route("/", methods=['GET','POST'])
@app.route("/api/index.py", methods=['GET','POST'])
def handler():
 if request.method=='GET': return f"V47.4.1 FIX BACK - {get_real()} LIVE",200
 try:
  data=request.get_json()
  if not data: return "ok",200
  if "callback_query" in data:
   cq=data["callback_query"]; cb=cq["data"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]; fn=clean(cq["from"].get("first_name"))
   is_photo = "photo" in cq["message"]
   SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})

   # FIX BACK DARI FOTO STATS
   if cb=="main":
    if is_photo:
     try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid},timeout=5)
     except: pass
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":welcome_msg(fn),"reply_markup":main_menu(cid)})
    else:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":welcome_msg(fn),"reply_markup":main_menu(cid)})
    return "ok",200

   if cb=="profil":
    g=get_global(); q=load(FILES["quota"],{}); key=f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"; cur=q.get(key,{"text":0,"media":0})
    txt=f"My Profile\nID: {cid}\nName: {fn}\n\nToday:\nText: {cur['text']}/{g['limit_text']}\nMedia: {cur['media']}/{g['limit_media']}"
    if is_photo:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
    else:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
    return "ok",200

   if cb=="threads":
    g=get_global(); status="ON ✅" if g["threads_enabled"] else "OFF ❌"
    txt=f"Threads Setting\n\nStatus: {status}\nUsername: {g['threads_user']}\n\nAuto repost ke Threads (optional)\n/setthreads @username\n/threadson / /threadsoff"
    kb={"inline_keyboard":[[{"text":"Turn ON" if not g["threads_enabled"] else "Turn OFF","callback_data":"threads_toggle"}],[{"text":"Set @jogjalend","callback_data":"threads_set"}],[{"text":"Back","callback_data":"main"}]]}
    if is_photo:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb})
    else:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":kb})
    return "ok",200

   if cb=="threads_toggle":
    if not is_admin(cid): return "ok",200
    g=get_global(); g["threads_enabled"]=not g["threads_enabled"]; save(FILES["global"],g)
    status="ON ✅" if g["threads_enabled"] else "OFF ❌"
    # after toggle, delete photo if any and send new
    if is_photo: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Threads {status}\nUser: {g['threads_user']}","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"threads"}]]}})
    return "ok",200

   if cb=="stats":
    g=get_global(); members=load(FILES["members"],{}); quota=load(FILES["quota"],{}); blocked=load(FILES["blocked"],{})
    real=get_real(); today=datetime.now(WIB).strftime('%Y-%m-%d'); today_posts=sum(1 for k in quota.keys() if today in k); total_posts=sum(v.get("text",0)+v.get("media",0) for v in quota.values())
    txt=f"📊 Stats LIVE\n\nChannel: {real} LIVE\nUsers: {len(members)}\nBlocked: {len(blocked)}\nTotal Posts: {total_posts}\nToday: {today_posts}\nThreads: {g['threads_user']} ({'ON' if g['threads_enabled'] else 'OFF'})\nUpdated: {datetime.now(WIB).strftime('%d/%m %H:%M')} WIB"
    img_url=f"https://via.placeholder.com/600x300/0f7a3a/ffffff?text=Channel+{real}+LIVE%0AUsers+{len(members)}+Posts+{total_posts}"
    if is_photo:
     # update caption aja kalau sudah foto
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption",json={"chat_id":cid,"message_id":mid,"caption":txt,"reply_markup":{"inline_keyboard":[[{"text":"Refresh","callback_data":"stats"},{"text":"Back","callback_data":"main"}]]}})
    else:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",json={"chat_id":cid,"photo":img_url,"caption":txt,"reply_markup":{"inline_keyboard":[[{"text":"Refresh","callback_data":"stats"},{"text":"Back","callback_data":"main"}]]}})
     try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
     except: pass
    return "ok",200

   # RULES POST HELP DLL
   if cb in ["rules","post","help","b_info","blocked","all"]:
    g=get_global()
    maps={"rules":f"Rules\n{g['rules']}","post":"Kirim teks/foto/video langsung ke bot!","help":"Help: Kirim menfess auto post","b_info":"Ketik /block ID","blocked":f"Blocked {len(load(FILES['blocked'],{}))}","all":"All Users"}
    txt=maps.get(cb,cb)
    if cb=="blocked":
     b=load(FILES["blocked"],{}); txt=f"Blocked {len(b)}\n"+"\n".join(b.keys()) or "0"
    if cb=="all":
     m=load(FILES["members"],{}); txt="All Users\n"+"\n".join([f"{clean(v.get('name','-'))} {k}" for k,v in list(m.items())[-20:]]) or "0"
    if is_photo:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
    else:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"main"}]]}})
    return "ok",200

   if not is_admin(cid): return "ok",200
   if cb=="admin":
    members=load(FILES["members"],{}); blocked=load(FILES["blocked"],{}); quota=load(FILES["quota"],{}); real=get_real(); total=sum(v.get("text",0)+v.get("media",0) for v in quota.values())
    txt=f"Admin Panel\nSubs: {real} LIVE\nUsers: {len(members)}\nBlocked: {len(blocked)}\nPosts: {total}"
    if is_photo:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",json={"chat_id":cid,"message_id":mid})
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"All Users","callback_data":"all"}],[{"text":"Blocked","callback_data":"blocked"}],[{"text":"Back","callback_data":"main"}]]}})
    else:
     SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"All Users","callback_data":"all"}],[{"text":"Blocked","callback_data":"blocked"}],[{"text":"Back","callback_data":"main"}]]}})
    return "ok",200

  if "message" not in data: return "ok",200
  msg=data["message"]; cid=msg["chat"]["id"]; text=msg.get("text","")
  members=load(FILES["members"],{})
  if str(cid) not in members: members[str(cid)]={"name":clean(msg["from"].get("first_name"))}; save(FILES["members"],members)

  if is_admin(cid) and text.startswith("/"):
   g=get_global()
   if text.startswith("/setthreads "): u=text.split()[1]; g["threads_user"]=u; save(FILES["global"],g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Threads user {u}"}); return "ok",200
   if text.startswith("/threadson"): g["threads_enabled"]=True; save(FILES["global"],g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Threads ON"}); return "ok",200
   if text.startswith("/threadsoff"): g["threads_enabled"]=False; save(FILES["global"],g); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Threads OFF"}); return "ok",200
   if text.startswith("/block "): t=text.split()[1]; b=load(FILES["blocked"],{}); b[t]="x"; save(FILES["blocked"],b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{t} blocked"}); return "ok",200
   if text.startswith("/unblock "): t=text.split()[1]; b=load(FILES["blocked"],{}); b.pop(t,None); save(FILES["blocked"],b); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"{t} unblocked"}); return "ok",200
   if text.startswith("/resetquota "): t=text.split()[1]; q=load(FILES["quota"],{}); 
    if t=="all": q={}
    else: 
     for k in list(q.keys()):
      if k.startswith(t+"_"): q.pop(k)
    save(FILES["quota"],q); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Quota reset"}); return "ok",200

  if text.startswith(("/start","/menu")):
   fn=clean(msg["from"].get("first_name")); SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":welcome_msg(fn),"reply_markup":main_menu(cid)}); return "ok",200

  quota=load(FILES["quota"],{}); blocked=load(FILES["blocked"],{})
  if str(cid) in blocked: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":"Kamu di blokir"}); return "ok",200
  key=f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
  if key not in quota: quota[key]={"text":0,"media":0}
  g=get_global(); is_media="photo" in msg; raw=msg.get("caption") or msg.get("text") or ""
  if not raw and not is_media: return "ok",200
  if is_media and quota[key]["media"]>=g["limit_media"]: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Limit media {g['limit_media']}/hari"}); return "ok",200
  if not is_media and quota[key]["text"]>=g["limit_text"]: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"Limit text {g['limit_text']}/hari"}); return "ok",200
  caption=raw+(g["hashtag"] if "jogjalend" not in raw.lower() else "")
  if is_media:
   fid=msg["photo"][-1]["file_id"]; r=SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json(); fb=SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
   res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={"chat_id":CHANNEL_ID,"caption":caption},files={"photo":("a.jpg",fb,"image/jpeg")}).json()
  else: res=SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHANNEL_ID,"text":caption}).json()
  if res.get("ok"):
   if is_media: quota[key]["media"]+=1
   else: quota[key]["text"]+=1
   save(FILES["quota"],quota)
   SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":f"✅ Sent! {quota[key]['text']}/{g['limit_text']} {quota[key]['media']}/{g['limit_media']}"})
 except Exception as e: print(e)
 return "ok",200
