import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

API_TOKEN = "7556358154:AAGdl65GLbDi4EvHdRl84VPRxlRkqgsTGVg"

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

    # ---------- НАЗАД ----------
    if text == "⬅️ Назад":

        if user.get("level") == "topic":
            user.pop("topic", None)
            user["level"] = "month"
            months = menu_data[user["age"]][user["season"]]
            await msg.answer("Оберіть місяць:", reply_markup=make_kb(months.keys()))
            return

        if user.get("level") == "month":
            user.pop("month", None)
            user["level"] = "season"
            await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[user["age"]].keys()))
            return

        if user.get("level") == "season":
            user.pop("season", None)
            user["level"] = "age"
            await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))
            return

        if user.get("level") == "age":
            user.clear()
            await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))
            return

    # ---------- ВІК ----------
    if text in menu_data:
        user["age"] = text
        user["level"] = "season"
        await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[text].keys()))
        return

    # ---------- СЕЗОН ----------
    if user.get("age") and text in menu_data[user["age"]]:
        user["season"] = text
        user["level"] = "month"
        await msg.answer("Оберіть місяць:", reply_markup=make_kb(menu_data[user["age"]][text].keys()))
        return

    # ---------- МІСЯЦЬ ----------
    if user.get("season"):
        months = menu_data[user["age"]][user["season"]]
        if text in months:
            user["month"] = text
            user["level"] = "topic"

            topics = months[text]["topics"]
            kb = list(topics.keys()) + ["📄 PDF"]

            await msg.answer("Оберіть тему:", reply_markup=make_kb(kb))
            return

    # ---------- PDF ----------
    if text == "📄 PDF":
        try:
            link = menu_data[user["age"]][user["season"]][user["month"]]["pdf"]
            await msg.answer(f"📄 Відкрити PDF:\n{link}")
        except:
            await msg.answer("PDF поки не додано")
        return

    # ---------- ТЕМИ ----------
    if user.get("level") == "topic":
        topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]

        if text in topics:
            user["topic"] = text
            user["level"] = "inside_topic"

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

    # ---------- ВСЕРЕДИНІ ТЕМИ ----------
    if user.get("level") == "inside_topic":

        topic = menu_data[user["age"]][user["season"]][user["month"]]["topics"][user["topic"]]

        # БАТЬКИ
        if text == "📩 Батькам":
            await msg.answer(topic.get("parents", "Немає даних"))
            return

        # ДНІ
        if text == "📅 Дні":
            await msg.answer("Оберіть день:", reply_markup=make_kb(topic.get("days", {}).keys()))
            return

        if text in topic.get("days", {}):
            await msg.answer(topic["days"][text], protect_content=True)
            return

        # ПІСНІ
        if text == "🎵 Пісні":
            songs = topic.get("songs", [])
            kb = [s["name"] for s in songs]
            await msg.answer("Оберіть пісню:", reply_markup=make_kb(kb))
            return

        for song in topic.get("songs", []):
            if text == song["name"]:
                await msg.answer(
                    f"🎵 {song['name']}\n\n"
                    f"🔘 Текст пісні:\n{song['text']}\n\n"
                    f"🔘 Відкрити відео:\n{song['link']}"
                )
                return

        # ІГРИ
        if text == "🎮 Ігри":
            await msg.answer("\n".join(topic.get("games", [])), protect_content=True)
            return

# ---------- ЗАПУСК ----------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
