from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# التوكن ومعرف قناتك الخاصة
BOT_TOKEN = "8781535112:AAGZMYuxEnDKscV3DBlc3cKUyohLCyIeX0g"
CHANNEL_ID = "-1002511482830"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400

    message_text = data.get("text", "إشارة جديدة من مؤشر King of Reversals")

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": str(message_text)
    }

    try:
        response = requests.post(telegram_url, json=payload, timeout=10)
        result = response.json()

        if response.ok and result.get("ok") is True:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "telegram_error", "details": result}), 502

    except requests.RequestException as e:
        return jsonify({"status": "error", "details": str(e)}), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

