# audittrail/audit.py
from django.forms.models import model_to_dict

SENSITIVE_FIELDS = {"password",}

def _normalize(value):
    """
    Приводимо значення до серіалізованого вигляду, який можна безпечно порівнювати.
    - numpy/pgvector -> list
    - memoryview -> bytes
    - set/tuple -> відсортований список
    - list -> рекурсивно нормалізуємо елементи
    """
    if value is None:
        return None

    # numpy.ndarray або pgvector.Vector часто мають .tolist()
    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:
            pass

    # memoryview -> bytes
    try:
        import builtins
        if isinstance(value, memoryview):
            value = value.tobytes()
    except Exception:
        pass

    if isinstance(value, (set, tuple)):
        return sorted([_normalize(v) for v in value])
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value

def model_diff(old_obj, new_obj, include_fields=None, exclude_fields=None):
    """
    Повертає diff у форматі {field: {"old": x, "new": y}}
    """
    exclude_fields = set(exclude_fields or set())
    exclude_fields |= SENSITIVE_FIELDS

    old = model_to_dict(old_obj) if old_obj else {}
    new = model_to_dict(new_obj) if new_obj else {}

    keys = set(include_fields) if include_fields else (set(old.keys()) | set(new.keys()))
    diff = {}
    for k in keys:
        if k in exclude_fields:
            continue
        ov = _normalize(old.get(k))
        nv = _normalize(new.get(k))
        try:
            changed = (ov != nv)
        except Exception:
            # На випадок "ambiguous truth value" тощо
            changed = (str(ov) != str(nv))
        if changed:
            diff[k] = {"old": ov, "new": nv}
    return diff
