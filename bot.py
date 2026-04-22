import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

API_TOKEN = "7556358154:AAGdl65GLbDi4EvHdRl84VPRxlRkqgsTGVg"
ADMIN_ID = 711960970

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

with open("menu_data.json", "r", encoding="utf-8") as f:
    menu_data = json.load(f)

user_state = {}

# ---------- КНОПКИ ----------
def make_kb(items, back=True):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for item in items:
        kb.add(KeyboardButton(item))
    if back:
        kb.add(KeyboardButton("⬅️ Назад"))
    return kb

def save_json():
    with open("menu_data.json", "w", encoding="utf-8") as f:
        json.dump(menu_data, f, ensure_ascii=False, indent=2)

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_state[msg.chat.id] = {"level": "age", "admin": False}
    await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))

# ---------- ADMIN ----------
@dp.message_handler(commands=["admin"])
async def admin(msg: types.Message):
    if msg.chat.id != ADMIN_ID:
        return

    user_state[msg.chat.id] = {"level": "age", "admin": True}
    await msg.answer("🔐 Адмін режим\nОберіть вік:", reply_markup=make_kb(menu_data.keys(), False))

# ---------- ОБРОБКА ----------
@dp.message_handler()
async def handler(msg: types.Message):
    text = msg.text
    user = user_state.setdefault(msg.chat.id, {"level": "age", "admin": False})

    # ---------- НАЗАД ----------
    if text == "⬅️ Назад":

    # з днів → назад в тему
    if user["level"] == "days":
        user["level"] = "inside"

        if user.get("admin"):
            await msg.answer(
                "✏️ Редагування:",
                reply_markup=make_kb(["✏️ Батьки", "➕ Гра", "➕ Пісня"])
            )
        else:
            await msg.answer(
                "Оберіть:",
                reply_markup=make_kb(["📩 Батькам", "📅 Дні", "🎵 Пісні", "🎮 Ігри"])
            )
        return

    # з теми всередині → список тем
    if user["level"] == "inside":
        user["level"] = "topic"

        topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]
        await msg.answer("Оберіть тему:", reply_markup=make_kb(topics.keys()))
        return

    # з тем → місяці
    if user["level"] == "topic":
        user["level"] = "month"

        months = menu_data[user["age"]][user["season"]]
        await msg.answer("Оберіть місяць:", reply_markup=make_kb(months.keys()))
        return

    # з місяців → сезони
    if user["level"] == "month":
        user["level"] = "season"

        await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[user["age"]].keys()))
        return

    # з сезонів → вік
    if user["level"] == "season":
        user["level"] = "age"

        await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))
        return

    # ---------- ВІК ----------
    if user["level"] == "age":
        if text in menu_data:
            user["age"] = text
            user["level"] = "season"
            await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[text].keys()))
        return

    # ---------- СЕЗОН ----------
    if user["level"] == "season":
        if text in menu_data[user["age"]]:
            user["season"] = text
            user["level"] = "month"
            await msg.answer("Оберіть місяць:", reply_markup=make_kb(menu_data[user["age"]][text].keys()))
        return

    # ---------- МІСЯЦЬ ----------
    if user["level"] == "month":
        months = menu_data[user["age"]][user["season"]]

        if text in months:
            user["month"] = text
            user["level"] = "topic"

            topics = months[text]["topics"]
            await msg.answer("Оберіть тему:", reply_markup=make_kb(topics.keys()))
        return

    # ---------- ТЕМА ----------
    if user["level"] == "topic":
        topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]

        if text in topics:
            user["topic"] = text
            user["level"] = "inside"

            if user["admin"]:
                await msg.answer(
                    "✏️ Редагування:",
                    reply_markup=make_kb(["✏️ Батьки", "➕ Гра", "➕ Пісня"])
                )
            else:
                await msg.answer(
                    "Оберіть:",
                    reply_markup=make_kb(["📩 Батькам", "📅 Дні", "🎵 Пісні", "🎮 Ігри"])
                )
        return

    # ---------- АДМІН ДІЇ ----------
    if user.get("admin") and user["level"] == "inside":
        topic = menu_data[user["age"]][user["season"]][user["month"]]["topics"][user["topic"]]

        if text == "✏️ Батьки":
            user["edit"] = "parents"
            await msg.answer("Введи новий текст для батьків:")
            return

        if text == "➕ Гра":
            user["edit"] = "game"
            await msg.answer("Введи назву гри:")
            return

        if text == "➕ Пісня":
            user["edit"] = "song"
            await msg.answer("Формат: назва|текст|посилання")
            return

        # ВВІД ТЕКСТУ
        if user.get("edit") == "parents":
            topic["parents"] = text
            save_json()
            await msg.answer("✔ Оновлено")
            user["edit"] = None
            return

        if user.get("edit") == "game":
            topic["games"].append(text)
            save_json()
            await msg.answer("✔ Додано")
            user["edit"] = None
            return

        if user.get("edit") == "song":
            try:
                name, song_text, link = text.split("|")
                topic["songs"].append({
                    "name": name,
                    "text": song_text,
                    "link": link
                })
                save_json()
                await msg.answer("✔ Додано")
            except:
                await msg.answer("❌ Невірний формат")
            user["edit"] = None
            return

    # ---------- КОРИСТУВАЧ ----------
    if not user.get("admin"):
        topic = menu_data[user["age"]][user["season"]][user["month"]]["topics"][user["topic"]]

        if text == "📩 Батькам":
            await msg.answer(topic.get("parents", ""))
            return

        if text == "📅 Дні":
            user["level"] = "days"
            await msg.answer("Оберіть день:", reply_markup=make_kb(topic["days"].keys()))
            return

        if user["level"] == "days" and text in topic["days"]:
            await msg.answer(topic["days"][text], protect_content=True)
            return

        if text == "🎵 Пісні":
            kb = [s["name"] for s in topic["songs"]]
            await msg.answer("Оберіть пісню:", reply_markup=make_kb(kb))
            return

        for song in topic["songs"]:
            if text == song["name"]:
                await msg.answer(f"{song['text']}\n\n{song['link']}")
                return

        if text == "🎮 Ігри":
            await msg.answer("\n".join(topic["games"]), protect_content=True)
            return


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
