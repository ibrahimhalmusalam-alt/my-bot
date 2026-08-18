from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1004362577027"


def clean_and_format(text):
    """
    تنسيق رسائل TradingView بدون تداخل بين الدخول
    والأهداف ووقف الخسارة.
    """
    try:
        stock_name = (
            text.split("اسم السهم:")[1].split("|")[0].strip()
            if "اسم السهم:" in text else "غير محدد"
        )

        symbol = (
            text.split("الرمز:")[1].split("|")[0].strip()
            if "الرمز:" in text else "N/A"
        )

        current_price = (
            text.split("السعر الحالي:")[1].split("|")[0].strip()
            if "السعر الحالي:" in text else ""
        )

        # ==========================================
        # 1. تحقق الهدف
        # ==========================================
        if "تحقق الهدف" in text:

            target = "غير معروف"

            if "تحقق الهدف 1" in text:
                target = "1"
            elif "تحقق الهدف 2" in text:
                target = "2"
            elif "تحقق الهدف 3" in text:
                target = "3"

            change_pct = (
                text.split("التغير:")[1].split("|")[0].strip()
                if "التغير:" in text else ""
            )

            msg = (
                f"🏆 تم تحقيق الهدف {target} بنجاح!\n\n"
                f"📌 السهم: {stock_name}\n"
                f"🏷 الرمز: {symbol}"
            )

            if current_price:
                msg += f"\n💰 السعر الحالي: {current_price}"

            if change_pct:
                msg += f"  |  📈 التغير: {change_pct}"

            return msg

        # ==========================================
        # 2. وقف الخسارة
        # ==========================================
        elif "وقف الخسارة" in text and "دخول" not in text:

            stop_price = (
                text.split("وقف الخسارة:")[1].split("|")[0].strip()
                if "وقف الخسارة:" in text else ""
            )

            msg = (
                f"🛑 ضرب وقف الخسارة\n\n"
                f"📌 السهم: {stock_name}\n"
                f"🏷 الرمز: {symbol}"
            )

            if current_price:
                msg += f"\n💰 السعر الحالي: {current_price}"

            if stop_price:
                msg += f"\n📉 سعر الوقف: {stop_price}"

            return msg

        # ==========================================
        # 3. صفقة جديدة
        # ==========================================
        elif "دخول" in text or "شراء" in text or "صفقة جديدة" in text:

            entry_price = (
                text.split("سعر الدخول:")[1].split("|")[0].strip()
                if "سعر الدخول:" in text else ""
            )

            t1 = (
                text.split("الهدف 1:")[1].split("|")[0].strip()
                if "الهدف 1:" in text else ""
            )

            t2 = (
                text.split("الهدف 2:")[1].split("|")[0].strip()
                if "الهدف 2:" in text else ""
            )

            t3 = (
                text.split("الهدف 3:")[1].split("|")[0].strip()
                if "الهدف 3:" in text else ""
            )

            stop_loss = (
                text.split("وقف الخسارة:")[1].split("|")[0].strip()
                if "وقف الخسارة:" in text else ""
            )

            msg = (
                f"🚀 صفقة جديدة\n\n"
                f"📌 السهم: {stock_name}\n"
                f"🏷 الرمز: {symbol}"
            )

            if entry_price:
                msg += f"\n💵 سعر الدخول: {entry_price}"

            if current_price:
                msg += f"\n📍 السعر الحالي: {current_price}"

            if t1 or t2 or t3:
                msg += "\n\n🎯 الأهداف:"

                if t1:
                    msg += f"\n• الهدف 1: {t1}"

                if t2:
                    msg += f"\n• الهدف 2: {t2}"

                if t3:
                    msg += f"\n• الهدف 3: {t3}"

            if stop_loss:
                msg += f"\n\n🛑 وقف الخسارة: {stop_loss}"

            return msg

        # ==========================================
        # 4. أي رسالة غير معروفة
        # ==========================================
        return text

    except Exception as e:
        print(f"❌ Formatting error: {e}")
        return text


@app.route('/webhook', methods=['POST'])
def webhook():

    try:
        data = request.get_json(silent=True)

        if not data or "text" not in data:
            return jsonify({
                "success": False,
                "error": "Invalid JSON or missing text"
            }), 400

        message_text = data.get("text")
        final_message = clean_and_format(message_text)

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": CHANNEL_ID,
            "text": final_message
        }

        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        telegram_result = response.json()

        # Telegram رفض الرسالة
        if not telegram_result.get("ok"):
            print("❌ Telegram Error:")
            print(telegram_result)

            return jsonify({
                "success": False,
                "telegram_error": telegram_result
            }), 500

        # Telegram قبل الرسالة
        print("✅ Telegram message sent successfully")

        return jsonify({
            "success": True
        }), 200

    except Exception as e:

        print(f"❌ Webhook Error: {e}")

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000
    )
