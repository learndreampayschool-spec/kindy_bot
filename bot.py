import logging
import json
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "711960970"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

with open("menu_data.json", "r", encoding="utf-8") as f:
    menu_data = json.load(f)

user_state = {}
admin_state = {}

# =====================
# КНОПКИ
# =====================

def make_kb(items, back=True):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for item in items:
        kb.add(KeyboardButton(str(item)))
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

    admin_state[msg.chat.id] = {"step": "age"}
    await msg.answer("🔐 Обери вік:", reply_markup=make_kb(menu_data.keys(), False))

# =====================
# ОСНОВНИЙ ХЕНДЛЕР
# =====================

@dp.message_handler()
async def handler(msg: types.Message):
    text = msg.text
    user = user_state.setdefault(msg.chat.id, {"level": "age"})
    admin = admin_state.get(msg.chat.id)

    # =====================
    # ADMIN ЛОГІКА
    # =====================

    if admin:

        if text == "⬅️ Назад":
            admin_state.pop(msg.chat.id)
            await msg.answer("Вийшли з адмінки")
            return

        # ВІК
        if admin["step"] == "age":
            if text in menu_data:
                admin["age"] = text
                admin["step"] = "season"
                await msg.answer("Обери сезон:", reply_markup=make_kb(menu_data[text].keys()))
            return

        # СЕЗОН
        if admin["step"] == "season":
            if text in menu_data[admin["age"]]:
                admin["season"] = text
                admin["step"] = "month"
                await msg.answer("Обери місяць:", reply_markup=make_kb(menu_data[admin["age"]][text].keys()))
            return

        # МІСЯЦЬ
        if admin["step"] == "month":
            if text in menu_data[admin["age"]][admin["season"]]:
                admin["month"] = text
                admin["step"] = "topic"
                topics = menu_data[admin["age"]][admin["season"]][text]["topics"]
                await msg.answer("Обери тему:", reply_markup=make_kb(topics.keys()))
            return

        # ТЕМА
        if admin["step"] == "topic":
            topics = menu_data[admin["age"]][admin["season"]][admin["month"]]["topics"]
            if text in topics:
                admin["topic"] = text
                admin["step"] = "edit"

                await msg.answer(
                    "Що редагуємо:",
                    reply_markup=make_kb([
                        "✏️ Батьки",
                        "📅 Дні",
                        "🎮 Ігри",
                        "📄 PDF"
                    ])
                )
            return

        # ВИБІР РЕДАГУВАННЯ
        if admin["step"] == "edit":

            if text == "📅 Дні":
                admin["step"] = "choose_day"

                topic = menu_data[admin["age"]][admin["season"]][admin["month"]]["topics"][admin["topic"]]

                days = topic.get("days", {
                    "Понеділок": "",
                    "Вівторок": "",
                    "Середа": "",
                    "Четвер": "",
                    "Пʼятниця": ""
                })

                await msg.answer("Обери день:", reply_markup=make_kb(days.keys()))
                return

            else:
                admin["edit_type"] = text
                admin["step"] = "input"
                await msg.answer("Введи текст:")
                return

        # ВИБІР ДНЯ
        if admin.get("step") == "choose_day":
            admin["day"] = text
            admin["step"] = "edit_day"
            await msg.answer(f"Введи текст для {text}:")
            return

        # ЗБЕРЕЖЕННЯ ДНЯ
        if admin.get("step") == "edit_day":

            topic = menu_data[admin["age"]][admin["season"]][admin["month"]]["topics"][admin["topic"]]

            if "days" not in topic:
                topic["days"] = {}

            topic["days"][admin["day"]] = text

            with open("menu_data.json", "w", encoding="utf-8") as f:
                json.dump(menu_data, f, ensure_ascii=False, indent=2)

            await msg.answer("✅ День збережено")
            admin_state.pop(msg.chat.id)
            return

        # ВВІД ДАНИХ
        if admin["step"] == "input":

            topic = menu_data[admin["age"]][admin["season"]][admin["month"]]["topics"][admin["topic"]]

            if admin["edit_type"] == "✏️ Батьки":
                topic["parents"] = text

            elif admin["edit_type"] == "🎮 Ігри":
                topic["games"] = topic.get("games", [])
                topic["games"].append(text)

            elif admin["edit_type"] == "📄 PDF":
                topic["pdf"] = text

            with open("menu_data.json", "w", encoding="utf-8") as f:
                json.dump(menu_data, f, ensure_ascii=False, indent=2)

            await msg.answer("✅ Збережено")
            admin_state.pop(msg.chat.id)
            return

    # =====================
    # НАЗАД (КОРИСТУВАЧ)
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
            await msg.answer(days.get(text, "Немає інформації"), protect_content=True)

        elif text == "🎵 Пісні":
            songs = topic.get("songs", [])
            kb = [s["name"] for s in songs] if songs else []
            await msg.answer(
    f"{s['name']}\n\n{s.get('text','')}\n\n{s.get('link','')}",
    protect_content=True
)
            return

        elif text == "🎮 Ігри та досліди":
            games = topic.get("games", [])
            await msg.answer("\n".join(games) if games else "Немає ігор", protect_content=True)

        elif text == "📄 PDF":
            await msg.answer(topic.get("pdf", "Немає PDF"))

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
