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
# نخزن آخر رسالة فقط لضمان الاقتباس المتسلسل
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
    match = re.search(r"الهدف المحقق:\s*([123])", text)
    if match:
        return match.group(1)

    match = re.search(r"closed_after_target_([123])", text)
    if match:
        return match.group(1)

    if "تحقق الهدف 3" in text or "الهدف 3" in text:
        return "3"
    if "تحقق الهدف 2" in text or "الهدف 2" in text:
        return "2"
    if "تحقق الهدف 1" in text or "الهدف 1" in text:
        return "1"

    return None


# =========================================================
# تحديد نوع التنبيه (ترتيب الأولويات المعدل والاصح)
# =========================================================

def detect_event(text):
    # 1. أولاً: فحص الإغلاق بعد تحقيق هدف (يجب أن يكون بالأعلى لكي لا يسرقه فحص الهدف العادي)
    if "closed_after_target_" in text or "إيقاف الصفقة بهدف" in text:
        return "stop_after_target"

    # 2. ثانياً: فحص وقف الخسارة الصريح
    if "closed_stop_loss" in text or "وقف الخسارة" in text or "وقف الخساره" in text:
        return "stop"

    # 3. ثالثاً: فحص تحقيق الهدف العادي
    if "تحقق الهدف" in text or "الهدف المحقق" in text:
        return "target"

    # 4. رابعاً: بداية الصفقة
    if "بداية صفقة شراء" in text or "صفقة جديدة" in text:
        return "entry"

    return "unknown"


# =========================================================
# تنسيق الرسائل
# =========================================================

def clean_and_format(text):
    try:
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
            if not target:
                target = "1"

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
            if change_pct:
                msg += f"\n📈 التغير: {change_pct}"
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

    if reply_to_message_id is not None:
        payload["reply_parameters"] = {
            "message_id": reply_to_message_id
        }

    response = requests.post(url, json=payload, timeout=15)
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
        if not BOT_TOKEN:
            return jsonify({"success": False, "error": "BOT_TOKEN is missing"}), 500

        data = request.get_json(silent=True)
        if not data or "text" not in data:
            return jsonify({"success": False, "error": "No JSON data or text received"}), 400

        text = data.get("text", "")
        if not isinstance(text, str):
            return jsonify({"success": False, "error": "text must be a string"}), 400

        parsed = clean_and_format(text)
        message = parsed["message"]
        event_type = parsed["event_type"]
        symbol = parsed["symbol"]
        target = parsed["target"]

        # =================================================
        # 🚀 ENTRY
        # =================================================
        if event_type == "entry":
            result = send_telegram_message(message)
            if not result.get("ok"):
                return jsonify({"success": False, "event": "entry", "telegram_error": result}), 500

            message_id = result["result"]["message_id"]
            active_trades[symbol] = {"message_id": message_id}

            return jsonify({
                "success": True,
                "event": "entry",
                "symbol": symbol,
                "message_id": message_id
            }), 200

        # =================================================
        # 🎯 TARGET / STOP / STOP_AFTER_TARGET
        # =================================================
        if event_type in ["target", "stop", "stop_after_target"]:
            trade = active_trades.get(symbol)
            reply_id = trade.get("message_id") if trade else None

            result = send_telegram_message(message, reply_to_message_id=reply_id)

            if not result.get("ok") and reply_id is not None:
                result = send_telegram_message(message)

            if not result.get("ok"):
                return jsonify({"success": False, "event": event_type, "telegram_error": result}), 500

            new_message_id = result["result"]["message_id"]

            if event_type == "target" and target == "3":
                active_trades.pop(symbol, None)
            elif event_type in ["stop", "stop_after_target"]:
                active_trades.pop(symbol, None)
            else:
                active_trades[symbol] = {"message_id": new_message_id}

            return jsonify({
                "success": True,
                "event": event_type,
                "target": target,
                "replied_to_previous": reply_id is not None
            }), 200

        # =================================================
        # UNKNOWN
        # =================================================
        result = send_telegram_message(message)
        if not result.get("ok"):
            return jsonify({"success": False, "event": "unknown", "telegram_error": result}), 500

        return jsonify({"success": True, "event": "unknown"}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================
# تشغيل التطبيق
# =========================================================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000
    )

