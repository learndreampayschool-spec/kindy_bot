import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Завантаження JSON
def load_data():
    with open("menu_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open("menu_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

menu_data = load_data()

users = {}

def make_kb(items):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in items:
        kb.add(types.KeyboardButton(i))
    kb.add(types.KeyboardButton("⬅️ Назад"))
    return kb


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    users[msg.from_user.id] = {}
    await msg.answer("Оберіть вік:", reply_markup=make_kb(list(menu_data.keys())))


@dp.message_handler(commands=["admin"])
async def admin(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    users[msg.from_user.id] = {"admin": True}
    await msg.answer("Адмін: оберіть вік", reply_markup=make_kb(list(menu_data.keys())))


@dp.message_handler()
async def handler(msg: types.Message):
    global menu_data
    user_id = msg.from_user.id
    text = msg.text

    if user_id not in users:
        users[user_id] = {}

    user = users[user_id]

    # 🔙 НАЗАД
    if text == "⬅️ Назад":

        if "edit_mode" in user:
            del user["edit_mode"]

        elif "topic" in user:
            del user["topic"]
            topics = menu_data[user["age"]][user["season"]][user["month"]]
            topics = [k for k in topics if k != "PDF"]
            await msg.answer("Оберіть тему:", reply_markup=make_kb(topics))
            return

        elif "month" in user:
            del user["month"]
            months = menu_data[user["age"]][user["season"]]
            await msg.answer("Оберіть місяць:", reply_markup=make_kb(list(months.keys())))
            return

        elif "season" in user:
            del user["season"]
            seasons = menu_data[user["age"]]
            await msg.answer("Оберіть сезон:", reply_markup=make_kb(list(seasons.keys())))
            return

        elif "age" in user:
            del user["age"]
            await msg.answer("Оберіть вік:", reply_markup=make_kb(list(menu_data.keys())))
            return

    # ВІК
    if "age" not in user:
        if text in menu_data:
            user["age"] = text
            seasons = list(menu_data[text].keys())
            await msg.answer("Оберіть сезон:", reply_markup=make_kb(seasons))
        return

    # СЕЗОН
    if "season" not in user:
        seasons = menu_data[user["age"]]
        if text in seasons:
            user["season"] = text
            months = list(seasons[text].keys())
            await msg.answer("Оберіть місяць:", reply_markup=make_kb(months))
        return

    # МІСЯЦЬ
    if "month" not in user:
        months = menu_data[user["age"]][user["season"]]
        if text in months:
            user["month"] = text

            month_data = months[text]
            topics = [k for k in month_data.keys() if k != "PDF"]

            kb = topics + ["📄 PDF"]
            await msg.answer("Оберіть:", reply_markup=make_kb(kb))
        return

    # 📄 PDF МІСЯЦЯ
    if text == "📄 PDF":
        month_data = menu_data[user["age"]][user["season"]][user["month"]]
        pdf = month_data.get("PDF", "Немає PDF")
        await msg.answer(f"📄 PDF:\n{pdf}")
        return

    # ТЕМА
    if "topic" not in user:
        topics = menu_data[user["age"]][user["season"]][user["month"]]
        if text in topics:
            user["topic"] = text

            buttons = ["📩 Батькам", "📅 Дні", "🎵 Пісні", "🎮 Ігри"]
            if user_id == ADMIN_ID:
                buttons += ["✏️ Редагувати"]

            await msg.answer("Оберіть розділ:", reply_markup=make_kb(buttons))
        return

    topic_data = menu_data[user["age"]][user["season"]][user["month"]][user["topic"]]

    # 📩 БАТЬКАМ
    if text == "📩 Батькам":
        await msg.answer(topic_data.get("Повідомлення батькам", "Немає тексту"))
        return

    # 📅 ДНІ
    if text == "📅 Дні":
        days = ["Понеділок", "Вівторок", "Середа", "Четвер", "П’ятниця"]
        await msg.answer("Оберіть день:", reply_markup=make_kb(days))
        return

    if text in ["Понеділок", "Вівторок", "Середа", "Четвер", "П’ятниця"]:
        await msg.answer(topic_data.get(text, "Немає інформації"))
        return

    if text == "🎵 Пісні":
        await msg.answer("Поки пусто")
        return

    if text == "🎮 Ігри":
        await msg.answer("Поки пусто")
        return

    # ✏️ РЕДАГУВАННЯ
    if text == "✏️ Редагувати" and user_id == ADMIN_ID:
        user["edit_mode"] = True
        await msg.answer("Що редагуємо?", reply_markup=make_kb([
            "Батькам",
            "Понеділок",
            "Вівторок",
            "Середа",
            "Четвер",
            "П’ятниця",
            "📄 PDF"
        ]))
        return

    if "edit_mode" in user and user_id == ADMIN_ID:

        if text == "📄 PDF":
            user["edit_field"] = "PDF"
            await msg.answer("Встав посилання на PDF:")
            return

        user["edit_field"] = text
        await msg.answer("Встав новий текст:")
        return

    if "edit_field" in user and user_id == ADMIN_ID:

        field = user["edit_field"]

        if field == "PDF":
            menu_data[user["age"]][user["season"]][user["month"]]["PDF"] = text
        else:
            menu_data[user["age"]][user["season"]][user["month"]][user["topic"]][field] = text

        save_data(menu_data)

        del user["edit_field"]
        del user["edit_mode"]

        await msg.answer("Збережено ✅")
        return


if __name__ == "__main__":
    executor.start_polling(dp)
