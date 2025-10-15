from flask import Flask, request, abort
from bs4 import BeautifulSoup
import requests
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI

app = Flask(__name__)

# 環境変数からLINEとOpenAIのキーを取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = OpenAI(api_key=OPENAI_API_KEY)


# --- Wikipedia 検索関数 ---
def wiki_search(keyword):
    try:
        url = f"https://ja.wikipedia.org/wiki/{keyword}"
        res = requests.get(url)
        if res.status_code != 200:
            return "Wikipediaで情報を見つけられませんでした。"
        soup = BeautifulSoup(res.text, "html.parser")
        paragraphs = soup.select("p")
        if not paragraphs:
            return "Wikipediaで情報を取得できませんでした。"
        text = "\n".join([p.get_text() for p in paragraphs[:3]])
        return text.strip()
    except Exception as e:
        return f"エラーが発生しました: {e}"


# --- LINEからのWebhook受信 ---
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# --- メッセージイベント処理 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # Wikipedia検索
    wiki_result = wiki_search(user_message)

    # OpenAIで要約生成
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは日本語で説明するAIアシスタントです。"},
                {"role": "user", "content": f"次の情報を日本語でわかりやすく要約してください:\n{wiki_result}"}
            ]
        )
        ai_reply = response.choices[0].message.content.strip()
    except Exception as e:
        ai_reply = f"エラーが発生しました: {e}"

    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_reply)
    )


# --- Render用の起動設定 ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
