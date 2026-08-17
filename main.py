from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

BOT_TOKEN = "7547073289:AAGZMYuxEnDKscV3DBlc3cKUyohLCyIeX0g"
CHANNEL_ID = "-1004362577027"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("\n==============================")
        print("📩 WEBHOOK RECEIVED")
        print("Headers:", dict(request.headers))
        print("Raw Body:", request.get_data(as_text=True))

        data = request.get_json(silent=True)

        print("JSON DATA:", data)

        if not data:
            print("❌ No JSON received")
            return jsonify({
                "success": False,
                "error": "No JSON data received"
            }), 400

        message_text = data.get("text")

        if not message_text:
            print("❌ No text field")
            return jsonify({
                "success": False,
                "error": "No text field in JSON",
                "received": data
            }), 400

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": CHANNEL_ID,
            "text": message_text
        }

        print("📤 Sending to Telegram...")
        print("Chat ID:", CHANNEL_ID)
        print("Message:", message_text)

        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        print("📥 Telegram HTTP Status:", response.status_code)
        print("📥 Telegram Response:", response.text)

        try:
            telegram_result = response.json()
        except Exception:
            telegram_result = {
                "raw_response": response.text
            }

        if not telegram_result.get("ok"):
            print("❌ TELEGRAM REJECTED MESSAGE")

            return jsonify({
                "success": False,
                "telegram_error": telegram_result
            }), 500

        print("✅ TELEGRAM ACCEPTED MESSAGE")
        print("==============================\n")

        return jsonify({
            "success": True,
            "telegram": telegram_result
        }), 200

    except Exception as e:
        print("🔥 SERVER ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000
    )

