import logging

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
    # no change to imports below
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)
os.environ.setdefault("PYTHONUNBUFFERED", "1")


# Читаємо .env із кореня репозиторію
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# --- Конфіг ---
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://localhost:8000/api")
parsed = urlparse(DJANGO_API_URL)
API_ORIGIN = f"{parsed.scheme}://{parsed.netloc}"
API_PREFIX = parsed.path.rstrip("/")
DJANGO_API_KEY = os.getenv("DJANGO_API_KEY", "")
DJANGO_HMAC_SECRET = os.getenv("DJANGO_HMAC_SECRET", "")
DEFAULT_TIMEOUT = 10

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher(storage=MemoryStorage())

# --- Мінімальна довжина запиту ---
MIN_WORDS = 3


def _count_words_ua(text: str) -> int:
    import re
    cleaned = re.sub(r"[^\w’'ґєіїа-яА-Яa-zA-Z0-9]+", " ", text, flags=re.U).strip()
    return len([w for w in cleaned.split() if w])


# ---------- HMAC-підпис ----------
def _make_signature(method: str, full_path: str, body_bytes: bytes) -> tuple[str, str, str]:
    ts = str(int(time.time()))
    content_hash = hashlib.sha256(body_bytes or b"").hexdigest()
    to_sign = "\n".join([ts, method.upper(), full_path, content_hash]).encode("utf-8")
    sig = hmac.new(DJANGO_HMAC_SECRET.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return ts, f"v1={sig}", content_hash


def _base_headers(user_id: int | None, want_json: bool) -> dict:
    h = {"X-API-Key": DJANGO_API_KEY, "Accept": "application/json"}
    if want_json:
        h["Content-Type"] = "application/json"
    if user_id is not None:
        h["X-Telegram-Id"] = str(user_id)
    return h


def _full_path_for_sig(path: str, params: dict | None) -> str:
    if not path.startswith("/"):
        path = "/" + path
    base = f"{API_PREFIX}{path}"
    if params:
        base = f"{base}?{urlencode(params, doseq=True)}"
    return base


def api_get(path: str, params: dict | None = None, *, user_id: int | None = None, timeout: int = DEFAULT_TIMEOUT):
    full_path = _full_path_for_sig(path, params)
    url = f"{API_ORIGIN}{full_path}"
    ts, signature, content_hash = _make_signature("GET", full_path, b"")
    headers = _base_headers(user_id, want_json=False) | {
        "X-Timestamp": ts,
        "X-Signature": signature,
        "X-Content-SHA256": content_hash,
    }
    return requests.get(url, headers=headers, params=None, timeout=timeout)


def api_post(path: str, json: dict | None = None, *, user_id: int | None = None, timeout: int = DEFAULT_TIMEOUT):
    raw_body = pyjson.dumps(json or {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    full_path = _full_path_for_sig(path, None)
    url = f"{API_ORIGIN}{full_path}"
    ts, signature, content_hash = _make_signature("POST", full_path, raw_body)
    headers = _base_headers(user_id, want_json=True) | {
        "X-Timestamp": ts,
        "X-Signature": signature,
        "X-Content-SHA256": content_hash,
    }
    return requests.post(url, data=raw_body, headers=headers, timeout=timeout)


# =====================
#   МЕНЮ ТА КНОПКИ
# =====================
HOME_BTN_QA = "📚 Питання та інструкції"
HOME_BTN_ABILITY = "ℹ️ Що вміє бот"
HOME_BTN_REPORT = "❗️Повідомити про помилку"
BACK_HOME = "🏠 На головну"

# Підменю QA
QA_BTN_ASK = "🔍 Задати питання"
QA_BTN_FIND = "🔎 Знайти інструкцію"
QA_BTN_GET = "📄 Отримати інструкцію"
ASK_GUIDE = "📘 Як формулювати запитання"
ASK_GUIDE_TEXT = """<b>Як правильно ставити запитання чат-боту</b>
... (без змін текст підказки) ...
"""

# Підменю Допродаж
UPSELL_HOME_BTN = "🛒 Допродаж"
UPSELL_BTN_CROSS = "Кросс"
UPSELL_BTN_CHANGE = "Change"   # ← перейменовано
UPSELL_BTN_ACCESS = "Аксесуари"
UPSELL_BACK = "⬅️ Назад"

# Головне меню
home_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=HOME_BTN_QA)],
        [KeyboardButton(text=UPSELL_HOME_BTN)],
        [KeyboardButton(text=HOME_BTN_ABILITY), KeyboardButton(text=HOME_BTN_REPORT)],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# Підменю "Питання та інструкції"
qa_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=QA_BTN_ASK)],
        [KeyboardButton(text=QA_BTN_FIND), KeyboardButton(text=QA_BTN_GET)],
        [KeyboardButton(text=ASK_GUIDE)],
        [KeyboardButton(text=BACK_HOME)],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# Підменю "Допродаж"
upsell_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=UPSELL_BTN_CROSS), KeyboardButton(text=UPSELL_BTN_CHANGE)],
        [KeyboardButton(text=UPSELL_BTN_ACCESS)],
        [KeyboardButton(text=BACK_HOME), KeyboardButton(text=UPSELL_BACK)],
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
    change_wait = State()  # ← новий стан


# ---------- Доступ (whitelist) ----------
async def _has_access(user_id: int) -> bool:
    """
    Єдина точка істини: /api/ping/ повертає 200 тільки якщо HMAC+API-key+whitelist ок.
    """
    try:
        r = api_get("/api/ping/" if not API_PREFIX else "/ping/", user_id=user_id)
        # NB: якщо твій API вже включає префікс /api у DJANGO_API_URL, лишай "/ping/"
        logging.info("[ACCESS] uid=%s status=%s body=%s", user_id, r.status_code, r.text[:200])
        return r.status_code == 200
    except Exception as e:
        logging.exception("[ACCESS] exception uid=%s", user_id)
        return False

async def _guard_access(message: Message) -> bool:
    if not await _has_access(message.from_user.id):
        await message.answer("🚫 Доступ заборонено. Зверніться до адміністратора.")
        return False
    return True


async def _guard_access_cb(callback: CallbackQuery) -> bool:
    if not await _has_access(callback.from_user.id):
        await callback.message.answer("🚫 Доступ заборонено. Зверніться до адміністратора.")
        await callback.answer()
        return False
    return True



# ---------- /start ----------
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(SearchMode.idle)
    if not await _guard_access(message):
        return
    user_name = message.from_user.first_name or message.from_user.full_name or "друже"
    await message.answer(f"👋 Вітаю, {user_name}! Обери дію з меню нижче:", reply_markup=home_keyboard)


# ---------- Навігація головного меню ----------
@dp.message(F.text == HOME_BTN_QA)
async def open_qa_menu(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await state.set_state(SearchMode.idle)
    await message.answer(
        "📚 Питання та інструкції:\n\n"
        "• 🔍 Задати питання\n"
        "• 🔎 Знайти інструкцію\n"
        "• 📄 Отримати інструкцію\n"
        f"• {ASK_GUIDE}",
        reply_markup=qa_keyboard,
    )


@dp.message(F.text == BACK_HOME)
async def back_to_home(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await state.set_state(SearchMode.idle)
    await message.answer("🏠 Повертаємось до головного меню:", reply_markup=home_keyboard)


# ---------- Підменю "Питання та інструкції" ----------
@dp.message(F.text == QA_BTN_ASK)
async def ask_question(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await state.set_state(SearchMode.search_answer)
    r = api_get("/ping/", user_id=message.from_user.id)
    print("PING RESPONSE:", r.status_code, r.text)
    await message.answer("✍️ Напишіть ваше питання:")


@dp.message(F.text == QA_BTN_FIND)
async def start_instruction_search(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await state.set_state(SearchMode.search_instruction)
    await message.answer("🔎 Введіть ключове слово для пошуку інструкції:")


@dp.message(F.text == QA_BTN_GET)
async def get_instruction_entry(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
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
        await message.answer("📂 Оберіть категорію:", reply_markup=kb)
    except Exception as e:
        await message.answer(f"⚠️ Помилка при отриманні категорій: {str(e)}")


@dp.message(F.text == ASK_GUIDE)
async def handle_how_to_ask(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await message.answer(ASK_GUIDE_TEXT, parse_mode="HTML")


# ---------- Що вміє бот ----------
@dp.message(F.text == HOME_BTN_ABILITY)
async def show_help(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await message.answer(
        "🤖 Вітаю! Я — ваш бот-помічник. Моє завдання — спростити пошук інформації та зробити вашу роботу комфортнішою.\n\n"
        "Ось що я можу:\n\n"
        "🔍 Задати питання — поставте будь-яке запитання, і я спробую знайти відповідь у базі знань.\n\n"
        "📄 Отримати інструкцію — перегляньте список доступних інструкцій у зручній структурі.\n\n"
        "🔎 Знайти інструкцію — введіть ключові слова й я знайду потрібну інструкцію.\n\n"
        "❗ Повідомити про помилку — якщо щось працює неправильно або відповідь була некоректною, надішліть відгук."
    )


# ---------- Повідомити про помилку ----------
@dp.message(F.text == HOME_BTN_REPORT)
async def start_feedback(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await state.set_state(SearchMode.feedback)
    await message.answer("🛠️ Опишіть проблему або помилку, яку ви виявили:")


@dp.message(SearchMode.feedback)
async def handle_feedback(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
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
            await message.reply("✅ Ваш відгук успішно надіслано. Дякуємо!")
        elif r.status_code in (401, 403):
            await message.reply("🚫 Доступ заборонено. Зверніться до адміністратора.")
        else:
            await message.reply(f"⚠️ Помилка від бекенду: {r.status_code}")
    except Exception as e:
        await message.reply(f"⚠️ Помилка: {str(e)}")
    await state.set_state(SearchMode.idle)


# ---------- Підкатегорії та інструкції ----------
@dp.callback_query(F.data.startswith("cat_"))
async def category_selected(callback: CallbackQuery):
    if not await _guard_access_cb(callback):
        return
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
        await callback.message.answer("📁 Оберіть підкатегорію:", reply_markup=kb)
    except Exception as e:
        await callback.message.answer(f"⚠️ Помилка при завантаженні підкатегорій: {str(e)}")
    await callback.answer()


@dp.callback_query(F.data.startswith("sub_"))
async def subcategory_selected(callback: CallbackQuery):
    if not await _guard_access_cb(callback):
        return
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
        await callback.message.answer("📜 Оберіть інструкцію:", reply_markup=kb)
    except Exception as e:
        await callback.message.answer(f"⚠️ Помилка при завантаженні інструкцій: {str(e)}")
    await callback.answer()


@dp.callback_query(F.data.startswith("instr_"))
async def instruction_selected(callback: CallbackQuery):
    if not await _guard_access_cb(callback):
        return
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
        await callback.message.answer(f"⚠️ Помилка при завантаженні інструкції: {str(e)}")
    await callback.answer()


# ---------- Пошук ----------
@dp.message(SearchMode.search_instruction)
async def process_instruction_query(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
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
                await message.answer("🔽 Оберіть інструкцію:", reply_markup=kb)
            else:
                await message.answer("Інструкцій за вашим запитом не знайдено.")
        else:
            await message.answer(f"⚠️ Помилка при пошуку інструкцій: {r.status_code}")
    except Exception as e:
        await message.answer(f"⚠️ Помилка: {str(e)}")


@dp.message(SearchMode.search_answer)
async def handle_question(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    question = (message.text or "").strip()
    if not question:
        await message.reply("Введіть питання, будь ласка.")
        return
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


# ---------- Допродаж: вхід та розділи ----------
@dp.message(F.text == UPSELL_HOME_BTN)
async def open_upsell_menu(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await state.set_state(SearchMode.idle)
    await message.answer(
        "🛒 Допродаж:\n"
        "• Кросс — один текст із порадами\n"
        "• Change — введіть артикул/код і отримаєте інструкцію\n"
        "• Аксесуари — оберіть категорію та перегляньте текст категорії",
        reply_markup=upsell_keyboard,
    )


@dp.message(F.text == UPSELL_BACK)
async def upsell_back(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await state.set_state(SearchMode.idle)
    await message.answer("🔙 Повертаємось до меню «Допродаж»", reply_markup=upsell_keyboard)


# ----- Кросс → просто текст
@dp.message(F.text == UPSELL_BTN_CROSS)
async def upsell_cross_text(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    try:
        r = api_get("/upsell/cross/text/", user_id=message.from_user.id)
        if r.status_code in (401, 403):
            await message.answer("🚫 Доступ заборонено.")
            return
        r.raise_for_status()
        data = r.json()
        text = (data.get("text") or "").strip()
        if not text:
            await message.answer("Наразі текст для 'Кросс' відсутній.")
            return
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"⚠️ Помилка: {str(e)}")


# ----- Change → очікування артикула/коду → пошук → текст
@dp.message(F.text == UPSELL_BTN_CHANGE)
async def upsell_change_prompt(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    await state.set_state(SearchMode.change_wait)
    await message.answer("🔁 Введіть артикул або код товару:")


@dp.message(SearchMode.change_wait)
async def upsell_change_search(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    q = (message.text or "").strip()
    if not q:
        await message.answer("Введіть, будь ласка, артикул або код.")
        return
    try:
        r = api_get("/upsell/change/search/", params={"q": q}, user_id=message.from_user.id)
        if r.status_code in (401, 403):
            await message.answer("🚫 Доступ заборонено.")
            await state.set_state(SearchMode.idle)
            return
        if r.status_code == 404:
            await message.answer("Нічого не знайдено за цим артикулом/кодом.")
            await state.set_state(SearchMode.idle)
            return
        r.raise_for_status()
        data = r.json()
        title = data.get("title") or "Позиція"
        text = (data.get("instruction_text") or "").strip() or "Опис відсутній."
        await message.answer(f"<b>{title}</b>\n\n{text}", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"⚠️ Помилка: {str(e)}")
    await state.set_state(SearchMode.idle)


# ----- Аксесуари → категорії → текст категорії
@dp.message(F.text == UPSELL_BTN_ACCESS)
async def upsell_accessory_categories(message: Message, state: FSMContext):
    if not await _guard_access(message):
        return
    try:
        r = api_get("/upsell/accessories/categories/", user_id=message.from_user.id)
        if r.status_code in (401, 403):
            await message.answer("🚫 Доступ заборонено.")
            return
        r.raise_for_status()
        cats = r.json()
        if not cats:
            await message.answer("Категорії аксесуарів відсутні.")
            return
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=c["name"], callback_data=f"ac_cat_{c['id']}")] for c in cats]
        )
        await message.answer("Оберіть категорію аксесуарів:", reply_markup=kb)
    except Exception as e:
        await message.answer(f"⚠️ Помилка: {str(e)}")


@dp.callback_query(F.data.startswith("ac_cat_"))
async def upsell_accessories_category_text(callback: CallbackQuery):
    if not await _guard_access_cb(callback):
        return
    cat_id = int(callback.data.split("_")[-1])
    try:
        r = api_get(f"/upsell/accessories/category/{cat_id}/text/", user_id=callback.from_user.id)
        if r.status_code in (401, 403):
            await callback.message.answer("🚫 Доступ заборонено.")
            await callback.answer(); return
        if r.status_code == 404:
            await callback.message.answer("Категорію не знайдено.")
            await callback.answer(); return
        r.raise_for_status()
        data = r.json()
        name = data.get("name") or "Категорія"
        text = (data.get("instruction_text") or "").strip() or "Опис відсутній."
        await callback.message.answer(f"<b>{name}</b>\n\n{text}", parse_mode="HTML")
    except Exception as e:
        await callback.message.answer(f"⚠️ Помилка: {str(e)}")
    await callback.answer()


# ---------- Точка входу ----------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
