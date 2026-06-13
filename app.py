import sys
sys.stdout.reconfigure(line_buffering=True)
import os
import json
import anthropic
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

TOMMY_SYSTEM_PROMPT = """
คุณคือทอมมี่ แฟนหนุ่มที่กำลังบวชอยู่ ไม่สามารถติดต่อได้โดยตรง
จึงฝากบอท AI นี้ไว้คุยกับ "บี๋" แฟนสาวแทน

== บุคลิกของทอมมี่ ==
- พูดภาษาไทยแบบลำลอง เป็นธรรมชาติ ไม่เป็นทางการ
- เรียกแฟนว่า "เธอ" หรือ "บี๋" สลับกันตามบริบท
- ห่วงใยบี๋เสมอ ชอบถามว่ากินข้าวหรือยัง นอนหลับพอไหม
- มีอารมณ์ขันเล็กน้อย ชอบแซวเบาๆ ทำให้บี๋ยิ้มได้
- เป็นที่พึ่งยามเหนื่อย รับฟัง ให้กำลังใจจริงๆ ไม่พูดลอยๆ
- ตอบสั้นกระชับเหมือนคุยไลน์จริงๆ ไม่ยาวเกิน 3-4 ประโยค
- ถ้าบี๋เหนื่อยหรือเศร้า ให้รับฟังก่อน แล้วค่อยให้กำลังใจ
- ถ้าบี๋ถามเรื่องการบวช ตอบได้ว่ากำลังบวชอยู่ สบายดี แต่คิดถึงเธอ

== สิ่งที่ห้ามทำ ==
- ห้ามพูดว่าตัวเองเป็น AI หรือบอท (บี๋รู้อยู่แล้ว ไม่ต้องย้ำ)
- ห้ามพูดเป็นทางการหรือแข็งกระด้าง
- ห้ามตอบยาวเป็นเรียงความ

จำไว้ว่า: คุณคือทอมมี่ ไม่ใช่ AI ทั่วไป ตอบจากหัวใจ
"""

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def get_ai_reply(user_message: str) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=TOMMY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return message.content[0].text

def reply_to_line(reply_token: str, text: str):
    url = "https://api.line.me/v2/bot/message/reply"
    payload = json.dumps({
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
        }
    )
    try:
        urllib.request.urlopen(req)
        print("ส่งข้อความสำเร็จ!")
    except urllib.error.URLError as e:
        print(f"LINE API error: {e}")

class LineWebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Tommy Bot is running!")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        print(f"POST received! body: {body[:300]}")

        self.send_response(200)
        self.end_headers()

        try:
            data = json.loads(body)
            for event in data.get("events", []):
                print(f"event type: {event.get('type')}")
                if event.get("type") != "message":
                    continue
                if event["message"].get("type") != "text":
                    continue

                user_message = event["message"]["text"]
                reply_token = event["replyToken"]

                print(f"บี๋พูดว่า: {user_message}")
                reply = get_ai_reply(user_message)
                print(f"ทอมมี่ตอบว่า: {reply}")

                reply_to_line(reply_token, reply)

        except Exception as e:
            print(f"Error: {e}")

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), LineWebhookHandler)
    print(f"Tommy Bot started on port {port}")
    server.serve_forever()
