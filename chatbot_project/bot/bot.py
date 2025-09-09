import time
import hmac
import hashlib
import json as pyjson
from urllib.parse import urlencode, urlparse

from pathlib import Path
import asyncio
import os
import requests
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Читаємо один спільний .env з кореня репозиторію
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# --- Конфіг ---
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://localhost:8000/api")
parsed = urlparse(DJANGO_API_URL)
API_ORIGIN = f"{parsed.scheme}://{parsed.netloc}"      # напр., https://api.pabot.online
API_PREFIX = parsed.path.rstrip("/")                    # напр., /api
DJANGO_API_KEY = os.getenv("DJANGO_API_KEY", "")
DJANGO_HMAC_SECRET = os.getenv("DJANGO_HMAC_SECRET", "")
DEFAULT_TIMEOUT = 10

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher(storage=MemoryStorage())

# --- Мінімальна довжина запиту (перевірка «мінімум 3 слова») ---
MIN_WORDS = 3

def _count_words_ua(text: str) -> int:
    """
    Рахує кількість «слів» у тексті, ігноруючи розділові знаки.
    Підтримує укр./латиницю, цифри та апострофи.
    """
    import re
    cleaned = re.sub(r"[^\w’'ґєіїа-яА-Яa-zA-Z0-9]+", " ", text, flags=re.U).strip()
    return len([w for w in cleaned.split() if w])

# ---------- HMAC-підпис ----------
def _make_signature(method: str, full_path: str, body_bytes: bytes) -> tuple[str, str, str]:
    """
    Підписуємо рядок: "<ts>\n<METHOD>\n<full_path>\n<sha256(body)>".
    Повертає (timestamp, "v1=<sig>", content_sha256_hex).
    """
    ts = str(int(time.time()))
    content_hash = hashlib.sha256(body_bytes or b"").hexdigest()
    to_sign = "\n".join([ts, method.upper(), full_path, content_hash]).encode("utf-8")
    sig = hmac.new(DJANGO_HMAC_SECRET.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return ts, f"v1={sig}", content_hash

def _base_headers(user_id: int | None, want_json: bool) -> dict:
    h = {
        "X-API-Key": DJANGO_API_KEY,
        "Accept": "application/json",
    }
    if want_json:
        h["Content-Type"] = "application/json"
    if user_id is not None:
        h["X-Telegram-Id"] = str(user_id)
    return h

def _full_path_for_sig(path: str, params: dict | None) -> str:
    """
    Канонічний шлях для ПІДПИСУ:
    <API_PREFIX><path>[?<sorted query>]
    приклад: "/api/search/?q=abc&page=1"
    """
    if not path.startswith("/"):
        path = "/" + path
    base = f"{API_PREFIX}{path}"
    if params:
        # важливо: впорядкування параметрів стабілізує підпис
        base = f"{base}?{urlencode(params, doseq=True)}"
    return base

# --- HTTP-хелпери (підписані) ---
def api_get(
    path: str,
    params: dict | None = None,
    *,
    user_id: int | None = None,
    timeout: int = DEFAULT_TIMEOUT,
):
    full_path = _full_path_for_sig(path, params)         # те, що підписуємо
    url = f"{API_ORIGIN}{full_path}"                     # ORIGIN + full_path (без повторного /api)
    ts, signature, content_hash = _make_signature("GET", full_path, b"")
    headers = _base_headers(user_id, want_json=False) | {
        "X-Timestamp": ts,
        "X-Signature": signature,
        "X-Content-SHA256": content_hash,
    }
    return requests.get(url, headers=headers, params=None, timeout=timeout)

def api_post(
    path: str,
    json: dict | None = None,
    *,
    user_id: int | None = None,
    timeout: int = DEFAULT_TIMEOUT,
):
    # серіалізуємо самі, щоб байти підпису == байтам тіла запиту
    raw_body = pyjson.dumps(json or {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    full_path = _full_path_for_sig(path, None)
    url = f"{API_ORIGIN}{full_path}"                     # ORIGIN + full_path
    ts, signature, content_hash = _make_signature("POST", full_path, raw_body)
    headers = _base_headers(user_id, want_json=True) | {
        "X-Timestamp": ts,
        "X-Signature": signature,
        "X-Content-SHA256": content_hash,
    }
    return requests.post(url, data=raw_body, headers=headers, timeout=timeout)

# ---------- Головна клавіатура ----------
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔍 Задати питання"),
            KeyboardButton(text="📄 Отримати інструкцію"),
            KeyboardButton(text="🔎 Знайти інструкцію"),
        ],
        [
            KeyboardButton(text="❗️Повідомити про помилку"),
            KeyboardButton(text="ℹ️ Що вміє бот"),
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# ---------- Стан FSM ----------
class SearchMode(StatesGroup):
    idle = State()
    search_instruction = State()
    search_answer = State()
    feedback = State()

# ---------- /start ----------
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(SearchMode.idle)
    await message.answer("Вітаю! Оберіть дію з меню нижче:", reply_markup=main_keyboard)

# ---------- Обробка повідомлень з reply-кнопок ----------
@dp.message(F.text == "🔍 Задати питання")
async def ask_question(message: Message, state: FSMContext):
    await state.set_state(SearchMode.search_answer)

    # Діагностика: пінг беку з HMAC-підписом
    r = api_get("/ping/", user_id=message.from_user.id)
    print("PING RESPONSE:", r.status_code, r.text)

    await message.answer("Напишіть ваше питання:")

@dp.message(F.text == "❗️Повідомити про помилку")
async def start_feedback(message: Message, state: FSMContext):
    await state.set_state(SearchMode.feedback)
    await message.answer("Будь ласка, опишіть проблему, яку ви виявили:")

@dp.message(F.text == "ℹ️ Що вміє бот")
async def show_help(message: Message, state: FSMContext):
    await message.answer(
        "🤖 Я бот-помічник.\n\n"
        "🟢 «🔍 Задати питання» — поставити питання\n"
        "🟢 «📄 Отримати інструкцію» — перегляд через меню\n"
        "🟢 «🔎 Знайти інструкцію» — пошук за ключовим словом\n"
        "🟢 «❗️ Повідомити про помилку» — надіслати відгук"
    )

@dp.message(F.text == "🔎 Знайти інструкцію")
async def start_instruction_search(message: Message, state: FSMContext):
    await state.set_state(SearchMode.search_instruction)
    await message.answer("Введіть ключове слово для пошуку інструкції:")

# ---------- Обробка стану 'feedback' ----------
@dp.message(SearchMode.feedback)
async def handle_feedback(message: Message, state: FSMContext):
    feedback_text = (message.text or "").strip()
    if not feedback_text:
        await message.reply("❌ Відгук не може бути порожнім. Спробуйте ще раз.")
        return

    try:
        r = api_post(
            "/feedback/",
            json={"user_id": str(message.from_user.id), "message": feedback_text},
            user_id=message.from_user.id,
        )
        if r.status_code == 201:
            await message.reply("✅ Ваш відгук успішно надіслано.")
        elif r.status_code in (401, 403):
            await message.reply("🚫 Доступ заборонено. Зверніться до адміністратора.")
        else:
            await message.reply(f"⚠️ Помилка від бекенду: {r.status_code}")
    except Exception as e:
        await message.reply(f"⚠️ Помилка: {str(e)}")

    await state.set_state(SearchMode.idle)

# ---------- Отримання інструкції (через меню категорій) ----------
@dp.message(F.text == "📄 Отримати інструкцію")
async def get_instruction_entry(message: Message, state: FSMContext):
    await state.set_state(SearchMode.idle)
    try:
        r = api_get("/categories/", user_id=message.from_user.id)
        if r.status_code in (401, 403):
            await message.answer("🚫 Доступ заборонено. Переконайтеся, що ваш Telegram ID додано в білий список.")
            return
        r.raise_for_status()
        categories = r.json()

        if not categories:
            await message.answer("Категорії ще не додано.")
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=c["name"], callback_data=f"cat_{c['id']}")] for c in categories]
        )
        await message.answer("Оберіть категорію:", reply_markup=kb)
    except Exception as e:
        await message.answer(f"Помилка при отриманні категорій: {str(e)}")

@dp.callback_query(F.data.startswith("cat_"))
async def category_selected(callback: CallbackQuery):
    category_id = callback.data.split("_", 1)[1]
    try:
        r = api_get(f"/subcategories/{category_id}/", user_id=callback.from_user.id)
        if r.status_code in (401, 403):
            await callback.message.answer("🚫 Доступ заборонено.")
            await callback.answer()
            return
        r.raise_for_status()
        subs = r.json()

        if not subs:
            await callback.message.answer("Немає підкатегорій для цієї категорії.")
            await callback.answer()
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=s["name"], callback_data=f"sub_{s['id']}")] for s in subs]
        )
        await callback.message.answer("Оберіть підкатегорію:", reply_markup=kb)
    except Exception as e:
        await callback.message.answer(f"Помилка при завантаженні підкатегорій: {str(e)}")
    await callback.answer()

@dp.callback_query(F.data.startswith("sub_"))
async def subcategory_selected(callback: CallbackQuery):
    sub_id = callback.data.split("_", 1)[1]
    try:
        r = api_get(f"/instructions/{sub_id}/", user_id=callback.from_user.id)
        if r.status_code in (401, 403):
            await callback.message.answer("🚫 Доступ заборонено.")
            await callback.answer()
            return
        r.raise_for_status()
        instrs = r.json()

        if not instrs:
            await callback.message.answer("Немає інструкцій у цій підкатегорії.")
            await callback.answer()
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=i["title"], callback_data=f"instr_{i['id']}")] for i in instrs]
        )
        await callback.message.answer("Оберіть інструкцію:", reply_markup=kb)
    except Exception as e:
        await callback.message.answer(f"Помилка при завантаженні інструкцій: {str(e)}")
    await callback.answer()

@dp.callback_query(F.data.startswith("instr_"))
async def instruction_selected(callback: CallbackQuery):
    instr_id = callback.data.split("_", 1)[1]
    try:
        r = api_get(f"/instruction/{instr_id}/", user_id=callback.from_user.id)
        if r.status_code in (401, 403):
            await callback.message.answer("🚫 Доступ заборонено.")
            await callback.answer()
            return

        if r.status_code == 200:
            data = r.json()
            text = f"<b>{data['title']}</b>\n\n{data['content']}"
            if data.get("image_url"):
                await callback.message.answer_photo(photo=data["image_url"], caption=text, parse_mode="HTML")
            else:
                await callback.message.answer(text, parse_mode="HTML")
        else:
            await callback.message.answer("Інструкція не знайдена.")
    except Exception as e:
        await callback.message.answer(f"Помилка при завантаженні інструкції: {str(e)}")
    await callback.answer()

# ---------- Пошук інструкції за ключовим словом ----------
@dp.message(SearchMode.search_instruction)
async def process_instruction_query(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        await message.answer("Введіть ключове слово для пошуку інструкції.")
        return

    try:
        r = api_get("/search_instructions/", params={"query": query}, user_id=message.from_user.id)
        if r.status_code in (401, 403):
            await message.answer("🚫 Доступ заборонено.")
            return
        if r.status_code == 200:
            instrs = r.json()
            if instrs:
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text=i["title"], callback_data=f"instr_{i['id']}")] for i in instrs]
                )
                await message.answer("Оберіть інструкцію:", reply_markup=kb)
            else:
                await message.answer("Інструкцій за вашим запитом не знайдено.")
        else:
            await message.answer(f"Помилка при пошуку інструкцій: {r.status_code}")
    except Exception as e:
        await message.answer(f"⚠️ Помилка: {str(e)}")

# ---------- Пошук відповіді ----------
@dp.message(SearchMode.search_answer)
async def handle_question(message: Message, state: FSMContext):
    question = (message.text or "").strip()
    if not question:
        await message.reply("Введіть питання, будь ласка.")
        return

    # Нове: валідація мінімальної кількості слів
    if _count_words_ua(question) < MIN_WORDS:
        await message.reply("Запит занадто короткий. Будь ласка, сформулюйте його детальніше (мінімум 3 слова).")
        return

    try:
        r = api_post("/search/", json={"question": question}, user_id=message.from_user.id)

        if r.status_code in (401, 403):
            await message.reply("🚫 Доступ заборонено. Зверніться до адміністратора.")
        elif r.status_code == 200:
            data = r.json()
            await message.reply(data.get("answer", "Відповідь не знайдена."))
        elif r.status_code == 404:
            data = r.json()
            await message.reply(data.get("answer", "Вибачте, відповідь не знайдена."))
        elif r.status_code == 429:
            try:
                data = r.json()
                await message.reply(f"⏳ {data.get('detail', 'Занадто багато запитів, спробуйте пізніше.')}")
            except Exception:
                await message.reply("⏳ Занадто багато запитів. Спробуйте пізніше.")
        else:
            await message.reply(f"⚠️ Помилка при пошуку відповіді: {r.status_code}")
    except Exception as e:
        await message.reply(f"⚠️ Помилка: {str(e)}")

    await state.set_state(SearchMode.idle)

# ---------- Точка входу ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
