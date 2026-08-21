from flask import Flask, request, jsonify
import requests
import os
import re
from apscheduler.schedulers.background import BackgroundScheduler # <-- إضافة مكتبة الجدول فقط

app = Flask(__name__)

# =========================================================
# Telegram
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1004362577027"

# =========================================================
# الصفقة النشطة وحالة السوق العامة (تاسي)
# =========================================================

active_trades = {}
market_state = {
    "tasi_change": 0.0
}

# =========================================================
# Functions
# =========================================================

def extract_value(text, key):
    if key not in text:
        return ""
    try:
        return text.split(key, 1)[1].split("|", 1)[0].strip()
    except Exception:
        return ""

def extract_target_number(text):
    match = re.search(r"الهدف المحقق:\s*([123])", text)
    if match: return match.group(1)
    match = re.search(r"closed_after_target_([123])", text)
    if match: return match.group(1)
    match = re.search(r"closed_target_([123])", text)
    if match: return match.group(1)
    
    if "تحقق الهدف 3" in text or "الهدف 3" in text or "الهدف 3 النهائي" in text: return "3"
    if "تحقق الهدف 2" in text or "الهدف 2" in text: return "2"
    if "تحقق الهدف 1" in text or "الهدف 1" in text: return "1"
    return None

def detect_event(text):
    if "closed_after_target_" in text or "closed_target_" in text or "إيقاف الصفقة بهدف" in text or "اكتمل الهدف" in text:
        if "closed_target_3" in text or "الهدف 3 النهائي" in text or "اكتمل الهدف 3" in text: return "target"
        if "closed_after_target_" in text: return "stop_after_target"
        return "target"
    if "closed_stop_loss" in text or "أغلق الصفقة عند وقف" in text or text.startswith("وقف الخسارة"): return "stop"
    if "تحقق الهدف" in text or "الهدف المحقق" in text or "الحالة: 1" in text or "الحالة: 2" in text or "الحالة: 3" in text: return "target"
    if "بداية صفقة شراء" in text or "صفقة جديدة" in text: return "entry"
    return "unknown"

def clean_and_format(text):
    try:
        stock_name = extract_value(text, "اسم السهم:")
        symbol = extract_value(text, "الرمز:")
        current_price = extract_value(text, "السعر الحالي:")
        change_pct = extract_value(text, "التغير:")

        if not stock_name: stock_name = "غير محدد"
        if not symbol: symbol = "N/A"

        event_type = detect_event(text)

        if event_type == "entry":
            entry_price = extract_value(text, "سعر الدخول:")
            tp1 = extract_value(text, "الهدف 1:")
            tp2 = extract_value(text, "الهدف 2:")
            tp3 = extract_value(text, "الهدف 3:")
            stop_loss = extract_value(text, "وقف الخسارة:") or extract_value(text, "وقف الخساره:")

            msg = f"🚀🔥 صفقة جديدة 🔥🚀\n\n📌 السهم: {stock_name}\n🏷 الرمز: {symbol}"
            if entry_price: msg += f"\n💵 سعر الدخول: {entry_price}"
            if current_price: msg += f"\n📍 السعر الحالي: {current_price}"
            if tp1 or tp2 or tp3:
                msg += "\n\n🎯 الأهداف:"
                if tp1: msg += f"\n🥇 الهدف 1: {tp1}"
                if tp2: msg += f"\n🥈 الهدف 2: {tp2}"
                if tp3: msg += f"\n🥉 الهدف 3: {tp3}"
            if stop_loss: msg += f"\n\n🛑 وقف الخسارة: {stop_loss}"
            return {"message": msg, "event_type": "entry", "symbol": symbol, "target": None}

        if event_type == "target":
            target = extract_target_number(text) or "1"
            if target == "3": msg = "🏆🎉🎉 الهدف الثالث تحقق! 🎉🎉🏆\n\n🔥 اكتملت الصفقة بنجاح!\n💰 مبروك تحقيق كامل الأهداف!\n\n"
            elif target == "2": msg = "🎯🔥 الهدف الثاني تحقق! 🔥🎯\n\n👏 ممتاز! الصفقة مستمرة نحو الهدف النهائي.\n\n"
            else: msg = "🎯✨ الهدف الأول تحقق! ✨🎯\n\n💪 بداية ممتازة والصفقة مستمرة.\n\n"
            msg += f"📌 السهم: {stock_name}\n🏷 الرمز: {symbol}"
            if current_price: msg += f"\n💰 السعر الحالي: {current_price}"
            if change_pct: msg += f"\n📈 التغير: {change_pct}"
            return {"message": msg, "event_type": "target", "symbol": symbol, "target": target}

        if event_type == "stop_after_target":
            target = extract_target_number(text) or "1"
            stop_price = extract_value(text, "وقف الخسارة:") or extract_value(text, "وقف الخساره:")
            msg = f"🛡️✅ تم إغلاق الصفقة بعد تحقيق هدف\n\n📌 السهم: {stock_name}\n🏷 الرمز: {symbol}\n🎯 آخر هدف محقق: الهدف {target}"
            if current_price: msg += f"\n💰 السعر الحالي: {current_price}"
            if stop_price: msg += f"\n📉 سعر الوقف: {stop_price}"
            msg += "\n\n💚 الصفقة أغلقت بعد تحقيق هدف."
            return {"message": msg, "event_type": "stop_after_target", "symbol": symbol, "target": target}

        if event_type == "stop":
            stop_price = extract_value(text, "وقف الخسارة:") or extract_value(text, "وقف الخساره:")
            msg = f"🛑💥 وقف الخسارة\n\n📌 السهم: {stock_name}\n🏷 الرمز: {symbol}"
            if current_price: msg += f"\n💰 السعر الحالي: {current_price}"
            if change_pct: msg += f"\n📉 التغير: {change_pct}"
            if stop_price: msg += f"\n📉 سعر الوقف: {stop_price}"
            msg += "\n\n⚠️ أغلقت الصفقة عند وقف الخسارة."
            return {"message": msg, "event_type": "stop", "symbol": symbol, "target": None}

        return {"message": text, "event_type": "unknown", "symbol": symbol, "target": None}
    except Exception:
        return {"message": text, "event_type": "unknown", "symbol": "N/A", "target": None}

def send_telegram_message(message, reply_to_message_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": message}
    if reply_to_message_id: payload["reply_parameters"] = {"message_id": reply_to_message_id}
    response = requests.post(url, json=payload, timeout=15)
    return response.json() if response.ok else {"ok": False}

# <-- إضافة دالة الإرسال الصباحي فقط
def send_morning_guidelines():
    msg = (
        "☀️ إرشادات ما قبل الافتتاح (ملك الإنعكاس السعودي):\n\n"
        "⚠️ تذكير هام لإدارة المحفظة:\n"
        "1️⃣ لا تدخل بكامل المحفظة في صفقة واحدة أبداً.\n"
        "2️⃣ وزع السيولة على عدة صفقات لحماية رأس المال.\n"
        "3️⃣ التزم بوقف الخسارة واعرف هدفك مسبقاً.\n\n"
        "بالتوفيق للجميع 📊"
    )
    send_telegram_message(msg)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True)
        text = data.get("text", "")
        symbol = extract_value(text, "الرمز:")
        stock_name = extract_value(text, "اسم السهم:")

        if symbol == "TASI" or "TASI" in text or "المؤشر العام" in stock_name or "تاسي" in stock_name:
            change_val_str = extract_value(text, "التغير:")
            try:
                cleaned_num = re.sub(r"[^\d\.\-]", "", change_val_str)
                if cleaned_num: market_state["tasi_change"] = float(cleaned_num)
            except: pass
            return jsonify({"success": True}), 200

        parsed = clean_and_format(text)
        message = parsed["message"]
        event_type = parsed["event_type"]
        symbol = parsed["symbol"]

        if event_type == "entry":
            if market_state["tasi_change"] <= -80: return jsonify({"success": True, "action": "blocked"}), 200
            result = send_telegram_message(message)
            if result.get("ok"): active_trades[symbol] = {"message_id": result["result"]["message_id"]}
            return jsonify({"success": True}), 200

        if event_type in ["target", "stop", "stop_after_target"]:
            trade = active_trades.get(symbol)
            reply_id = trade.get("message_id") if trade else None
            result = send_telegram_message(message, reply_to_message_id=reply_id)
            if not result.get("ok") and reply_id: result = send_telegram_message(message)
           
            if result.get("ok"):
                new_id = result["result"]["message_id"]
                if event_type == "target" and parsed["target"] == "3": active_trades.pop(symbol, None)
                elif event_type in ["stop", "stop_after_target"]: active_trades.pop(symbol, None)
                else: active_trades[symbol] = {"message_id": new_id}
            return jsonify({"success": True}), 200

        send_telegram_message(message)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # <-- بدء المجدول
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_morning_guidelines, 'cron', hour=19, minute=13)
    scheduler.start()
    
    app.run(host='0.0.0.0', port=5000)

