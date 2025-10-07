from flask import Flask, request, abort

app = Flask(__name__)

@app.route("/", methods=['GET'])
def home():
    return "Tina Assistant is running!", 200

@app.route("/", methods=['POST'])
def callback():
    # LINEからのWebhook確認用
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
