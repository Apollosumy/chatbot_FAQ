import re
import unicodedata

# дозволені символи: букви, цифри, дефіс, апостроф, пробіли
_KEEP_RE = re.compile(r"[^\w\-\s'’ґєіїґҐЄІЇ]+", flags=re.U)

def normalize_text(text: str) -> str:
    """
    Нормалізація для індексації/пошуку:
    - unicode NFKC
    - привести до нижнього регістру
    - прибрати небажану пунктуацію (залишаємо apostrophe та дефіс)
    - стиснути множинні пробіли
    """
    if not text:
        return ""
    # нормалізація Юнікоду
    s = unicodedata.normalize("NFKC", text)
    # нижній регістр
    s = s.lower()
    # видалити небажані символи
    s = _KEEP_RE.sub(" ", s)
    # стиснути пробіли
    s = re.sub(r"\s+", " ", s).strip()
    return s
