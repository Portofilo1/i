import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode

# ================== НАСТРОЙКИ ==================
API_ID = 37559780  # Замени на свой
API_HASH = "a1d3109abd47ee6226e76701b2f2154e"  # Замени на свой
BOT_TOKEN = "8699361720:AAGPx5UdJOTfIf4iSzJdbN0HbNzh-mGvrYg"  # Замени на токен от @BotFather
ADMIN_LINK = "@loxtorp"  # Ссылка на админа

# ================== ПРАЙС-ЛИСТ (БЕЗ СМАЙЛОВ) ==================
PRICE_DATA = {
    "Сим карты": {
        "MTC (сим/есим)": "5",
        "Мегафон (сим/есим)": "4",
        "T2 (сим/есим)": "2.5",
        "СБЕР (сим/есим)": "2.5",
        "Т.Мобайл (сим)": "2.2",
        "Билайн (сим/есим)": "3",
        "Остальные операторы": "Договорная"
    },
    "Приложения и банки": {
        "Youmoney (максимальный)": "4.5",
        "Авито (максимальный) (с документами)": "400 рублей",
        "Госуслуги": "обговаривается в лс",
        "Другие банки/приложения": "узнавать в лс"
    },
    "Куплю": {
        "ГК операторов": "Предложите цену",
        "ГК банков": "Предложите цену",
        "Госуслуги подтверждённые": "15 $ за аккаунт"
    }
}

# ================== СОЗДАНИЕ КЛИЕНТА ==================
app = Client("my_price_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================== КЛАВИАТУРЫ ==================
def get_main_reply_keyboard():
    """Главная reply-клавиатура"""
    buttons = [
        [KeyboardButton("Сим карты")],
        [KeyboardButton("Приложения и банки")],
        [KeyboardButton("Куплю")],
        [KeyboardButton("Контакты")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_back_reply_keyboard():
    """Кнопка 'Назад' """
    buttons = [[KeyboardButton("Назад в главное меню")]]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_category_inline_keyboard(category_name):
    """Инлайн клавиатура для конкретной категории"""
    buttons = []
    if category_name in PRICE_DATA:
        for item_name, price in PRICE_DATA[category_name].items():
            buttons.append([InlineKeyboardButton(
                text=item_name,
                callback_data=f"price_{category_name}_{item_name}"
            )])
    
    buttons.append([InlineKeyboardButton(
        text="Связаться с админом",
        url=f"https://t.me/{ADMIN_LINK.replace('@', '')}"
    )])
    
    return InlineKeyboardMarkup(buttons)

# ================== ОБРАБОТЧИКИ СООБЩЕНИЙ ==================
@app.on_message(filters.command(["start"]))
async def start_command(client: Client, message: Message):
    """Обработчик команды /start"""
    welcome_text = (
        "Здравствуйте. Я бот для подписи сим-карт и приложений.\n\n"
        "Выберите интересующий вас раздел в меню ниже."
    )
    await message.reply_text(
        welcome_text,
        reply_markup=get_main_reply_keyboard()
    )

@app.on_message(filters.text & filters.private)
async def handle_reply_buttons(client: Client, message: Message):
    """Обработчик нажатий на reply-кнопки"""
    text = message.text
    
    if text == "Сим карты":
        response = "Выберите оператора:"
        await message.reply_text(
            response,
            reply_markup=get_category_inline_keyboard("Сим карты")
        )
    
    elif text == "Приложения и банки":
        response = "Выберите приложение или банк:"
        await message.reply_text(
            response,
            reply_markup=get_category_inline_keyboard("Приложения и банки")
        )
    
    elif text == "Куплю":
        response = "Что интересует для покупки:"
        await message.reply_text(
            response,
            reply_markup=get_category_inline_keyboard("Куплю")
        )
    
    elif text == "Контакты":
        contact_text = (
            "Связь с админом:\n"
            f"{ADMIN_LINK}\n\n"
            "По всем вопросам, а также для заказа услуг или продажи ГК - пишите в личные сообщения."
        )
        await message.reply_text(
            contact_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    text="Написать админу",
                    url=f"https://t.me/{ADMIN_LINK.replace('@', '')}"
                )
            ]])
        )
    
    elif text == "Назад в главное меню":
        await message.reply_text(
            "Главное меню:",
            reply_markup=get_main_reply_keyboard()
        )
    
    else:
        await message.reply_text(
            "Используйте кнопки меню для навигации.",
            reply_markup=get_main_reply_keyboard()
        )

# ================== ОБРАБОТЧИКИ ИНЛАЙН КНОПОК ==================
@app.on_callback_query()
async def handle_inline_buttons(client: Client, callback_query: CallbackQuery):
    """Обработчик нажатий на инлайн-кнопки"""
    data = callback_query.data
    
    if data.startswith("price_"):
        parts = data.split("_", 2)
        if len(parts) == 3:
            _, category, item = parts
            if category in PRICE_DATA and item in PRICE_DATA[category]:
                price = PRICE_DATA[category][item]
                await callback_query.answer()
                await callback_query.message.reply_text(
                    f"{item}\nЦена: {price}\n\nДля заказа напишите админу: {ADMIN_LINK}",
                    reply_markup=get_back_reply_keyboard()
                )
            else:
                await callback_query.answer("Информация не найдена", show_alert=True)
    
    await callback_query.answer()

# ================== ЗАПУСК БОТА ==================
if __name__ == "__main__":
    print("Бот запущен...")
    app.run()