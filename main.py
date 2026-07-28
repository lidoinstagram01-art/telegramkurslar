import asyncio
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Tokenni Render Environment Variable-dan oladi, bo'lmasa standart tokendan foydalanadi
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8137205406:AAFdmX1gOStU4s4oUP9WQxSS3CU90OJ90RQ")

# =====================================================================
# RENDER DUMMY SERVER (Render "Port check failed" deb o'chirmasligi uchun)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

    def log_message(self, format, *args):
        return  # Konsoldagi keraksiz so'rov loglarini o'chirish

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Portni orqa fonda (background thread) tinglash
threading.Thread(target=start_dummy_server, daemon=True).start()

# =====================================================================
# BIRJA MA'LUMOTLARI VA TEXNIK TAHLIL (TA)
# =====================================================================
def get_market_data():
    """Yahoo Finance'dan oltin narxi va 30 minutlik 1m shamlar tarixini oladi"""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=30m"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        
        result = data["chart"]["result"][0]
        price = round(float(result["meta"]["regularMarketPrice"]), 2)
        
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        
        return price, closes
    except Exception:
        return None, []

def calculate_rsi(prices, period=14):
    """RSI (Relative Strength Index) indikatori"""
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains[-period:]) / period if gains else 0
    avg_loss = sum(losses[-period:]) / period if losses else 0

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_sma(prices, period):
    """SMA (Simple Moving Average) indikatori"""
    if len(prices) < period:
        return sum(prices) / len(prices)
    return sum(prices[-period:]) / period

def make_real_prediction(closes):
    """Impuls va Volatillik (ATR) filtri qo'shilgan tahlil"""
    if len(closes) < 15:
        return "flat", 0, 0.0, "Yetarli ma'lumot yo'q"

    last_price = closes[-1]
    rsi = calculate_rsi(closes)
    sma5 = calculate_sma(closes, 5)
    sma15 = calculate_sma(closes, 15)

    # Oxirgi 10 minutdagi o'rtacha 1m harakat amplitudasi (ATR analogi)
    ranges = [abs(closes[i] - closes[i-1]) for i in range(len(closes)-10, len(closes))]
    avg_range = sum(ranges) / len(ranges)

    # 1. VOLATILLIK FILTRI: Harakat $0.25 dan kam bo'lsa - bozor sust (Flat)
    if avg_range < 0.25:
        return "flat", 0, round(avg_range, 2), "Bozor sust (Flat). Kirish xavfli!"

    # 2. Kutilayotgan harakatni kamida $0.40 - $1.50+ diapazoniga sozlash
    expected_move_usd = max(avg_range * 1.5, 0.40)
    expected_change_pct = (expected_move_usd / last_price) * 100

    # 3. Signal va yo'nalish tahlili
    if sma5 > sma15: # O'sish trendi
        if rsi < 35:
            direction = "up"
            confidence = 88
            reason = f"Kuchli impuls! O'sish kutilmoqda (~${expected_move_usd:.2f})"
        elif rsi > 70:
            direction = "down"
            confidence = 72
            reason = f"Tushish korreksiyasi kutilmoqda (~${expected_move_usd:.2f})"
        else:
            direction = "up"
            confidence = 65
            reason = f"O'sish trendi davom etmoqda (~${expected_move_usd:.2f})"
    else: # Tushish trendi
        if rsi > 65:
            direction = "down"
            confidence = 88
            reason = f"Kuchli impuls! Tushish kutilmoqda (~${expected_move_usd:.2f})"
        elif rsi < 30:
            direction = "up"
            confidence = 72
            reason = f"O'sish korreksiyasi kutilmoqda (~${expected_move_usd:.2f})"
        else:
            direction = "down"
            confidence = 65
            reason = f"Tushish trendi davom etmoqda (~${expected_move_usd:.2f})"

    return direction, confidence, expected_change_pct, reason

# =====================================================================
# XABAR FORMATI
# =====================================================================
def build_compact_message(price, direction, confidence, change_pct, reason):
    now = datetime.now().strftime("%H:%M")

    if direction == "up":
        emoji, label = "📈", "OSHISHI KUTILMOQDA"
        target = price + (price * change_pct / 100)
        target_str = f"${target:,.2f}"
    elif direction == "down":
        emoji, label = "📉", "TUSHISHI KUTILMOQDA"
        target = price - (price * change_pct / 100)
        target_str = f"${target:,.2f}"
    else: # Flat (sust bozor)
        emoji, label = "⏸", "BOZOR SUST (FLAT)"
        target_str = "Kutish tavsiya etiladi"

    filled = int(confidence / 10) if confidence > 0 else 0
    bar = "█" * filled + "░" * (10 - filled)

    msg = (
        f"📊 *XAU/USD (Oltin)* | 🕒 {now}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 *Joriy narx:* ${price:,.2f}\n"
        f"🎯 *Maqsad (Target):* {target_str}\n\n"
        f"{emoji} *Signal:* {label}\n"
        f"📌 *Tahlil:* {reason}\n"
        f"📐 *Ishonch:* `[{bar}]` {confidence}%\n"
        f"━━━━━━━━━━━━━━━"
    )
    return msg

# =====================================================================
# TELEGRAM BOT HANDLERLARI
# =====================================================================
async def send_or_update_prediction(update: Update, message_obj, is_edit=False):
    price, closes = get_market_data()

    if price is None:
        text = "❌ *Xatolik:* Birja ma'lumotlarini olib bo'lmadi. Qayta urinib ko'ring."
        if is_edit:
            await message_obj.edit_text(text, parse_mode="Markdown")
        else:
            await message_obj.reply_text(text, parse_mode="Markdown")
        return

    direction, confidence, change_pct, reason = make_real_prediction(closes)
    msg = build_compact_message(price, direction, confidence, change_pct, reason)
    keyboard = [[InlineKeyboardButton("🔄 Yangilash", callback_data="new_forecast")]]

    try:
        if is_edit:
            await message_obj.edit_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await message_obj.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        pass  # Xabar o'zgarmagan bo'lsa Telegram xatosini yutib yuborish

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_update_prediction(update, update.message, is_edit=False)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Soat / yuklanish belgisini o'chirish
    await send_or_update_prediction(update, query.message, is_edit=True)

# =====================================================================
# ASOSIY ISHGA TUSHIRISH
# =====================================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="new_forecast"))
    
    print("✅ Professional Oltin Boti va Web Server ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
