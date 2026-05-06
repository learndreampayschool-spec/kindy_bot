import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

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
    await msg.answer("🔐 Адмін режим", reply_markup=make_kb(list(menu_data.keys())))


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
        for key in ["edit_field", "topic", "month", "season", "age"]:
            if key in user:
                del user[key]
                break

    # ВІК
    if "age" not in user:
        if text in menu_data:
            user["age"] = text
            await msg.answer("Сезон:", reply_markup=make_kb(list(menu_data[text].keys())))
        return

    # СЕЗОН
    if "season" not in user:
        seasons = menu_data[user["age"]]
        if text in seasons:
            user["season"] = text
            await msg.answer("Місяць:", reply_markup=make_kb(list(seasons[text].keys())))
        return

    # МІСЯЦЬ
    if "month" not in user:
        months = menu_data[user["age"]][user["season"]]
        if text in months:
            user["month"] = text

            topics = [k for k in months[text] if k != "PDF"]
            kb = topics + ["📄 PDF"]
            await msg.answer("Оберіть:", reply_markup=make_kb(kb))
        return

    # PDF
    if text == "📄 PDF":
        if user.get("admin"):
            user["edit_field"] = "PDF"
            await msg.answer("Встав новий PDF:")
        else:
            pdf = menu_data[user["age"]][user["season"]][user["month"]].get("PDF", "Немає")
            await msg.answer(pdf)
        return

    # ТЕМА
    if "topic" not in user:
        topics = menu_data[user["age"]][user["season"]][user["month"]]
        if text in topics:
            user["topic"] = text

            if user.get("admin"):
                await msg.answer("Що редагувати?",
                    reply_markup=make_kb([
                        "✏️ Батькам",
                        "✏️ Понеділок",
                        "✏️ Вівторок",
                        "✏️ Середа",
                        "✏️ Четвер",
                        "✏️ П’ятниця"
                    ])
                )
            else:
                await msg.answer("Оберіть розділ",
                    reply_markup=make_kb([
                        "📩 Батькам",
                        "📅 Дні"
                    ])
                )
        return

    topic_data = menu_data[user["age"]][user["season"]][user["month"]][user["topic"]]

    # АДМІН РЕДАГУВАННЯ
    if text.startswith("✏️"):
        field = text.replace("✏️ ", "")
        user["edit_field"] = field
        await msg.answer("Встав новий текст:")
        return

    if "edit_field" in user and user.get("admin"):
        field = user["edit_field"]

        if field == "PDF":
            menu_data[user["age"]][user["season"]][user["month"]]["PDF"] = text
        else:
            topic_data[field] = text

        save_data(menu_data)
        del user["edit_field"]

        await msg.answer("Збережено ✅")
        return

    # КОРИСТУВАЧ
    if text == "📩 Батькам":
        await msg.answer(topic_data.get("Повідомлення батькам", "Пусто"))
        return

    if text == "📅 Дні":
        await msg.answer("Обери день",
            reply_markup=make_kb([
                "Понеділок",
                "Вівторок",
                "Середа",
                "Четвер",
                "П’ятниця"
            ])
        )
        return

    if text in ["Понеділок", "Вівторок", "Середа", "Четвер", "П’ятниця"]:
        await msg.answer(topic_data.get(text, "Немає"))
        return


if __name__ == "__main__":
    executor.start_polling(dp)
