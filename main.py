import asyncio
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Token (Render Environment Variable dan oladi, bo'lmasa pastdagini ishlatadi)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8943373950:AAE59hFM95gGgdmzMwX0EETJUeeUSQXIJBw")

# =====================================================================
# 1. RENDER SERVER UCHUN "DUMMY" PORT TINGLOVCHI
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Real-time Gold Bot is running!")

    def log_message(self, format, *args):
        return  # Konsolga keraksiz loglar chiqarmaslik uchun

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Orqa fonda portni tinglashni boshlash
threading.Thread(target=start_dummy_server, daemon=True).start()

# =====================================================================
# 2. BIRJA MA'LUMOTLARI (REAL-TIME SPOT GOLD - 0 DELAY)
# =====================================================================
def get_market_data():
    """
    Real-Time Spot Oltin (PAXGUSDT) narxi (Render serverlari uchun bloklanmaydigan versiya).
    1-Manba: Binance Vision
    2-Manba (Zaxira): Coinbase Global API
    """
    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. BIRINCHI MANBA (Binance Vision)
    try:
        url = "https://data-api.binance.vision/api/v3/klines?symbol=PAXGUSDT&interval=1m&limit=30"
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            closes = [float(candle[4]) for candle in data]
            if closes:
                return round(closes[-1], 2), closes
    except Exception:
        pass  # Xatolik bo'lsa zaxiraga o'tadi

    # 2. ZAXIRA MANBASI (Coinbase)
    try:
        url = "https://api.exchange.coinbase.com/products/PAXG-USD/candles?granularity=60"
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            # Coinbase eng yangi vaqtni 0-indeksda beradi, shuning uchun tartiblaymiz
            data = sorted(data[:30], key=lambda x: x[0])
            closes = [float(candle[4]) for candle in data]
            if closes:
                return round(closes[-1], 2), closes
    except Exception:
        pass

    return None, []

# =====================================================================
# 3. TEXNIK TAHLIL VA INDIKATORLAR (TA)
# =====================================================================
def calculate_rsi(prices, period=14):
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
    if len(prices) < period:
        return sum(prices) / len(prices)
    return sum(prices[-period:]) / period

def make_real_prediction(closes):
    """Impuls va Volatillik (ATR) filtri asosidagi tahlil"""
    if len(closes) < 15:
        return "flat", 0, 0.0, "Yetarli ma'lumot yo'q"

    last_price = closes[-1]
    rsi = calculate_rsi(closes)
    sma5 = calculate_sma(closes, 5)
    sma15 = calculate_sma(closes, 15)

    # O'rtacha 1 minutlik harakat amplitudasi (ATR analogi)
    ranges = [abs(closes[i] - closes[i-1]) for i in range(len(closes)-10, len(closes))]
    avg_range = sum(ranges) / len(ranges)

    # BOZOR SUSTLIK FILTRI: Harakat $0.20 dan kam bo'lsa
    if avg_range < 0.20:
        return "flat", 0, round(avg_range, 2), "Bozor juda tinch (Flat). Kirish xavfli!"

    # Maqsad (Target) o'rnatish
    expected_move_usd = max(avg_range * 1.6, 0.45)
    expected_change_pct = (expected_move_usd / last_price) * 100

    # Trend va RSI Signallari
    if sma5 > sma15: # Uptrend
        if rsi < 35:
            direction, confidence, reason = "up", 88, f"Kuchli impuls! O'sish kutilmoqda (~${expected_move_usd:.2f})"
        elif rsi > 70:
            direction, confidence, reason = "down", 72, f"Tushish korreksiyasi kutilmoqda (~${expected_move_usd:.2f})"
        else:
            direction, confidence, reason = "up", 66, f"O'sish trendi davom etmoqda (~${expected_move_usd:.2f})"
    else: # Downtrend
        if rsi > 65:
            direction, confidence, reason = "down", 88, f"Kuchli impuls! Tushish kutilmoqda (~${expected_move_usd:.2f})"
        elif rsi < 30:
            direction, confidence, reason = "up", 72, f"O'sish korreksiyasi kutilmoqda (~${expected_move_usd:.2f})"
        else:
            direction, confidence, reason = "down", 66, f"Tushish trendi davom etmoqda (~${expected_move_usd:.2f})"

    return direction, confidence, expected_change_pct, reason

# =====================================================================
# 4. XABAR YARATISH (UI/UX)
# =====================================================================
def build_compact_message(price, direction, confidence, change_pct, reason):
    now = datetime.now().strftime("%H:%M:%S")

    if direction == "up":
        emoji, label = "📈", "OSHISHI KUTILMOQDA"
        target = price + (price * change_pct / 100)
        target_str = f"${target:,.2f}"
    elif direction == "down":
        emoji, label = "📉", "TUSHISHI KUTILMOQDA"
        target = price - (price * change_pct / 100)
        target_str = f"${target:,.2f}"
    else:
        emoji, label = "⏸", "BOZOR SUST (FLAT)"
        target_str = "Kutish tavsiya etiladi"

    filled = int(confidence / 10) if confidence > 0 else 0
    bar = "█" * filled + "░" * (10 - filled)

    msg = (
        f"⚡ *XAU/USD (Real-time Spot)* | 🕒 {now}\n"
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
# 5. TELEGRAM BOT FUNKSIYALARI
# =====================================================================
async def send_or_update_prediction(update: Update, message_obj, is_edit=False):
    price, closes = get_market_data()

    if price is None:
        text = "❌ *Xatolik:* Birja serveriga ulanishda xatolik."
        if is_edit:
            await message_obj.edit_text(text, parse_mode="Markdown")
        else:
            await message_obj.reply_text(text, parse_mode="Markdown")
        return

    direction, confidence, change_pct, reason = make_real_prediction(closes)
    msg = build_compact_message(price, direction, confidence, change_pct, reason)
    keyboard = [[InlineKeyboardButton("🔄 Yangilash (Real-time)", callback_data="new_forecast")]]

    try:
        if is_edit:
            await message_obj.edit_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await message_obj.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        pass # Ma'lumot bir xil bo'lsa xato chiqarmaydi

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_update_prediction(update, update.message, is_edit=False)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_or_update_prediction(update, query.message, is_edit=True)

# =====================================================================
# ASOSIY START
# =====================================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="new_forecast"))
    
    print("✅ Real-time Oltin Boti ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
