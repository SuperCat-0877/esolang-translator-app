# langs/rockstar.py
"""Rockstar — эзотерический язык, код выглядит как текст песни."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS


# Поэтические литералы Rockstar → числа
_ROCKSTAR_LITERALS = [
    # (regex, replacement, описание)
    (r"\bnothing\b",  "0",  "nothing = 0"),
    (r"\bmy world\b", "2",  "my world = 2"),
    (r"\bmy heart\b", "0",  "my heart = 0"),
    (r"\ba dream\b",  "1",  "a dream = 1"),
    (r"\bmy dream\b", "1",  "my dream = 1"),
    (r"\ba lie\b",    "-1", "a lie = -1"),
    (r"\bmy lie\b",   "-1", "my lie = -1"),
    (r"\bice\b",      "1",  "ice = 1"),
    (r"\bfire\b",     "2",  "fire = 2"),
]


def _rockstar_literals(e):
    """Заменяет поэтические литералы на числа. Многословные — первыми."""
    for pat, val, _ in sorted(_ROCKSTAR_LITERALS,
                              key=lambda x: -len(x[0])):
        e = re.sub(pat, val, e, flags=re.IGNORECASE)
    return e


def _rockstar_expr_to_py(expr):
    e = expr.strip().rstrip(".")
    e = _rockstar_literals(e)
    e = re.sub(r"\btrue\b", "True", e, flags=re.IGNORECASE)
    e = re.sub(r"\bfalse\b", "False", e, flags=re.IGNORECASE)
    e = re.sub(r"\bnull\b", "None", e, flags=re.IGNORECASE)
    e = re.sub(r"\bmysterious\b", "None", e, flags=re.IGNORECASE)
    e = re.sub(r"\bempty\b", '""', e, flags=re.IGNORECASE)
    e = re.sub(r"\bsilence\b", '""', e, flags=re.IGNORECASE)

    e = re.sub(r"\bplus\b", "+", e, flags=re.IGNORECASE)
    e = re.sub(r"\bminus\b", "-", e, flags=re.IGNORECASE)
    e = re.sub(r"\btimes\b", "*", e, flags=re.IGNORECASE)
    e = re.sub(r"\bover\b", "/", e, flags=re.IGNORECASE)

    e = re.sub(r"\bis\s+higher\s+than\b", ">", e, flags=re.IGNORECASE)
    e = re.sub(r"\bis\s+lower\s+than\b", "<", e, flags=re.IGNORECASE)
    e = re.sub(r"\bis\s+as\s+high\s+as\b", ">=", e, flags=re.IGNORECASE)
    e = re.sub(r"\bis\s+as\s+low\s+as\b", "<=", e, flags=re.IGNORECASE)
    e = re.sub(r"\bis\s+not\b", "!=", e, flags=re.IGNORECASE)
    e = re.sub(r"\bis\b", "==", e, flags=re.IGNORECASE)

    e = re.sub(r"\band\b", " and ", e, flags=re.IGNORECASE)
    e = re.sub(r"\bor\b", " or ", e, flags=re.IGNORECASE)
    e = re.sub(r"\bnot\b", " not ", e, flags=re.IGNORECASE)

    e = re.sub(r"\s+", " ", e).strip()
    return e


def _rockstar_to_python(src):
    lines = src.splitlines()
    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("(") or line.startswith("#"):
            continue

        m = re.match(r"(?:Say|Shout|Whisper|Scream)\s+(.+)$",
                     line, re.IGNORECASE)
        if m:
            arg = m.group(1).strip().rstrip(".")
            emit(f"print({arg if arg.startswith(chr(34)) else _rockstar_expr_to_py(arg)})")
            continue

        m = re.match(r"Listen\s+to\s+(?:your\s+|my\s+|the\s+)?(.+)$",
                     line, re.IGNORECASE)
        if m:
            var = _rockstar_expr_to_py(m.group(1))
            emit(f"{var} = input()")
            continue

        m = re.match(r"Put\s+(.+?)\s+into\s+(.+)$", line, re.IGNORECASE)
        if m:
            expr = _rockstar_expr_to_py(m.group(1))
            var = _rockstar_expr_to_py(m.group(2))
            emit(f"{var} = {expr}")
            continue

        m = re.match(r"Let\s+(.+?)\s+be\s+(.+)$", line, re.IGNORECASE)
        if m:
            var = _rockstar_expr_to_py(m.group(1))
            rhs = m.group(2).strip()
            # Массив: Let X be 1, 2, 3
            if "," in rhs and not any(
                    op in rhs for op in (" + ", " - ", " * ", " / ")):
                items = [p.strip() for p in rhs.split(",")]
                conv = ", ".join(_rockstar_expr_to_py(p) for p in items)
                emit(f"{var} = [{conv}]")
            else:
                emit(f"{var} = {_rockstar_expr_to_py(rhs)}")
            continue

        m = re.match(r"Build\s+(.+?)\s+up$", line, re.IGNORECASE)
        if m:
            var = _rockstar_expr_to_py(m.group(1))
            emit(f"{var} += 1")
            continue
        m = re.match(r"Knock\s+(.+?)\s+down$", line, re.IGNORECASE)
        if m:
            var = _rockstar_expr_to_py(m.group(1))
            emit(f"{var} -= 1")
            continue

        m = re.match(r"If\s+(.+)$", line, re.IGNORECASE)
        if m:
            cond = m.group(1).strip().rstrip(".")
            cond = re.sub(r"\s+then\s*$", "", cond, flags=re.IGNORECASE)
            emit(f"if {_rockstar_expr_to_py(cond)}:")
            ind += 1
            continue

        if re.match(r"^Else$", line, re.IGNORECASE):
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        m = re.match(r"While\s+(.+)$", line, re.IGNORECASE)
        if m:
            emit(f"while {_rockstar_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"Until\s+(.+)$", line, re.IGNORECASE)
        if m:
            emit(f"while not ({_rockstar_expr_to_py(m.group(1))}):")
            ind += 1
            continue

        emit(f"# Rockstar: не поддержано: {line}")

    return "\n".join(out) + "\n"


def _rockstar_run(src):
    py = _rockstar_to_python(src)
    out = StringIO()
    old = sys.stdout
    sys.stdout = out
    try:
        exec(compile(py, "<rockstar>", "exec"), {})
    except Exception:
        pass
    finally:
        sys.stdout = old
    return out.getvalue()


def _rockstar_print(text):
    if not text:
        return 'Say ""\n'
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    out = []
    for line in lines:
        out.append(f'Say {json.dumps(line, ensure_ascii=False)}')
    return "\n".join(out) + "\n"


def _rockstar_gen_numbers():
    return "\n".join([f'Say "{i}"' for i in range(1, 11)])


def _rockstar_gen_squares():
    return "\n".join([f'Say "{i * i}"' for i in range(1, 11)])


def _rockstar_gen_cubes():
    return "\n".join([f'Say "{i ** 3}"' for i in range(1, 11)])


def _rockstar_gen_table7():
    return "\n".join([f'Say "{i * 7}"' for i in range(1, 11)])


def _rockstar_gen_fib():
    return "\n".join([f'Say "{n}"' for n in [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]])


def _rockstar_gen_arith():
    return (
        "Put 5 into X\n"
        "Put 7 into Y\n"
        "Put X plus Y into Z\n"
        "Say Z"
    )


def _rockstar_gen_loop():
    return (
        "Put 0 into X\n"
        "Build X up\n"
        "Build X up\n"
        "Build X up\n"
        "Say X"
    )


def _rockstar_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f'Say "=== {k} x {k} ==="')
        for i in range(1, 6):
            parts.append(f'Say "{i * k}"')
    return "\n".join(parts)


def _rockstar_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f'Say "=== Таблица {k} ==="')
        for i in range(1, 11):
            parts.append(f'Say "{i * k}"')
    return "\n".join(parts)


class RockstarLang(Language):
    name = "rockstar"
    title = "Rockstar"
    category = "Э"
    ext = ".rock"
    keywords = ["Say", "Shout", "Whisper", "Scream",
                "Put", "Let", "If", "Else",
                "While", "Until", "Build", "Knock", "Listen"]
    comment_regex = r"\([^\n]*\)"

    templates = {

        '[1] Hello, World': 'Say "Hello, World!"\n',

        '[2] Буква A': 'Say "A"\n',

        '[3] Цифры 0-9': 'Say "0123456789"\n',

        '[4] Hi!': 'Say "Hi!"\n',

        '[5] Short': 'Say "ABC"\n',

        '[6] Алфавит A-J': 'Say "ABCDEFGHIJ"\n',

        '[7] Esolang': 'Say "Esolang"\n',

        '[8] LOL': 'Say "LOL"\n',

        '[9] ABC': 'Say "ABC"\n',

        '[10] XYZ': 'Say "XYZ"\n',

        '[11] Длинная': 'Say "Hello, World! Welcome!"\n',

        '[12] Fox': 'Say "The quick brown fox"\n',

        '[13] Lorem': 'Say "Lorem ipsum dolor sit"\n',

        '[14] Mix': 'Say "ABCabc123!"\n',

        '[15] Symbols': 'Say "!@#$%^&*()"\n',

        '[16] AZ+az': 'Say "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"\n',

        '[17] Digital': 'Say "0123456789!@#"\n',

        '[18] Pan x1': 'Say "The quick brown fox jumps over the lazy dog."\n',

        '[19] Hello+': 'Say "Hello, World! Hello, World!"\n',

        '[20] Numbers': 'Say "1234567890"\n',

        '[Test 1] Панграмма x2': 'Say "The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. "\n',

        '[Test 2] Lorem x2': 'Say "Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet. "\n',

        '[Test 3] Всё вместе': 'Say "Hello! ABCDEFGHIJ 0123456789 !@#$"\n',

    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        try:
            return _rockstar_run(src)
        except Exception as e:
            return f"// Rockstar: {type(e).__name__}: {e}"

    def generate_code(self, output):
        if not output:
            return 'Say ""\n'
        return _rockstar_print(output)


TRANSPILERS[("rockstar", "python")] = _rockstar_to_python
