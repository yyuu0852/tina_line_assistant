from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import openai
import requests

app = Flask(__name__)

# 環境変数（Renderの Environment Variables に設定）
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")  # ← 検索用APIキーも追加！

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY


# --- 🔍 Web検索関数 ---
def web_search(query):
    try:
        headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
        params = {"q": query, "count": 3}
        res = requests.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params)
        data = res.json()
        if "webPages" in data:
            results = [f"{item['name']}: {item['url']}" for item in data["webPages"]["value"]]
            return "\n".join(results)
        else:
            return "検索結果が見つかりませんでした。"
    except Exception as e:
        return f"検索エラー: {e}"


@app.route("/", methods=['GET'])
def index():
    return "LINE Bot with ChatGPT + Web Search is running!", 200


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


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # ChatGPTにまず内容を理解させる
    try:
        # 検索が必要そうかを判断させる
        check = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "次のユーザーの質問が、検索が必要かどうかを 'はい' または 'いいえ' で答えてください。"},
                {"role": "user", "content": user_message}
            ]
        )
        needs_search = "はい" in check["choices"][0]["message"]["content"]

        if needs_search:
            search_result = web_search(user_message)
            prompt = f"次の検索結果をもとに、わかりやすく回答してください:\n\n{search_result}"
        else:
            prompt = user_message

        # ChatGPTに最終回答を生成させる
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはユーザーの質問に丁寧に答えるAIアシスタントです。"},
                {"role": "user", "content": prompt}
            ]
        )

        ai_reply = response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        ai_reply = f"エラーが発生しました: {e}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_reply)
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
