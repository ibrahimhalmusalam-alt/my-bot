import os
import json
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
        raw_data = request.data.decode('utf-8')
        
        # محاولة استخراج النص النظيف إذا كان مرسل بصيغة JSON معقدة
        message_to_send = ""
        try:
            parsed_json = json.loads(raw_data)
            if isinstance(parsed_json, dict):
                # البحث عن مفتاح النص أو محاولة تجميع الحقول المهمة
                message_to_send = parsed_json.get("text") or str(parsed_json)
            else:
                message_to_send = raw_data
        except:
            message_to_send = raw_data

        # تنظيف النص إذا احتوى على صيغة الـ JSON المزعجة وتصفية رسالة الهدف والسهم
        if "Middle East Healthcare" in message_to_send or "الهدف" in message_to_send:
            # إعادة صياغة النص بشكل مرتب وجميل للقناة
            clean_msg = "🏆 *تنبيه ملك الانعكاس السعودي*\n\n"
            if "الهدف 3 النهائي" in message_to_send:
                clean_msg += "📌 *الحالة:* تحقق الهدف 3 النهائي\n"
            elif "الهدف" in message_to_send:
                clean_msg += "📌 *الحالة:* تحقق هدف جديد\n"
                
            clean_msg += "🏢 *اسم السهم:* Middle East Healthcare Company\n"
            clean_msg += "🔢 *الرمز:* 4009\n"
            clean_msg += "entry *سعر الدخول:* 30.98\n"
            clean_msg += "🎯 *الهدف 1:* 31.24\n"
            clean_msg += "🎯 *الهدف 2:* 31.48\n"
            clean_msg += "🎯 *الهدف 3:* 31.74\n"
            clean_msg += "🛑 *وقف الخسارة:* 30.06"
            message_to_send = clean_msg

        send_telegram_message(message_to_send)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/', methods=['GET'])
def home():
    return "Bot is running successfully!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

