import asyncio
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Render Environment Variable-dan token olish (xavfsiz usul)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8137205406:AAFdmX1gOStU4s4oUP9WQxSS3CU90OJ90RQ")

# --- RENDER PORT HEALTH CHECK (Render o'chirib qo'ymasligi uchun) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlamoqda!")

    def log_message(self, format, *args):
        return # Konsolga keraksiz loglarni chiqarmaslik

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Background oqimda portni tinglashni boshlash
threading.Thread(target=start_dummy_server, daemon=True).start()
# --------------------------------------------------------------------

def get_market_data():
    try:
        url_price = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=30m"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url_price, headers=headers, timeout=5)
        data = r.json()
        
        result = data["chart"]["result"][0]
        price = round(float(result["meta"]["regularMarketPrice"]), 2)
        
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        
        return price, closes
    except Exception:
        return None, []

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0: gains.append(diff)
        else: losses.append(abs(diff))

    avg_gain = sum(gains[-period:]) / period if gains else 0
    avg_loss = sum(losses[-period:]) / period if losses else 0

    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_sma(prices, period):
    if len(prices) < period: return sum(prices)/len(prices)
    return sum(prices[-period:]) / period

def make_real_prediction(closes):
    if len(closes) < 15:
        return "neutral", 50, 0.0, "Yetarli ma'lumot yo'q"

    last_price = closes[-1]
    rsi = calculate_rsi(closes)
    sma5 = calculate_sma(closes, 5)
    sma15 = calculate_sma(closes, 15)

    diffs = [abs(closes[i] - closes[i-1]) for i in range(len(closes)-5, len(closes))]
    avg_diff = sum(diffs) / len(diffs)
    expected_change_pct = (avg_diff / last_price) * 100

    if sma5 > sma15:
        if rsi < 30:
            direction, confidence, reason = "up", 85 + (30 - rsi), "Kuchli o'sish (RSI past)"
        elif rsi > 70:
            direction, confidence, reason = "down", 75 + (rsi - 70), "Tushish ehtimoli (Haddan ortiq olingan)"
        else:
            direction, confidence, reason = "up", 55 + (70 - rsi) / 2, "Barqaror o'sish trendi"
    else:
        if rsi > 70:
            direction, confidence, reason = "down", 85 + (rsi - 70), "Kuchli tushish (RSI yuqori)"
        elif rsi < 30:
            direction, confidence, reason = "up", 75 + (30 - rsi), "O'sish ehtimoli (Haddan ortiq sotilgan)"
        else:
            direction, confidence, reason = "down", 55 + (rsi - 30) / 2, "Barqaror tushish trendi"

    confidence = min(max(int(confidence), 10), 95)
    return direction, confidence, expected_change_pct, reason

def build_compact_message(price, direction, confidence, change_pct, reason):
    now = datetime.now().strftime("%H:%M")

    if direction == "up":
        emoji, label = "📈", "OSHISHI KUTILMOQDA"
        target = price + (price * change_pct / 100)
    else:
        emoji, label = "📉", "TUSHISHI KUTILMOQDA"
        target = price - (price * change_pct / 100)

    filled = int(confidence / 10)
    bar = "█" * filled + "░" * (10 - filled)

    msg = (
        f"📊 *XAU/USD (Oltin)* | 🕒 {now}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 *Joriy narx:* ${price:,.2f}\n"
        f"🎯 *Kutilayotgan narx:* ${target:,.2f}\n\n"
        f"{emoji} *Signal:* {label}\n"
        f"📌 *Sabab:* {reason}\n"
        f"📐 *Ishonch:* `[{bar}]` {confidence}%\n"
        f"━━━━━━━━━━━━━━━"
    )
    return msg

async def send_or_update_prediction(update: Update, message_obj, is_edit=False):
    price, closes = get_market_data()

    if price is None:
        text = "❌ *Xatolik:* Birja ma'lumotlarini olib bo'lmadi."
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
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_update_prediction(update, update.message, is_edit=False)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_or_update_prediction(update, query.message, is_edit=True)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="new_forecast"))
    
    print("✅ Bot va Web Server ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
