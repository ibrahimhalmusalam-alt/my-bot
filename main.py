from flask import Flask, request, jsonify
import requests
import os
import re

app = Flask(__name__)

# =========================================================
# Telegram
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1004362577027"

# =========================================================
# الصفقة النشطة
#
# نخزن آخر رسالة فقط.
#
# Entry
#   ↓
# TP1
#   ↓
# TP2
#   ↓
# TP3
#
# بحيث كل تنبيه جديد يقتبس التنبيه السابق مباشرة.
# =========================================================

active_trades = {}


# =========================================================
# استخراج قيمة من رسالة TradingView
# =========================================================

def extract_value(text, key):

    if key not in text:
        return ""

    try:
        return text.split(key, 1)[1].split("|", 1)[0].strip()
    except Exception:
        return ""


# =========================================================
# استخراج رقم الهدف
# =========================================================

def extract_target_number(text):

    # مثال:
    # الهدف المحقق: 1

    match = re.search(r"الهدف المحقق:\s*([123])", text)

    if match:
        return match.group(1)

    # مثال:
    # closed_after_target_2

    match = re.search(r"closed_after_target_([123])", text)

    if match:
        return match.group(1)

    # احتياط إضافي
    if "تحقق الهدف 3" in text:
        return "3"

    if "تحقق الهدف 2" in text:
        return "2"

    if "تحقق الهدف 1" in text:
        return "1"

    return None


# =========================================================
# تحديد نوع التنبيه
# =========================================================

def detect_event(text):

    # -----------------------------------------------------
    # 🚀 بداية الصفقة
    # -----------------------------------------------------

    if (
        "الحالة: active" in text
        or "بداية صفقة شراء" in text
        or "صفقة جديدة" in text
    ):
        return "entry"


    # -----------------------------------------------------
    # 🛡️ وقف بعد تحقيق هدف
    # -----------------------------------------------------

    if (
        "closed_after_target_" in text
        or "إيقاف الصفقة بهدف" in text
    ):
        return "stop_after_target"


    # -----------------------------------------------------
    # 🎯 تحقيق هدف
    # -----------------------------------------------------

    if "تحقق الهدف" in text:
        return "target"


    # -----------------------------------------------------
    # 🛑 وقف خسارة
    # -----------------------------------------------------

    if (
        "closed_stop_loss" in text
        or "وقف الخسارة" in text
        or "وقف الخساره" in text
    ):
        return "stop"


    return "unknown"


# =========================================================
# تنسيق الرسائل
# =========================================================

def clean_and_format(text):

    try:

        # -------------------------------------------------
        # البيانات المشتركة
        # -------------------------------------------------

        stock_name = extract_value(text, "اسم السهم:")
        symbol = extract_value(text, "الرمز:")
        current_price = extract_value(text, "السعر الحالي:")
        change_pct = extract_value(text, "التغير:")

        if not stock_name:
            stock_name = "غير محدد"

        if not symbol:
            symbol = "N/A"

        event_type = detect_event(text)


        # =================================================
        # 🚀 بداية صفقة
        # =================================================

        if event_type == "entry":

            entry_price = extract_value(text, "سعر الدخول:")

            tp1 = extract_value(text, "الهدف 1:")
            tp2 = extract_value(text, "الهدف 2:")
            tp3 = extract_value(text, "الهدف 3:")

            stop_loss = extract_value(text, "وقف الخسارة:")

            if not stop_loss:
                stop_loss = extract_value(text, "وقف الخساره:")


            msg = (
                "🚀🔥 صفقة جديدة 🔥🚀\n\n"
                f"📌 السهم: {stock_name}\n"
                f"🏷 الرمز: {symbol}"
            )

            if entry_price:
                msg += f"\n💵 سعر الدخول: {entry_price}"

            if current_price:
                msg += f"\n📍 السعر الحالي: {current_price}"


            if tp1 or tp2 or tp3:

                msg += "\n\n🎯 الأهداف:"

                if tp1:
                    msg += f"\n🥇 الهدف 1: {tp1}"

                if tp2:
                    msg += f"\n🥈 الهدف 2: {tp2}"

                if tp3:
                    msg += f"\n🥉 الهدف 3: {tp3}"


            if stop_loss:
                msg += f"\n\n🛑 وقف الخسارة: {stop_loss}"


            return {
                "message": msg,
                "event_type": "entry",
                "symbol": symbol,
                "target": None
            }


        # =================================================
        # 🎯 تحقيق هدف
        # =================================================

        if event_type == "target":

            target = extract_target_number(text)


            if target == "3":

                msg = (
                    "🏆🎉🎉 الهدف الثالث تحقق! 🎉🎉🏆\n\n"
                    "🔥 اكتملت الصفقة بنجاح!\n"
                    "💰 مبروك تحقيق كامل الأهداف!\n\n"
                )

            elif target == "2":

                msg = (
                    "🎯🔥 الهدف الثاني تحقق! 🔥🎯\n\n"
                    "👏 ممتاز! الصفقة مستمرة نحو الهدف النهائي.\n\n"
                )

            else:

                msg = (
                    "🎯✨ الهدف الأول تحقق! ✨🎯\n\n"
                    "💪 بداية ممتازة والصفقة مستمرة.\n\n"
                )


            msg += (
                f"📌 السهم: {stock_name}\n"
                f"🏷 الرمز: {symbol}"
            )

            if current_price:
                msg += f"\n💰 السعر الحالي: {current_price}"

            if change_pct:
                msg += f"\n📈 التغير: {change_pct}"


            return {
                "message": msg,
                "event_type": "target",
                "symbol": symbol,
                "target": target
            }


        # =================================================
        # 🛡️ وقف بعد تحقيق هدف
        # =================================================

        if event_type == "stop_after_target":

            target = extract_target_number(text)

            if not target:
                target = "1"


            stop_price = extract_value(text, "وقف الخسارة:")

            if not stop_price:
                stop_price = extract_value(text, "وقف الخساره:")


            msg = (
                "🛡️✅ تم إغلاق الصفقة بعد تحقيق هدف\n\n"
                f"📌 السهم: {stock_name}\n"
                f"🏷 الرمز: {symbol}\n"
                f"🎯 آخر هدف محقق: الهدف {target}"
            )

            if current_price:
                msg += f"\n💰 السعر الحالي: {current_price}"

            if stop_price:
                msg += f"\n📉 سعر الوقف: {stop_price}"

            msg += "\n\n💚 الصفقة أغلقت بنتيجة إيجابية."


            return {
                "message": msg,
                "event_type": "stop_after_target",
                "symbol": symbol,
                "target": target
            }


        # =================================================
        # 🛑 وقف خسارة
        # =================================================

        if event_type == "stop":

            stop_price = extract_value(text, "وقف الخسارة:")

            if not stop_price:
                stop_price = extract_value(text, "وقف الخساره:")


            msg = (
                "🛑💥 وقف الخسارة\n\n"
                f"📌 السهم: {stock_name}\n"
                f"🏷 الرمز: {symbol}"
            )

            if current_price:
                msg += f"\n💰 السعر الحالي: {current_price}"

            if change_pct:
                msg += f"\n📉 التغير: {change_pct}"

            if stop_price:
                msg += f"\n📉 سعر الوقف: {stop_price}"

            msg += "\n\n⚠️ أغلقت الصفقة عند وقف الخسارة."


            return {
                "message": msg,
                "event_type": "stop",
                "symbol": symbol,
                "target": None
            }


        # =================================================
        # غير معروف
        # =================================================

        return {
            "message": text,
            "event_type": "unknown",
            "symbol": symbol,
            "target": None
        }


    except Exception:

        return {
            "message": text,
            "event_type": "unknown",
            "symbol": "N/A",
            "target": None
        }


# =========================================================
# إرسال رسالة Telegram
# =========================================================

def send_telegram_message(message, reply_to_message_id=None):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHANNEL_ID,
        "text": message
    }


    # إذا عندنا رسالة سابقة
    # نرسل الرسالة كرد عليها
    if reply_to_message_id is not None:

        payload["reply_parameters"] = {
            "message_id": reply_to_message_id
        }


    response = requests.post(
        url,
        json=payload,
        timeout=15
    )


    try:

        return response.json()

    except Exception:

        return {
            "ok": False,
            "description": response.text
        }


# =========================================================
# Webhook
# =========================================================

@app.route('/webhook', methods=['POST'])
def webhook():

    try:

        # -------------------------------------------------
        # التأكد من وجود التوكن
        # -------------------------------------------------

        if not BOT_TOKEN:

            return jsonify({
                "success": False,
                "error": "BOT_TOKEN is missing"
            }), 500


        # -------------------------------------------------
        # استقبال JSON
        # -------------------------------------------------

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "success": False,
                "error": "No JSON data received"
            }), 400


        if "text" not in data:

            return jsonify({
                "success": False,
                "error": "Missing text field"
            }), 400


        text = data.get("text", "")

        if not isinstance(text, str):

            return jsonify({
                "success": False,
                "error": "text must be a string"
            }), 400


        # -------------------------------------------------
        # تحليل الرسالة
        # -------------------------------------------------

        parsed = clean_and_format(text)

        message = parsed["message"]
        event_type = parsed["event_type"]
        symbol = parsed["symbol"]
        target = parsed["target"]


        # =================================================
        # 🚀 ENTRY
        # =================================================

        if event_type == "entry":

            # بداية جديدة لا تحتاج اقتباس
            result = send_telegram_message(message)


            if not result.get("ok"):

                return jsonify({
                    "success": False,
                    "event": "entry",
                    "telegram_error": result
                }), 500


            # ---------------------------------------------
            # نحفظ message_id لبداية الصفقة
            # ---------------------------------------------

            message_id = result["result"]["message_id"]


            active_trades[symbol] = {
                "message_id": message_id
            }


            return jsonify({
                "success": True,
                "event": "entry",
                "symbol": symbol,
                "message_id": message_id
            }), 200


        # =================================================
        # 🎯 TARGET
        # =================================================

        if event_type == "target":

            trade = active_trades.get(symbol)

            reply_id = None

            if trade:
                reply_id = trade.get("message_id")


            # ---------------------------------------------
            # الهدف يقتبس آخر رسالة
            #
            # TP1 → Entry
            # TP2 → TP1
            # TP3 → TP2
            # ---------------------------------------------

            result = send_telegram_message(
                message,
                reply_to_message_id=reply_id
            )


            # ---------------------------------------------
            # إذا فشل الاقتباس
            # نرسل بدون اقتباس
            # ---------------------------------------------

            if not result.get("ok") and reply_id is not None:

                result = send_telegram_message(message)


            if not result.get("ok"):

                return jsonify({
                    "success": False,
                    "event": "target",
                    "telegram_error": result
                }), 500


            # ---------------------------------------------
            # حفظ message_id الجديد
            #
            # الآن هذا الهدف يصبح آخر رسالة
            #
            # TP1 message_id
            #      ↓
            # TP2 يقتبسه
            # ---------------------------------------------

            new_message_id = result["result"]["message_id"]


            if target == "3":

                # الهدف الثالث نهاية الصفقة
                active_trades.pop(symbol, None)

            else:

                # تحديث آخر رسالة
                active_trades[symbol] = {
                    "message_id": new_message_id
                }


            return jsonify({
                "success": True,
                "event": "target",
                "target": target,
                "replied_to_previous": reply_id is not None
            }), 200


        # =================================================
        # 🛡️ STOP AFTER TARGET
        # =================================================

        if event_type == "stop_after_target":

            trade = active_trades.get(symbol)

            reply_id = None

            if trade:
                reply_id = trade.get("message_id")


            # ---------------------------------------------
            # يقتبس آخر هدف مباشرة
            # ---------------------------------------------

            result = send_telegram_message(
                message,
                reply_to_message_id=reply_id
            )


            # ---------------------------------------------
            # إذا فشل الاقتباس
            # أرسل عادي
            # ---------------------------------------------

            if not result.get("ok") and reply_id is not None:

                result = send_telegram_message(message)


            if not result.get("ok"):

                return jsonify({
                    "success": False,
                    "event": "stop_after_target",
                    "telegram_error": result
                }), 500


            # الصفقة انتهت
            active_trades.pop(symbol, None)


            return jsonify({
                "success": True,
                "event": "stop_after_target",
                "target": target,
                "replied_to_previous": reply_id is not None
            }), 200


        # =================================================
        # 🛑 STOP
        # =================================================

        if event_type == "stop":

            trade = active_trades.get(symbol)

            reply_id = None

            if trade:
                reply_id = trade.get("message_id")


            # ---------------------------------------------
            # يقتبس آخر رسالة:
            #
            # بدون أهداف → Entry
            # بعد TP1 → TP1
            # بعد TP2 → TP2
            # ---------------------------------------------

            result = send_telegram_message(
                message,
                reply_to_message_id=reply_id
            )


            # ---------------------------------------------
            # fallback
            # ---------------------------------------------

            if not result.get("ok") and reply_id is not None:

                result = send_telegram_message(message)


            if not result.get("ok"):

                return jsonify({
                    "success": False,
                    "event": "stop",
                    "telegram_error": result
                }), 500


            # الصفقة انتهت
            active_trades.pop(symbol, None)


            return jsonify({
                "success": True,
                "event": "stop",
                "replied_to_previous": reply_id is not None
            }), 200


        # =================================================
        # UNKNOWN
        # =================================================

        result = send_telegram_message(message)


        if not result.get("ok"):

            return jsonify({
                "success": False,
                "event": "unknown",
                "telegram_error": result
            }), 500


        return jsonify({
            "success": True,
            "event": "unknown"
        }), 200


    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# تشغيل التطبيق
# =========================================================

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000
    )
