# langs/shakespeare.py
"""Shakespeare Programming Language (SPL) — упрощённый интерпретатор.

Персонажи — переменные (числа). Действия:
    Speak your mind!                — вывести символ (chr(var))
    Open your heart                 — вывести число
    Listen to your heart            — ввод (заглушка 0)
    You are as good as X            — var = value(X)
    You are as good as the sum of X and Y    — var = X + Y
    You are as good as the difference between X and Y — var = X - Y
    You are as good as the product of X and Y — var = X * Y
    You are as bad as X             — var = var - X
    Remember X                      — push
    Recall X                        — pop
"""

import re
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS


def _shakespeare_value(token, characters):
    token = token.strip().rstrip(".")
    if re.match(r"^-?\d+$", token):
        return int(token)
    if token in characters:
        return characters[token]
    # Неизвестный — не число
    return 0


def _shakespeare_run(src):
    if not src:
        return ""

    characters = {}
    stack = []
    out = []

    lines = src.splitlines()

    # Первый проход — собираем персонажей
    for line in lines:
        m = re.search(r"\[Enter\s+([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)*)\]",
                      line)
        if m:
            names = re.split(r"\s+and\s+", m.group(1))
            for n in names:
                characters.setdefault(n.strip(), 0)

    # Метки сцен: Scene I:, Scene II:, Scene 1:, …
    scene_labels = {}
    for idx, l in enumerate(lines):
        sm = re.match(r"Scene\s+([IVXLCDM]+|\d+)\s*:", l.strip())
        if sm:
            scene_labels[sm.group(1)] = idx

    pc = 0
    safety = 0
    while pc < len(lines) and safety < 100000:
        safety += 1
        raw = lines[pc]
        line = raw.strip()

        if not line:
            pc += 1
            continue
        if (line.startswith("[") or line.startswith("The")
                or line.startswith("Act ") or line.startswith("Scene ")
                or line.startswith("//")):
            pc += 1
            continue

        m = re.match(r"^([A-Z][a-z]+):\s*(.+?)$", line)
        if not m:
            pc += 1
            continue
        who = m.group(1)
        action = m.group(2).strip().rstrip(".")
        characters.setdefault(who, 0)

        if action == "Speak your mind!":
            out.append(chr(characters[who] & 0xFF))
            pc += 1
            continue
        if action == "Open your heart":
            out.append(str(characters[who]))
            pc += 1
            continue
        if action == "Listen to your heart":
            characters[who] = 0
            pc += 1
            continue

        m2 = re.match(r"Remember\s+(.+)$", action)
        if m2:
            stack.append(characters[who])
            pc += 1
            continue
        m2 = re.match(r"Recall\s+(.+)$", action)
        if m2:
            if stack:
                characters[who] = stack.pop()
            pc += 1
            continue

        m2 = re.match(r"You are as good as the sum of (.+?) and (.+)$", action)
        if m2:
            v1 = _shakespeare_value(m2.group(1), characters)
            v2 = _shakespeare_value(m2.group(2), characters)
            characters[who] = v1 + v2
            pc += 1
            continue
        m2 = re.match(
            r"You are as good as the difference between (.+?) and (.+)$",
            action)
        if m2:
            v1 = _shakespeare_value(m2.group(1), characters)
            v2 = _shakespeare_value(m2.group(2), characters)
            characters[who] = v1 - v2
            pc += 1
            continue
        m2 = re.match(r"You are as good as the product of (.+?) and (.+)$",
                      action)
        if m2:
            v1 = _shakespeare_value(m2.group(1), characters)
            v2 = _shakespeare_value(m2.group(2), characters)
            characters[who] = v1 * v2
            pc += 1
            continue
        m2 = re.match(r"You are as good as the quotient of (.+?) and (.+)$", action)
        if m2:
            v1 = _shakespeare_value(m2.group(1), characters)
            v2 = _shakespeare_value(m2.group(2), characters)
            characters[who] = 0 if v2 == 0 else v1 // v2
            pc += 1
            continue
        m2 = re.match(r"You are as good as the remainder of (.+?) and (.+)$", action)
        if m2:
            v1 = _shakespeare_value(m2.group(1), characters)
            v2 = _shakespeare_value(m2.group(2), characters)
            characters[who] = 0 if v2 == 0 else v1 % v2
            pc += 1
            continue
        m2 = re.match(r"You are as good as the square of (.+)$", action)
        if m2:
            v1 = _shakespeare_value(m2.group(1), characters)
            characters[who] = v1 * v1
            pc += 1
            continue
        m2 = re.match(r"You are as good as the cube of (.+)$", action)
        if m2:
            v1 = _shakespeare_value(m2.group(1), characters)
            characters[who] = v1 ** 3
            pc += 1
            continue
        m2 = re.match(r"You are as good as (.+)$", action)
        if m2:
            characters[who] = _shakespeare_value(m2.group(1), characters)
            pc += 1
            continue
        m2 = re.match(r"You are as bad as (.+)$", action)
        if m2:
            characters[who] = characters[who] - \
                _shakespeare_value(m2.group(1), characters)
            pc += 1
            continue

        # Goto и условные переходы
        m2 = re.match(r"Let us proceed to scene ([IVXLCDM]+|\d+)", action)
        if m2:
            pc = scene_labels.get(m2.group(1), pc + 1)
            continue
        m2 = re.match(r"If so, let us proceed to scene ([IVXLCDM]+|\d+)",
                      action)
        if m2:
            if characters.get(who, 0) != 0:
                pc = scene_labels.get(m2.group(1), pc + 1)
            else:
                pc += 1
            continue
        m2 = re.match(r"If not, let us proceed to scene ([IVXLCDM]+|\d+)",
                      action)
        if m2:
            if characters.get(who, 0) == 0:
                pc = scene_labels.get(m2.group(1), pc + 1)
            else:
                pc += 1
            continue

        pc += 1

    return "".join(out)

def _shakespeare_to_python(src):
    result = _shakespeare_run(src)
    return (
        "# Shakespeare → Python (симуляция + вывод)\n"
        f"_out = {result!r}\n"
        "print(_out, end='')\n"
    )


def _shakespeare_print(text):
    """SPL-программа, печатающая текст через Speak your mind!."""
    if not text:
        return "The Tragedy of Empty.\nAct I: Silence.\n[Exeunt]"
    lines = [
        "The Tragedy of Output.",
        "",
        "Act I: The Beginning.",
        "[Enter Romeo and Juliet]",
        "",
    ]
    for ch in text:
        n = ord(ch) & 0xFF
        lines.append(f"Romeo: You are as good as {n}.")
        lines.append("Romeo: Speak your mind!")
    lines.append("")
    lines.append("[Exeunt]")
    return "\n".join(lines)


def _shakespeare_gen_numbers():
    return _shakespeare_print("1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n")


def _shakespeare_gen_squares():
    return _shakespeare_print("1\n4\n9\n16\n25\n36\n49\n64\n81\n100\n")


def _shakespeare_gen_cubes():
    return _shakespeare_print("1\n8\n27\n64\n125\n216\n343\n512\n729\n1000\n")


def _shakespeare_gen_table7():
    return _shakespeare_print("7\n14\n21\n28\n35\n42\n49\n56\n63\n70\n")


def _shakespeare_gen_factorial():
    return _shakespeare_print("120\n")


def _shakespeare_gen_fib():
    return _shakespeare_print("0\n1\n1\n2\n3\n5\n8\n13\n21\n34\n")


def _shakespeare_gen_arith():
    return (
        "The Tragedy of Math.\n"
        "Act I: Numbers.\n"
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are as good as 5.\n"
        "Juliet: You are as good as 7.\n"
        "Romeo: You are as good as the sum of Romeo and Juliet.\n"
        "Romeo: Open your heart.\n"
        "[Exeunt]"
    )


def _shakespeare_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f"=== {k} x {k} ===")
        for i in range(1, 6):
            parts.append(str(i * k))
    return _shakespeare_print("\n".join(parts) + "\n")


def _shakespeare_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f"=== Таблица {k} ===")
        for i in range(1, 11):
            parts.append(str(i * k))
    return _shakespeare_print("\n".join(parts) + "\n")


class ShakespeareLang(Language):
    name = "shakespeare"
    title = "Shakespeare"
    category = "Э"
    ext = ".spl"
    keywords = ["Act", "Scene", "Enter", "Exit", "Exeunt",
                "Speak your mind", "Open your heart",
                "Listen to your heart", "Remember", "Recall",
                "You are as good as", "You are as bad as"]
    comment_regex = r"//[^\n]*"

    templates = {

        '[1] Hello, World': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 44.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 87.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[2] Буква A': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 65.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[3] Цифры 0-9': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 48.\nRomeo: Speak your mind!\nRomeo: You are as good as 49.\nRomeo: Speak your mind!\nRomeo: You are as good as 50.\nRomeo: Speak your mind!\nRomeo: You are as good as 51.\nRomeo: Speak your mind!\nRomeo: You are as good as 52.\nRomeo: Speak your mind!\nRomeo: You are as good as 53.\nRomeo: Speak your mind!\nRomeo: You are as good as 54.\nRomeo: Speak your mind!\nRomeo: You are as good as 55.\nRomeo: Speak your mind!\nRomeo: You are as good as 56.\nRomeo: Speak your mind!\nRomeo: You are as good as 57.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[4] Hi!': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[5] Short': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 65.\nRomeo: Speak your mind!\nRomeo: You are as good as 66.\nRomeo: Speak your mind!\nRomeo: You are as good as 67.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[6] Алфавит A-J': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 65.\nRomeo: Speak your mind!\nRomeo: You are as good as 66.\nRomeo: Speak your mind!\nRomeo: You are as good as 67.\nRomeo: Speak your mind!\nRomeo: You are as good as 68.\nRomeo: Speak your mind!\nRomeo: You are as good as 69.\nRomeo: Speak your mind!\nRomeo: You are as good as 70.\nRomeo: Speak your mind!\nRomeo: You are as good as 71.\nRomeo: Speak your mind!\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 73.\nRomeo: Speak your mind!\nRomeo: You are as good as 74.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[7] Esolang': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 69.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 97.\nRomeo: Speak your mind!\nRomeo: You are as good as 110.\nRomeo: Speak your mind!\nRomeo: You are as good as 103.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[8] LOL': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 76.\nRomeo: Speak your mind!\nRomeo: You are as good as 79.\nRomeo: Speak your mind!\nRomeo: You are as good as 76.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[9] ABC': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 65.\nRomeo: Speak your mind!\nRomeo: You are as good as 66.\nRomeo: Speak your mind!\nRomeo: You are as good as 67.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[10] XYZ': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 88.\nRomeo: Speak your mind!\nRomeo: You are as good as 89.\nRomeo: Speak your mind!\nRomeo: You are as good as 90.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[11] Длинная': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 44.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 87.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 87.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 99.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[12] Fox': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 84.\nRomeo: Speak your mind!\nRomeo: You are as good as 104.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 113.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 99.\nRomeo: Speak your mind!\nRomeo: You are as good as 107.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 98.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 119.\nRomeo: Speak your mind!\nRomeo: You are as good as 110.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 102.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 120.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[13] Lorem': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 76.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 112.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[14] Mix': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 65.\nRomeo: Speak your mind!\nRomeo: You are as good as 66.\nRomeo: Speak your mind!\nRomeo: You are as good as 67.\nRomeo: Speak your mind!\nRomeo: You are as good as 97.\nRomeo: Speak your mind!\nRomeo: You are as good as 98.\nRomeo: Speak your mind!\nRomeo: You are as good as 99.\nRomeo: Speak your mind!\nRomeo: You are as good as 49.\nRomeo: Speak your mind!\nRomeo: You are as good as 50.\nRomeo: Speak your mind!\nRomeo: You are as good as 51.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[15] Symbols': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\nRomeo: You are as good as 64.\nRomeo: Speak your mind!\nRomeo: You are as good as 35.\nRomeo: Speak your mind!\nRomeo: You are as good as 36.\nRomeo: Speak your mind!\nRomeo: You are as good as 37.\nRomeo: Speak your mind!\nRomeo: You are as good as 94.\nRomeo: Speak your mind!\nRomeo: You are as good as 38.\nRomeo: Speak your mind!\nRomeo: You are as good as 42.\nRomeo: Speak your mind!\nRomeo: You are as good as 40.\nRomeo: Speak your mind!\nRomeo: You are as good as 41.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[16] AZ+az': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 65.\nRomeo: Speak your mind!\nRomeo: You are as good as 66.\nRomeo: Speak your mind!\nRomeo: You are as good as 67.\nRomeo: Speak your mind!\nRomeo: You are as good as 68.\nRomeo: Speak your mind!\nRomeo: You are as good as 69.\nRomeo: Speak your mind!\nRomeo: You are as good as 70.\nRomeo: Speak your mind!\nRomeo: You are as good as 71.\nRomeo: Speak your mind!\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 73.\nRomeo: Speak your mind!\nRomeo: You are as good as 74.\nRomeo: Speak your mind!\nRomeo: You are as good as 75.\nRomeo: Speak your mind!\nRomeo: You are as good as 76.\nRomeo: Speak your mind!\nRomeo: You are as good as 77.\nRomeo: Speak your mind!\nRomeo: You are as good as 78.\nRomeo: Speak your mind!\nRomeo: You are as good as 79.\nRomeo: Speak your mind!\nRomeo: You are as good as 80.\nRomeo: Speak your mind!\nRomeo: You are as good as 81.\nRomeo: Speak your mind!\nRomeo: You are as good as 82.\nRomeo: Speak your mind!\nRomeo: You are as good as 83.\nRomeo: Speak your mind!\nRomeo: You are as good as 84.\nRomeo: Speak your mind!\nRomeo: You are as good as 85.\nRomeo: Speak your mind!\nRomeo: You are as good as 86.\nRomeo: Speak your mind!\nRomeo: You are as good as 87.\nRomeo: Speak your mind!\nRomeo: You are as good as 88.\nRomeo: Speak your mind!\nRomeo: You are as good as 89.\nRomeo: Speak your mind!\nRomeo: You are as good as 90.\nRomeo: Speak your mind!\nRomeo: You are as good as 97.\nRomeo: Speak your mind!\nRomeo: You are as good as 98.\nRomeo: Speak your mind!\nRomeo: You are as good as 99.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 102.\nRomeo: Speak your mind!\nRomeo: You are as good as 103.\nRomeo: Speak your mind!\nRomeo: You are as good as 104.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 106.\nRomeo: Speak your mind!\nRomeo: You are as good as 107.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 110.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 112.\nRomeo: Speak your mind!\nRomeo: You are as good as 113.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 118.\nRomeo: Speak your mind!\nRomeo: You are as good as 119.\nRomeo: Speak your mind!\nRomeo: You are as good as 120.\nRomeo: Speak your mind!\nRomeo: You are as good as 121.\nRomeo: Speak your mind!\nRomeo: You are as good as 122.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[17] Digital': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 48.\nRomeo: Speak your mind!\nRomeo: You are as good as 49.\nRomeo: Speak your mind!\nRomeo: You are as good as 50.\nRomeo: Speak your mind!\nRomeo: You are as good as 51.\nRomeo: Speak your mind!\nRomeo: You are as good as 52.\nRomeo: Speak your mind!\nRomeo: You are as good as 53.\nRomeo: Speak your mind!\nRomeo: You are as good as 54.\nRomeo: Speak your mind!\nRomeo: You are as good as 55.\nRomeo: Speak your mind!\nRomeo: You are as good as 56.\nRomeo: Speak your mind!\nRomeo: You are as good as 57.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\nRomeo: You are as good as 64.\nRomeo: Speak your mind!\nRomeo: You are as good as 35.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[18] Pan x1': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 84.\nRomeo: Speak your mind!\nRomeo: You are as good as 104.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 113.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 99.\nRomeo: Speak your mind!\nRomeo: You are as good as 107.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 98.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 119.\nRomeo: Speak your mind!\nRomeo: You are as good as 110.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 102.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 120.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 106.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 112.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 118.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\nRomeo: You are as good as 104.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 97.\nRomeo: Speak your mind!\nRomeo: You are as good as 122.\nRomeo: Speak your mind!\nRomeo: You are as good as 121.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 103.\nRomeo: Speak your mind!\nRomeo: You are as good as 46.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[19] Hello+': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 44.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 87.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 44.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 87.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[20] Numbers': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 49.\nRomeo: Speak your mind!\nRomeo: You are as good as 50.\nRomeo: Speak your mind!\nRomeo: You are as good as 51.\nRomeo: Speak your mind!\nRomeo: You are as good as 52.\nRomeo: Speak your mind!\nRomeo: You are as good as 53.\nRomeo: Speak your mind!\nRomeo: You are as good as 54.\nRomeo: Speak your mind!\nRomeo: You are as good as 55.\nRomeo: Speak your mind!\nRomeo: You are as good as 56.\nRomeo: Speak your mind!\nRomeo: You are as good as 57.\nRomeo: Speak your mind!\nRomeo: You are as good as 48.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[Test 1] Панграмма x2': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 84.\nRomeo: Speak your mind!\nRomeo: You are as good as 104.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 113.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 99.\nRomeo: Speak your mind!\nRomeo: You are as good as 107.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 98.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 119.\nRomeo: Speak your mind!\nRomeo: You are as good as 110.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 102.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 120.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 106.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 112.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 118.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\nRomeo: You are as good as 104.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 97.\nRomeo: Speak your mind!\nRomeo: You are as good as 122.\nRomeo: Speak your mind!\nRomeo: You are as good as 121.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 103.\nRomeo: Speak your mind!\nRomeo: You are as good as 46.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 84.\nRomeo: Speak your mind!\nRomeo: You are as good as 104.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 113.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 99.\nRomeo: Speak your mind!\nRomeo: You are as good as 107.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 98.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 119.\nRomeo: Speak your mind!\nRomeo: You are as good as 110.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 102.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 120.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 106.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 112.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 118.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\nRomeo: You are as good as 104.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 97.\nRomeo: Speak your mind!\nRomeo: You are as good as 122.\nRomeo: Speak your mind!\nRomeo: You are as good as 121.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 103.\nRomeo: Speak your mind!\nRomeo: You are as good as 46.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[Test 2] Lorem x2': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 76.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 112.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 97.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\nRomeo: You are as good as 46.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 76.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 112.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 117.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 100.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 114.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 115.\nRomeo: Speak your mind!\nRomeo: You are as good as 105.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 97.\nRomeo: Speak your mind!\nRomeo: You are as good as 109.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 116.\nRomeo: Speak your mind!\nRomeo: You are as good as 46.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\n\n[Exeunt]',

        '[Test 3] Всё вместе': 'The Tragedy of Output.\n\nAct I: The Beginning.\n[Enter Romeo and Juliet]\n\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 101.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 108.\nRomeo: Speak your mind!\nRomeo: You are as good as 111.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 65.\nRomeo: Speak your mind!\nRomeo: You are as good as 66.\nRomeo: Speak your mind!\nRomeo: You are as good as 67.\nRomeo: Speak your mind!\nRomeo: You are as good as 68.\nRomeo: Speak your mind!\nRomeo: You are as good as 69.\nRomeo: Speak your mind!\nRomeo: You are as good as 70.\nRomeo: Speak your mind!\nRomeo: You are as good as 71.\nRomeo: Speak your mind!\nRomeo: You are as good as 72.\nRomeo: Speak your mind!\nRomeo: You are as good as 73.\nRomeo: Speak your mind!\nRomeo: You are as good as 74.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 48.\nRomeo: Speak your mind!\nRomeo: You are as good as 49.\nRomeo: Speak your mind!\nRomeo: You are as good as 50.\nRomeo: Speak your mind!\nRomeo: You are as good as 51.\nRomeo: Speak your mind!\nRomeo: You are as good as 52.\nRomeo: Speak your mind!\nRomeo: You are as good as 53.\nRomeo: Speak your mind!\nRomeo: You are as good as 54.\nRomeo: Speak your mind!\nRomeo: You are as good as 55.\nRomeo: Speak your mind!\nRomeo: You are as good as 56.\nRomeo: Speak your mind!\nRomeo: You are as good as 57.\nRomeo: Speak your mind!\nRomeo: You are as good as 32.\nRomeo: Speak your mind!\nRomeo: You are as good as 33.\nRomeo: Speak your mind!\nRomeo: You are as good as 64.\nRomeo: Speak your mind!\nRomeo: You are as good as 35.\nRomeo: Speak your mind!\nRomeo: You are as good as 36.\nRomeo: Speak your mind!\n\n[Exeunt]',

    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        try:
            return _shakespeare_run(src)
        except Exception as e:
            return f"// Shakespeare: {type(e).__name__}: {e}"

    def generate_code(self, output):
        if not output:
            return "The Tragedy of Empty.\nAct I: Silence.\n[Exeunt]"
        return _shakespeare_print(output)


TRANSPILERS[("shakespeare", "python")] = _shakespeare_to_python
