import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

API_TOKEN = "7556358154:AAGdl65GLbDi4EvHdRl84VPRxlRkqgsTGVg"

ADMIN_ID = 711960970  # твій Telegram ID

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


# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_state[msg.chat.id] = {"level": "age"}
    await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))


# ---------- АДМІН ----------
@dp.message_handler(commands=["admin"])
async def admin(msg: types.Message):
    if msg.chat.id != ADMIN_ID:
        return

    user_state[msg.chat.id] = {"level": "admin_age"}
    await msg.answer("Адмін: оберіть вік", reply_markup=make_kb(menu_data.keys(), False))


# ---------- ОСНОВНИЙ ХЕНДЛЕР ----------
@dp.message_handler()
async def handler(msg: types.Message):
    text = msg.text
    user = user_state.setdefault(msg.chat.id, {"level": "age"})

    level = user.get("level")

    # 🔙 НАЗАД
    if text == "⬅️ Назад":
        if level == "inside":
            user["level"] = "topic"
        elif level == "topic":
            user["level"] = "month"
        elif level == "month":
            user["level"] = "season"
        elif level == "season":
            user["level"] = "age"

    # ВІК
    if level == "age" and text in menu_data:
        user["age"] = text
        user["level"] = "season"
        await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[text].keys()))
        return

    # СЕЗОН
    if level == "season":
        seasons = menu_data[user["age"]]
        if text in seasons:
            user["season"] = text
            user["level"] = "month"
            await msg.answer("Оберіть місяць:", reply_markup=make_kb(seasons[text].keys()))
            return

    # МІСЯЦЬ
    if level == "month":
        months = menu_data[user["age"]][user["season"]]
        if text in months:
            user["month"] = text
            user["level"] = "topic"
            topics = months[text]["topics"]
            kb = list(topics.keys()) + ["📄 PDF"]
            await msg.answer("Оберіть тему:", reply_markup=make_kb(kb))
            return

    # PDF
    if text == "📄 PDF":
        link = menu_data[user["age"]][user["season"]][user["month"]]["pdf"]
        await msg.answer(link)
        return

    # ТЕМА
    if level == "topic":
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
                    "🎮 Ігри"
                ])
            )
            return

    topic = menu_data[user["age"]][user["season"]][user["month"]]["topics"].get(user.get("topic"))

    if not topic:
        return

    # БАТЬКИ
    if text == "📩 Батькам":
        await msg.answer(topic["parents"])
        return

    # ДНІ
    if text == "📅 Дні":
        await msg.answer("Оберіть день:", reply_markup=make_kb(topic["days"].keys()))
        return

    if text in topic["days"]:
        await msg.answer(topic["days"][text], protect_content=True)
        return

    # ІГРИ
    if text == "🎮 Ігри":
        await msg.answer("\n".join(topic["games"]), protect_content=True)
        return

    # ПІСНІ
    if text == "🎵 Пісні":
        kb = [s["name"] for s in topic["songs"]]
        await msg.answer("Оберіть пісню:", reply_markup=make_kb(kb))
        return

    for song in topic["songs"]:
        if text == song["name"]:
            await msg.answer(
                f"{song['name']}\n\n{song['text']}\n\n{song['link']}",
                protect_content=True
            )
            return


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
