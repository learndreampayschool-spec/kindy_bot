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

# ---------- ЗАГРУЗКА JSON ----------
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

# ---------- ЗБЕРЕГТИ JSON ----------
def save_json():
    with open("menu_data.json", "w", encoding="utf-8") as f:
        json.dump(menu_data, f, ensure_ascii=False, indent=2)

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_state[msg.chat.id] = {"level": "age"}
    await msg.answer("Оберіть вік:", reply_markup=make_kb(menu_data.keys(), False))

# ---------- АДМІН ----------
@dp.message_handler(commands=["admin"])
async def admin_panel(msg: types.Message):
    if msg.chat.id != ADMIN_ID:
        return

    await msg.answer(
        "🔐 Адмін панель:\n\n"
        "батьки: текст\n"
        "гра: назва гри\n"
        "пісня: назва|текст|посилання"
    )

# ---------- ОСНОВНИЙ ОБРОБНИК ----------
@dp.message_handler()
async def handler(msg: types.Message):
    text = msg.text

    if msg.chat.id not in user_state:
        user_state[msg.chat.id] = {"level": "age"}

    user = user_state[msg.chat.id]

    # ---------- АДМІН РЕДАГУВАННЯ ----------
    if msg.chat.id == ADMIN_ID and "topic" in user:
        topic = menu_data[user["age"]][user["season"]][user["month"]]["topics"][user["topic"]]

        if text.startswith("батьки:"):
            topic["parents"] = text.replace("батьки:", "").strip()
            save_json()
            await msg.answer("✔ Оновлено")
            return

        if text.startswith("гра:"):
            topic["games"].append(text.replace("гра:", "").strip())
            save_json()
            await msg.answer("✔ Гру додано")
            return

        if text.startswith("пісня:"):
            try:
                _, data = text.split(":", 1)
                name, song_text, link = data.split("|")

                topic["songs"].append({
                    "name": name.strip(),
                    "text": song_text.strip(),
                    "link": link.strip()
                })

                save_json()
                await msg.answer("✔ Пісню додано")
            except:
                await msg.answer("❌ Формат: пісня: назва|текст|посилання")
            return

    # ---------- НАЗАД ----------
    if text == "⬅️ Назад":

        if user.get("level") == "days":
            user["level"] = "inside"
            await msg.answer(
                "Оберіть розділ:",
                reply_markup=make_kb(["📩 Батькам", "📅 Дні", "🎵 Пісні", "🎮 Ігри"])
            )
            return

        if user.get("level") == "inside":
            user["level"] = "topic"
            topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]
            kb = list(topics.keys()) + ["📄 PDF"]
            await msg.answer("Оберіть тему:", reply_markup=make_kb(kb))
            return

        if user.get("level") == "topic":
            user["level"] = "month"
            months = menu_data[user["age"]][user["season"]]
            await msg.answer("Оберіть місяць:", reply_markup=make_kb(months.keys()))
            return

        if user.get("level") == "month":
            user["level"] = "season"
            await msg.answer("Оберіть сезон:", reply_markup=make_kb(menu_data[user["age"]].keys()))
            return

        if user.get("level") == "season":
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
            kb = list(topics.keys()) + ["📄 PDF"]

            await msg.answer("Оберіть тему:", reply_markup=make_kb(kb))
        return

    # ---------- PDF ----------
    if text == "📄 PDF":
        link = menu_data[user["age"]][user["season"]][user["month"]]["pdf"]
        await msg.answer(f"📄 Відкрити PDF:\n{link}")
        return

    # ---------- ТЕМИ ----------
    if user["level"] == "topic":
        topics = menu_data[user["age"]][user["season"]][user["month"]]["topics"]

        if text in topics:
            user["topic"] = text
            user["level"] = "inside"

            await msg.answer(
                "Оберіть розділ:",
                reply_markup=make_kb(["📩 Батькам", "📅 Дні", "🎵 Пісні", "🎮 Ігри"])
            )
        return

    # ---------- ВСЕРЕДИНІ ТЕМИ ----------
    topic = menu_data[user["age"]][user["season"]][user["month"]]["topics"].get(user.get("topic"))

    if not topic:
        return

    # БАТЬКИ
    if text == "📩 Батькам":
        await msg.answer(topic.get("parents", ""))
        return

    # ДНІ
    if text == "📅 Дні":
        user["level"] = "days"
        await msg.answer("Оберіть день:", reply_markup=make_kb(topic.get("days", {}).keys()))
        return

    if user.get("level") == "days" and text in topic.get("days", {}):
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
            await msg.answer(f"{song['text']}\n\n{song['link']}")
            return

    # ІГРИ
    if text == "🎮 Ігри":
        await msg.answer("\n".join(topic.get("games", [])), protect_content=True)
        return


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
