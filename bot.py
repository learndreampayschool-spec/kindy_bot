import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

TOKEN = "7556358154:AAGdl65GLbDi4EvHdRl84VPRxlRkqgsTGVg"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

DATA_PATH = "/var/data/menu_data.json"

# ---------- LOAD DATA ----------
def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

menu_data = load_data()

# ---------- STATES ----------
class MenuStates(StatesGroup):
    age = State()
    season = State()
    topic = State()
    section = State()

# ---------- KEYBOARD ----------
def kb(items, add_back=True):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for i in items:
        keyboard.add(KeyboardButton(i))
    if add_back:
        keyboard.add(KeyboardButton("⬅️ Назад"))
    return keyboard

def section_kb():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📘 Методичка"))
    keyboard.add(KeyboardButton("🎥 Відео/пісня"))
    keyboard.add(KeyboardButton("👪 Батькам"))
    keyboard.add(KeyboardButton("🎮 Ігри"))
    keyboard.add(KeyboardButton("📝 Завдання"))
    keyboard.add(KeyboardButton("⬅️ Назад"))
    return keyboard

# ---------- START ----------
@dp.message_handler(commands=["start"], state="*")
async def start(m: types.Message, s: FSMContext):
    await s.finish()
    await m.answer("Оберіть вікову категорію:", reply_markup=kb(menu_data.keys(), add_back=False))
    await MenuStates.age.set()

# ---------- AGE ----------
@dp.message_handler(state=MenuStates.age)
async def choose_age(m: types.Message, s: FSMContext):
    if m.text not in menu_data:
        return
    await s.update_data(age=m.text)
    await m.answer("Оберіть сезон:", reply_markup=kb(menu_data[m.text].keys()))
    await MenuStates.season.set()

# ---------- SEASON ----------
@dp.message_handler(state=MenuStates.season)
async def choose_season(m: types.Message, s: FSMContext):
    data = await s.get_data()

    if m.text == "⬅️ Назад":
        return await m.answer("Оберіть вікову категорію:", reply_markup=kb(menu_data.keys(), add_back=False))

    age = data["age"]

    if m.text not in menu_data[age]:
        return

    await s.update_data(season=m.text)
    await m.answer("Оберіть тему:", reply_markup=kb(menu_data[age][m.text].keys()))
    await MenuStates.topic.set()

# ---------- TOPIC ----------
@dp.message_handler(state=MenuStates.topic)
async def choose_topic(m: types.Message, s: FSMContext):
    data = await s.get_data()

    if m.text == "⬅️ Назад":
        age = data["age"]
        return await m.answer("Оберіть сезон:", reply_markup=kb(menu_data[age].keys()))

    age = data["age"]
    season = data["season"]

    if m.text not in menu_data[age][season]:
        return

    await s.update_data(topic=m.text)
    await m.answer("Оберіть розділ:", reply_markup=section_kb())
    await MenuStates.section.set()

# ---------- SECTION ----------
@dp.message_handler(state=MenuStates.section)
if m.text == "⬅️ Назад":
    data = await s.get_data()

    # назад до тем
    if "topic" in data:
        await MenuStates.topic.set()
        age = data["age"]
        season = data["season"]
        return await m.answer(
            "Оберіть тему:",
            reply_markup=kb(menu_data[age][season].keys())
        )

    # назад до сезонів
    elif "season" in data:
        await MenuStates.season.set()
        age = data["age"]
        return await m.answer(
            "Оберіть сезон:",
            reply_markup=kb(menu_data[age].keys())
        )

    # назад до віку
    elif "age" in data:
        await MenuStates.age.set()
        return await m.answer(
            "Оберіть вікову категорію:",
            reply_markup=kb(menu_data.keys(), add_back=False)
        )

    age = data["age"]
    season = data["season"]
    topic = data["topic"]

    topic_data = menu_data[age][season][topic]

    mapping = {
        "📘 Методичка": "method",
        "🎥 Відео/пісня": "video",
        "👪 Батькам": "parents",
        "🎮 Ігри": "games",
        "📝 Завдання": "tasks"
    }

    key = mapping.get(m.text)
    if not key:
        return

    for item in topic_data.get(key, []):
        await m.answer(item)

# ---------- RUN ----------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
