from flask import Flask, request
import os, json, requests, re
app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@menfessangel"
SESSION = requests.Session()

def clean(s):
  return re.sub(r'[^A-Za-z0-9 ]','',s).strip()[:12] or "Kamu"

def main_menu():
  return {"inline_keyboard":[
    [{"text":"My Profile","callback_data":"a"}],
    [{"text":"Rules","callback_data":"b"},{"text":"Post","callback_data":"c"}],
    [{"text":"Threads Setting","callback_data":"d"}],
    [{"text":"Admin Panel","callback_data":"admin"}],
    [{"text":"Stats","callback_data":"e"},{"text":"Help","callback_data":"f"}]
  ]}

@app.route("/", methods=['GET','POST'])
@app.route("/api/index.py", methods=['GET','POST'])
def handler():
  if request.method=='GET':
    return "V47.3 ULTRA CLEAN - READY",200
  try:
    data=request.get_json()
    if not data: return "ok",200
    if "callback_query" in data:
      cq=data["callback_query"]; cid=cq["message"]["chat"]["id"]; mid=cq["message"]["message_id"]
      SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]})
      txt=f"Hi {clean(cq['from'].get('first_name','Kamu'))}!\nPromote your account here!\n______________________________________\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend [optional]\n- X -> @jogjalendpm [maintenance]\n\nTap Post to start!"
      SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",json={"chat_id":cid,"message_id":mid,"text":txt,"reply_markup":main_menu()})
      return "ok",200
    if "message" in data:
      msg=data["message"]; cid=msg["chat"]["id"]; fn=clean(msg["from"].get("first_name","Kamu"))
      if msg.get("text","").startswith("/start"):
        txt=f"Hi {fn}!\nPromote your account here!\n______________________________________\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend [optional]\n- X -> @jogjalendpm [maintenance]\n\nTap Post to start!"
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":main_menu()})
  except Exception as e: print(e)
  return "ok",200
