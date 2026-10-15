# langs/deadfish.py
"""Deadfish — эзотерический язык с одним счётчиком.

Команды:
    i — counter += 1
    d — counter -= 1
    s — counter = counter * counter
    o — print(counter)        (число)
    O — print(chr(counter))   (символ)
"""

from core.base import Language
from core.translate import TRANSPILERS


def _deadfish_to_python(src):
    """Deadfish → Python: линейная генерация."""
    lines = ["n = 0"]
    for ch in src:
        if ch == 'i':
            lines.append("n += 1")
        elif ch == 'd':
            lines.append("n -= 1")
        elif ch == 's':
            lines.append("n = n * n")
        elif ch == 'o':
            lines.append("print(n)")
        elif ch == 'O':
            lines.append("print(chr(n & 0xFF), end='')")
    return "\n".join(lines) + "\n"


def _gen_text(text):
    """Deadfish-код, печатающий строку через O (chr)."""
    parts = []
    prev = 0
    for ch in text:
        target = ord(ch) & 0xFF
        diff = target - prev
        if diff > 0:
            parts.append("i" * diff)
        elif diff < 0:
            parts.append("d" * (-diff))
        parts.append("O")
        prev = target
    return "".join(parts)


def _gen_numbers(nums):
    """Deadfish-код, печатающий числа через o."""
    parts = []
    prev = 0
    for n in nums:
        diff = n - prev
        if diff > 0:
            parts.append("i" * diff)
        elif diff < 0:
            parts.append("d" * (-diff))
        parts.append("o")
        prev = n
    return "".join(parts)


class DeadfishLang(Language):
    name = "deadfish"
    title = "Deadfish"
    category = "Э"
    ext = ".df"
    keywords = ["i", "d", "s", "o", "O"]
    types = []
    comment_regex = None

    templates = {

        '[1] Hello, World': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOOiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiOiiiOddddddOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddO',

        '[2] Буква A': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiO',

        '[3] Цифры 0-9': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiOiOiOiOiOiOiOiO',

        '[4] Hi!': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddO',

        '[5] Short': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiO',

        '[6] Алфавит A-J': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiOiOiOiOiOiOiOiO',

        '[7] Esolang': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddOdddOdddddddddddOiiiiiiiiiiiiiOdddddddO',

        '[8] LOL': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiOdddO',

        '[9] ABC': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiO',

        '[10] XYZ': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiO',

        '[11] Длинная': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOOiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiOiiiOddddddOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOdOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiOiiiiiiiOdddddddddOiiiiiiiiiiiiOddOddddddddOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddO',

        '[12] Fox': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiOdddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiOddddddddddddOddddddOiiiiiiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiOdddOiiiiiiiiOdddddddddOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiOiiiiiiiiiO',

        '[13] Lorem': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiOdddddddddddddOiiiiiiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOiiiOiiOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOdddOiiiOiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddddddddOiiiiiiiiiiiO',

        '[14] Mix': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiOddddddddddddddddddddddddddddddddddddddddddddddddddOiOiOddddddddddddddddddO',

        '[15] Symbols': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOdddddddddddddddddddddddddddddOiOiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiOddOiO',

        '[16] AZ+az': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiiiiiiiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiOiO',

        '[17] Digital': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiOiOiOiOiOiOiOiOddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOdddddddddddddddddddddddddddddO',

        '[18] Pan x1': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiOdddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiOddddddddddddOddddddOiiiiiiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiOdddOiiiiiiiiOdddddddddOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiOiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOddddddddOiiiOiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOdddddddddddddddddOiiiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddddddddddOdddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOdddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiOdOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddO',

        '[19] Hello+': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOOiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiOiiiOddddddOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOdOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOOiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiOiiiOddddddOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddO',

        '[20] Numbers': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiOiOiOiOiOiOiOdddddddddO',

        '[Test 1] Панграмма x2': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiOdddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiOddddddddddddOddddddOiiiiiiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiOdddOiiiiiiiiOdddddddddOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiOiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOddddddddOiiiOiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOdddddddddddddddddOiiiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddddddddddOdddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOdddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiOdOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddOddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiOdddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiOddddddddddddOddddddOiiiiiiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiOdddOiiiiiiiiOdddddddddOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiOiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOddddddddOiiiOiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOdddddddddddddddddOiiiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddddddddddOdddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOdddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiOdOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddOddddddddddddddO',

        '[Test 2] Lorem x2': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiOdddddddddddddOiiiiiiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOiiiOiiOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOdddOiiiOiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddddddddOiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiOddddddddOiiiiiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiOdddddddddddddOiiiiiiiiOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOiiiOiiOddddddddOdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiOdddOiiiOiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOddddddddddOiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiOddddddddOiiiiiiiiiiiiiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOddddddddddddddO',

        '[Test 3] Всё вместе': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiiiiiiiOOiiiOddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddOdOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOiOiOiOiOiOiOiOiOiOddddddddddddddddddddddddddddddddddddddddddOiiiiiiiiiiiiiiiiOiOiOiOiOiOiOiOiOiOdddddddddddddddddddddddddOiOiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiOdddddddddddddddddddddddddddddOiO',

    }

    def execute(self, src):
        if not src:
            return ""
        n = 0
        out = []
        for ch in src:
            if ch == 'i':
                n += 1
            elif ch == 'd':
                n -= 1
            elif ch == 's':
                n = n * n
            elif ch == 'o':
                out.append(str(n))
            elif ch == 'O':
                out.append(chr(n & 0xFF))
        return "".join(out)

    def generate_code(self, output):
        if not output:
            return ""
        return _gen_text(output)


TRANSPILERS[("deadfish", "python")] = _deadfish_to_python
