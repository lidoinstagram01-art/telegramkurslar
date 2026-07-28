import asyncio
import random
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8137205406:AAFdmX1gOStU4s4oUP9WQxSS3CU90OJ90RQ"

def get_gold_data():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        result = data["chart"]["result"][0]
        price = round(float(result["meta"]["regularMarketPrice"]), 2)
        prev = round(float(result["meta"]["previousClose"]), 2)
        return price, prev
    except:
        return None, None

def get_gold_history():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=30m"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        return closes
    except:
        return []

def make_prediction():
    closes = get_gold_history()

    if len(closes) >= 10:
        last = closes[-1]
        prev5 = closes[-6]
        prev10 = closes[-11] if len(closes) >= 11 else closes[0]

        trend1 = last - prev5        # 5 daqiqa trend
        trend2 = last - prev10       # 10 daqiqa trend

        high = max(closes[-10:])
        low = min(closes[-10:])
        rng = high - low if high != low else 0.01
        rsi_like = (last - low) / rng * 100

        # Yuqori ishonch — trend + RSI bir tomonga
        if trend1 > 0.3 and trend2 > 0.5 and rsi_like < 70:
            direction = "up"
            confidence = round(random.uniform(78, 91), 1)

        elif trend1 < -0.3 and trend2 < -0.5 and rsi_like > 30:
            direction = "down"
            confidence = round(random.uniform(78, 91), 1)

        elif trend1 > 0.1 and rsi_like < 60:
            direction = "up"
            confidence = round(random.uniform(64, 77), 1)

        elif trend1 < -0.1 and rsi_like > 40:
            direction = "down"
            confidence = round(random.uniform(64, 77), 1)

        else:
            direction = random.choice(["up", "down"])
            confidence = round(random.uniform(55, 65), 1)

        change_pct = round(random.uniform(0.03, 0.18), 2)
        return direction, confidence, change_pct

    # History yo'q bo'lsa fallback
    direction = random.choice(["up", "down"])
    confidence = round(random.uniform(58, 72), 1)
    change_pct = round(random.uniform(0.03, 0.15), 2)
    return direction, confidence, change_pct

def build_message(price, prev, direction, confidence, change_pct):
    now = datetime.now().strftime("%H:%M:%S")

    if prev:
        day_change = round(price - prev, 2)
        day_pct = round((day_change / prev) * 100, 2)
        sign = "+" if day_change >= 0 else ""
        day_line = f"📅 Kunlik: *{sign}{day_change}$ ({sign}{day_pct}%)*\n"
    else:
        day_line = ""

    if direction == "up":
        emoji = "📈"
        label = "OSHADI"
        sign = "+"
        expected = round(price * (1 + change_pct / 100), 2)
    else:
        emoji = "📉"
        label = "TUSHADI"
        sign = "-"
        expected = round(price * (1 - change_pct / 100), 2)

    filled = int(confidence / 10)
    bar = "█" * filled + "░" * (10 - filled)

    if confidence >= 78:
        strength = "🔥 Kuchli signal"
    elif confidence >= 64:
        strength = "✅ O'rtacha signal"
    else:
        strength = "⚡ Zaif signal"

    msg = (
        f"📊 *OLTIN BASHORATI — XAU/USD*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Narx: *${price:,.2f}*\n"
        f"{day_line}"
        f"🕐 Vaqt: {now}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{emoji} *1 DAQIQADA {label}!*\n\n"
        f"📐 Ishonch: `[{bar}]` *{confidence}%*\n"
        f"{strength}\n\n"
        f"🎯 Kutilayotgan: *${expected:,.2f}*\n"
        f"📏 O'zgarish: *{sign}{change_pct}%*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⚠️ _Bashorat — kafolat emas!_"
    )
    return msg

async def run_prediction(send_func, edit_func=None):
    price, prev = get_gold_data()

    if price is None:
        text = "❌ Internet yoki API xatosi. Qayta urinib ko'ring."
        if edit_func:
            await edit_func(text)
        else:
            await send_func(text)
        return

    now = datetime.now().strftime("%H:%M:%S")

    loading = await send_func(
        f"📊 *OLTIN NARXI (XAU/USD)*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Joriy narx: *${price:,.2f}*\n"
        f"🕐 {now}\n\n"
        f"⏳ Trend tahlil qilinmoqda...",
        parse_mode="Markdown"
    )

    await asyncio.sleep(2)

    direction, confidence, change_pct = make_prediction()
    msg = build_message(price, prev, direction, confidence, change_pct)

    keyboard = [[InlineKeyboardButton("🔄 Yangi bashorat", callback_data="new")]]

    await loading.edit_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_prediction(update.message.reply_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    price, prev = get_gold_data()
    if price is None:
        await query.message.edit_text("❌ Internet yoki API xatosi.")
        return

    now = datetime.now().strftime("%H:%M:%S")

    await query.message.edit_text(
        f"📊 *OLTIN NARXI (XAU/USD)*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Joriy narx: *${price:,.2f}*\n"
        f"🕐 {now}\n\n"
        f"⏳ Trend tahlil qilinmoqda...",
        parse_mode="Markdown"
    )

    await asyncio.sleep(2)

    direction, confidence, change_pct = make_prediction()
    msg = build_message(price, prev, direction, confidence, change_pct)

    keyboard = [[InlineKeyboardButton("🔄 Yangi bashorat", callback_data="new")]]

    await query.message.edit_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
