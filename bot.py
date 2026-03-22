import os, sqlite3, random, logging
from datetime import datetime
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
import asyncio

logging.basicConfig(level=logging.INFO)

# ========== КОНФИГ ==========
BOT_TOKEN      = "8793859441:AAFVJOoz-VvLqKlCnYeXBHn3CoYPWmlzGDU"
CRYPTOBOT_TOKEN= "529877:AAF9Vho8Lw4X6ELXxSeXCyb0YqnwnqzOOFk""
MIN_DEPOSIT    = float(os.environ.get("MIN_DEPOSIT", "2.2"))
DB_PATH        = os.environ.get("DB_PATH", "data.db")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp  = Dispatcher()

# ========== ЭМОДЗИ ==========
EMOJI_BALANCE = '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>'
EMOJI_TMOBILE = '<tg-emoji emoji-id="5413405680713351826">📱</tg-emoji>'
EMOJI_T2      = '<tg-emoji emoji-id="5244453379664534900">🟢</tg-emoji>'
EMOJI_BEELINE = '<tg-emoji emoji-id="5280919528908267119">🐝</tg-emoji>'
EMOJI_MEGAFON = '<tg-emoji emoji-id="5229218997521631084">🟣</tg-emoji>'
EMOJI_MTS     = '<tg-emoji emoji-id="5312126452043363774">🔴</tg-emoji>'
EMOJI_PROFILE = '<tg-emoji emoji-id="5258011929993026890">👤</tg-emoji>'
EMOJI_BACK    = '<tg-emoji emoji-id="5256247952564825322">◀️</tg-emoji>'
EMOJI_SUCCESS = '<tg-emoji emoji-id="5206607081334906820">✅</tg-emoji>'
EMOJI_CANCEL  = '<tg-emoji emoji-id="5323760032389548468">❌</tg-emoji>'
EMOJI_HEART   = '<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji>'
EMOJI_SHOP    = '📱'
EMOJI_TOPUP   = '💳'
EMOJI_HISTORY = '📜'

# ========== БД ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0,
                  username TEXT, reg_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sim_cards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
                  operator TEXT, price REAL, stock INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases
                 (user_id INTEGER, sim_id INTEGER, phone_number TEXT,
                  price REAL, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoices
                 (invoice_id TEXT PRIMARY KEY, user_id INTEGER,
                  amount REAL, status TEXT)''')
    c.execute("SELECT COUNT(*) FROM sim_cards")
    if c.fetchone()[0] == 0:
        sims = [
            ("MTS Esim/Sim",     "MTS",      5.0, 999),
            ("Beeline Esim/Sim", "Beeline",   3.2, 999),
            ("T2 Esim/Sim",      "T2",        1.5, 999),
            ("Megafon Esim/Sim", "Megafon",   4.0, 999),
            ("Yota Sim",         "Yota",      1.5, 999),
            ("T.Mobile",         "T.Mobile",  2.0, 999),
            ("Miranda",          "Other",     1.5, 999),
        ]
        c.executemany("INSERT INTO sim_cards (name,operator,price,stock) VALUES (?,?,?,?)", sims)
    conn.commit()
    conn.close()

def ensure_user(user_id, username=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id,balance,username,reg_date) VALUES (?,0,?,?)",
                  (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0.0

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def get_sims():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, operator, price FROM sim_cards WHERE stock > 0")
    sims = c.fetchall()
    conn.close()
    return sims

def get_sim_by_id(sim_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, operator, price, stock FROM sim_cards WHERE id=?", (sim_id,))
    sim = c.fetchone()
    conn.close()
    return sim

def do_buy_sim(user_id, sim_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, operator, price, stock FROM sim_cards WHERE id=?", (sim_id,))
    sim = c.fetchone()
    if not sim or sim[3] <= 0:
        conn.close()
        return False, "Нет в наличии"
    name, operator, price, stock = sim
    balance = get_balance(user_id)
    if balance < price:
        conn.close()
        return False, f"Недостаточно средств\nНужно: ${price:.2f} | Баланс: ${balance:.2f}"
    phone = f"+{random.randint(70000000000, 79999999999)}"
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, user_id))
    c.execute("UPDATE sim_cards SET stock = stock - 1 WHERE id=?", (sim_id,))
    c.execute("INSERT INTO purchases VALUES (?,?,?,?,?)",
              (user_id, sim_id, phone, price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return True, (f"{EMOJI_SUCCESS} <b>Покупка успешна!</b>\n\n"
                  f"📦 Товар: {name}\n"
                  f"📞 Номер: <code>{phone}</code>\n"
                  f"{EMOJI_BALANCE} Списано: ${price:.2f}")

def get_operator_emoji(operator):
    return {"MTS": EMOJI_MTS, "Beeline": EMOJI_BEELINE, "T2": EMOJI_T2,
            "Megafon": EMOJI_MEGAFON, "Yota": "⚪", "T.Mobile": EMOJI_TMOBILE}.get(operator, "📱")

# ========== CRYPTOBOT ==========
CRYPTOBOT_API = "https://pay.crypt.bot/api"

def create_invoice(amount, user_id):
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    try:
        r = requests.post(f"{CRYPTOBOT_API}/createInvoice", headers=headers,
                          json={"asset": "USDT", "amount": str(amount), "currency_type": "fiat"})
        res = r.json()
        if res.get("ok"):
            inv = res["result"]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO invoices (invoice_id,user_id,amount,status) VALUES (?,?,?,?)",
                      (str(inv["invoice_id"]), user_id, amount, "active"))
            conn.commit()
            conn.close()
            return inv["pay_url"], str(inv["invoice_id"])
    except Exception as e:
        logging.error(f"create_invoice: {e}")
    return None, None

def check_invoice(invoice_id):
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    try:
        r = requests.post(f"{CRYPTOBOT_API}/getInvoices", headers=headers,
                          json={"invoice_ids": [invoice_id]})
        res = r.json()
        if res.get("ok") and res["result"]["items"]:
            inv = res["result"]["items"][0]
            if inv["status"] == "paid":
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT status, amount, user_id FROM invoices WHERE invoice_id=?", (invoice_id,))
                row = c.fetchone()
                if row and row[0] != "paid":
                    c.execute("UPDATE invoices SET status='paid' WHERE invoice_id=?", (invoice_id,))
                    amount, uid = row[1], row[2]
                    conn.commit()
                    conn.close()
                    update_balance(uid, amount)
                    return True, uid, amount
                conn.close()
    except Exception as e:
        logging.error(f"check_invoice: {e}")
    return False, None, None

# ========== КЛАВИАТУРЫ ==========
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI_BALANCE} Баланс",  callback_data="balance"),
         InlineKeyboardButton(text=f"{EMOJI_SHOP} Магазин",    callback_data="shop")],
        [InlineKeyboardButton(text=f"{EMOJI_TOPUP} Пополнить", callback_data="topup"),
         InlineKeyboardButton(text=f"{EMOJI_HISTORY} История", callback_data="history")],
        [InlineKeyboardButton(text=f"{EMOJI_PROFILE} Профиль", callback_data="profile")],
    ])

def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI_BACK} Назад", callback_data="menu")]
    ])

def kb_confirm_buy(sim_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI_SUCCESS} Подтвердить", callback_data=f"confirm_{sim_id}"),
         InlineKeyboardButton(text=f"{EMOJI_CANCEL} Отмена",       callback_data="shop")],
    ])

def kb_check_invoice(inv_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI_SUCCESS} Проверить оплату", callback_data=f"check_{inv_id}")],
        [InlineKeyboardButton(text=f"{EMOJI_BACK} Назад", callback_data="menu")],
    ])

# ========== ХЭНДЛЕРЫ ==========
@dp.message(CommandStart())
async def cmd_start(message: Message):
    ensure_user(message.from_user.id, message.from_user.username)
    bal = get_balance(message.from_user.id)
    await message.answer(
        f"{EMOJI_HEART} <b>Добро пожаловать в магазин сим-карт!</b>\n\n"
        f"Работаем с 2024 года — ни одной ошибки {EMOJI_SUCCESS}\n\n"
        f"{EMOJI_BALANCE} Баланс: <b>${bal:.2f}</b>",
        reply_markup=kb_main()
    )

@dp.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    bal = get_balance(call.from_user.id)
    await call.message.edit_text(
        f"{EMOJI_HEART} <b>Главное меню</b>\n\n"
        f"{EMOJI_BALANCE} Баланс: <b>${bal:.2f}</b>",
        reply_markup=kb_main()
    )
    await call.answer()

@dp.callback_query(F.data == "balance")
async def cb_balance(call: CallbackQuery):
    bal = get_balance(call.from_user.id)
    await call.message.edit_text(
        f"{EMOJI_BALANCE} <b>Ваш баланс: ${bal:.2f}</b>\n\n"
        f"Минимум пополнения: <b>${MIN_DEPOSIT}</b>",
        reply_markup=kb_back()
    )
    await call.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    uid = call.from_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, reg_date FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()
    conn.close()
    uname = f"@{row[0]}" if row and row[0] else "Нет"
    reg   = row[1][:10]  if row and row[1] else "Неизвестно"
    bal   = get_balance(uid)
    await call.message.edit_text(
        f"{EMOJI_PROFILE} <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"👤 Username: {uname}\n"
        f"📅 Регистрация: {reg}\n"
        f"{EMOJI_BALANCE} Баланс: <b>${bal:.2f}</b>",
        reply_markup=kb_back()
    )
    await call.answer()

@dp.callback_query(F.data == "shop")
async def cb_shop(call: CallbackQuery):
    sims = get_sims()
    if not sims:
        await call.message.edit_text(f"{EMOJI_CANCEL} Нет доступных сим-карт", reply_markup=kb_back())
        await call.answer()
        return
    buttons = []
    for sim_id, name, operator, price in sims:
        buttons.append([InlineKeyboardButton(
            text=f"{get_operator_emoji(operator)} {name} — ${price:.2f}",
            callback_data=f"buy_{sim_id}"
        )])
    buttons.append([InlineKeyboardButton(text=f"{EMOJI_BACK} Назад", callback_data="menu")])
    await call.message.edit_text(
        f"{EMOJI_SHOP} <b>Доступные сим-карты:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await call.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy_confirm(call: CallbackQuery):
    sim_id = int(call.data.split("_")[1])
    sim = get_sim_by_id(sim_id)
    if not sim:
        await call.answer("Товар не найден", show_alert=True)
        return
    _, name, operator, price, stock = sim
    bal   = get_balance(call.from_user.id)
    emoji = get_operator_emoji(operator)
    await call.message.edit_text(
        f"🛒 <b>Подтверждение покупки</b>\n\n"
        f"{emoji} Товар: <b>{name}</b>\n"
        f"{EMOJI_BALANCE} Цена: <b>${price:.2f}</b>\n"
        f"💰 Ваш баланс: <b>${bal:.2f}</b>\n\n"
        f"Вы подтверждаете покупку?",
        reply_markup=kb_confirm_buy(sim_id)
    )
    await call.answer()

@dp.callback_query(F.data.startswith("confirm_"))
async def cb_buy_do(call: CallbackQuery):
    sim_id  = int(call.data.split("_")[1])
    success, msg = do_buy_sim(call.from_user.id, sim_id)
    if success:
        bal = get_balance(call.from_user.id)
        await call.message.edit_text(
            f"{msg}\n\n{EMOJI_BALANCE} Новый баланс: <b>${bal:.2f}</b>",
            reply_markup=kb_main()
        )
    else:
        await call.answer(msg, show_alert=True)
    await call.answer()

@dp.callback_query(F.data == "topup")
async def cb_topup(call: CallbackQuery):
    url, inv_id = create_invoice(MIN_DEPOSIT, call.from_user.id)
    if url:
        await call.message.edit_text(
            f"{EMOJI_TOPUP} <b>Пополнение баланса</b>\n\n"
            f"Сумма: {EMOJI_BALANCE} <b>${MIN_DEPOSIT}</b>\n"
            f"Валюта: USDT\n\n"
            f'<a href="{url}">💳 Нажми сюда для оплаты</a>',
            reply_markup=kb_check_invoice(inv_id),
            disable_web_page_preview=True
        )
    else:
        await call.message.edit_text(
            f"{EMOJI_CANCEL} Ошибка создания счёта. Попробуй позже.",
            reply_markup=kb_back()
        )
    await call.answer()

@dp.callback_query(F.data.startswith("check_"))
async def cb_check(call: CallbackQuery):
    inv_id = call.data.split("_", 1)[1]
    paid, uid, amount = check_invoice(inv_id)
    if paid and uid == call.from_user.id:
        bal = get_balance(call.from_user.id)
        await call.message.edit_text(
            f"{EMOJI_SUCCESS} <b>Пополнение успешно!</b>\n\n"
            f"{EMOJI_BALANCE} Зачислено: <b>${amount:.2f}</b>\n"
            f"💰 Новый баланс: <b>${bal:.2f}</b>",
            reply_markup=kb_main()
        )
        await call.answer()
    else:
        await call.answer(f"{EMOJI_CANCEL} Оплата ещё не поступила", show_alert=True)

@dp.callback_query(F.data == "history")
async def cb_history(call: CallbackQuery):
    uid = call.from_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT s.name, p.phone_number, p.price, p.date
                 FROM purchases p JOIN sim_cards s ON p.sim_id = s.id
                 WHERE p.user_id=? ORDER BY p.date DESC LIMIT 10''', (uid,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await call.message.edit_text(
            f"{EMOJI_HISTORY} У вас пока нет покупок", reply_markup=kb_back()
        )
        await call.answer()
        return
    text = f"{EMOJI_HISTORY} <b>История покупок:</b>\n\n"
    for name, phone, price, date in rows:
        text += f"📱 {name}\n📞 <code>{phone}</code>\n{EMOJI_BALANCE} ${price:.2f}\n📅 {date[:10]}\n\n"
    await call.message.edit_text(text, reply_markup=kb_back())
    await call.answer()

# ========== ЗАПУСК ==========
async def main():
    init_db()
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
