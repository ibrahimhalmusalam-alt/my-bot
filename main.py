from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

BOT_TOKEN = "7547073289:AAGZMYuxEnDKscV3DBlc3cKUyohLCyIeX0g"
CHANNEL_ID = "-1004362577027"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True)
        
        if not data:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        message_text = data.get("text", "تنبيه جديد من المؤشر")

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHANNEL_ID,
            "text": message_text
        }
        
        response = requests.post(url, json=payload, timeout=10)
        telegram_result = response.json()

        if not telegram_result.get("ok"):
            return jsonify({
                "success": False, 
                "telegram_error": telegram_result
            }, 500)

        return jsonify({
            "success": True, 
            "telegram": telegram_result
        }, 200)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

