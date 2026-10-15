# langs/befunge.py
"""Befunge-93 — классический 2D-эзотерический язык."""

import random

from core.base import Language
from core.translate import TRANSPILERS


def _befunge_run(src, step_limit=500_000):
    """Интерпретатор Befunge-93. Ширина/высота — по размеру программы."""
    lines = src.splitlines() if src else [""]
    W = max(80, max((len(l) for l in lines), default=0))
    H = max(25, len(lines))

    grid = [[" "] * W for _ in range(H)]
    for y, line in enumerate(lines[:H]):
        for x, ch in enumerate(line[:W]):
            grid[y][x] = ch

    stack = []
    x = y = 0
    dx, dy = 1, 0
    string_mode = False
    out = []
    steps = 0

    def pop():
        return stack.pop() if stack else 0

    def push(v):
        stack.append(v)

    while steps < step_limit:
        steps += 1
        ch = grid[y][x]

        if string_mode:
            if ch == '"':
                string_mode = False
            else:
                push(ord(ch))
        else:
            if ch == " ":
                pass
            elif ch == "+":
                a, b = pop(), pop()
                push(a + b)
            elif ch == "-":
                a, b = pop(), pop()
                push(b - a)
            elif ch == "*":
                a, b = pop(), pop()
                push(a * b)
            elif ch == "/":
                a, b = pop(), pop()
                push(0 if a == 0 else b // a)
            elif ch == "%":
                a, b = pop(), pop()
                push(0 if a == 0 else b % a)
            elif ch == "!":
                push(1 if pop() == 0 else 0)
            elif ch == "`":
                a, b = pop(), pop()
                push(1 if b > a else 0)
            elif ch == ">":
                dx, dy = 1, 0
            elif ch == "<":
                dx, dy = -1, 0
            elif ch == "^":
                dx, dy = 0, -1
            elif ch == "v":
                dx, dy = 0, 1
            elif ch == "?":
                dx, dy = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            elif ch == "_":
                dx, dy = (1, 0) if pop() == 0 else (-1, 0)
            elif ch == "|":
                dx, dy = (0, 1) if pop() == 0 else (0, -1)
            elif ch == '"':
                string_mode = True
            elif ch == ":":
                v = pop()
                push(v)
                push(v)
            elif ch == "\\":
                a, b = pop(), pop()
                push(a)
                push(b)
            elif ch == "$":
                pop()
            elif ch == ".":
                out.append(str(pop()))
            elif ch == ",":
                out.append(chr(pop() & 0xFF))
            elif ch == "#":
                x = (x + dx) % W
                y = (y + dy) % H
            elif ch == "g":
                yy, xx = pop(), pop()
                if 0 <= yy < H and 0 <= xx < W:
                    push(ord(grid[yy][xx]))
                else:
                    push(0)
            elif ch == "p":
                yy, xx, v = pop(), pop(), pop()
                if 0 <= yy < H and 0 <= xx < W:
                    grid[yy][xx] = chr(v & 0xFF)
            elif ch == "&":
                try:
                    line = input()
                    push(int(line) if line else 0)
                except (EOFError, ValueError):
                    push(0)
            elif ch == "~":
                try:
                    line = input()
                    push(ord(line[0]) if line else 0)
                except EOFError:
                    push(0)
            elif ch == "@":
                break
            elif ch.isdigit():
                push(int(ch))

        x = (x + dx) % W
        y = (y + dy) % H

    return "".join(out)


def _befunge_print(text):
    """Befunge-программа, печатающая любой текст.

    Для каждого символа в обратном порядке пушим код:
      - обычные  : string-mode "c"
      - \n       : 55+ (5+5=10)
      - \t       : 33* (3*3=9)
      - "        : 84*2+ (8*4+2=34)
    Затем len(text) раз запятая.
    """
    if not text:
        return "@"

    parts = []
    for ch in reversed(text):
        if ch == '"':
            parts.append("84*2+")
        elif ch == "\n":
            parts.append("55+")
        elif ch == "\t":
            parts.append("33*")
        elif ch == "\r":
            parts.append("99+")  # 9+9=18
        else:
            parts.append(f'"{ch}"')

    return "".join(parts) + "," * len(text) + "@"

def _befunge_to_python(src):
    result = _befunge_run(src) if src else ""
    lines = [
        "# Befunge-93 → Python (симуляция + вывод)",
        f"_out = {result!r}",
        "print(_out, end='')",
    ]
    return "\n".join(lines) + "\n"


class BefungeLang(Language):
    name = "befunge"
    title = "Befunge-93"
    category = "Э"
    ext = ".bf93"
    keywords = [">", "<", "^", "v", "?", "_", "|", '"', ":",
                "\\", "$", ".", ",", "#", "g", "p", "&", "~", "@"]
    comment_regex = None

    templates = {

        '[1] Hello, World': '"!""d""l""r""o""W"" "",""o""l""l""e""H",,,,,,,,,,,,,@',

        '[2] Буква A': '"A",@',

        '[3] Цифры 0-9': '"9""8""7""6""5""4""3""2""1""0",,,,,,,,,,@',

        '[4] Hi!': '"!""i""H",,,@',

        '[5] Befunge': '"e""g""n""u""f""e""B",,,,,,,@',

        '[6] Алфавит A-J': '"J""I""H""G""F""E""D""C""B""A",,,,,,,,,,@',

        '[7] Esolang': '"g""n""a""l""o""s""E",,,,,,,@',

        '[8] LOL': '"L""O""L",,,@',

        '[9] ABC': '"C""B""A",,,@',

        '[10] XYZ': '"Z""Y""X",,,@',

        '[11] Длинная': '"!""e""m""o""c""l""e""W"" ""!""d""l""r""o""W"" "",""o""l""l""e""H",,,,,,,,,,,,,,,,,,,,,,@',

        '[12] Befunge rocks': '"!""s""k""c""o""r"" ""e""g""n""u""f""e""B",,,,,,,,,,,,,,@',

        '[13] TwoD rules': '"s""e""l""u""r"" ""D""o""w""T",,,,,,,,,,@',

        '[14] Stack magic': '"c""i""g""a""m"" ""k""c""a""t""S",,,,,,,,,,,@',

        '[15] Push pop': '"p""o""p"" ""h""s""u""P",,,,,,,,@',

        '[16] AZ + az': '"z""y""x""w""v""u""t""s""r""q""p""o""n""m""l""k""j""i""h""g""f""e""d""c""b""a""Z""Y""X""W""V""U""T""S""R""Q""P""O""N""M""L""K""J""I""H""G""F""E""D""C""B""A",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,@',

        '[17] Цифры+знаки': '")""(""*""&""^""%""$""#""@""!""9""8""7""6""5""4""3""2""1""0",,,,,,,,,,,,,,,,,,,,@',

        '[18] Fox': '"x""o""f"" ""n""w""o""r""b"" ""k""c""i""u""q"" ""e""h""T",,,,,,,,,,,,,,,,,,,@',

        '[19] Lorem': '"t""i""s"" ""r""o""l""o""d"" ""m""u""s""p""i"" ""m""e""r""o""L",,,,,,,,,,,,,,,,,,,,,@',

        '[20] Mix': '"!""3""2""1""c""b""a""C""B""A",,,,,,,,,,@',

        '[Test 1] Панграмма x2': '" "".""g""o""d"" ""y""z""a""l"" ""e""h""t"" ""r""e""v""o"" ""s""p""m""u""j"" ""x""o""f"" ""n""w""o""r""b"" ""k""c""i""u""q"" ""e""h""T"" "".""g""o""d"" ""y""z""a""l"" ""e""h""t"" ""r""e""v""o"" ""s""p""m""u""j"" ""x""o""f"" ""n""w""o""r""b"" ""k""c""i""u""q"" ""e""h""T",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,@',

        '[Test 2] Lorem x2': '" "".""r""u""t""e""t""c""e""s""n""o""c"" "",""t""e""m""a"" ""t""i""s"" ""r""o""l""o""d"" ""m""u""s""p""i"" ""m""e""r""o""L"" "".""r""u""t""e""t""c""e""s""n""o""c"" "",""t""e""m""a"" ""t""i""s"" ""r""o""l""o""d"" ""m""u""s""p""i"" ""m""e""r""o""L",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,@',

        '[Test 3] Всё вместе': '"$""#""@""!"" ""9""8""7""6""5""4""3""2""1""0"" ""J""I""H""G""F""E""D""C""B""A"" ""!""o""l""l""e""H",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,@',

    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        try:
            return _befunge_run(src)
        except Exception as e:
            return f"// Befunge-93: {type(e).__name__}: {e}"

    def generate_code(self, output):
        if not output:
            return "@"
        return _befunge_print(output)


TRANSPILERS[("befunge", "python")] = _befunge_to_python
