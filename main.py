import telebot
from telebot.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from usd import get_all_usd_rates

BOT_TOKEN = "8137205406:AAFdmX1gOStU4s4oUP9WQxSS3CU90OJ90RQ"
bot = telebot.TeleBot(BOT_TOKEN)

# Foydalanuvchilar tanlagan miqdor (default: 1 dollar)
user_amounts = {}

def format_sum(val):
    """Raqamlarni chiroyli formatlash (masalan: 12 850,00)"""
    if not val:
        return "Noma'lum"
    return f"{val:,.2f}".replace(",", " ").replace(".", ",")

def create_usd_keyboard(user_id, rates):
    """3 xil kurs bo'yicha tugmalarni shakllantirish"""
    amount = user_amounts.get(user_id, 1)
    
    # Miqdor matni (masalan: 1 yoki 10)
    amount_text = int(amount) if amount == int(amount) else amount

    # Har bir kurs bo'yicha hisob-kitob
    mb_total = amount * (rates["mb"] or 0)
    buy_total = amount * (rates["buy"] or 0)
    sell_total = amount * (rates["sell"] or 0)

    markup = InlineKeyboardMarkup(row_width=1)
    
    # Tugmalar
    btn_amount = InlineKeyboardButton(f"✏️ Miqdor: {amount_text} USD", callback_data="change_amount")
    btn_mb = InlineKeyboardButton(f"🏛 MB kursi: {format_sum(mb_total)} so'm", callback_data="none")
    btn_buy = InlineKeyboardButton(f"📥 Bank oladi (Sotib olish): {format_sum(buy_total)} so'm", callback_data="none")
    btn_sell = InlineKeyboardButton(f"📤 Bank sotadi (Sotish): {format_sum(sell_total)} so'm", callback_data="none")
    
    markup.add(btn_amount, btn_mb, btn_buy, btn_sell)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("💵 USD"))
    
    bot.send_message(
        message.chat.id, 
        "Assalomu alaykum! Valyutani tanlang:", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda msg: msg.text == "💵 USD")
def usd_handler(message):
    rates = get_all_usd_rates()
    if not rates["mb"]:
        bot.send_message(message.chat.id, "Xatolik: USD kurslarini olib bo'lmadi.")
        return

    user_id = message.from_user.id
    if user_id not in user_amounts:
        user_amounts[user_id] = 1

    markup = create_usd_keyboard(user_id, rates)
    
    bot.send_message(
        message.chat.id,
        "📊 <b>Real vaqt Dollar kurslari</b>\n"
        "<i>Tahrirlash uchun miqdor tugmasini bosing:</i>",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "change_amount")
def prompt_amount_input(call):
    msg = bot.send_message(
        call.message.chat.id, 
        "Qiymat yuboring (masalan: 10, 50, 100):"
    )
    bot.register_next_step_handler(msg, process_new_amount, call.message.message_id)

def process_new_amount(message, original_message_id):
    user_id = message.from_user.id
    
    try:
        new_amount = float(message.text.replace(",", "."))
        if new_amount <= 0:
            raise ValueError

        user_amounts[user_id] = new_amount
        rates = get_all_usd_rates()

        # Chat toza turishi uchun foydalanuvchi yuborgan raqamni o'chiramiz
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

        if rates["mb"]:
            markup = create_usd_keyboard(user_id, rates)
            bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=original_message_id,
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "USD kursini yangilab bo'lmadi.")

    except ValueError:
        bot.send_message(message.chat.id, "Iltimos, faqat musbat son kiriting (masalan: 10)!")

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
