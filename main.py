import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from usd import get_usd_rate

BOT_TOKEN = "8764824134:AAHwno-FSHv2y0HMPizkU5BwG_tGna4HcCc"  # O'z tokeningizni yozing
bot = telebot.TeleBot(BOT_TOKEN)

user_amounts = {}
active_prompts = {}

def format_num(val):
    return f"{val:,.2f}".replace(",", " ").replace(".", ",")

def get_converter_keyboard(user_id, rate):
    usd_val = user_amounts.get(user_id, 1.0)
    uzs_val = usd_val * rate

    usd_str = f"{int(usd_val)}" if usd_val == int(usd_val) else f"{usd_val:.2f}"
    uzs_str = format_num(uzs_val)

    markup = InlineKeyboardMarkup(row_width=1)
    # Tugma nomini "Sotib olish kursi" deb aniq ko'rsatamiz
    btn_usd = InlineKeyboardButton(f"💵 USD: {usd_str}", callback_data="edit_usd")
    btn_uzs = InlineKeyboardButton(f"💰 UZS (Sotib olish): {uzs_str} so'm", callback_data="edit_uzs")
    markup.add(btn_usd, btn_uzs)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💱 USD - Sotib olish kursi", callback_data="open_converter"))
    
    bot.send_message(
        message.chat.id, 
        "Assalomu alaykum! Bankning sotib olish kursi bo'yicha konvertor:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "open_converter")
def open_converter(call):
    rate = get_usd_rate()
    user_id = call.from_user.id
    if user_id not in user_amounts:
        user_amounts[user_id] = 1.0

    markup = get_converter_keyboard(user_id, rate)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="💱 <b>Sotib olish kursi konvertori</b>\nQiymatni o'zgartirish uchun mos tugmani bosing:",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data in ["edit_usd", "edit_uzs"])
def handle_edit(call):
    user_id = call.from_user.id
    
    if user_id in active_prompts:
        try:
            bot.delete_message(call.message.chat.id, active_prompts[user_id])
        except:
            pass

    if call.data == "edit_usd":
        prompt_msg = bot.send_message(user_id, "💵 USD miqdorini kiriting (masalan: 10, 50):")
        active_prompts[user_id] = prompt_msg.message_id
        bot.register_next_step_handler(prompt_msg, process_usd_input, call.message.message_id)
    else:
        prompt_msg = bot.send_message(user_id, "💰 So'm miqdorini kiriting (masalan: 2400000):")
        active_prompts[user_id] = prompt_msg.message_id
        bot.register_next_step_handler(prompt_msg, process_uzs_input, call.message.message_id)

def process_usd_input(message, original_message_id):
    user_id = message.from_user.id
    active_prompts.pop(user_id, None)

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    try:
        new_usd = float(message.text.replace(",", "."))
        if new_usd < 0:
            raise ValueError
        
        user_amounts[user_id] = new_usd
        rate = get_usd_rate()
        markup = get_converter_keyboard(user_id, rate)
        
        bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=original_message_id,
            reply_markup=markup
        )
    except ValueError:
        err = bot.send_message(message.chat.id, "Iltimos, to'g'ri musbat son kiriting!")
        bot.after(3, lambda: bot.delete_message(message.chat.id, err.message_id))

def process_uzs_input(message, original_message_id):
    user_id = message.from_user.id
    active_prompts.pop(user_id, None)

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    try:
        clean_text = message.text.replace(" ", "").replace(",", ".")
        new_uzs = float(clean_text)
        if new_uzs < 0:
            raise ValueError
        
        rate = get_usd_rate()
        if rate == 0:
            raise ValueError
        
        new_usd = new_uzs / rate
        user_amounts[user_id] = new_usd
        
        markup = get_converter_keyboard(user_id, rate)
        
        bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=original_message_id,
            reply_markup=markup
        )
    except ValueError:
        err = bot.send_message(message.chat.id, "Iltimos, to'g'ri so'm miqdorini kiriting (masalan: 2400000)!")
        bot.after(3, lambda: bot.delete_message(message.chat.id, err.message_id))

if __name__ == "__main__":
    print("Konvertor bot ishga tushdi...")
    bot.infinity_polling()
