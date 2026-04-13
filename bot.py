import os
import json
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 711960970

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

MENU_FILE = "/var/data/menu_data.json"

# ================= DATA =================

def ensure_file():
    os.makedirs("/var/data", exist_ok=True)
    if not os.path.exists(MENU_FILE):
        with open(MENU_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def migrate(data):
    for age in data:
        for season in data[age]:
            for topic in data[age][season]:
                t = data[age][season][topic]

                # стара структура → нова
                if "messages" in t:
                    t = {
                        "method": t["messages"],
                        "video": [],
                        "parents": [],
                        "games": [],
                        "tasks": []
                    }

                # гарантуємо всі поля
                for key in ["method","video","parents","games","tasks"]:
                    t.setdefault(key, [])

                data[age][season][topic] = t

            # 🔥 додаємо літо автоматично
            if "Літо" not in data[age]:
                data[age]["Літо"] = {}

    return data

def load_menu():
    ensure_file()
    try:
        with open(MENU_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return migrate(data)
    except:
        return {}

def save_menu(data):
    with open(MENU_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

menu_data = load_menu()

# ================= UI =================

def kb(list_items, back=True):
    k = ReplyKeyboardMarkup(resize_keyboard=True)
    for i in list_items:
        k.add(KeyboardButton(i))
    if back:
        k.add(KeyboardButton("⬅️ Назад"))
    return k

def topic_menu():
    k = ReplyKeyboardMarkup(resize_keyboard=True)
    k.add("📘 Методичка")
    k.add("🎵 Відео/пісня")
    k.add("💬 Батькам")
    k.add("🎲 Ігри")
    k.add("📄 Завдання")
    k.add("⬅️ Назад")
    return k

# ================= STATES =================

class S(StatesGroup):
    age = State()
    season = State()
    topic = State()
    section = State()

# ================= FLOW =================

@dp.message_handler(commands=["start"], state="*")
async def start(m: types.Message, s: FSMContext):
    await s.finish()
    if not menu_data:
        return await m.answer("⚠️ Дані ще не додані")

    k = kb(menu_data.keys(), False)
    if m.from_user.id == ADMIN_ID:
        k.add("🛠 Адмін")

    await m.answer("Оберіть вік:", reply_markup=k)
    await S.age.set()

@dp.message_handler(state=S.age)
async def age(m: types.Message, s: FSMContext):
    if m.text not in menu_data:
        return
    await s.update_data(age=m.text)
    await m.answer("Сезон:", reply_markup=kb(menu_data[m.text].keys()))
    await S.season.set()

@dp.message_handler(state=S.season)
async def season(m: types.Message, s: FSMContext):
    d = await s.get_data()
    age = d["age"]

    if m.text not in menu_data[age]:
        return

    await s.update_data(season=m.text)
    await m.answer("Тема:", reply_markup=kb(menu_data[age][m.text].keys()))
    await S.topic.set()

@dp.message_handler(state=S.topic)
async def topic(m: types.Message, s: FSMContext):
    d = await s.get_data()
    age, season = d["age"], d["season"]

    if m.text not in menu_data[age][season]:
        return

    await s.update_data(topic=m.text)
    await m.answer("Обери розділ:", reply_markup=topic_menu())
    await S.section.set()

# ================= SECTIONS =================

def send_list(m, data):
    if not data:
        return m.answer("Поки немає інформації")
    for item in data:
        m.answer(item)

@dp.message_handler(state=S.section)
async def section(m: types.Message, s: FSMContext):
    if m.text == "⬅️ Назад":
        d = await s.get_data()
        age, season = d["age"], d["season"]
        return await m.answer("Тема:", reply_markup=kb(menu_data[age][season].keys()))

    d = await s.get_data()
    t = menu_data[d["age"]][d["season"]][d["topic"]]

    mapping = {
        "📘 Методичка": "method",
        "🎵 Відео/пісня": "video",
        "💬 Батькам": "parents",
        "🎲 Ігри": "games",
        "📄 Завдання": "tasks"
    }

    key = mapping.get(m.text)
    if not key:
        return

    for msg in t.get(key, []):
        await m.answer(msg)

# ================= RUN =================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
