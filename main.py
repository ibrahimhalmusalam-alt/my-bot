import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "7963385750:AAHs_k1f3v9gQ2t9v7z8x6c5b4n3m2l1k0"
TELEGRAM_CHAT_ID = "-1004362577027"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # استلام البيانات سواء أرسلت كـ JSON أو نص مباشر
        data = request.get_json(silent=True)
        if data and "text" in data:
            msg_text = data["text"]
        else:
            msg_text = request.data.decode('utf-8') or "تنبيه جديد من ملك الانعكاس"
            
        send_telegram_message(msg_text)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/', methods=['GET'])
def home():
    return "Bot is running successfully!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

