from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1004362577027"

# حفظ رسالة بداية الصفقة لكل سهم
active_trades = {}

def clean_and_format(text):
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
        change_pct = (
            text.split("التغير:")[1].split("|")[0].strip()
            if "التغير:" in text else ""
        )

        # ==========================================
        # 1. إغلاق الصفقة بعد تحقيق هدف
        # ==========================================
        if "closed_after_target" in text or "إيقاف الصفقة بهدف" in text:
            stop_price = (
                text.split("وقف الخسارة:")[1].split("|")[0].strip()
                if "وقف الخسارة:" in text else ""
            )
            msg = (
                "🛡️ تم إغلاق الصفقة (وقف بعد تحقيق الهدف)\n\n"
                f"📌 السهم: {stock_name}\n"
                f"🏷 الرمز: {symbol}"
            )
            if current_price: msg += f"\n💰 السعر الحالي: {current_price}"
            if change_pct: msg += f"\n📈 الربح: {change_pct}"
            if stop_price: msg += f"\n📉 سعر الوقف: {stop_price}"
            return msg, "stop", symbol, None

        # ==========================================
        # 2. تحقق هدف
        # ==========================================
        elif "تحقق الهدف" in text:
            target = "1"
            if "الهدف المحقق: 2" in text: target = "2"
            elif "الهدف المحقق: 3" in text: target = "3"
            
            if target == "3": msg = "🏆🎉🎉 الهدف الثالث تحقق! 🎉🎉🏆\n\n🔥 اكتملت الصفقة بنجاح!\n\n"
            elif target == "2": msg = "🎯🔥 الهدف الثاني تحقق! 🔥🎯\n\n👏 الصفقة مستمرة!\n\n"
            else: msg = "🎯✨ الهدف الأول تحقق! ✨🎯\n\n💪 بداية ممتازة والصفقة مستمرة!\n\n"
            
            msg += f"📌 السهم: {stock_name}\n🏷 الرمز: {symbol}"
            if current_price: msg += f"\n💰 السعر الحالي: {current_price}"
            if change_pct: msg += f"\n📈 الربح: {change_pct}"
            return msg, "target", symbol, target

        # ==========================================
        # 3. وقف الخسارة العادي
        # ==========================================
        elif "وقف الخسارة" in text and "دخول" not in text:
            stop_price = (text.split("وقف الخسارة:")[1].split("|")[0].strip() if "وقف الخسارة:" in text else "")
            msg = "🛑💥 وقف الخسارة\n\n" f"📌 السهم: {stock_name}\n" f"🏷 الرمز: {symbol}"
            if current_price: msg += f"\n💰 السعر الحالي: {current_price}"
            if change_pct: msg += f"\n📉 الخسارة: {change_pct}"
            if stop_price: msg += f"\n📉 سعر الوقف: {stop_price}"
            return msg, "stop", symbol, None

        # ==========================================
        # 4. صفقة جديدة
        # ==========================================
        elif "دخول" in text and "closed_after" not in text:
            entry_price = (text.split("سعر الدخول:")[1].split("|")[0].strip() if "سعر الدخول:" in text else "")
            t1 = (text.split("الهدف 1:")[1].split("|")[0].strip() if "الهدف 1:" in text else "")
            t2 = (text.split("الهدف 2:")[1].split("|")[0].strip() if "الهدف 2:" in text else "")
            t3 = (text.split("الهدف 3:")[1].split("|")[0].strip() if "الهدف 3:" in text else "")
            stop_loss = (text.split("وقف الخسارة:")[1].split("|")[0].strip() if "وقف الخسارة:" in text else "")

            msg = "🚀🔥 صفقة جديدة 🔥🚀\n\n" f"📌 السهم: {stock_name}\n" f"🏷 الرمز: {symbol}"
            if entry_price: msg += f"\n💵 سعر الدخول: {entry_price}"
            if current_price: msg += f"\n📍 السعر الحالي: {current_price}"
            if change_pct: msg += f"\n📈 التغير: {change_pct}"
            if t1 or t2 or t3:
                msg += "\n\n🎯 الأهداف:"
                if t1: msg += f"\n🥇 الهدف 1: {t1}"
                if t2: msg += f"\n🥈 الهدف 2: {t2}"
                if t3: msg += f"\n🥉 الهدف 3: {t3}"
            if stop_loss: msg += f"\n\n🛑 وقف الخسارة: {stop_loss}"
            return msg, "entry", symbol, None

        return text, "unknown", symbol, None
    except Exception:
        return text, "unknown", "N/A", None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True)
        if not data or "text" not in data: return jsonify({"success": False}), 400
        
        final_message, event_type, symbol, target = clean_and_format(data.get("text", ""))
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHANNEL_ID, "text": final_message}

        if event_type == "entry":
            response = requests.post(url, json=payload, timeout=15).json()
            if response.get("ok"): active_trades[symbol] = response["result"]["message_id"]
            return jsonify({"success": response.get("ok", False)}), 200

        elif event_type in ("target", "stop"):
            entry_message_id = active_trades.get(symbol)
            if entry_message_id: payload["reply_parameters"] = {"message_id": entry_message_id}
            
            response = requests.post(url, json=payload, timeout=15).json()
            if response.get("ok"):
                if (event_type == "target" and target == "3") or event_type == "stop":
                    active_trades.pop(symbol, None)
            return jsonify({"success": response.get("ok", False)}), 200
        
        else:
            requests.post(url, json=payload, timeout=15)
            return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

