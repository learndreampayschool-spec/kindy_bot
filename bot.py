import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Завантаження даних
with open("menu_data.json", "r", encoding="utf-8") as f:
    menu_data = json.load(f)

users = {}

# Клавіатура
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


@dp.message_handler()
async def handler(msg: types.Message):
    user_id = msg.from_user.id
    text = msg.text

    if user_id not in users:
        users[user_id] = {}

    user = users[user_id]

    # 🔙 НАЗАД (повністю робочий)
    if text == "⬅️ Назад":

        if "topic" in user:
            del user["topic"]
            topics = menu_data[user["age"]][user["season"]][user["month"]]
            await msg.answer("Оберіть тему:", reply_markup=make_kb(list(topics.keys())))
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
            topics = list(months[text].keys())
            await msg.answer("Оберіть тему:", reply_markup=make_kb(topics))
        return

    # ТЕМА
    if "topic" not in user:
        topics = menu_data[user["age"]][user["season"]][user["month"]]
        if text in topics:
            user["topic"] = text

            buttons = ["📩 Батькам", "📅 Дні", "🎵 Пісні", "🎮 Ігри", "📄 PDF"]
            await msg.answer("Оберіть розділ:", reply_markup=make_kb(buttons))
        return

    # ВСЕРЕДИНІ ТЕМИ
    topic_data = menu_data[user["age"]][user["season"]][user["month"]][user["topic"]]

    if text == "📩 Батькам":
        await msg.answer(topic_data.get("Повідомлення батькам", "Немає тексту"))
        return

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

    if text == "📄 PDF":
        await msg.answer(topic_data.get("PDF", "Немає PDF"))
        return


if __name__ == "__main__":
    executor.start_polling(dp)
