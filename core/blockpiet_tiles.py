# core/pixel_tiles.py
"""
Библиотека плиток 2×1 для PixelCode.

Каждая плитка = (category, value). 20×20 = 400 комбинаций.
"""

KEYWORDS = [
    "print", "for", "in", "range", "if", "else", "elif", "while",
    "def", "return", "True", "False", "None", "and", "or", "not",
    "break", "continue", "import", "from",
]

NAMES = [
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j",
    "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
]

OPERATORS = [
    "+", "-", "*", "/", "//", "%", "**",
    "=", "==", "!=", "<", ">", "<=", ">=",
    "+=", "-=", "*=", "/=", "->", "=>",
]

BRACKETS = [
    "(", ")", "[", "]", "{", "}", ":", ";",
    "@", "$", "&", "|", "^", "~", "\\", "/", "<", ">", "`", "?",
]

SEPARATORS = [
    ",", ".", "'", '"', " ",
    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
]

STRUCT = [
    "NEWLINE", "INDENT", "DEDENT", "END",
    "STR_START", "STR_END",
    "", "", "", "", "", "", "", "", "", "", "", "", "", "",
]

RESERVED = [""] * 20


def tile_to_token(cat: int, val: int, string_mode: bool = False):
    """Плитка → (kind, value)."""
    if 0 <= cat <= 12:
        n = cat * 20 + val
        if string_mode:
            return ("CHAR", chr(n & 0xFF))
        return ("NUMBER", str(n))
    if cat == 13 and val < len(KEYWORDS):
        return ("ID", KEYWORDS[val])
    if cat == 14 and val < len(NAMES):
        return ("ID", NAMES[val])
    if cat == 15 and val < len(OPERATORS):
        return ("OP", OPERATORS[val])
    if cat == 16 and val < len(BRACKETS) and BRACKETS[val]:
        return ("OP", BRACKETS[val])
    if cat == 17 and val < len(SEPARATORS) and SEPARATORS[val]:
        return ("OP", SEPARATORS[val])
    if cat == 18 and val < len(STRUCT):
        return ("STRUCT", STRUCT[val])
    return ("?", "")


def token_to_tile(ttype: str, tstr: str):
    """Python-токен → (cat, val). None если не подходит."""
    if ttype == "KEYWORD":
        if tstr in KEYWORDS:
            return (13, KEYWORDS.index(tstr))
    elif ttype == "NAME":
        if tstr in NAMES:
            return (14, NAMES.index(tstr))
    elif ttype == "NUMBER":
        try:
            n = int(tstr) % 260
        except ValueError:
            n = 0
        return (n // 20, n % 20)
    elif ttype == "OP":
        if tstr in BRACKETS:
            return (16, BRACKETS.index(tstr))
        if tstr in OPERATORS:
            return (15, OPERATORS.index(tstr))
        if tstr in SEPARATORS and tstr:
            return (17, SEPARATORS.index(tstr))
    elif ttype == "NEWLINE":
        return (18, 0)
    elif ttype == "INDENT":
        return (18, 1)
    elif ttype == "DEDENT":
        return (18, 2)
    return None