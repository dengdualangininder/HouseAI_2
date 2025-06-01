from dotenv import load_dotenv
load_dotenv()

import os
import traceback
from flask import Flask, request, abort
from linebot.v3.messaging import (
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.messaging.api_client import ApiClient
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent
from linebot.v3.exceptions import InvalidSignatureError
import google.generativeai as genai

# 設定環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or input("請輸入 Line Channel Access Token: ")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET") or input("請輸入 Line Channel Secret: ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or input("請輸入 Gemini API Key: ")

# 初始化 LINE 和 Gemini
api_client = ApiClient(Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN))
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')  # 使用通用模型

app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    print(f"收到請求內容:\n{body}")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        print(f"簽名錯誤: {str(e)}")
        abort(400)
    except Exception as e:
        print(f"未預期錯誤: {traceback.format_exc()}")
        abort(500)
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    try:
        print(f"收到訊息: {event.message.text}")
        response = model.generate_content(event.message.text)
        print(f"Gemini 回覆: {response.text}")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response.text)]
            )
        )
    except Exception as e:
        print(f"錯誤詳情: {str(e)}")
        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"錯誤: {str(e)}")]
                )
            )
        except Exception as line_error:
            print(f"LINE 回覆錯誤: {str(line_error)}")

if __name__ == "__main__":
    print("請在另一個終端執行: ngrok http 5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
