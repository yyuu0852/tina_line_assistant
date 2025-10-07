from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "LINE Bot is running!", 200

@app.route("/", methods=["POST"])
def webhook():
    print("Received POST request from LINE")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
