import os
import json
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# --- Load env and init ---
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 711960970  # ← заміни на свій Telegram ID

bot = Bot(token=API_TOKEN, parse_mode="HTML")  # можна "HTML" або None
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

MENU_FILE = "menu_data.json"

# === Helpers for long messages & schema migration ===

MAX_TG = 4000  # запас до обмеження Telegram 4096 символів

def split_text(text: str, max_len: int = MAX_TG):
    """Розумний поділ довгого тексту на шматки ≤ max_len."""
    seps = ["\n\n", "\n", ". "]
    chunks, buf = [], text or ""
    for sep in seps:
        if len(buf) <= max_len:
            break
        while len(buf) > max_len:
            cut = buf.rfind(sep, 0, max_len)
            if cut == -1:
                cut = max_len
            chunks.append(buf[:cut].rstrip())
            buf = buf[cut:].lstrip()
    if buf:
        chunks.append(buf)
    return chunks

def ensure_topic_structure(topic_obj: dict):
    """
    Міграція зі старого формату:
      {'text': '...'} →
      {'messages': ['...'], 'media': [], 'links': []}
    і гарантія ключів у новому форматі.
    """
    if topic_obj is None:
        return {"messages": [], "media": [], "links": []}
    if "messages" not in topic_obj:
        msgs = []
        if topic_obj.get("text"):
            msgs.append(topic_obj["text"])
        topic_obj["messages"] = msgs
    topic_obj.setdefault("media", [])
    topic_obj.setdefault("links", [])
    return topic_obj

def migrate_menu_schema(data: dict):
    """Пройтись по всіх темах і гарантувати наявність messages[]."""
    for age_key, seasons in data.items():
        for season_key, topics in seasons.items():
            for topic_key, topic_obj in list(topics.items()):
                topics[topic_key] = ensure_topic_structure(topic_obj)
    return data

def load_menu():
    with open(MENU_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    return migrate_menu_schema(raw)

def save_menu(data):
    with open(MENU_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

menu_data = load_menu()

# === FSM ===

class MenuStates(StatesGroup):
    age = State()
    season = State()
    topic = State()

class AdminStates(StatesGroup):
    age = State()
    season = State()
    topic = State()
    action = State()
    content = State()

class AdminMsgStates(StatesGroup):
    """Робота з повідомленнями в межах теми (add/edit/delete)."""
    age = State()
    season = State()
    topic = State()
    mode = State()        # "add" / "edit" / "delete"
    list_wait = State()   # вибір номеру повідомлення
    content = State()     # введення тексту для add/edit

class AdminRenameStates(StatesGroup):
    """Перейменування теми."""
    age = State()
    season = State()
    topic = State()
    new_title = State()

# === UI helpers ===

def make_keyboard(options, add_back=True):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for opt in options:
        kb.add(KeyboardButton(opt))
    if add_back:
        kb.add(KeyboardButton("⬅️ Назад"))
    return kb

admin_panel_kb = ReplyKeyboardMarkup(resize_keyboard=True)
admin_panel_kb.add(
    KeyboardButton("➕ Додати тему"),
    KeyboardButton("✏️ Перейменувати тему"),
)
admin_panel_kb.add(
    KeyboardButton("🧩 Повідомлення теми (додати/редагувати/видалити)"),
)
admin_panel_kb.add(
    KeyboardButton("❌ Видалити тему"),
    KeyboardButton("⬅️ Назад")
)

def make_mode_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Додати повідомлення"))
    kb.add(KeyboardButton("✏️ Редагувати повідомлення"))
    kb.add(KeyboardButton("🗑 Видалити повідомлення"))
    kb.add(KeyboardButton("⬅️ Назад"))
    return kb

# ========================= USER FLOW =========================

@dp.message_handler(commands=['start'], state="*")
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish()
    kb = make_keyboard(list(menu_data.keys()), add_back=False)
    if message.from_user.id == ADMIN_ID:
        kb.add(KeyboardButton("🛠 Адмін панель"))
    await message.answer("Оберіть вікову категорію:", reply_markup=kb)
    await MenuStates.age.set()

@dp.message_handler(lambda m: m.text in menu_data, state=MenuStates.age)
async def choose_season(message: types.Message, state: FSMContext):
    age = message.text.strip()
    await state.update_data(age=age)
    seasons = menu_data[age].keys()
    await message.answer("Оберіть сезон:", reply_markup=make_keyboard(seasons))
    await MenuStates.season.set()

@dp.message_handler(lambda m: m.text in ["⬅️ Назад"], state=MenuStates.season)
async def back_to_age(message: types.Message, state: FSMContext):
    await start_cmd(message, state)

@dp.message_handler(state=MenuStates.season)
async def choose_topic(message: types.Message, state: FSMContext):
    data = await state.get_data()
    age = data["age"]
    season = message.text.strip()
    if season not in menu_data[age]:
        await message.answer("Невірний сезон")
        return
    await state.update_data(season=season)
    topics = list(menu_data[age][season].keys())
    await message.answer("Оберіть тему:", reply_markup=make_keyboard(topics))
    await MenuStates.topic.set()

@dp.message_handler(lambda m: m.text == "⬅️ Назад", state=MenuStates.topic)
async def back_to_season(message: types.Message, state: FSMContext):
    data = await state.get_data()
    age = data.get("age", "")
    seasons = list(menu_data[age].keys())
    await message.answer("Оберіть сезон:", reply_markup=make_keyboard(seasons))
    await MenuStates.season.set()


@dp.message_handler(state=MenuStates.topic)
async def handle_topic_selection(message: types.Message, state: FSMContext):
    text = message.text.strip()

    # Якщо натиснуто "⬅️ Назад"
    if text == "⬅️ Назад":
        data = await state.get_data()
        age = data.get("age", "")
        seasons = list(menu_data[age].keys())
        await message.answer("Оберіть сезон:", reply_markup=make_keyboard(seasons))
        return await MenuStates.season.set()

    # Якщо натиснуто "📩 Текст для батьків"
    if text == "📩 Текст для батьків":
        data = await state.get_data()
        age = data.get("age")
        season = data.get("season")
        topic = data.get("topic")

        topic_obj = menu_data.get(age, {}).get(season, {}).get(topic)
        topic_obj = ensure_topic_structure(topic_obj)
        messages_list = topic_obj.get("messages", [])

        if not messages_list:
            return await message.answer("⚠️ Немає повідомлень у темі.")

        first_msg = messages_list[0]
        for chunk in split_text(first_msg):
            await message.answer(chunk)
        return

    # Інакше — звичайний вибір теми
    data = await state.get_data()
    age = data.get("age")
    season = data.get("season")
    topic = text

    topic_obj = menu_data.get(age, {}).get(season, {}).get(topic)
    if not topic_obj:
        await message.answer("⛔ Тема не знайдена.")
        return

    await state.update_data(topic=topic)

    topic_obj = ensure_topic_structure(topic_obj)
    messages_list = topic_obj.get("messages", [])
    if not messages_list:
        await message.answer(
            "🔸 Наразі у темі немає повідомлень.",
            reply_markup=make_keyboard(["⬅️ Назад"], add_back=False)
        )
        return

    for msg_text in messages_list:
        for chunk in split_text(msg_text):
            await message.answer(chunk)

    await message.answer(
        "Готово ✅",
        reply_markup=make_keyboard(["📩 Текст для батьків", "⬅️ Назад"], add_back=False)
    )



# ========================= ADMIN FLOW =========================

@dp.message_handler(lambda m: m.text == "🛠 Адмін панель", state="*")
async def admin_panel(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Ти не адмін.")
        return
    await state.finish()
    await message.answer("Панель адміністратора:", reply_markup=admin_panel_kb)

# ----- Старе меню керування темами (add/edit/delete) -----

@dp.message_handler(lambda m: m.text in ["➕ Додати тему", "❌ Видалити тему"], state="*")
async def choose_admin_action_simple(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Ти не адмін.")
    action_map = {
        "➕ Додати тему": "add",
        "❌ Видалити тему": "delete"
    }
    await state.set_state(AdminStates.age)
    await state.update_data(action=action_map[message.text])
    await message.answer("Оберіть вікову категорію:", reply_markup=make_keyboard(list(menu_data.keys())))

@dp.message_handler(lambda m: m.text == "✏️ Перейменувати тему", state="*")
async def rename_topic_entry(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Ти не адмін.")
    await state.finish()
    await AdminRenameStates.age.set()
    await message.answer("Оберіть вікову категорію:", reply_markup=make_keyboard(list(menu_data.keys())))

@dp.message_handler(state=AdminStates.age)
async def admin_choose_season(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_panel(message, state)
    age = message.text.strip()
    if age not in menu_data:
        await message.answer("Невірна категорія")
        return
    await state.update_data(age=age)
    await AdminStates.season.set()
    await message.answer("Оберіть сезон:", reply_markup=make_keyboard(menu_data[age].keys()))

@dp.message_handler(state=AdminStates.season)
async def admin_choose_topic(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await choose_admin_action_simple(message, state)
    data = await state.get_data()
    age = data['age']
    season = message.text.strip()
    if season not in menu_data[age]:
        await message.answer("Невірний сезон")
        return
    await state.update_data(season=season)
    await AdminStates.topic.set()
    topics = list(menu_data[age][season].keys())
    await message.answer("Оберіть тему:", reply_markup=make_keyboard(topics))

@dp.message_handler(state=AdminStates.topic)
async def admin_topic_action(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_choose_season(message, state)

    data = await state.get_data()
    action = data['action']
    age, season, topic = data['age'], data['season'], message.text.strip()
    await state.update_data(topic=topic)

    if action == "delete":
        if topic in menu_data[age][season]:
            del menu_data[age][season][topic]
            save_menu(menu_data)
            await message.answer("✅ Тему видалено.", reply_markup=admin_panel_kb)
        else:
            await message.answer("❌ Тема не знайдена.", reply_markup=admin_panel_kb)
        await state.finish()
        return

    # action == "add": додавання/оновлення «першого повідомлення» теми
    await AdminStates.content.set()
    await message.answer("Введіть текст теми (буде збережено як перше повідомлення):", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=AdminStates.content)
async def admin_save_content(message: types.Message, state: FSMContext):
    """Збереження 'першого' повідомлення теми для простого сценарію."""
    data = await state.get_data()
    age, season, topic = data["age"], data["season"], data["topic"]
    content = (message.text or "").strip()
    if not content:
        await message.answer("⚠️ Текст не може бути порожнім.")
        return

    topic_obj = menu_data[age][season].get(topic)
    if not topic_obj:
        # створюємо нову тему
        menu_data[age][season][topic] = {"messages": [content], "media": [], "links": []}
    else:
        topic_obj = ensure_topic_structure(topic_obj)
        if topic_obj["messages"]:
            topic_obj["messages"][0] = content
        else:
            topic_obj["messages"].append(content)
        menu_data[age][season][topic] = topic_obj

    save_menu(menu_data)
    await message.answer("✅ Тему збережено.", reply_markup=admin_panel_kb)
    await state.finish()

# ----- Перейменування теми -----

@dp.message_handler(state=AdminRenameStates.age)
async def rename_topic_age(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_panel(message, state)
    age = message.text.strip()
    if age not in menu_data:
        return await message.answer("Невірна категорія")
    await state.update_data(age=age)
    await AdminRenameStates.season.set()
    await message.answer("Оберіть сезон:", reply_markup=make_keyboard(menu_data[age].keys()))

@dp.message_handler(state=AdminRenameStates.season)
async def rename_topic_season(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await rename_topic_entry(message, state)
    data = await state.get_data()
    age = data["age"]
    season = message.text.strip()
    if season not in menu_data[age]:
        return await message.answer("Невірний сезон")
    await state.update_data(season=season)
    topics = list(menu_data[age][season].keys())
    await AdminRenameStates.topic.set()
    await message.answer("Оберіть тему для перейменування:", reply_markup=make_keyboard(topics))

@dp.message_handler(state=AdminRenameStates.topic)
async def rename_topic_pick(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await rename_topic_season(message, state)
    data = await state.get_data()
    age, season = data["age"], data["season"]
    old_topic = message.text.strip()
    if old_topic not in menu_data[age][season]:
        return await message.answer("❌ Тема не знайдена.")
    await state.update_data(old_topic=old_topic)
    await AdminRenameStates.new_title.set()
    await message.answer(f"Поточна назва: «{old_topic}»\n\nВведи НОВУ назву теми:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=AdminRenameStates.new_title)
async def rename_topic_apply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    age, season, old_topic = data["age"], data["season"], data["old_topic"]
    new_title = (message.text or "").strip()
    if not new_title:
        return await message.answer("Назва не може бути порожньою. Введи іншу:")
    # перейменувати ключ теми в JSON
    topic_obj = menu_data[age][season].pop(old_topic)
    menu_data[age][season][new_title] = topic_obj
    save_menu(menu_data)
    await state.finish()
    await message.answer(f"✅ Назву змінено на: «{new_title}»", reply_markup=admin_panel_kb)

# ----- НОВЕ: робота з повідомленнями теми (add/edit/delete) -----

@dp.message_handler(lambda m: m.text == "🧩 Повідомлення теми (додати/редагувати/видалити)", state="*")
async def admin_msgs_entry(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Ти не адмін.")
    await state.finish()
    await AdminMsgStates.age.set()
    await message.answer("Оберіть вікову категорію:", reply_markup=make_keyboard(list(menu_data.keys())))

@dp.message_handler(state=AdminMsgStates.age)
async def admin_msgs_choose_season(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_panel(message, state)
    age = message.text.strip()
    if age not in menu_data:
        return await message.answer("Невірна категорія")
    await state.update_data(age=age)
    await AdminMsgStates.season.set()
    await message.answer("Оберіть сезон:", reply_markup=make_keyboard(menu_data[age].keys()))

@dp.message_handler(state=AdminMsgStates.season)
async def admin_msgs_choose_topic(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_msgs_entry(message, state)
    data = await state.get_data()
    age = data['age']
    season = message.text.strip()
    if season not in menu_data[age]:
        return await message.answer("Невірний сезон")
    await state.update_data(season=season)
    topics = list(menu_data[age][season].keys())
    await AdminMsgStates.topic.set()
    await message.answer("Оберіть тему:", reply_markup=make_keyboard(topics))

@dp.message_handler(state=AdminMsgStates.topic)
async def admin_msgs_mode(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_msgs_choose_topic(message, state)
    data = await state.get_data()
    age, season = data["age"], data["season"]
    topic = message.text.strip()
    if topic not in menu_data[age][season]:
        return await message.answer("❌ Тема не знайдена.")
    await state.update_data(topic=topic)
    await AdminMsgStates.mode.set()
    await message.answer("Виберіть дію:", reply_markup=make_mode_kb())

@dp.message_handler(state=AdminMsgStates.mode)
async def admin_msgs_route(message: types.Message, state: FSMContext):
    action = message.text.strip()
    data = await state.get_data()
    age, season, topic = data["age"], data["season"], data["topic"]
    topic_obj = ensure_topic_structure(menu_data[age][season][topic])
    msgs = topic_obj["messages"]

    if action == "➕ Додати повідомлення":
        await AdminMsgStates.content.set()
        return await message.answer("Надішли текст НОВОГО повідомлення (може бути довгим):", reply_markup=ReplyKeyboardRemove())

    if action in ("✏️ Редагувати повідомлення", "🗑 Видалити повідомлення"):
        if not msgs:
            await AdminMsgStates.mode.set()
            return await message.answer("У темі ще немає повідомлень.", reply_markup=make_mode_kb())
        # список для вибору індексу
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        for i in range(1, len(msgs)+1):
            kb.add(KeyboardButton(str(i)))
        kb.add(KeyboardButton("⬅️ Назад"))
        await state.update_data(op="edit" if "Редагувати" in action else "delete")
        await AdminMsgStates.list_wait.set()
        return await message.answer("Оберіть номер повідомлення:", reply_markup=kb)

    if action == "⬅️ Назад":
        topics = list(menu_data[age][season].keys())
        await AdminMsgStates.topic.set()
        return await message.answer("Оберіть тему:", reply_markup=make_keyboard(topics))

    await message.answer("Команда не розпізнана. Оберіть дію з клавіатури.")

@dp.message_handler(state=AdminMsgStates.list_wait)
async def admin_msgs_pick_index(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await AdminMsgStates.mode.set()
        return await message.answer("Виберіть дію:", reply_markup=make_mode_kb())

    if not (message.text or "").isdigit():
        return await message.answer("Введи номер з клавіатури.")
    idx = int(message.text) - 1

    data = await state.get_data()
    age, season, topic, op = data["age"], data["season"], data["topic"], data["op"]
    topic_obj = ensure_topic_structure(menu_data[age][season][topic])
    msgs = topic_obj["messages"]

    if idx < 0 or idx >= len(msgs):
        return await message.answer("Невірний номер.")

    await state.update_data(index=idx)

    if op == "edit":
        await AdminMsgStates.content.set()
        prev = msgs[idx]
        preview = prev if len(prev) < 900 else prev[:900] + "…"
        return await message.answer(
            "Надішли НОВИЙ текст для цього повідомлення (старий заміниться повністю):\n\n" + preview,
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        # delete
        del msgs[idx]
        save_menu(menu_data)
        await AdminMsgStates.mode.set()
        return await message.answer("✅ Повідомлення видалено.", reply_markup=make_mode_kb())

@dp.message_handler(state=AdminMsgStates.content)
async def admin_msgs_save_content(message: types.Message, state: FSMContext):
    data = await state.get_data()
    age, season, topic = data["age"], data["season"], data["topic"]
    topic_obj = ensure_topic_structure(menu_data[age][season][topic])
    msgs = topic_obj["messages"]

    new_text = (message.text or "").strip()
    if not new_text:
        return await message.answer("⚠️ Текст не може бути порожнім. Спробуй ще раз:")

    idx = data.get("index", None)
    if idx is None:
        # ADD
        msgs.append(new_text)
        save_menu(menu_data)
        await AdminMsgStates.mode.set()
        return await message.answer("✅ Повідомлення додано.", reply_markup=make_mode_kb())
    else:
        # EDIT
        msgs[idx] = new_text
        save_menu(menu_data)
        await state.update_data(index=None)
        await AdminMsgStates.mode.set()
        return await message.answer("✅ Повідомлення оновлено.", reply_markup=make_mode_kb())

# ==== RUN ====

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
