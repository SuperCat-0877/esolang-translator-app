# core/template_types.py
"""Типы шаблонов: E (простой), M (средний), H (сложный),
W (безумный), T (тест)."""

import re

TEMPLATE_TYPES = {
    "E": "Простой",
    "M": "Средний",
    "H": "Сложный",
    "W": "Безумный",
    "T": "Тест",
}
TYPE_BY_LABEL = {v: k for k, v in TEMPLATE_TYPES.items()}
ALL_LABELS = ["Все"] + list(TEMPLATE_TYPES.values())

_PREFIX_RE = re.compile(r"^\[([EMHWT])(\d+)\]\s*(.*)$")
_NUM_RE = re.compile(r"^\[(\d+)\]\s*(.*)$")
_TEST_RE = re.compile(r"^\[Test\]\s*(.*)$", re.IGNORECASE)


def classify(name):
    """[E1] Foo → 'E'. Уже классифицированные — как есть."""
    if not name:
        return None
    m = _PREFIX_RE.match(name)
    return m.group(1) if m else None


def reclassify(templates):
    """Идемпотентно переименовывает [N] и [Test] в [E1..], [M..], [H..], [T..]."""
    if not templates:
        return {}

    new = {}
    counters = {"E": 0, "M": 0, "H": 0, "T": 0}

    # Первый проход: сохранить уже классифицированные
    # (чтобы не менять индексы, если кто-то вручную добавил)
    pending = []
    for name, code in templates.items():
        if classify(name):
            new[name] = code
        else:
            pending.append((name, code))

    for name, code in pending:
        m = _NUM_RE.match(name)
        if m:
            n = int(m.group(1))
            rest = m.group(2)
            if n <= 5:
                counters["E"] += 1
                new[f"[E{counters['E']}] {rest}"] = code
            elif n <= 10:
                counters["M"] += 1
                new[f"[M{counters['M']}] {rest}"] = code
            else:
                counters["H"] += 1
                new[f"[H{counters['H']}] {rest}"] = code
            continue
        t = _TEST_RE.match(name)
        if t:
            counters["T"] += 1
            new[f"[T{counters['T']}] {t.group(1)}"] = code
            continue
        # Не подошло ни под один шаблон — оставляем
        new[name] = code

    return new


def stats(templates):
    """Сколько каких типов."""
    counts = {k: 0 for k in TEMPLATE_TYPES}
    counts["?"] = 0
    for name in templates:
        code = classify(name)
        if code in counts:
            counts[code] += 1
        else:
            counts["?"] += 1
    return counts