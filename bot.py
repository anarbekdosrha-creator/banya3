"""
Telegram-бот для продажи бань "Ваша баня"
Полный функционал согласно ТЗ
"""

import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============= КОНФИГУРАЦИЯ =============
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 1011232205  # ВАШ TELEGRAM ID

# Состояния диалогов
(CALC_TYPE, CALC_SIZE, CALC_LAYOUT, CALC_ADDRESS, CALC_TIMING, 
 CALC_INSTALLMENT, CALC_NAME, CALC_PHONE, CALC_COMMENT) = range(9)
CONSULT_NAME, CONSULT_PHONE, CONSULT_QUESTION = range(10, 13)
REVIEW_TEXT = 13

# ============= БАЗА ДАННЫХ =============
def init_db():
    """Инициализация БД"""
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id INTEGER PRIMARY KEY,
                  name TEXT,
                  type TEXT,
                  dimensions TEXT,
                  area TEXT,
                  price TEXT,
                  timeline TEXT,
                  description TEXT,
                  category TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS leads
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  lead_type TEXT,
                  bath_type TEXT,
                  size TEXT,
                  layout TEXT,
                  address TEXT,
                  timing TEXT,
                  installment TEXT,
                  name TEXT,
                  phone TEXT,
                  comment TEXT,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reviews
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  review_text TEXT,
                  status TEXT,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS faq
                 (id INTEGER PRIMARY KEY,
                  question TEXT,
                  answer TEXT,
                  category TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_type TEXT,
                  user_id INTEGER,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY,
                  value TEXT)''')
    
    conn.commit()
    conn.close()

def add_sample_data():
    """Добавление демо-данных"""
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM projects')
    if c.fetchone()[0] == 0:
        projects = [
            (1, "Компактная 4×4", "Модульная", "4×4 м", "16 м²", "от 650 000₽", "14 дней", 
             "✓ Парная 2×2м\n✓ Моечная 2×2м\n✓ Печь электрическая\n✓ Внутренняя отделка\n✓ Монтаж под ключ", "compact"),
            (2, "Классик 6×4", "Каркасная", "6×4 м", "24 м²", "от 850 000₽", "21 день",
             "✓ Парная 3×2м\n✓ Моечная с душем\n✓ Комната отдыха\n✓ Печь дровяная Harvia\n✓ Отделка липа\n✓ Терраса 2×4м", "medium"),
            (3, "Семейная 6×6", "Каркасная", "6×6 м", "36 м²", "от 1 250 000₽", "30 дней",
             "✓ Просторная парная 4×3м\n✓ Душевая с санузлом\n✓ Большая комната отдыха\n✓ Печь Harvia премиум\n✓ Отделка премиум\n✓ Терраса 3×6м", "medium"),
            (4, "Люкс с террасой", "Дом-баня", "8×6 м", "48 м²", "от 1 850 000₽", "45 дней",
             "✓ Парная 4×3м с гималайской солью\n✓ Санузел премиум\n✓ Комната отдыха с кухней\n✓ Второй этаж под спальни\n✓ Терраса 4×8м\n✓ Отделка премиум", "premium")
        ]
        c.executemany('INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)', projects)
        
        faq_items = [
            (1, "Какие сроки строительства?", "Компактные бани - 14-21 день, средние - 30-45 дней, премиум - от 60 дней. Сроки указаны с момента согласования проекта и оплаты.", "timing"),
            (2, "Какая гарантия?", "Мы даём гарантию 5 лет на конструкцию и 2 года на отделочные работы. Всё по договору!", "warranty"),
            (3, "Как происходит оплата?", "30% - предоплата, 40% - после возведения коробки, 30% - после полной сдачи объекта. Возможна рассрочка на 6-12 месяцев.", "payment"),
            (4, "Нужен ли мне фундамент?", "Да, под баню нужен фундамент (свайно-винтовой или ленточный). Мы можем его сделать или вы можете подготовить сами - подскажем требования.", "foundation"),
            (5, "Работаете ли за пределами Москвы?", "Да! Работаем по всей Московской области. В другие регионы - обсуждается индивидуально.", "geography"),
            (6, "Можно ли изменить проект?", "Конечно! Все проекты можно адаптировать под ваши пожелания: изменить планировку, размеры, добавить опции.", "custom")
        ]
        c.executemany('INSERT INTO faq VALUES (?,?,?,?)', faq_items)
        
        settings = [
            ("company_name", "Ваша баня"),
            ("phone", "+7 (999) 123-45-67"),
            ("address", "г. Москва, ул. Примерная, д. 1"),
            ("work_hours", "Пн-Пт: 9:00-18:00, Сб-Вс: 10:00-16:00"),
            ("channel", "https://t.me/vashabanya21"),
            ("warranty_years", "5"),
            ("geography", "Москва и Московская область")
        ]
        c.executemany('INSERT INTO settings VALUES (?,?)', settings)
    
    conn.commit()
    conn.close()

def save_stat(event_type, user_id):
    """Сохранение статистики"""
    try:
        conn = sqlite3.connect('banya_bot.db')
        c = conn.cursor()
        c.execute('INSERT INTO stats (event_type, user_id, created_at) VALUES (?, ?, ?)',
                  (event_type, user_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")

def get_setting(key, default=""):
    """Получение настройки"""
    try:
        conn = sqlite3.connect('banya_bot.db')
        c = conn.cursor()
        c.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else default
    except:
        return default

calc_handler = ConversationHandler(
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
    fallbacks=[CallbackQueryHandler(show_menu, pattern="^menu$")],
)

consult_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_consultation, pattern="^consultation$")],
    states={
        CONSULT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_name)],
        CONSULT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_phone)],
        CONSULT_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_question)],
    },
    fallbacks=[CallbackQueryHandler(show_menu, pattern="^menu$")],
)

review_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_review, pattern="^write_review$")],
    states={
        REVIEW_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_text)],
    },
    fallbacks=[CallbackQueryHandler(show_menu, pattern="^menu$")],
)

# ============= КЛАВИАТУРЫ =============
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🧖 Подобрать баню", callback_data='catalog')],
        [InlineKeyboardButton("🧮 Рассчитать стоимость", callback_data='calculate')],
        [InlineKeyboardButton("🧰 Комплектация", callback_data='equipment'),
         InlineKeyboardButton("🏗 Наши работы", callback_data='portfolio')],
        [InlineKeyboardButton("⭐ Отзывы", callback_data='reviews'),
         InlineKeyboardButton("❓ Вопросы (FAQ)", callback_data='faq')],
        [InlineKeyboardButton("📞 Консультация", callback_data='consultation')],
        [InlineKeyboardButton("📍 Контакты", callback_data='contacts'),
         InlineKeyboardButton("📣 Канал", callback_data='channel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 В меню", callback_data='menu')]])

def catalog_keyboard():
    keyboard = [
        [InlineKeyboardButton("Компактные", callback_data='cat_compact')],
        [InlineKeyboardButton("Средние", callback_data='cat_medium')],
        [InlineKeyboardButton("Премиум", callback_data='cat_premium')],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============= ОБРАБОТЧИКИ =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_stat('start', user.id)
    
    welcome = (
        f"Здравствуйте, {user.first_name}! 🏠\n\n"
        f"Добро пожаловать в компанию **«{get_setting('company_name')}»**\n\n"
        "🔥 Строим бани **под ключ** с гарантией 5 лет\n"
        "✅ Прозрачная комплектация и цены\n"
        "⚡ Сроки от 14 дней\n"
        "💳 Рассрочка без переплат\n\n"
        "**Что вас интересует?**"
    )
    
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(), parse_mode='Markdown')

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query  
    await query.answer()          

    
    if query.data == 'menu':
        await show_menu(query)
    elif query.data == 'catalog':
        await show_catalog(query)
    elif query.data.startswith('cat_'):
        await show_category(query, context)
    elif query.data.startswith('proj_'):
        await show_project(query, context)
    elif query.data == 'calculate':
        return await start_calculate(update=query, context=context)

    elif query.data == 'equipment':
        await show_equipment(query)
    elif query.data == 'portfolio':
        await show_portfolio(query)
    elif query.data == 'reviews':
        await show_reviews(query)
    elif query.data == 'write_review':
        return await start_review(update=query, context=context)
    elif query.data == 'faq':
        await show_faq(query)
    elif query.data.startswith('faq_'):
        await show_faq_answer(query)
    elif query.data == 'consultation':
        return await start_consultation(update=query, context=context)
    elif query.data == 'contacts':
        await show_contacts(query)
    elif query.data == 'channel':
        await show_channel(query)
    
    return ConversationHandler.END

async def show_menu(query):
    text = "🏠 **Главное меню**\n\nВыберите интересующий раздел:"
    await query.edit_message_text(text, reply_markup=main_menu_keyboard(), parse_mode='Markdown')

async def show_catalog(query):
    text = (
        "🧖 **Каталог наших бань**\n\n"
        "Выберите категорию:\n\n"
        "**Компактные** - для небольших участков (до 20 м²)\n"
        "**Средние** - оптимальный размер для семьи (20-40 м²)\n"
        "**Премиум** - с террасой и доп. этажом (от 40 м²)"
    )
    await query.edit_message_text(text, reply_markup=catalog_keyboard(), parse_mode='Markdown')

async def show_category(query, context):
    category = query.data.split('_')[1]
    
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    c.execute('SELECT id, name, price, dimensions FROM projects WHERE category = ?', (category,))
    projects = c.fetchall()
    conn.close()
    
    if not projects:
        await query.edit_message_text("Проекты в разработке", reply_markup=back_to_menu())
        return
    
    context.user_data['current_category'] = category
    context.user_data['category_projects'] = [p[0] for p in projects]
    context.user_data['current_project_index'] = 0
    
    await show_project_by_index(query, context)

async def show_project_by_index(query, context):
    projects = context.user_data.get('category_projects', [])
    index = context.user_data.get('current_project_index', 0)
    
    if not projects or index >= len(projects):
        await query.edit_message_text("Проект не найден", reply_markup=back_to_menu())
        return
    
    project_id = projects[index]
    
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    proj = c.fetchone()
    conn.close()
    
    if not proj:
        return
    
    _, name, bath_type, dims, area, price, timeline, desc, _ = proj
    
    text = (
        f"**{name}**\n\n"
        f"📦 Тип: {bath_type}\n"
        f"📐 Размер: {dims} ({area})\n"
        f"💰 Цена: **{price}**\n"
        f"⏱ Срок: {timeline}\n\n"
        f"**Комплектация:**\n{desc}\n\n"
        f"_Проект {index + 1} из {len(projects)}_"
    )
    
    keyboard = []
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data='proj_prev'))
    if index < len(projects) - 1:
        nav_row.append(InlineKeyboardButton("➡️ Вперёд", callback_data='proj_next'))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.extend([
        [InlineKeyboardButton("✅ Хочу такую!", callback_data='calculate')],
        [InlineKeyboardButton("🧮 Рассчитать под меня", callback_data='calculate')],
        [InlineKeyboardButton("◀️ К категориям", callback_data='catalog')],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_project(query, context):
    action = query.data.split('_')[1]
    index = context.user_data.get('current_project_index', 0)
    
    if action == 'prev':
        context.user_data['current_project_index'] = max(0, index - 1)
    elif action == 'next':
        projects = context.user_data.get('category_projects', [])
        context.user_data['current_project_index'] = min(len(projects) - 1, index + 1)
    
    await show_project_by_index(query, context)

# ============= РАСЧЁТ СТОИМОСТИ =============
async def start_calculate(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    save_stat('calculate_start', user_id)  

    
    text = (
        "🧮 **Рассчитать стоимость бани**\n\n"
        "Отлично! Ответьте на несколько вопросов, "
        "и мы подготовим индивидуальный расчёт.\n\n"
        "**Шаг 1/9:** Какой тип бани вас интересует?"
    )
    
    keyboard = [
        [InlineKeyboardButton("Модульная", callback_data='type_modular')],
        [InlineKeyboardButton("Каркасная", callback_data='type_frame')],
        [InlineKeyboardButton("Дом-баня", callback_data='type_house')],
        [InlineKeyboardButton("Не знаю", callback_data='type_unknown')],
        [InlineKeyboardButton("◀️ Отмена", callback_data='menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CALC_TYPE

async def calc_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    types = {'modular': 'Модульная', 'frame': 'Каркасная', 'house': 'Дом-баня', 'unknown': 'Не знаю'}
    bath_type = types.get(query.data.split('_')[1], 'Не указано')
    context.user_data['bath_type'] = bath_type
    
    text = "**Шаг 2/9:** Какой размер бани вам нужен?"
    
    keyboard = [
        [InlineKeyboardButton("4×4 м (16 м²)", callback_data='size_4x4')],
        [InlineKeyboardButton("6×4 м (24 м²)", callback_data='size_6x4')],
        [InlineKeyboardButton("6×6 м (36 м²)", callback_data='size_6x6')],
        [InlineKeyboardButton("8×6 м и более", callback_data='size_8x6')],
        [InlineKeyboardButton("Свой вариант", callback_data='size_custom')],
        [InlineKeyboardButton("◀️ Назад", callback_data='calculate')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CALC_SIZE

async def calc_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    sizes = {'4x4': '4×4 м', '6x4': '6×4 м', '6x6': '6×6 м', '8x6': '8×6 м+', 'custom': 'Свой вариант'}
    size = sizes.get(query.data.split('_')[1], 'Не указано')
    context.user_data['size'] = size
    
    text = (
        "**Шаг 3/9:** Какие помещения должны быть?\n\n"
        "_Напишите через запятую, например:_\n"
        "`парная, моечная, комната отдыха, терраса`\n\n"
        "Или просто: `стандарт`"
    )
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return CALC_LAYOUT

async def calc_layout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    layout = update.message.text
    context.user_data['layout'] = layout
    
    text = (
        "**Шаг 4/9:** В каком населённом пункте будет баня?\n\n"
        "_Укажите город/посёлок/СНТ_"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')
    return CALC_ADDRESS

async def calc_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text
    context.user_data['address'] = address
    
    text = "**Шаг 5/9:** Когда планируете строительство?"
    
    keyboard = [
        [InlineKeyboardButton("Срочно (1-2 недели)", callback_data='time_urgent')],
        [InlineKeyboardButton("2-4 недели", callback_data='time_month')],
        [InlineKeyboardButton("1-3 месяца", callback_data='time_3month')],
        [InlineKeyboardButton("Пока прицениваюсь", callback_data='time_looking')]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CALC_TIMING

async def calc_timing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    timings = {'urgent': 'Срочно', 'month': '2-4 недели', '3month': '1-3 месяца', 'looking': 'Прицениваюсь'}
    timing = timings.get(query.data.split('_')[1], 'Не указано')
    context.user_data['timing'] = timing
    
    text = "**Шаг 6/9:** Интересует рассрочка?"
    
    keyboard = [
        [InlineKeyboardButton("Да, интересует", callback_data='inst_yes')],
        [InlineKeyboardButton("Нет", callback_data='inst_no')],
        [InlineKeyboardButton("Не важно", callback_data='inst_maybe')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CALC_INSTALLMENT

async def calc_installment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    inst = {'yes': 'Да', 'no': 'Нет', 'maybe': 'Не важно'}
    context.user_data['installment'] = inst.get(query.data.split('_')[1], 'Не указано')
    
    text = (
        "**Шаг 7/9:** Как вас зовут?\n\n"
        "_Напишите ваше имя_"
    )
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return CALC_NAME

async def calc_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['name'] = name
    
    text = (
        f"**Шаг 8/9:** Отлично, {name}!\n\n"
        "Укажите ваш номер телефона:\n\n"
        "_Например: +7 999 123-45-67_"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')
    return CALC_PHONE

async def calc_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    context.user_data['phone'] = phone
    
    text = (
        "**Шаг 9/9:** Есть ли дополнительные пожелания?\n\n"
        "_Напишите комментарий или 'нет'_"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')
    return CALC_COMMENT

async def calc_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text
    context.user_data['comment'] = comment
    user = update.effective_user
    
    try:
        conn = sqlite3.connect('banya_bot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO leads 
                     (user_id, username, lead_type, bath_type, size, layout, address, 
                      timing, installment, name, phone, comment, created_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (user.id, user.username or 'нет', 'calculation',
                   context.user_data.get('bath_type'), context.user_data.get('size'),
                   context.user_data.get('layout'), context.user_data.get('address'),
                   context.user_data.get('timing'), context.user_data.get('installment'),
                   context.user_data.get('name'), context.user_data.get('phone'),
                   comment, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        save_stat('lead_created', user.id)
    except Exception as e:
        logger.error(f"Ошибка сохранения заявки: {e}")
    
    admin_msg = (
        "🔔 **НОВАЯ ЗАЯВКА НА РАСЧЁТ**\n\n"
        f"👤 Имя: {context.user_data.get('name')}\n"
        f"📞 Телефон: {context.user_data.get('phone')}\n"
        f"📱 Telegram: @{user.username or 'нет'}\n"
        f"🆔 ID: `{user.id}`\n\n"
        f"**Параметры:**\n"
        f"🏠 Тип: {context.user_data.get('bath_type')}\n"
        f"📐 Размер: {context.user_data.get('size')}\n"
        f"🚪 Планировка: {context.user_data.get('layout')}\n"
        f"📍 Адрес: {context.user_data.get('address')}\n"
        f"⏱ Сроки: {context.user_data.get('timing')}\n"
        f"💳 Рассрочка: {context.user_data.get('installment')}\n"
        f"💬 Комментарий: {comment}\n\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")
    
    reply = (
        "✅ **Заявка принята!**\n\n"
        f"{context.user_data.get('name')}, спасибо за обращение!\n\n"
        "Наш менеджер свяжется с вами в ближайшее время "
        "и подготовит индивидуальный расчёт с учётом всех ваших пожеланий.\n\n"
        "⏱ Обычно это занимает 15-30 минут в рабочее время."
    )
    
    await update.message.reply_text(reply, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
    context.user_data.clear()
    return ConversationHandler.END

# ============= КОНСУЛЬТАЦИЯ =============
async def start_consultation(query, context):
    save_stat('consultation_start', query.from_user.id)
    
    text = (
        "📞 **Бесплатная консультация**\n\n"
        "Оставьте свои контакты, и наш специалист "
        "свяжется с вами для ответов на все вопросы.\n\n"
        "**Шаг 1/3:** Как вас зовут?"
    )
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return CONSULT_NAME

async def consult_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['consult_name'] = update.message.text
    
    text = (
        "**Шаг 2/3:** Ваш номер телефона?\n\n"
        "_Например: +7 999 123-45-67_"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')
    return CONSULT_PHONE

async def consult_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['consult_phone'] = update.message.text
    
    text = (
        "**Шаг 3/3:** Какой вопрос вас интересует?\n\n"
        "_Напишите ваш вопрос или 'просто консультация'_"
    )
    await update.message.reply_text(text, parse_mode='Markdown')
    return CONSULT_QUESTION    

async def consult_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    user = update.effective_user
    
    try:
        conn = sqlite3.connect('banya_bot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO leads 
                     (user_id, username, lead_type, name, phone, comment, created_at)
                     VALUES (?,?,?,?,?,?,?)''',
                  (user.id, user.username or 'нет', 'consultation',
                   context.user_data.get('consult_name'),
                   context.user_data.get('consult_phone'),
                   question, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        save_stat('consultation_created', user.id)
    except Exception as e:
        logger.error(f"Ошибка сохранения консультации: {e}")
    
    admin_msg = (
        "📞 **ЗАПРОС НА КОНСУЛЬТАЦИЮ**\n\n"
        f"👤 Имя: {context.user_data.get('consult_name')}\n"
        f"📞 Телефон: {context.user_data.get('consult_phone')}\n"
        f"📱 Telegram: @{user.username or 'нет'}\n"
        f"🆔 ID: `{user.id}`\n\n"
        f"❓ Вопрос: {question}\n\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")
    
    reply = (
        "✅ **Заявка на консультацию принята!**\n\n"
        "Наш специалист свяжется с вами в ближайшее время.\n\n"
        f"📞 Если срочно, звоните: {get_setting('phone')}"
    )
    
    await update.message.reply_text(reply, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
    context.user_data.clear()
    return ConversationHandler.END

# ============= ОТЗЫВЫ =============
async def show_reviews(query):
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    c.execute("SELECT review_text, created_at FROM reviews WHERE status = 'approved' ORDER BY created_at DESC LIMIT 5")
    reviews = c.fetchall()
    conn.close()
    
    text = "⭐ **Отзывы наших клиентов**\n\n"
    
    if reviews:
        for i, (review, date) in enumerate(reviews, 1):
            date_str = datetime.fromisoformat(date).strftime('%d.%m.%Y')
            text += f"**{i}.** {review}\n_({date_str})_\n\n"
    else:
        text += "Пока нет отзывов. Станьте первым!\n\n"
    
    text += "_Построили у нас баню? Поделитесь впечатлениями!_"
    
    keyboard = [
        [InlineKeyboardButton("✍️ Оставить отзыв", callback_data='write_review')],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def start_review(query, context):
    text = (
        "✍️ **Оставить отзыв**\n\n"
        "Расскажите о своём опыте работы с нами!\n\n"
        "Напишите ваш отзыв:"
    )
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return REVIEW_TEXT

async def review_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    review = update.message.text
    user = update.effective_user
    
    try:
        conn = sqlite3.connect('banya_bot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO reviews (user_id, username, review_text, status, created_at)
                     VALUES (?,?,?,?,?)''',
                  (user.id, user.username or 'Аноним', review, 'moderation',
                   datetime.now().isoformat()))
        conn.commit()
        conn.close()
        save_stat('review_created', user.id)
    except Exception as e:
        logger.error(f"Ошибка сохранения отзыва: {e}")
    
    admin_msg = (
        "⭐ **НОВЫЙ ОТЗЫВ**\n\n"
        f"👤 От: @{user.username or 'Аноним'}\n"
        f"🆔 ID: `{user.id}`\n\n"
        f"**Текст отзыва:**\n{review}\n\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"_Статус: На модерации_"
    )
    
    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")
    
    reply = (
        "✅ **Спасибо за отзыв!**\n\n"
        "Ваш отзыв отправлен на модерацию и "
        "скоро появится в общем списке.\n\n"
        "Мы очень ценим ваше мнение! 🙏"
    )
    
    await update.message.reply_text(reply, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
    return ConversationHandler.END

# ============= ИНФОРМАЦИОННЫЕ РАЗДЕЛЫ =============
async def show_equipment(query):
    text = (
        "🧰 **Что входит в комплектацию **\n\n"
        "**Фундамент:**\n"
        "✓ Свайно-винтовой или ленточный\n"
        "✓ Обвязка бруса\n\n"
        "**Конструкция:**\n"
        "✓ Каркас из бруса 150×150 мм\n"
        "✓ Утепление ROCKWOOL 150 мм\n"
        "✓ Гидро- и пароизоляция\n"
        "✓ Металлочерепица\n\n"
        "**Внутренняя отделка:**\n"
        "✓ Вагонка липа класса А (парная)\n"
        "✓ Вагонка сосна (остальные помещения)\n"
        "✓ Полки в парной (2-3 яруса)\n\n"
        "**Печь и электрика:**\n"
        "✓ Печь Harvia\n"
        "✓ Дымоход с изоляцией\n"
        "✓ Электропроводка\n"
        "✓ Светильники влагостойкие"
    )
    
    keyboard = [
        [InlineKeyboardButton("🧮 Рассчитать стоимость", callback_data='calculate')],
        [InlineKeyboardButton("📞 Задать вопрос", callback_data='consultation')],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_portfolio(query):
    text = (
        "🏗 **Наши работы**\n\n"
        "**200+ построенных бань** за 15 лет работы!\n\n"
        "**Последние проекты 2024:**\n\n"
        "📍 **Баня 6×4 м, д. Раменское**\n"
        "Модульная баня с террасой. Срок: 18 дней.\n"
        "_\"Быстро, качественно, без переплат!\"_\n\n"
        "📍 **Баня 6×6 м, п. Жуковка**\n"
        "Каркасная баня с мансардой. Срок: 32 дня.\n"
        "_\"Ребята - профи! Рекомендую!\"_\n\n"
        "📍 **Дом-баня 8×6 м, КП Лесные дали**\n"
        "Премиум проект с террасой. Срок: 48 дней.\n"
        "_\"Мечта сбылась! Спасибо!\"_\n\n"
        "📸 Больше фото в нашем канале!"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Хочу похожую!", callback_data='calculate')],
        [InlineKeyboardButton("📣 Канал с фото", callback_data='channel')],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_faq(query):
    text = "❓ **Частые вопросы**\n\nВыберите вопрос:"
    
    keyboard = [
        [InlineKeyboardButton("⏱ Сроки строительства", callback_data='faq_timing')],
        [InlineKeyboardButton("✅ Гарантия", callback_data='faq_warranty')],
        [InlineKeyboardButton("💳 Оплата и этапы", callback_data='faq_payment')],
        [InlineKeyboardButton("🏗 Фундамент", callback_data='faq_foundation')],
        [InlineKeyboardButton("📍 География работы", callback_data='faq_geography')],
        [InlineKeyboardButton("🎨 Индивидуальный проект", callback_data='faq_custom')],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_faq_answer(query):
    faq_id = query.data.split('_')[1]
    
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    c.execute('SELECT question, answer FROM faq WHERE category = ?', (faq_id,))
    faq = c.fetchone()
    conn.close()
    
    if faq:
        question, answer = faq
        text = f"**{question}**\n\n{answer}"
    else:
        text = "Информация не найдена"
    
    keyboard = [
        [InlineKeyboardButton("◀️ К вопросам", callback_data='faq')],
        [InlineKeyboardButton("📞 Задать свой вопрос", callback_data='consultation')],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_contacts(query):
    text = (
        f"📍 **Контакты компании «{get_setting('company_name')}»**\n\n"
        f"📞 Телефон: **{get_setting('phone')}**\n"
        f"📧 Email: info@vasha-banya.ru\n"
        f"🏢 Адрес: {get_setting('address')}\n"
        f"⏰ Режим работы: {get_setting('work_hours')}\n\n"
        f"🌍 Работаем: {get_setting('geography')}\n\n"
        "_Звоните или пишите - ответим на все вопросы!_"
    )
    
    keyboard = [
        [InlineKeyboardButton("✉️ Написать", callback_data='consultation')],
        [InlineKeyboardButton("📣 Наш канал", callback_data='channel')],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_channel(query):
    channel_url = get_setting('channel')
    
    text = (
        "📣 **Наш Telegram-канал**\n\n"
        "Подписывайтесь на наш канал!\n\n"
        "✨ Фото готовых проектов\n"
        "🎁 Акции и спецпредложения\n"
        "📰 Новости компании\n"
        "💡 Полезные советы\n\n"
        f"👉 {channel_url}"
    )
    
    keyboard = [
        [InlineKeyboardButton("📣 Перейти в канал", url=channel_url)],
        [InlineKeyboardButton("🏠 В меню", callback_data='menu')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============= АДМИН-КОМАНДЫ =============
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(DISTINCT user_id) FROM stats WHERE event_type = 'start'")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM leads WHERE lead_type = 'calculation'")
    calc_leads = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM leads WHERE lead_type = 'consultation'")
    consult_leads = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM reviews")
    reviews_count = c.fetchone()[0]
    
    today = datetime.now().date().isoformat()
    c.execute("SELECT COUNT(*) FROM leads WHERE DATE(created_at) = ?", (today,))
    today_leads = c.fetchone()[0]
    
    conn.close()
    
    text = (
        "📊 **Статистика бота**\n\n"
        f"👥 Всего пользователей: **{total_users}**\n"
        f"📝 Заявок на расчёт: **{calc_leads}**\n"
        f"📞 Запросов консультации: **{consult_leads}**\n"
        f"⭐ Отзывов: **{reviews_count}**\n\n"
        f"**Сегодня:**\n"
        f"✅ Новых заявок: **{today_leads}**"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    conn = sqlite3.connect('banya_bot.db')
    c = conn.cursor()
    c.execute('''SELECT name, phone, lead_type, created_at 
                 FROM leads ORDER BY created_at DESC LIMIT 10''')
    leads = c.fetchall()
    conn.close()
    
    if not leads:
        await update.message.reply_text("Пока нет заявок")
        return
    
    text = "📋 **Последние 10 заявок:**\n\n"
    
    for i, (name, phone, lead_type, created) in enumerate(leads, 1):
        date = datetime.fromisoformat(created).strftime('%d.%m %H:%M')
        type_emoji = "🧮" if lead_type == 'calculation' else "📞"
        text += f"{i}. {type_emoji} **{name}** - {phone}\n   _{date}_\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ============= ЗАПУСК БОТА =============
async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Нажмите /start")

def main():
    init_db()
    add_sample_data()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("leads", leads_command))

    app.add_handler(calc_handler)
    app.add_handler(consult_handler)
    app.add_handler(review_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))

    logger.info("🚀 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

