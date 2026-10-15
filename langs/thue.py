# langs/thue.py
"""Thue — язык переписывания строк.

Правила:
    lhs::=rhs   — заменить первое вхождение
    lhs:::rhs   — заменить все вхождения
    lhs::~rhs   — заменить случайное вхождение
    # comment   — комментарий
"""

import random
from core.base import Language
from core.translate import TRANSPILERS


def _thue_run(src, step_limit=100000):
    lines = src.splitlines()

    # Многострочные правила: если строка кончается на \\,
    # продолжаем на следующей
    merged = []
    for raw in lines:
        if merged and merged[-1].endswith("\\"):
            merged[-1] = merged[-1][:-1] + raw
        else:
            merged.append(raw)
    lines = merged

    rules = []          # (lhs, rhs, mode) mode: 'once'|'all'|'random'
    state_lines = []
    in_rules = True

    for line in lines:
        if in_rules and line.lstrip().startswith("#"):
            continue
        if in_rules and ":::" in line:
            lhs, rhs = line.split(":::", 1)
            rules.append((lhs, rhs, "all"))
            continue
        if in_rules and "::~" in line:
            lhs, rhs = line.split("::~", 1)
            rules.append((lhs, rhs, "random"))
            continue
        if in_rules and "::=" in line:
            lhs, rhs = line.split("::=", 1)
            rules.append((lhs, rhs, "once"))
            continue
        if in_rules and line.strip() == "":
            # Пустая строка между правилами и стейтом
            if rules:
                in_rules = False
            continue
        in_rules = False
        state_lines.append(line)

    state = "\n".join(state_lines)

    for _ in range(step_limit):
        applied = False

        # Сначала random
        random_rules = [(l, r) for l, r, m in rules
                        if m == "random" and l]
        if random_rules:
            lhs, rhs = random.choice(random_rules)
            if lhs in state:
                i = state.find(lhs)
                state = state[:i] + rhs + state[i + len(lhs):]
                applied = True
                continue

        # Потом all
        all_rules = [(l, r) for l, r, m in rules if m == "all" and l]
        for lhs, rhs in all_rules:
            if lhs in state:
                state = state.replace(lhs, rhs)
                applied = True
                break
        if applied:
            continue

        # Потом once
        once_rules = [(l, r) for l, r, m in rules if m == "once"]
        for lhs, rhs in once_rules:
            if lhs == "":
                state = rhs + state
                applied = True
                break
            if lhs in state:
                state = state.replace(lhs, rhs, 1)
                applied = True
                break
        if not applied:
            break

    return state


def _thue_to_python(src):
    result = _thue_run(src)
    return (
        "# Thue → Python (симуляция + вывод)\n"
        f"_out = {result!r}\n"
        "print(_out, end='')\n"
    )


def _thue_print(text):
    """Тривиально: пустая LHS даёт текст."""
    if not text:
        return "# empty\n::=\n"
    return f"# Пустая LHS → вставка в начало\n::=\n{text}"


def _thue_replace_demo():
    """Пример с реальным переписыванием: 1 → 2 → 3."""
    return (
        "# Замена: a -> b, b -> c\n"
        "a::=b\n"
        "b::=c\n"
        "::=\n"
        "abcabc"
    )


def _thue_random_demo():
    """Пример со случайной заменой."""
    return (
        "# Случайная замена\n"
        "a::~b\n"
        "a::~c\n"
        "::=\n"
        "aaaaa"
    )


def _thue_all_demo():
    """Пример с заменой всех вхождений."""
    return (
        "# Заменить все\n"
        "a:::X\n"
        "::=\n"
        "banana"
    )


def _thue_number_demo():
    return "::=\n1 2 3 4 5 6 7 8 9 10"


def _thue_squares_demo():
    return "::=\n1 4 9 16 25 36 49 64 81 100"


def _thue_cubes_demo():
    return "::=\n1 8 27 64 125 216 343 512 729 1000"


def _thue_table7_demo():
    return "::=\n7 14 21 28 35 42 49 56 63 70"


def _thue_fib_demo():
    return "::=\n0 1 1 2 3 5 8 13 21 34"


def _thue_50_demo():
    parts = ["=== Таблицы ==="]
    for k in range(1, 6):
        parts.append(f"-- {k} --")
        for i in range(1, 6):
            parts.append(str(i * k))
    return "::=\n" + "\n".join(parts)


def _thue_200_demo():
    parts = ["=== Большие таблицы ==="]
    for k in range(2, 8):
        parts.append(f"-- Таблица {k} --")
        for i in range(1, 11):
            parts.append(str(i * k))
    return "::=\n" + "\n".join(parts)


class ThueLang(Language):
    name = "thue"
    title = "Thue"
    category = "Э"
    ext = ".thue"
    keywords = ["::=", ":::", "::~"]
    comment_regex = r"#[^\n]*"

    templates = {

        '[1] Hello, World': '# Пустая LHS → вставка в начало\n::=\nHello, World!',

        '[2] Буква A': '# Пустая LHS → вставка в начало\n::=\nA',

        '[3] Цифры 0-9': '# Пустая LHS → вставка в начало\n::=\n0123456789',

        '[4] Hi!': '# Пустая LHS → вставка в начало\n::=\nHi!',

        '[5] Short': '# Пустая LHS → вставка в начало\n::=\nABC',

        '[6] Алфавит A-J': '# Пустая LHS → вставка в начало\n::=\nABCDEFGHIJ',

        '[7] Esolang': '# Пустая LHS → вставка в начало\n::=\nEsolang',

        '[8] LOL': '# Пустая LHS → вставка в начало\n::=\nLOL',

        '[9] ABC': '# Пустая LHS → вставка в начало\n::=\nABC',

        '[10] XYZ': '# Пустая LHS → вставка в начало\n::=\nXYZ',

        '[11] Длинная': '# Пустая LHS → вставка в начало\n::=\nHello, World! Welcome!',

        '[12] Fox': '# Пустая LHS → вставка в начало\n::=\nThe quick brown fox',

        '[13] Lorem': '# Пустая LHS → вставка в начало\n::=\nLorem ipsum dolor sit',

        '[14] Mix': '# Пустая LHS → вставка в начало\n::=\nABCabc123!',

        '[15] Symbols': '# Пустая LHS → вставка в начало\n::=\n!@#$%^&*()',

        '[16] AZ+az': '# Пустая LHS → вставка в начало\n::=\nABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',

        '[17] Digital': '# Пустая LHS → вставка в начало\n::=\n0123456789!@#',

        '[18] Pan x1': '# Пустая LHS → вставка в начало\n::=\nThe quick brown fox jumps over the lazy dog.',

        '[19] Hello+': '# Пустая LHS → вставка в начало\n::=\nHello, World! Hello, World!',

        '[20] Numbers': '# Пустая LHS → вставка в начало\n::=\n1234567890',

        '[Test 1] Панграмма x2': '# Пустая LHS → вставка в начало\n::=\nThe quick brown fox',

        '[Test 2] Lorem x2': '# Пустая LHS → вставка в начало\n::=\nLorem ipsum dolor',

        '[Test 3] Всё вместе': '# Пустая LHS → вставка в начало\n::=\nHello! ABC',

    }

    def execute(self, src):
        if not src:
            return ""
        try:
            return _thue_run(src)
        except Exception as e:
            return f"// Thue: {type(e).__name__}: {e}"

    def generate_code(self, output):
        if not output:
            return "# empty\n::=\n"
        return _thue_print(output)


TRANSPILERS[("thue", "python")] = _thue_to_python
