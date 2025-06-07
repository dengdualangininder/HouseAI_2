from dotenv import load_dotenv
load_dotenv()

import sys
import logging
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

from google import genai
from google.genai import types
from functioncalling import time_function_declaration, get_current_time

# 設定環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not all([LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, GEMINI_API_KEY]):
    print("缺少必要的環境變數，程式無法啟動")
    sys.exit(1)

# 初始化 LINE 和 Gemini
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
api_client = ApiClient(Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN))
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    logging.info("Callback triggered")
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    logging.info(f"收到請求內容:\n{body}")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        logging.error(f"簽名錯誤: {str(e)}")
        abort(400)
    except Exception as e:
        logging.error(f"未預期錯誤: {traceback.format_exc()}")
        abort(500)
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    try:
        user_message = event.message.text
        logging.info(f"收到訊息: {user_message}")

        # 呼叫 Gemini 並啟用 function calling
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # 建議用最新支援 function calling 的模型
            contents=user_message,
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=[time_function_declaration])],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="AUTO")
                )
            )
        )

        # 判斷是否有 function call
        candidates = response.candidates
        reply_text = None
        if candidates and candidates[0].content.parts:
            part = candidates[0].content.parts[0]
            if hasattr(part, "function_call") and part.function_call:
                function_call = part.function_call
                logging.info(f"Function to call: {function_call.name}")
                logging.info(f"Arguments: {function_call.args}")
                if function_call.name == "get_current_time":
                    reply_text = get_current_time()
                else:
                    reply_text = "無法處理的 function call"
            elif hasattr(part, "text") and part.text:
                reply_text = part.text
        if not reply_text:
            reply_text = "無法生成回覆"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )
    except Exception as e:
        logging.error(f"錯誤詳情: {traceback.format_exc()}")
        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="抱歉，處理訊息時發生錯誤")]
                )
            )
        except Exception as line_error:
            logging.error(f"LINE 回覆錯誤: {str(line_error)}")

if __name__ == "__main__":
    logging.info("啟動 Flask 伺服器")
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5001)), debug=False)
