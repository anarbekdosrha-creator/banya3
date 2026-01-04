import logging
import sqlite3
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= КОНФИГУРАЦИЯ =============
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1011232205  # Ваш ID

# Состояния
(CALC_TYPE, CALC_SIZE, CALC_LAYOUT, CALC_ADDRESS, CALC_TIMING, 
 CALC_INSTALLMENT, CALC_NAME, CALC_PHONE, CALC_COMMENT) = range(9)
CONSULT_NAME, CONSULT_PHONE, CONSULT_QUESTION = range(10, 13)
REVIEW_TEXT = 13

# ============= БАЗА ДАННЫХ (БЕЗ ИЗМЕНЕНИЙ) =============
def init_db():
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, type TEXT, dimensions TEXT, area TEXT, price TEXT, timeline TEXT, description TEXT, category TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, lead_type TEXT, bath_type TEXT, size TEXT, layout TEXT, address TEXT, timing TEXT, installment TEXT, name TEXT, phone TEXT, comment TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, review_text TEXT, status TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS faq (id INTEGER PRIMARY KEY, question TEXT, answer TEXT, category TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, user_id INTEGER, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()

def save_stat(event_type, user_id):
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO stats (event_type, user_id, created_at) VALUES (?, ?, ?)', (event_type, user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else default

# ============= КЛАВИАТУРЫ =============
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🧖 Подобрать баню", callback_data='catalog')],
        [InlineKeyboardButton("🧮 Рассчитать стоимость", callback_data='calculate')],
        [InlineKeyboardButton("🧰 Комплектация", callback_data='equipment'), InlineKeyboardButton("🏗 Наши работы", callback_data='portfolio')],
        [InlineKeyboardButton("⭐ Отзывы", callback_data='reviews'), InlineKeyboardButton("❓ Вопросы (FAQ)", callback_data='faq')],
        [InlineKeyboardButton("📞 Консультация", callback_data='consultation')],
        [InlineKeyboardButton("📍 Контакты", callback_data='contacts'), InlineKeyboardButton("📣 Канал", callback_data='channel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 В меню", callback_data='menu')]])

# ============= ОБРАБОТЧИКИ ДИАЛОГОВ (РАСЧЕТ) =============
async def start_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    save_stat('calculate_start', query.from_user.id)
    
    text = "🧮 **Шаг 1/9:** Какой тип бани вас интересует?"
    keyboard = [
        [InlineKeyboardButton("Модульная", callback_data='type_modular')],
        [InlineKeyboardButton("Каркасная", callback_data='type_frame')],
        [InlineKeyboardButton("◀️ Отмена", callback_data='menu')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CALC_TYPE

async def calc_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['bath_type'] = query.data.replace('type_', '')
    
    text = "**Шаг 2/9:** Какой размер бани вам нужен?"
    keyboard = [[InlineKeyboardButton("4×4 м", callback_data='size_4x4')], [InlineKeyboardButton("6x6 м", callback_data='size_6x6')], [InlineKeyboardButton("◀️ Назад", callback_data='calculate')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CALC_SIZE

async def calc_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['size'] = query.data.replace('size_', '')
    await query.edit_message_text("**Шаг 3/9:** Какие помещения нужны? (напишите текстом)")
    return CALC_LAYOUT

async def calc_layout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['layout'] = update.message.text
    await update.message.reply_text("**Шаг 4/9:** Укажите город/адрес строительства:")
    return CALC_ADDRESS

async def calc_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    keyboard = [[InlineKeyboardButton("Срочно", callback_data='time_urgent')], [InlineKeyboardButton("Прицениваюсь", callback_data='time_looking')]]
    await update.message.reply_text("**Шаг 5/9:** Когда планируете начать?", reply_markup=InlineKeyboardMarkup(keyboard))
    return CALC_TIMING

async def calc_timing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['timing'] = query.data
    keyboard = [[InlineKeyboardButton("Да", callback_data='inst_yes')], [InlineKeyboardButton("Нет", callback_data='inst_no')]]
    await query.edit_message_text("**Шаг 6/9:** Нужна рассрочка?", reply_markup=InlineKeyboardMarkup(keyboard))
    return CALC_INSTALLMENT

async def calc_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['installment'] = query.data
    await query.edit_message_text("**Шаг 7/9:** Как вас зовут?")
    return CALC_NAME

async def calc_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("**Шаг 8/9:** Ваш номер телефона:")
    return CALC_PHONE

async def calc_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("**Шаг 9/9:** Любой комментарий или 'нет':")
    return CALC_COMMENT

async def calc_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text
    user = update.effective_user
    # Логика сохранения в БД и отправка админу (как в вашем коде)
    await update.message.reply_text("✅ Заявка принята! Менеджер свяжется с вами.", reply_markup=main_menu_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ МЕНЮ =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_stat('start', update.effective_user.id)
    await update.message.reply_text(f"Привет! Это бот «{get_setting('company_name')}»", reply_markup=main_menu_keyboard())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Общая функция для выхода из любого диалога
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🏠 Меню:", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

# ============= ОСНОВНОЙ ОБРАБОТЧИК КНОПОК =============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Здесь обрабатываем только те кнопки, которые НЕ ЗАПУСКАЮТ ConversationHandler
    if query.data == 'menu':
        await query.edit_message_text("🏠 Главное меню:", reply_markup=main_menu_keyboard())
    elif query.data == 'contacts':
        await query.edit_message_text(f"📞 Тел: {get_setting('phone')}\n📍 {get_setting('address')}", reply_markup=back_to_menu())
    # ... остальные информационные разделы (catalog, equipment и т.д.) ...

# ============= ЗАПУСК =============
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # 1. Диалог расчета стоимости
    calc_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_calculate, pattern="^calculate$")],
        states={
            CALC_TYPE: [CallbackQueryHandler(calc_type, pattern="^type_")],
            CALC_SIZE: [CallbackQueryHandler(calc_size, pattern="^size_")],
            CALC_LAYOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_layout)],
            CALC_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_address)],
            CALC_TIMING: [CallbackQueryHandler(calc_timing, pattern="^time_")],
            CALC_INSTALLMENT: [CallbackQueryHandler(calc_installment, pattern="^inst_")],
            CALC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_name)],
            CALC_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_phone)],
            CALC_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_comment)],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^menu$")],
        allow_reentry=True
    )

    # Добавляем обработчики в правильном порядке
    app.add_handler(CommandHandler("start", start))
    app.add_handler(calc_conv) # Сначала диалоги!
    app.add_handler(CallbackQueryHandler(button_handler)) # Потом общие кнопки

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

    logger.info("🚀 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()


