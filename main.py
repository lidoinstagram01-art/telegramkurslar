import os
import threading
import requests
from flask import Flask, render_template, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Render'dan olinadigan o'zgaruvchilar
BOT_TOKEN = os.environ.get("BOT_TOKEN", "TOKEN_SHU_YERGA_YOZING")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://sizning-loyiha.onrender.com")

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/rates')
def get_rates():
    try:
        btc = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()
        eth = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT").json()
        
        cbu = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/").json()
        usd_rate = next((item['Rate'] for item in cbu if item['Ccy'] == 'USD'), "Topilmadi")
        
        return jsonify({
            "BTC_USD": btc.get("price", "0"),
            "ETH_USD": eth.get("price", "0"),
            "USD_UZS": usd_rate
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        "📈 Kurslarni ko'rish", 
        web_app=WebAppInfo(url=WEBAPP_URL)
    ))
    bot.send_message(message.chat.id, "Bozor narxlarini kuzatish uchun tugmani bosing:", reply_markup=markup)

def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
