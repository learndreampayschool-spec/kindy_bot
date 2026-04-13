import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

API_TOKEN = "ТУТ_ТВІЙ_ТОКЕН"

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
    user_state[msg.chat.id] = {}
    await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))

# ---------- ОБРОБКА ----------

@dp.message_handler()
async def handler(msg: types.Message):
    text = msg.text
    user = user_state.setdefault(msg.chat.id, {})

    # НАЗАД
    if text == "⬅️ Назад":
        if "topic" in user:
            user.pop("topic")
            topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]
            await msg.answer("Оберіть тему:", reply_markup=make_kb(topics.keys()))
            return

        elif "month" in user:
            user.pop("month")
            months = menu_data[user["age"]][user["season"]]
            await msg.answer("Оберіть місяць:", reply_markup=make_kb(months.keys()))
            return

        elif "season" in user:
            user.pop("season")
            await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[user["age"]].keys()))
            return

        elif "age" in user:
            user.clear()
            await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))
            return

    # ВІК
    if text in menu_data:
        user["age"] = text
        await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[text].keys()))
        return

    # СЕЗОН
    if "age" in user and text in menu_data[user["age"]]:
        user["season"] = text
        await msg.answer("Оберіть місяць:", reply_markup=make_kb(menu_data[user["age"]][text].keys()))
        return

    # МІСЯЦЬ
    if "season" in user:
        months = menu_data[user["age"]][user["season"]]
        if text in months:
            user["month"] = text
            topics = months[text]["topics"]
            kb = list(topics.keys()) + ["📄 PDF"]
            await msg.answer("Оберіть тему:", reply_markup=make_kb(kb))
            return

    # PDF
    if text == "📄 PDF":
        link = menu_data[user["age"]][user["season"]][user["month"]]["pdf"]
        await msg.answer(f"Відкрити PDF:\n{link}")
        return

    # ТЕМА
    topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]
    if text in topics:
        user["topic"] = text
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

    topic = topics[user.get("topic")]

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

    # ПІСНІ
    if text == "🎵 Пісні":
        kb = [s["name"] for s in topic["songs"]]
        await msg.answer("Оберіть пісню:", reply_markup=make_kb(kb))
        return

    for song in topic["songs"]:
        if text == song["name"]:
            await msg.answer(
                f"🎵 {song['name']}\n\n"
                f"🔘 Текст:\n{song['text']}\n\n"
                f"🔘 Відео:\n{song['link']}"
            )
            return

    # ІГРИ
    if text == "🎮 Ігри":
        await msg.answer("\n".join(topic["games"]), protect_content=True)
        return


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
