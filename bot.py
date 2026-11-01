import telebot
from telebot import types
import random
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

TOKEN = os.environ.get('TELEGRAM_TOKEN', '9233836335:AAFK2NyHR6sgjllDr0nNABT09h34GeFcytk')
bot = telebot.TeleBot(TOKEN)

# --- Функция для создания кнопок (меню) ---
def get_main_menu():
    markup = types.InlineKeyboardMarkup()
    btn_help = types.InlineKeyboardButton("📌 Помощь", callback_data='help')
    btn_about = types.InlineKeyboardButton("ℹ️ О боте", callback_data='about')
    btn_settings = types.InlineKeyboardButton("⚙️ Настройки", callback_data='settings')
    btn_buy = types.InlineKeyboardButton("⭐ Купить оценку (5 звёзд)", callback_data='buy')
    
    markup.row(btn_help)
    markup.row(btn_about, btn_settings)
    markup.row(btn_buy) 
    return markup

# --- Обработка команды /start ---
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id, 
        f"Привет, {message.from_user.first_name}!\nЯ твой бот-помощник. Выбери действие:", 
        reply_markup=get_main_menu()
    )

# --- Обработка нажатий на кнопки ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    bot.answer_callback_query(call.id) 

    if call.data == 'help':
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text="📌 <b>Помощь</b>\n\nНажми на кнопку 'Купить оценку', чтобы проверить оплату.", 
            parse_mode='HTML',
            reply_markup=get_main_menu()
        )
    elif call.data == 'about':
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text="ℹ️ <b>О боте</b>\n\nУчебный проект. Версия 1.0", 
            parse_mode='HTML',
            reply_markup=get_main_menu()
        )
    elif call.data == 'settings':
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text="⚙️ <b>Настройки</b>\n\nТут позже появятся переключатели.", 
            parse_mode='HTML',
            reply_markup=get_main_menu()
        )
    # --- ОПЛАТА ЗВЕЗДАМИ ---
    elif call.data == 'buy':
        prices = [types.LabeledPrice(label="Оценка от бота", amount=5)]
        
        bot.send_invoice(
            chat_id=call.message.chat.id,
            title="Оценка от бота",
            description="Бот оценит твою фразу по 10-балльной шкале",
            invoice_payload="rate_payload",
            provider_token="", # Для звезд токен не нужен
            currency="XTR",    # XTR — это код Telegram Stars
            prices=prices
        )

# --- Подтверждение оплаты (обязательно для Telegram) ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# --- Успешная оплата ---
@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    bot.send_message(
        message.chat.id, 
        "✅ Оплата прошла! Теперь напиши мне любую фразу, и я дам ей честную оценку!"
    )

# --- Логика Рофлера (Оценка) ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text
    if text.startswith('/'):
        return
        
    score = random.randint(0, 10)
    
    if score >= 8:
        phrases = ["Ого, это просто шедевр! 🔥", "Братан, ты гений. 🤯", "Вот это уровень! 👑"]
    elif score >= 4:
        phrases = ["Ну, сойдет. Среднячок. 🤷‍♂️", "Не фонтан, но и не дно. 😅", "Твердая четверка. 👍"]
    else:
        phrases = ["Это полный кринж. 🤢", "Брат, ты вообще старался? 💀", "Мне жаль твою клавиатуру. 😂"]
    
    comment = random.choice(phrases)
    
    bot.reply_to(
        message, 
        f"📊 <b>Анализ завершен:</b>\n\nТвой текст: <i>«{text}»</i>\n\nОценка: <b>{score}/10</b>\nВердикт: {comment}", 
        parse_mode='HTML'
    )

# --- Запуск бота ---
print("Бот запущен и слушает сообщения...")
bot.infinity_polling()
