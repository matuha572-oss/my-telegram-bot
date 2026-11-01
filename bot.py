import telebot
from telebot import types
import random
import os
import sqlite3
import datetime
import string
from flask import Flask

# --- Настройка веб-сервера для Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

TOKEN = os.environ.get('TELEGRAM_TOKEN', '9233836335:AAFK2NyHR6sgjllDr0nNABT09h34GeFcytk')
bot = telebot.TeleBot(TOKEN)

# --- Настройка базы данных (SQLite) ---
def init_db():
    conn = sqlite3.connect('tokens.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS tokens
                      (token TEXT PRIMARY KEY, days INTEGER, activated_by INTEGER, end_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Функция генерации токена ---
def generate_token(days):
    letters = string.ascii_uppercase
    part1 = ''.join(random.choice(letters) for _ in range(4))
    part2 = ''.join(random.choice(string.digits) for _ in range(4))
    return f"VIP-{days}d-{part1}-{part2}"

# --- Главное меню ---
def get_main_menu():
    markup = types.InlineKeyboardMarkup()
    btn_help = types.InlineKeyboardButton("📌 Помощь", callback_data='help')
    btn_about = types.InlineKeyboardButton("ℹ️ О боте", callback_data='about')
    btn_rate = types.InlineKeyboardButton("🎲 Оценить меня", callback_data='rate')
    btn_buy = types.InlineKeyboardButton("⭐ Купить подписку", callback_data='buy')
    btn_activate = types.InlineKeyboardButton("🔑 Активировать токен", callback_data='activate')
    
    markup.row(btn_help, btn_about)
    markup.row(btn_rate)
    markup.row(btn_buy, btn_activate)
    return markup

# --- Обработка /start ---
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id, 
        f"Привет, {message.from_user.first_name}!\nЯ твой бот-помощник. Выбери действие:", 
        reply_markup=get_main_menu()
    )

# --- Обработка кнопок ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    bot.answer_callback_query(call.id)

    if call.data == 'help':
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text="📌 <b>Помощь</b>\n\nКупи подписку и активируй токен, чтобы получить доступ к платным функциям.", 
            parse_mode='HTML', reply_markup=get_main_menu()
        )
    elif call.data == 'about':
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text="ℹ️ <b>О боте</b>\n\nУчебный проект. Версия 2.0", 
            parse_mode='HTML', reply_markup=get_main_menu()
        )
    elif call.data == 'activate':
        msg = bot.send_message(call.message.chat.id, "Введи свой токен (например, VIP-7d-ABCD-1234):")
        bot.register_next_step_handler(msg, process_activate)
    elif call.data == 'buy':
        markup = types.InlineKeyboardMarkup()
        btn_3d = types.InlineKeyboardButton("3 дня - 80 ⭐", callback_data='pay_3')
        btn_7d = types.InlineKeyboardButton("7 дней - 180 ⭐", callback_data='pay_7')
        btn_30d = types.InlineKeyboardButton("30 дней - 270 ⭐", callback_data='pay_30')
        markup.add(btn_3d, btn_7d, btn_30d)
        bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            text="Выбери срок подписки:", reply_markup=markup
        )
    elif call.data.startswith('pay_'):
        days = int(call.data.split('_')[1])
        price = {3: 80, 7: 180, 30: 270}[days]
        
        prices = [types.LabeledPrice(label=f"Подписка на {days} дней", amount=price)]
        bot.send_invoice(
            chat_id=call.message.chat.id,
            title=f"VIP Подписка на {days} дней",
            description="После оплаты вы получите токен для активации.",
            invoice_payload=f"payload_{days}",
            provider_token="",
            currency="XTR",
            prices=prices
        )

# --- Обработка успешной оплаты ---
@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    days = int(message.successful_payment.invoice_payload.split('_')[1])
    
    token = generate_token(days)
    conn = sqlite3.connect('tokens.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tokens (token, days) VALUES (?, ?)", (token, days))
    conn.commit()
    conn.close()
    
    bot.send_message(
        message.chat.id, 
        f"✅ Оплата прошла! Твой токен для активации:\n\n<code>{token}</code>\n\nНажми кнопку «Активировать токен», чтобы ввести его.",
        parse_mode='HTML'
    )

# --- Обработка активации токена ---
def process_activate(message):
    token = message.text.strip()
    conn = sqlite3.connect('tokens.db')
    cursor = conn.cursor()
    cursor.execute("SELECT days, activated_by, end_date FROM tokens WHERE token = ?", (token,))
    result = cursor.fetchone()
    
    if not result:
        bot.reply_to(message, "❌ Такой токен не найден.")
    elif result[1] is not None:
        bot.reply_to(message, "❌ Этот токен уже активирован кем-то другим.")
    else:
        days = result[0]
        end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE tokens SET activated_by = ?, end_date = ? WHERE token = ?", (message.from_user.id, end_date, token))
        conn.commit()
        bot.reply_to(message, f"✅ Токен активирован! Подписка действует до: {end_date}")
    
    conn.close()

# --- РЕЖИМ РАЗРАБОТЧИКА (ТВОИ КОМАНДЫ) ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != 5863785374: # <--- ЗАМЕНИ НА СВОЙ ID
        bot.reply_to(message, "⛔ У тебя нет доступа.")
        return
    bot.reply_to(message, "👑 Режим разработчика активирован. Введи /gen_3, /gen_7 или /gen_30, чтобы выдать себе токен.")

@bot.message_handler(commands=['gen_3', 'gen_7', 'gen_30'])
def admin_gen(message):
    if message.from_user.id != 5863785374: # <--- ЗАМЕНИ НА СВОЙ ID
        return
    days = int(message.text.split('_')[1])
    token = generate_token(days)
    conn = sqlite3.connect('tokens.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tokens (token, days) VALUES (?, ?)", (token, days))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"Сгенерирован токен на {days} дней:\n<code>{token}</code>", parse_mode='HTML')

# --- РОФЛЕР (ОЦЕНКА) ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text
    # Если это команда (начинается с /), мы её просто игнорируем здесь
    if text.startswith('/'):
        return
        
    score = random.randint(0, 10)
    if score >= 8: phrases = ["Ого, это просто шедевр! 🔥", "Братан, ты гений. 🤯", "Вот это уровень! 👑"]
    elif score >= 4: phrases = ["Ну, сойдет. Среднячок. 🤷‍♂️", "Не фонтан, но и не дно. 😅", "Твердая четверка. 👍"]
    else: phrases = ["Это полный кринж. 🤢", "Брат, ты вообще старался? 💀", "Мне жаль твою клавиатуру. 😂"]
    
    bot.reply_to(message, f"📊 <b>Анализ завершен:</b>\n\nТвой текст: <i>«{text}»</i>\n\nОценка: <b>{score}/10</b>\nВердикт: {random.choice(phrases)}", parse_mode='HTML')

# --- Запуск ---
if __name__ == "__main__":
    import threading
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
