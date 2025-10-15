from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import openai
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# 環境変数
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY


# ---- Wikipediaスクレイピング関数 ----
def wiki_search(keyword):
    try:
        url = f"https://ja.wikipedia.org/wiki/{keyword}"
        res = requests.get(url)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            text = soup.get_text()
            # 長すぎるので最初の1000文字だけ使う
            summary = text[:1000]
            return summary
        else:
            return "Wikipediaで情報が見つかりませんでした。"
    except Exception as e:
        return f"検索中にエラーが発生しました: {e}"


@app.route("/", methods=['GET'])
def index():
    return "LINE Bot with ChatGPT + Wikipedia Search is running!", 200


@app.route("/", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# ---- LINEメッセージイベント ----
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    try:
        # Wikipedia検索を実行
        wiki_result = wiki_search(user_message)

        # ChatGPTで要約＆回答生成
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは日本語で説明するAIアシスタントです。Wikipediaの内容をもとに簡潔にまとめて答えてください。"},
                {"role": "user", "content": f"次の情報を要約して説明してください:\n{wiki_result}"}
            ]
        )

        ai_reply = response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        ai_reply = f"エラーが発生しました: {e}"

    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_reply)
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
