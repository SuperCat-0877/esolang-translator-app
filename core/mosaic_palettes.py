# core/mosaic_palettes.py
"""Реестр палитр плиток по языкам."""

from __future__ import annotations

from core.blockpiet_lib import default_tiles as blockpiet_tiles


# ══════════════════════════════════════════════════════════════════════
#  BrainPiet
# ══════════════════════════════════════════════════════════════════════
BRAINPIET_CHARS = [">", "<", "+", "-", ".", ",", "[", "]", "#", " "]


def _bf_char(ch: str) -> list[tuple[int, int]]:
    right = (0, BRAINPIET_CHARS.index(">"))
    plus  = (0, BRAINPIET_CHARS.index("+"))
    dot   = (0, BRAINPIET_CHARS.index("."))
    return [right] + [plus] * (ord(ch) & 0xFF) + [dot]


def _bf_word(s: str) -> list[tuple[int, int]]:
    halt = (0, BRAINPIET_CHARS.index("#"))
    out: list[tuple[int, int]] = []
    for c in s:
        out += _bf_char(c)
    out.append(halt)
    return out


_BRAINPIET_TEMPLATES: dict[str, list[tuple[int, int]]] = {
    "A":     _bf_word("A"),
    "42":    _bf_word("42"),
    "Hi":    _bf_word("Hi"),
    "Hello": _bf_word("Hello"),
    "halt":  [(0, BRAINPIET_CHARS.index("#"))],
}


def _brainpiet_palette() -> dict:
    items = []
    for i, c in enumerate(BRAINPIET_CHARS):
        name = "SPACE" if c == " " else f"BF {c}"
        items.append((name, (0, i), c))
    return {
        "title": "BrainPiet",
        "tile_size": (1, 1),
        "cell_px": 32,
        "categories": [("BF-команды", items)],
        "templates": _BRAINPIET_TEMPLATES,
    }


# ══════════════════════════════════════════════════════════════════════
#  BlockPiet
# ══════════════════════════════════════════════════════════════════════
def _b(ch: str) -> tuple[int, int]:
    n = ord(ch) & 0xFF
    return (n // 20, n % 20)


def _nl() -> tuple[int, int]:
    return (18, 0)


def _ind() -> tuple[int, int]:
    return (18, 1)


def _kw(s: str) -> tuple[int, int]:
    from core.blockpiet_tiles import KEYWORDS
    return (13, KEYWORDS.index(s))


def _nm(s: str) -> tuple[int, int]:
    from core.blockpiet_tiles import NAMES
    return (14, NAMES.index(s))


def _op(s: str) -> tuple[int, int]:
    from core.blockpiet_tiles import OPERATORS, BRACKETS
    if s in OPERATORS:
        return (15, OPERATORS.index(s))
    if s in BRACKETS:
        return (16, BRACKETS.index(s))
    raise ValueError(s)


def _num(n: int) -> tuple[int, int]:
    """Число → плитка NUMBER (n mod 260)."""
    n = n % 260
    return (n // 20, n % 20)


_BLOCKPIET_TEMPLATES: dict[str, list[tuple[int, int]]] = {
    # ─── вывод ────────────────────────────────────────────────────────
    "print(0)":       [_kw("print"), _op("("), _num(0), _op(")"), _nl()],
    "print(1)":       [_kw("print"), _op("("), _num(1), _op(")"), _nl()],
    "print(42)":      [_kw("print"), _op("("), _num(42), _op(")"), _nl()],
    "print(100)":     [_kw("print"), _op("("), _num(100), _op(")"), _nl()],
    "print(a)":       [_kw("print"), _op("("), _nm("a"), _op(")"), _nl()],
    "print(b)":       [_kw("print"), _op("("), _nm("b"), _op(")"), _nl()],
    "print(i)":       [_kw("print"), _op("("), _nm("i"), _op(")"), _nl()],
    "print('A')":     [_kw("print"), _op("("),
                       (18, 4), _b("A"), (18, 5), _op(")"), _nl()],
    "print('B')":     [_kw("print"), _op("("),
                       (18, 4), _b("B"), (18, 5), _op(")"), _nl()],
    "print('X')":     [_kw("print"), _op("("),
                       (18, 4), _b("X"), (18, 5), _op(")"), _nl()],
    "print('Hi')":    [_kw("print"), _op("("),
                       (18, 4), _b("H"), _b("i"), (18, 5),
                       _op(")"), _nl()],
    "print('OK')":    [_kw("print"), _op("("),
                       (18, 4), _b("O"), _b("K"), (18, 5),
                       _op(")"), _nl()],
    "print('Hello')": [_kw("print"), _op("("),
                       (18, 4), _b("H"), _b("e"), _b("l"), _b("l"),
                       _b("o"), (18, 5), _op(")"), _nl()],
    "print(a + 1)":   [_kw("print"), _op("("), _nm("a"), _op("+"),
                       _num(1), _op(")"), _nl()],
    "print(a * 2)":   [_kw("print"), _op("("), _nm("a"), _op("*"),
                       _num(2), _op(")"), _nl()],

    # ─── присваивания a ──────────────────────────────────────────────
    "a = 0":          [_nm("a"), _op("="), _num(0), _nl()],
    "a = 1":          [_nm("a"), _op("="), _num(1), _nl()],
    "a = 3":          [_nm("a"), _op("="), _num(3), _nl()],
    "a = 5":          [_nm("a"), _op("="), _num(5), _nl()],
    "a = 10":         [_nm("a"), _op("="), _num(10), _nl()],
    "a = 100":        [_nm("a"), _op("="), _num(100), _nl()],

    # ─── присваивания b ──────────────────────────────────────────────
    "b = 0":          [_nm("b"), _op("="), _num(0), _nl()],
    "b = 1":          [_nm("b"), _op("="), _num(1), _nl()],
    "b = 3":          [_nm("b"), _op("="), _num(3), _nl()],
    "b = 5":          [_nm("b"), _op("="), _num(5), _nl()],
    "b = 10":         [_nm("b"), _op("="), _num(10), _nl()],

    # ─── аугментация ─────────────────────────────────────────────────
    "a += 1":         [_nm("a"), _op("+="), _num(1), _nl()],
    "a += 2":         [_nm("a"), _op("+="), _num(2), _nl()],
    "a -= 1":         [_nm("a"), _op("-="), _num(1), _nl()],
    "b += 1":         [_nm("b"), _op("+="), _num(1), _nl()],
    "b -= 1":         [_nm("b"), _op("-="), _num(1), _nl()],

    # ─── копирование ─────────────────────────────────────────────────
    "a = b":          [_nm("a"), _op("="), _nm("b"), _nl()],
    "b = a":          [_nm("b"), _op("="), _nm("a"), _nl()],

    # ─── условия ─────────────────────────────────────────────────────
    "if a > 0:":      [_kw("if"), _nm("a"), _op(">"), _num(0),
                       _op(":"), _nl(), _ind()],
    "if a < 5:":      [_kw("if"), _nm("a"), _op("<"), _num(5),
                       _op(":"), _nl(), _ind()],
    "if a > b:":      [_kw("if"), _nm("a"), _op(">"), _nm("b"),
                       _op(":"), _nl(), _ind()],
    "if a < b:":      [_kw("if"), _nm("a"), _op("<"), _nm("b"),
                       _op(":"), _nl(), _ind()],
    "else:":          [_kw("else"), _op(":"), _nl(), _ind()],

    # ─── while ───────────────────────────────────────────────────────
    "while a > 0:":   [_kw("while"), _nm("a"), _op(">"), _num(0),
                       _op(":"), _nl(), _ind()],
    "while a < 5:":   [_kw("while"), _nm("a"), _op("<"), _num(5),
                       _op(":"), _nl(), _ind()],
    "while a < 10:":  [_kw("while"), _nm("a"), _op("<"), _num(10),
                       _op(":"), _nl(), _ind()],
    "while a > b:":   [_kw("while"), _nm("a"), _op(">"), _nm("b"),
                       _op(":"), _nl(), _ind()],
    "while a < b:":   [_kw("while"), _nm("a"), _op("<"), _nm("b"),
                       _op(":"), _nl(), _ind()],

    # ─── for ─────────────────────────────────────────────────────────
    "for i in range(3):":  [
        _kw("for"), _nm("i"), _kw("in"), _kw("range"),
        _op("("), _num(3), _op(")"), _op(":"), _nl(), _ind(),
    ],
    "for i in range(5):":  [
        _kw("for"), _nm("i"), _kw("in"), _kw("range"),
        _op("("), _num(5), _op(")"), _op(":"), _nl(), _ind(),
    ],
    "for i in range(10):": [
        _kw("for"), _nm("i"), _kw("in"), _kw("range"),
        _op("("), _num(10), _op(")"), _op(":"), _nl(), _ind(),
    ],

    # ─── блок ────────────────────────────────────────────────────────
    "end":            [(18, 2), _nl()],
}

_CAT_NAMES = {
    0:  "CTRL 0-19",
    1:  "пунктуация 20-39",
    2:  "цифры 40-59",
    3:  "буквы A-O",
    4:  "буквы P-Z",
    5:  "буквы `a-w",
    6:  "буквы x-z {|}~",
    7:  "расшир. 140-159",
    8:  "расшир. 160-179",
    9:  "расшир. 180-199",
    10: "расшир. 200-219",
    11: "расшир. 220-239",
    12: "расшир. 240-259",
    13: "КЛЮЧЕВЫЕ СЛОВА",
    14: "ИМЕНА",
    15: "ОПЕРАТОРЫ",
    16: "СКОБКИ",
    17: "РАЗДЕЛИТЕЛИ",
    18: "СТРУКТУРНЫЕ",
    19: "СЛУЖЕБНЫЕ",
}


def _blockpiet_palette() -> dict:
    lib = blockpiet_tiles()
    by_cat: dict[int, list] = {i: [] for i in range(20)}
    for name, (cat, val) in lib.items():
        by_cat[cat].append((name, (cat, val)))

    cats = []
    for c in range(20):
        items = sorted(by_cat[c], key=lambda x: x[1][1])
        cats.append((_CAT_NAMES.get(c, f"CAT {c}"), items))

    return {
        "title": "BlockPiet",
        "tile_size": (2, 2),
        "cell_px": 16,
        "categories": cats,
        "templates": _BLOCKPIET_TEMPLATES,
    }

# ══════════════════════════════════════════════════════════════════════
#  Piet++ : цвет = команда. Шаблоны строятся через дельты Piet.
# ══════════════════════════════════════════════════════════════════════
_PIET_ITEMS = [
    ("nop",       (0, 0)), ("push",     (0, 1)), ("pop",      (0, 2)),
    ("add",       (1, 0)), ("sub",      (1, 1)), ("mul",      (1, 2)),
    ("div",       (2, 0)), ("mod",      (2, 1)), ("not",      (2, 2)),
    ("gt",        (3, 0)), ("dp",       (3, 1)), ("cc",       (3, 2)),
    ("dup",       (4, 0)), ("roll",     (4, 1)), ("write",    (4, 2)),
    ("read",      (5, 0)), ("out_num",  (5, 1)), ("out_char", (5, 2)),
    ("white",     (18, 0)),
    ("black",     (19, 0)),
]


_PIET_DELTAS = {
    "nop": (0, 0), "push": (0, 1), "pop": (0, 2),
    "add": (1, 0), "sub": (1, 1), "mul": (1, 2),
    "div": (2, 0), "mod": (2, 1), "not": (2, 2),
    "gt":  (3, 0), "dp":  (3, 1), "cc":  (3, 2),
    "dup": (4, 0), "roll": (4, 1), "write": (4, 2),
    "read": (5, 0), "out_num": (5, 1), "out_char": (5, 2),
}


def _piet_chain(commands: list) -> list:
    """[('push', 5), ('out_num', None)] → [(cat, val), ...] под Piet.

    Строит цепочку так, чтобы каждая команда стала отдельным блоком
    нужного размера. Начинает с prev=(0, 0).
    """
    result = []
    prev_h, prev_l = 0, 0
    for cmd, arg in commands:
        dh, dl = _PIET_DELTAS[cmd]
        h = (prev_h + dh) % 6
        l = (prev_l + dl) % 3
        size = arg if (cmd == "push" and arg) else 1
        result += [(h, l)] * size
        prev_h, prev_l = h, l
    return result


_PIET_TEMPLATES = {
    "5":              _piet_chain([("push", 5), ("out_num", None)]),
    "5 + 3 = 8":      _piet_chain([("push", 5), ("push", 3),
                                    ("add", None), ("out_num", None)]),
    "10 - 4 = 6":     _piet_chain([("push", 10), ("push", 4),
                                    ("sub", None), ("out_num", None)]),
    "6 * 7 = 42":     _piet_chain([("push", 6), ("push", 7),
                                    ("mul", None), ("out_num", None)]),
    "20 / 4 = 5":     _piet_chain([("push", 20), ("push", 4),
                                    ("div", None), ("out_num", None)]),
    "42":             _piet_chain([("push", 42), ("out_num", None)]),
    "print 'A'":      _piet_chain([("push", 65), ("out_char", None)]),
    "print 'Hi'":     _piet_chain([("push", 72), ("out_char", None),
                                    ("push", 105), ("out_char", None)]),
    "no-op":          _piet_chain([("nop", None)]),
}


def _piet_palette() -> dict:
    items = [(name, (cat, val), name) for name, (cat, val) in _PIET_ITEMS]
    return {
        "title": "Piet++",
        "tile_size": (1, 1),
        "cell_px": 32,
        "categories": [("Piet-цвета", items)],
        "templates": _PIET_TEMPLATES,
    }


MOSAIC_PALETTES: dict[str, dict] = {
    "brainpiet": _brainpiet_palette(),
    "blockpiet": _blockpiet_palette(),
    "piet++":    _piet_palette(),
}





# ══════════════════════════════════════════════════════════════════════
#  Реестр
# ══════════════════════════════════════════════════════════════════════


def list_mosaic_langs() -> list[str]:
    return list(MOSAIC_PALETTES.keys())


def get_palette(lang: str) -> dict | None:
    return MOSAIC_PALETTES.get(lang)