# langs/intercal.py
"""INTERCAL — язык 1972 г. .var, :var, #N, операторы."""

import re
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS


# ==================================================================
#  Хелперы
# ==================================================================
def _ic_var_name(expr):
    """Извлекает имя переменной: .1 → v1, :2 → v2, ,3 → a3."""
    e = expr.strip()
    if e.startswith('.'):
        return 'v' + e[1:].replace('.', '_')
    if e.startswith(':'):
        return 'v' + e[1:].replace('.', '_')
    if e.startswith(','):
        return 'a' + e[1:].replace('.', '_')
    return e.replace('.', '_')


def _ic_expr_to_py(expr):
    """Преобразует INTERCAL-выражение в Python."""
    e = expr.strip()

    # #N — константа
    e = re.sub(r"#(\d+)", r"\1", e)

    # Переменные: .1 → v1, :1 → v1, ,1 → a1
    e = re.sub(r"\.(\w+)", r"v\1", e)
    e = re.sub(r":(\w+)", r"v\1", e)
    e = re.sub(r",(\w+)", r"a\1", e)

    # Побитовые бинарные операторы (INTERCAL: & — AND, | — OR,
    # ~ — XOR; ? — унарный XOR по биту).
    e = re.sub(r"(\S+)\s*&\s*(\S+)", r"(\1 & \2)", e)
    e = re.sub(r"(\S+)\s*\|\s*(\S+)", r"(\1 | \2)", e)
    e = re.sub(r"(\S+)\s*~\s*(\S+)", r"(\1 ^ \2)", e)
    e = re.sub(r"\?(\S+)", r"(\1 ^ 1)", e)

    return e


# ==================================================================
#  Транспайлер INTERCAL → Python
# ==================================================================
def _intercal_to_python(src):
    lines = src.splitlines()
    out = []
    ind = 0
    please_count = 0

    def emit(s):
        out.append("    " * ind + s)

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("NOTE"):
            continue

        # PLEASE — считаем, но не ругаемся
        if line.startswith("PLEASE"):
            please_count += 1
            line = line[len("PLEASE"):].strip()
            if not line:
                continue

        # DO NOT — игнорируем
        if line.startswith("DO NOT"):
            continue

        # DO ...
        m = re.match(r"DO\s+(.+)$", line, re.IGNORECASE)
        if m:
            line = m.group(1).strip()
        else:
            if line.startswith("STOP") or line.startswith("GIVE UP"):
                break
            continue

        # STOP / GIVE UP
        if line.startswith("STOP") or line.startswith("GIVE UP"):
            break

        # PRINT "text"
        m = re.match(r'PRINT\s+"(.*)"\s*$', line, re.IGNORECASE)
        if m:
            _s = m.group(1).replace('\\"', '"')
            if _s == "":
                emit("print()")           # пустая строка = \n
            else:
                emit(f"print({_s!r}, end='')")
            continue

        # READ OUT var
        m = re.match(r"READ\s+OUT\s+(.+?)\s*$", line, re.IGNORECASE)
        if m:
            var = _ic_var_name(m.group(1))
            emit(f"print({var})")
            continue

        # WRITE IN var
        m = re.match(r"WRITE\s+IN\s+(.+?)\s*$", line, re.IGNORECASE)
        if m:
            var = _ic_var_name(m.group(1))
            emit(f"{var} = input()")
            continue

        # var <- expr
        m = re.match(r"(.+?)\s*<-\s*(.+?)\s*$", line)
        if m:
            target = _ic_var_name(m.group(1))
            value = _ic_expr_to_py(m.group(2))
            emit(f"{target} = {value}")
            continue

        # FORGET var
        m = re.match(r"FORGET\s+(.+?)\s*$", line, re.IGNORECASE)
        if m:
            var = _ic_var_name(m.group(1))
            emit(f"try:\n    del {var}\nexcept NameError:\n    pass")
            continue

        if line.startswith("ABSTAIN"):
            continue
        if line.startswith("REINSTATE"):
            continue
        if line.startswith("COME FROM"):
            continue

        emit(f"# INTERCAL: не поддержано: {line}")

    return "\n".join(out) + "\n"


# ==================================================================
#  Генераторы шаблонов
# ==================================================================
def _intercal_print(text):
    """INTERCAL-программа, печатающая текст посимвольно.

    Символ '\n' → DO PRINT "" (даёт перевод строки).
    Символ '"'  → DO PRINT "\"" (экранированная).
    Остальные    → DO PRINT "X".
    """
    parts = []
    for ch in text:
        if ch == '"':
            parts.append('DO PRINT "\\""')
        elif ch == "\n":
            parts.append('DO PRINT ""')
        elif ch == "\\":
            parts.append('DO PRINT "\\\\"')
        else:
            parts.append(f'DO PRINT "{ch}"')
    parts.append("DO GIVE UP")
    return "\n".join(parts) + "\n"


def _intercal_gen_numbers():
    return "\n".join([f'DO PRINT "{i}"' for i in range(1, 11)] + ["DO GIVE UP"])


def _intercal_gen_squares():
    return "\n".join([f'DO PRINT "{i*i}"' for i in range(1, 11)] + ["DO GIVE UP"])


def _intercal_gen_cubes():
    return "\n".join([f'DO PRINT "{i**3}"' for i in range(1, 11)] + ["DO GIVE UP"])


def _intercal_gen_table7():
    return "\n".join([f'DO PRINT "{i*7}"' for i in range(1, 11)] + ["DO GIVE UP"])


def _intercal_gen_fib():
    return "\n".join(
        [f'DO PRINT "{n}"' for n in [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]] +
        ["DO GIVE UP"])


def _intercal_gen_with_vars():
    """Демонстрация .var и <-."""
    return (
        "DO .1 <- #1\n"
        "DO .2 <- #2\n"
        "DO .3 <- #3\n"
        'DO PRINT "Переменные:"\n'
        "DO READ OUT .1\n"
        "DO READ OUT .2\n"
        "DO READ OUT .3\n"
        "DO GIVE UP"
    )


def _intercal_gen_with_please():
    """PLEASE считается."""
    return (
        "PLEASE DO .1 <- #42\n"
        "PLEASE DO READ OUT .1\n"
        "PLEASE DO GIVE UP"
    )


def _intercal_gen_hello_world_direct():
    return 'DO PRINT "Hello, World!"\nDO GIVE UP'


def _intercal_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f'DO PRINT "=== {k} x {k} ==="')
        for i in range(1, 6):
            parts.append(f'DO PRINT "{i*k}"')
    parts.append("DO GIVE UP")
    return "\n".join(parts)


def _intercal_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f'DO PRINT "=== Таблица {k} ==="')
        for i in range(1, 11):
            parts.append(f'DO PRINT "{i*k}"')
    parts.append("DO GIVE UP")
    return "\n".join(parts)


class IntercalLang(Language):
    name = "intercal"
    title = "INTERCAL"
    category = "Э"
    ext = ".i"
    keywords = ["PLEASE", "DO", "PRINT", "READ OUT", "WRITE IN",
                "STOP", "GIVE UP", "FORGET", "ABSTAIN", "REINSTATE"]
    comment_regex = r"NOTE[^\n]*"

    templates = {

        '[1] Hello, World': 'DO PRINT "H"\nDO PRINT "e"\nDO PRINT "l"\nDO PRINT "l"\nDO PRINT "o"\nDO PRINT ","\nDO PRINT " "\nDO PRINT "W"\nDO PRINT "o"\nDO PRINT "r"\nDO PRINT "l"\nDO PRINT "d"\nDO PRINT "!"\nDO GIVE UP\n',

        '[2] Буква A': 'DO PRINT "A"\nDO GIVE UP\n',

        '[3] Цифры 0-9': 'DO PRINT "0"\nDO PRINT "1"\nDO PRINT "2"\nDO PRINT "3"\nDO PRINT "4"\nDO PRINT "5"\nDO PRINT "6"\nDO PRINT "7"\nDO PRINT "8"\nDO PRINT "9"\nDO GIVE UP\n',

        '[4] Hi!': 'DO PRINT "H"\nDO PRINT "i"\nDO PRINT "!"\nDO GIVE UP\n',

        '[5] Short': 'DO PRINT "A"\nDO PRINT "B"\nDO PRINT "C"\nDO GIVE UP\n',

        '[6] Алфавит A-J': 'DO PRINT "A"\nDO PRINT "B"\nDO PRINT "C"\nDO PRINT "D"\nDO PRINT "E"\nDO PRINT "F"\nDO PRINT "G"\nDO PRINT "H"\nDO PRINT "I"\nDO PRINT "J"\nDO GIVE UP\n',

        '[7] Esolang': 'DO PRINT "E"\nDO PRINT "s"\nDO PRINT "o"\nDO PRINT "l"\nDO PRINT "a"\nDO PRINT "n"\nDO PRINT "g"\nDO GIVE UP\n',

        '[8] LOL': 'DO PRINT "L"\nDO PRINT "O"\nDO PRINT "L"\nDO GIVE UP\n',

        '[9] ABC': 'DO PRINT "A"\nDO PRINT "B"\nDO PRINT "C"\nDO GIVE UP\n',

        '[10] XYZ': 'DO PRINT "X"\nDO PRINT "Y"\nDO PRINT "Z"\nDO GIVE UP\n',

        '[11] Длинная': 'DO PRINT "H"\nDO PRINT "e"\nDO PRINT "l"\nDO PRINT "l"\nDO PRINT "o"\nDO PRINT ","\nDO PRINT " "\nDO PRINT "W"\nDO PRINT "o"\nDO PRINT "r"\nDO PRINT "l"\nDO PRINT "d"\nDO PRINT "!"\nDO PRINT " "\nDO PRINT "W"\nDO PRINT "e"\nDO PRINT "l"\nDO PRINT "c"\nDO PRINT "o"\nDO PRINT "m"\nDO PRINT "e"\nDO PRINT "!"\nDO GIVE UP\n',

        '[12] Fox': 'DO PRINT "T"\nDO PRINT "h"\nDO PRINT "e"\nDO PRINT " "\nDO PRINT "q"\nDO PRINT "u"\nDO PRINT "i"\nDO PRINT "c"\nDO PRINT "k"\nDO PRINT " "\nDO PRINT "b"\nDO PRINT "r"\nDO PRINT "o"\nDO PRINT "w"\nDO PRINT "n"\nDO PRINT " "\nDO PRINT "f"\nDO PRINT "o"\nDO PRINT "x"\nDO GIVE UP\n',

        '[13] Lorem': 'DO PRINT "L"\nDO PRINT "o"\nDO PRINT "r"\nDO PRINT "e"\nDO PRINT "m"\nDO PRINT " "\nDO PRINT "i"\nDO PRINT "p"\nDO PRINT "s"\nDO PRINT "u"\nDO PRINT "m"\nDO PRINT " "\nDO PRINT "d"\nDO PRINT "o"\nDO PRINT "l"\nDO PRINT "o"\nDO PRINT "r"\nDO PRINT " "\nDO PRINT "s"\nDO PRINT "i"\nDO PRINT "t"\nDO GIVE UP\n',

        '[14] Mix': 'DO PRINT "A"\nDO PRINT "B"\nDO PRINT "C"\nDO PRINT "a"\nDO PRINT "b"\nDO PRINT "c"\nDO PRINT "1"\nDO PRINT "2"\nDO PRINT "3"\nDO PRINT "!"\nDO GIVE UP\n',

        '[15] Symbols': 'DO PRINT "!"\nDO PRINT "@"\nDO PRINT "#"\nDO PRINT "$"\nDO PRINT "%"\nDO PRINT "^"\nDO PRINT "&"\nDO PRINT "*"\nDO PRINT "("\nDO PRINT ")"\nDO GIVE UP\n',

        '[16] AZ+az': 'DO PRINT "A"\nDO PRINT "B"\nDO PRINT "C"\nDO PRINT "D"\nDO PRINT "E"\nDO PRINT "F"\nDO PRINT "G"\nDO PRINT "H"\nDO PRINT "I"\nDO PRINT "J"\nDO PRINT "K"\nDO PRINT "L"\nDO PRINT "M"\nDO PRINT "N"\nDO PRINT "O"\nDO PRINT "P"\nDO PRINT "Q"\nDO PRINT "R"\nDO PRINT "S"\nDO PRINT "T"\nDO PRINT "U"\nDO PRINT "V"\nDO PRINT "W"\nDO PRINT "X"\nDO PRINT "Y"\nDO PRINT "Z"\nDO PRINT "a"\nDO PRINT "b"\nDO PRINT "c"\nDO PRINT "d"\nDO PRINT "e"\nDO PRINT "f"\nDO PRINT "g"\nDO PRINT "h"\nDO PRINT "i"\nDO PRINT "j"\nDO PRINT "k"\nDO PRINT "l"\nDO PRINT "m"\nDO PRINT "n"\nDO PRINT "o"\nDO PRINT "p"\nDO PRINT "q"\nDO PRINT "r"\nDO PRINT "s"\nDO PRINT "t"\nDO PRINT "u"\nDO PRINT "v"\nDO PRINT "w"\nDO PRINT "x"\nDO PRINT "y"\nDO PRINT "z"\nDO GIVE UP\n',

        '[17] Digital': 'DO PRINT "0"\nDO PRINT "1"\nDO PRINT "2"\nDO PRINT "3"\nDO PRINT "4"\nDO PRINT "5"\nDO PRINT "6"\nDO PRINT "7"\nDO PRINT "8"\nDO PRINT "9"\nDO PRINT "!"\nDO PRINT "@"\nDO PRINT "#"\nDO GIVE UP\n',

        '[18] Pan x1': 'DO PRINT "T"\nDO PRINT "h"\nDO PRINT "e"\nDO PRINT " "\nDO PRINT "q"\nDO PRINT "u"\nDO PRINT "i"\nDO PRINT "c"\nDO PRINT "k"\nDO PRINT " "\nDO PRINT "b"\nDO PRINT "r"\nDO PRINT "o"\nDO PRINT "w"\nDO PRINT "n"\nDO PRINT " "\nDO PRINT "f"\nDO PRINT "o"\nDO PRINT "x"\nDO PRINT " "\nDO PRINT "j"\nDO PRINT "u"\nDO PRINT "m"\nDO PRINT "p"\nDO PRINT "s"\nDO PRINT " "\nDO PRINT "o"\nDO PRINT "v"\nDO PRINT "e"\nDO PRINT "r"\nDO PRINT " "\nDO PRINT "t"\nDO PRINT "h"\nDO PRINT "e"\nDO PRINT " "\nDO PRINT "l"\nDO PRINT "a"\nDO PRINT "z"\nDO PRINT "y"\nDO PRINT " "\nDO PRINT "d"\nDO PRINT "o"\nDO PRINT "g"\nDO PRINT "."\nDO GIVE UP\n',

        '[19] Hello+': 'DO PRINT "H"\nDO PRINT "e"\nDO PRINT "l"\nDO PRINT "l"\nDO PRINT "o"\nDO PRINT ","\nDO PRINT " "\nDO PRINT "W"\nDO PRINT "o"\nDO PRINT "r"\nDO PRINT "l"\nDO PRINT "d"\nDO PRINT "!"\nDO PRINT " "\nDO PRINT "H"\nDO PRINT "e"\nDO PRINT "l"\nDO PRINT "l"\nDO PRINT "o"\nDO PRINT ","\nDO PRINT " "\nDO PRINT "W"\nDO PRINT "o"\nDO PRINT "r"\nDO PRINT "l"\nDO PRINT "d"\nDO PRINT "!"\nDO GIVE UP\n',

        '[20] Numbers': 'DO PRINT "1"\nDO PRINT "2"\nDO PRINT "3"\nDO PRINT "4"\nDO PRINT "5"\nDO PRINT "6"\nDO PRINT "7"\nDO PRINT "8"\nDO PRINT "9"\nDO PRINT "0"\nDO GIVE UP\n',

        '[Test 1] Панграмма x2': 'DO PRINT "T"\nDO PRINT "h"\nDO PRINT "e"\nDO PRINT " "\nDO PRINT "q"\nDO PRINT "u"\nDO PRINT "i"\nDO PRINT "c"\nDO PRINT "k"\nDO PRINT " "\nDO PRINT "b"\nDO PRINT "r"\nDO PRINT "o"\nDO PRINT "w"\nDO PRINT "n"\nDO PRINT " "\nDO PRINT "f"\nDO PRINT "o"\nDO PRINT "x"\nDO GIVE UP\n',

        '[Test 2] Lorem x2': 'DO PRINT "L"\nDO PRINT "o"\nDO PRINT "r"\nDO PRINT "e"\nDO PRINT "m"\nDO PRINT " "\nDO PRINT "i"\nDO PRINT "p"\nDO PRINT "s"\nDO PRINT "u"\nDO PRINT "m"\nDO PRINT " "\nDO PRINT "d"\nDO PRINT "o"\nDO PRINT "l"\nDO PRINT "o"\nDO PRINT "r"\nDO GIVE UP\n',

        '[Test 3] Всё вместе': 'DO PRINT "H"\nDO PRINT "e"\nDO PRINT "l"\nDO PRINT "l"\nDO PRINT "o"\nDO PRINT "!"\nDO PRINT " "\nDO PRINT "A"\nDO PRINT "B"\nDO PRINT "C"\nDO GIVE UP\n',

    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        py = _intercal_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<intercal>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// INTERCAL: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return 'DO GIVE UP\n'
        return _intercal_print(output)


TRANSPILERS[("intercal", "python")] = _intercal_to_python
