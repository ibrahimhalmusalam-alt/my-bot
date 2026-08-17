from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1004362577027"

def clean_and_format(text):
    """
    تستخرج فقط المهم من الرسالة الطويلة وتنسقها بشكل مرتب
    """
    try:
        # استخراج اسم السهم والرمز
        # نبحث عن السهم والرمز في النص الأصلي وننظفهم
        if "اسم السهم:" in text:
            stock_name = text.split("اسم السهم:")[1].split("|")[0].strip()
        else:
            stock_name = "غير محدد"

        if "الرمز:" in text:
            symbol = text.split("الرمز:")[1].split("|")[0].strip()
        else:
            symbol = "N/A"

        # تحديد نوع الرسالة
        if "تحقق الهدف" in text:
            # استخراج رقم الهدف
            target = "غير معروف"
            if "الهدف 1" in text and "الهدف المحقق: 1" in text: target = "1"
            elif "الهدف 2" in text and "الهدف المحقق: 2" in text: target = "2"
            elif "الهدف 3" in text and "الهدف المحقق: 3" in text: target = "3"
            
            return f"🏆 تم تحقيق الهدف {target} بنجاح!\n\n📌 السهم: {stock_name}\n🏷 الرمز: {symbol}"
        
        elif "دخول" in text:
            return f"🚀 صفقة جديدة\n\n📌 السهم: {stock_name}\n🏷 الرمز: {symbol}\n💵 ابدأ المتابعة!"

        # إذا لم تكن أي من الحالات السابقة، نرجع النص الأصلي كما هو ولكن مرتب
        return text
    except:
        return text

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"success": False}), 400

    message_text = data.get("text")
    final_message = clean_and_format(message_text)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": final_message}
    
    requests.post(url, json=payload, timeout=15)
    return jsonify({"success": True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

