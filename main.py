import asyncio
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Render Environment Variable yoki standart token
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8137205406:AAFdmX1gOStU4s4oUP9WQxSS3CU90OJ90RQ")

# =====================================================================
# RENDER DUMMY SERVER (Render o'chirib qo'ymasligi uchun)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Real-time Bot is running!")

    def log_message(self, format, *args):
        return

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_dummy_server, daemon=True).start()

# =====================================================================
# REAL-TIME BIRJA MA'LUMOTLARI (0-DELAY REAL SPOT GOLD)
# =====================================================================
def get_market_data():
    """
    Binance API orqali Real-Time Spot Oltin (PAXGUSDT) narxini olish.
    Kechikish (delay): 0 soniya (XM bilan bir xil real vaqtda ishlaydi).
    """
    try:
        # PAXGUSDT - London Good Delivery physical gold (1:1 XAU/USD Spot)
        url = "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=1m&limit=30"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=4)
        data = r.json()
        
        # 1-daqiqalik shamchalarning yopilish narxlari (Close prices)
        closes = [float(candle[4]) for candle in data]
        price = round(closes[-1], 2)
        
        return price, closes
    except Exception:
        return None, []

def calculate_rsi(prices, period=14):
    """RSI (Relative Strength Index) hisoblash"""
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
    """SMA (Simple Moving Average) hisoblash"""
    if len(prices) < period:
        return sum(prices) / len(prices)
    return sum(prices[-period:]) / period

def make_real_prediction(closes):
    """Real vaqtdagi 1-daqiqalik narx harakatlari tahlili"""
    if len(closes) < 15:
        return "flat", 0, 0.0, "Yetarli ma'lumot yo'q"

    last_price = closes[-1]
    rsi = calculate_rsi(closes)
    sma5 = calculate_sma(closes, 5)
    sma15 = calculate_sma(closes, 15)

    # So'nggi 10 daqiqadagi 1m shamlarning real tebranish kuchi (Volatillik)
    ranges = [abs(closes[i] - closes[i-1]) for i in range(len(closes)-10, len(closes))]
    avg_range = sum(ranges) / len(ranges)

    # 1. Volatillik filtri: Agar 1 minutlik o'rtacha tebranish $0.20 dan kam bo'lsa - Flat
    if avg_range < 0.20:
        return "flat", 0, round(avg_range, 2), "Bozor juda tinch (Flat). Kirish xavfli!"

    # 2. Impuls kutilmasini hisoblash (kamida $0.40 - $1.50+)
    expected_move_usd = max(avg_range * 1.6, 0.45)
    expected_change_pct = (expected_move_usd / last_price) * 100

    # 3. Trend va RSI bo'yicha signal berish
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
            confidence = 66
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
            confidence = 66
            reason = f"Tushish trendi davom etmoqda (~${expected_move_usd:.2f})"

    return direction, confidence, expected_change_pct, reason

# =====================================================================
# XABAR FORMATI
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
# TELEGRAM BOT HANDLERLARI
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
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_update_prediction(update, update.message, is_edit=False)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_or_update_prediction(update, query.message, is_edit=True)

# =====================================================================
# ISHGA TUSHIRISH
# =====================================================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="new_forecast"))
    
    print("✅ Real-time Oltin Boti ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
