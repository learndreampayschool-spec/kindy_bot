import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

TOKEN = "7556358154:AAGdl65GLbDi4EvHdRl84VPRxlRkqgsTGVg"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DATA_PATH = "/var/data/menu_data.json"

def load_data():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

menu_data = load_data()
user_state = {}

# ================= START =================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    global menu_data
    menu_data = load_data()

    if not menu_data:
        await m.answer("⚠️ Дані ще не додані")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for age in menu_data.keys():
        kb.add(KeyboardButton(age))

    user_state[m.from_user.id] = {"step": "age"}
    await m.answer("Оберіть вікову категорію:", reply_markup=kb)

# ================= HANDLER =================

@dp.message_handler()
async def handler(m: types.Message):
    uid = m.from_user.id
    text = m.text

    if uid not in user_state:
        await start(m)
        return

    state = user_state[uid]

    # 🔹 ВИБІР ВІКУ
    if state["step"] == "age":
        if text not in menu_data:
            return

        state["age"] = text
        state["step"] = "season"

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for season in menu_data[text].keys():
            kb.add(KeyboardButton(season))
        kb.add("⬅️ Назад")

        await m.answer("Оберіть сезон:", reply_markup=kb)

    # 🔹 ВИБІР СЕЗОНУ
    elif state["step"] == "season":
        if text == "⬅️ Назад":
            await start(m)
            return

        age = state["age"]

        if text not in menu_data[age]:
            return

        state["season"] = text
        state["step"] = "topic"

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for topic in menu_data[age][text].keys():
            kb.add(KeyboardButton(topic))
        kb.add("⬅️ Назад")

        await m.answer("Оберіть тему:", reply_markup=kb)

    # 🔹 ВИБІР ТЕМИ
    elif state["step"] == "topic":
        if text == "⬅️ Назад":
            state["step"] = "season"
            await handler(types.Message(text=state["age"], from_user=m.from_user, chat=m.chat))
            return

        age = state["age"]
        season = state["season"]

        if text not in menu_data[age][season]:
            return

        state["topic"] = text
        state["step"] = "section"

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("📘 Методичка")
        kb.add("🎵 Відео/пісня")
        kb.add("💬 Батькам")
        kb.add("🎲 Ігри")
        kb.add("📄 Завдання")
        kb.add("⬅️ Назад")

        await m.answer("Оберіть розділ:", reply_markup=kb)

    # 🔹 РОЗДІЛИ
    elif state["step"] == "section":
        if text == "⬅️ Назад":
            state["step"] = "topic"
            await handler(types.Message(text=state["season"], from_user=m.from_user, chat=m.chat))
            return

        age = state["age"]
        season = state["season"]
        topic = state["topic"]

        data = menu_data[age][season][topic]

        mapping = {
            "📘 Методичка": "method",
            "🎵 Відео/пісня": "video",
            "💬 Батькам": "parents",
            "🎲 Ігри": "games",
            "📄 Завдання": "tasks"
        }

        key = mapping.get(text)

        if not key or key not in data:
            await m.answer("❌ Немає даних")
            return

        if not data[key]:
            await m.answer("⚠️ У цьому розділі поки нічого немає")
            return

        for item in data[key]:
            await m.answer(item)

# ================= RUN =================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
