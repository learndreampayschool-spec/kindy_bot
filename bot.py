import logging
import json
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

# =====================
# НАЛАШТУВАННЯ
# =====================

API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "711960970"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

with open("menu_data.json", "r", encoding="utf-8") as f:
    menu_data = json.load(f)

user_state = {}

# =====================
# КНОПКИ
# =====================

def make_kb(items, back=True):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for item in items:
        kb.add(KeyboardButton(item))
    if back:
        kb.add(KeyboardButton("⬅️ Назад"))
    return kb

# =====================
# START
# =====================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_state[msg.chat.id] = {"level": "age"}
    await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))

# =====================
# ADMIN
# =====================

@dp.message_handler(commands=["admin"])
async def admin(msg: types.Message):
    if msg.chat.id != ADMIN_ID:
        return

    user_state[msg.chat.id] = {"level": "admin"}
    await msg.answer(
        "🔐 Адмін панель",
        reply_markup=make_kb([
            "✏️ Батьки",
            "📅 День",
            "🎵 Пісня",
            "🎮 Гра"
        ])
    )

# =====================
# ОСНОВНИЙ ХЕНДЛЕР
# =====================

@dp.message_handler()
async def handler(msg: types.Message):
    text = msg.text
    user = user_state.setdefault(msg.chat.id, {"level": "age"})

    # =====================
    # НАЗАД
    # =====================

    if text == "⬅️ Назад":

        if user["level"] == "inside":
            user["level"] = "topic"

        elif user["level"] == "topic":
            user["level"] = "month"

        elif user["level"] == "month":
            user["level"] = "season"

        elif user["level"] == "season":
            user["level"] = "age"

        elif user["level"] == "admin":
            await start(msg)
            return

    # =====================
    # ВІК
    # =====================

    if user["level"] == "age":
        if text in menu_data:
            user["age"] = text
            user["level"] = "season"

    # =====================
    # СЕЗОН
    # =====================

    elif user["level"] == "season":
        seasons = menu_data[user["age"]]
        if text in seasons:
            user["season"] = text
            user["level"] = "month"

    # =====================
    # МІСЯЦЬ
    # =====================

    elif user["level"] == "month":
        months = menu_data[user["age"]][user["season"]]
        if text in months:
            user["month"] = text
            user["level"] = "topic"

    # =====================
    # ТЕМА
    # =====================

    elif user["level"] == "topic":
        topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]
        if text in topics:
            user["topic"] = text
            user["level"] = "inside"

            await msg.answer(
                "Оберіть розділ:",
                reply_markup=make_kb([
                    "📩 Батькам",
                    "📅 Дні",
                    "🎵 Пісні",
                    "🎮 Ігри та досліди",
                    "📄 PDF"
                ])
            )
            return

    # =====================
    # ВСЕРЕДИНІ ТЕМИ
    # =====================

    elif user["level"] == "inside":

        topic = menu_data[user["age"]][user["season"]][user["month"]]["topics"][user["topic"]]

        if text == "📩 Батькам":
            await msg.answer(topic.get("parents", "Немає тексту"))

        elif text == "📅 Дні":
            days = topic.get("days", {
                "Понеділок": "",
                "Вівторок": "",
                "Середа": "",
                "Четвер": "",
                "Пʼятниця": ""
            })
            await msg.answer("Оберіть день:", reply_markup=make_kb(days.keys()))
            return

        elif text in ["Понеділок", "Вівторок", "Середа", "Четвер", "Пʼятниця"]:
            days = topic.get("days", {})
            await msg.answer(days.get(text, "Немає інформації"))

        elif text == "🎵 Пісні":
            songs = topic.get("songs", [])
            kb = [s["name"] for s in songs] if songs else []
            await msg.answer("Оберіть пісню:", reply_markup=make_kb(kb))
            return

        elif text == "🎮 Ігри та досліди":
            games = topic.get("games", [])
            await msg.answer("\n".join(games) if games else "Немає ігор")

        elif text == "📄 PDF":
            await msg.answer(topic.get("pdf", "Немає PDF"))

        else:
            songs = topic.get("songs", [])
            for s in songs:
                if text == s["name"]:
                    await msg.answer(
                        f"{s['name']}\n\n{s.get('text','')}\n\n{s.get('link','')}"
                    )
                    return

    # =====================
    # ВІДМАЛЬОВКА КНОПОК
    # =====================

    if user["level"] == "age":
        await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))

    elif user["level"] == "season":
        await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[user["age"]].keys()))

    elif user["level"] == "month":
        await msg.answer("Оберіть місяць:", reply_markup=make_kb(menu_data[user["age"]][user["season"]].keys()))

    elif user["level"] == "topic":
        topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]
        await msg.answer("Оберіть тему:", reply_markup=make_kb(topics.keys()))

# =====================
# СТАРТ
# =====================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
