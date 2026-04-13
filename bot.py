import logging
import json
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = "ТУТ_ТВІЙ_ТОКЕН"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Завантаження JSON
with open("menu_data.json", "r", encoding="utf-8") as f:
    menu_data = json.load(f)

# --- STATES ---
class MenuStates(StatesGroup):
    age = State()
    season = State()
    topic = State()
    section = State()

# --- КНОПКИ ---
def kb(items, add_back=True):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for item in items:
        keyboard.add(item)
    if add_back:
        keyboard.add("⬅️ Назад")
    return keyboard

# --- START ---
@dp.message_handler(commands=["start"])
async def start(m: types.Message, state: FSMContext):
    await state.finish()
    await MenuStates.age.set()
    await m.answer("Оберіть вікову категорію:", reply_markup=kb(menu_data.keys(), add_back=False))

# --- ВІК ---
@dp.message_handler(state=MenuStates.age)
async def choose_age(m: types.Message, state: FSMContext):
    if m.text not in menu_data:
        return

    await state.update_data(age=m.text)
    await MenuStates.season.set()

    await m.answer("Оберіть сезон:", reply_markup=kb(menu_data[m.text].keys()))

# --- СЕЗОН ---
@dp.message_handler(state=MenuStates.season)
async def choose_season(m: types.Message, state: FSMContext):

    if m.text == "⬅️ Назад":
        await MenuStates.age.set()
        return await m.answer("Оберіть вікову категорію:", reply_markup=kb(menu_data.keys(), add_back=False))

    data = await state.get_data()
    age = data["age"]

    if m.text not in menu_data[age]:
        return

    await state.update_data(season=m.text)
    await MenuStates.topic.set()

    await m.answer("Оберіть тему:", reply_markup=kb(menu_data[age][m.text].keys()))

# --- ТЕМА ---
@dp.message_handler(state=MenuStates.topic)
async def choose_topic(m: types.Message, state: FSMContext):

    if m.text == "⬅️ Назад":
        data = await state.get_data()
        age = data["age"]

        await MenuStates.season.set()
        return await m.answer("Оберіть сезон:", reply_markup=kb(menu_data[age].keys()))

    data = await state.get_data()
    age = data["age"]
    season = data["season"]

    if m.text not in menu_data[age][season]:
        return

    await state.update_data(topic=m.text)
    await MenuStates.section.set()

    await m.answer(
        "Оберіть розділ:",
        reply_markup=kb(["Методичка", "Відео", "Батькам", "Ігри", "Завдання"])
    )

# --- РОЗДІЛ ---
@dp.message_handler(state=MenuStates.section)
async def show_section(m: types.Message, state: FSMContext):

    data = await state.get_data()

    # --- НАЗАД (РОЗУМНИЙ) ---
    if m.text == "⬅️ Назад":

        # назад до тем
        if "topic" in data:
            await MenuStates.topic.set()
            age = data["age"]
            season = data["season"]
            return await m.answer("Оберіть тему:", reply_markup=kb(menu_data[age][season].keys()))

        # назад до сезонів
        elif "season" in data:
            await MenuStates.season.set()
            age = data["age"]
            return await m.answer("Оберіть сезон:", reply_markup=kb(menu_data[age].keys()))

        # назад до віку
        elif "age" in data:
            await MenuStates.age.set()
            return await m.answer("Оберіть вікову категорію:", reply_markup=kb(menu_data.keys(), add_back=False))

    age = data["age"]
    season = data["season"]
    topic = data["topic"]

    content = menu_data[age][season][topic]

    # --- МЕТОДИЧКА ---
    if m.text == "Методичка":
        text = content.get("method", "Немає методички")
        await m.answer(text)

    # --- ВІДЕО ---
    elif m.text == "Відео":
        videos = content.get("video", [])
        if videos:
            for v in videos:
                await m.answer(v)
        else:
            await m.answer("Немає відео")

    # --- БАТЬКАМ ---
    elif m.text == "Батькам":
        text = content.get("parents", "Немає інформації")
        await m.answer(text)

    # --- ІГРИ ---
    elif m.text == "Ігри":
        games = content.get("games", [])
        if games:
            for g in games:
                await m.answer(g)
        else:
            await m.answer("Немає ігор")

    # --- ЗАВДАННЯ ---
    elif m.text == "Завдання":
        tasks = content.get("tasks", [])
        if tasks:
            for t in tasks:
                await m.answer(t)
        else:
            await m.answer("Немає завдань")

# --- ЗАПУСК ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
