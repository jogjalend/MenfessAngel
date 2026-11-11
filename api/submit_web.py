# api/submit_web.py - KHUSUS tombol Kirim di Web
# api/index.py JANGAN DIUBAH, ini file terpisah

import os
import json
import base64
import requests
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # contoh: -1001234567890

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode('utf-8') or '{}')

            username = data.get("username", "anon")
            content = data.get("content", "")
            photo = data.get("photo", "")

            if not content or not photo:
                self._send(400, {"ok": False, "error": "Foto & deskripsi wajib diisi"})
                return

            if not BOT_TOKEN or not CHANNEL_ID:
                self._send(500, {"ok": False, "error": "BOT_TOKEN / CHANNEL_ID belum di-set di Vercel"})
                return

            caption = f"💌 PROMOTE BARU\n\n{content}\n\n👤 Dari: @{username}\n#jogjalend"

            if "," in photo:
                photo = photo.split(",", 1)[1]
            img_bytes = base64.b64decode(photo)

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            files = {"photo": ("promote.jpg", img_bytes, "image/jpeg")}
            payload = {"chat_id": CHANNEL_ID, "caption": caption}

            r = requests.post(url, data=payload, files=files, timeout=30)
            tg = r.json()

            if not tg.get("ok"):
                self._send(500, {"ok": False, "error": tg.get("description", "Gagal kirim ke channel")})
                return

            self._send(200, {"ok": True})

        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})

    def _send(self, code, obj):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(405, {"ok": False, "error": "Method not allowed"})
