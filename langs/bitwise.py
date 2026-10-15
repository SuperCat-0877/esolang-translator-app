# langs/bitwise.py
"""Bitwise — стековый язык с битовыми операциями.
Числа пушатся цифрами, & | ^ ~ < > — операции, . и , — вывод."""

from core.base import Language
from core.translate import TRANSPILERS


def _bitwise_to_python(src):
    """Bitwise → Python: реальная линейная генерация."""
    lines = ["_s = []"]
    i = 0
    while i < len(src):
        ch = src[i]
        if ch.isdigit():
            num = ""
            while i < len(src) and src[i].isdigit():
                num += src[i]
                i += 1
            lines.append(f"_s.append({num})")
            continue
        elif ch == '&':
            lines.append("_a, _b = _s.pop(), _s.pop(); _s.append(_a & _b)")
        elif ch == '|':
            lines.append("_a, _b = _s.pop(), _s.pop(); _s.append(_a | _b)")
        elif ch == '^':
            lines.append("_a, _b = _s.pop(), _s.pop(); _s.append(_a ^ _b)")
        elif ch == '~':
            lines.append("_s.append(~_s.pop() & 0xFF)")
        elif ch == '<':
            lines.append("_s.append(_s.pop() << 1)")
        elif ch == '>':
            lines.append("_s.append(_s.pop() >> 1)")
        elif ch == '.':
            lines.append("print(_s.pop())")
        elif ch == ',':
            lines.append("print(chr(_s.pop() & 0xFF), end='')")
        i += 1
    return "\n".join(lines) + "\n"


class BitwiseLang(Language):
    name = "bitwise"
    title = "Bitwise"
    category = "Э"
    ext = ".bw"
    keywords = ["&", "|", "^", "~", "<", ">", ".", ","]
    types = []
    comment_regex = None

    templates = {

        '[1] Hello, World': '72,101,108,108,111,44,32,87,111,114,108,100,33,',

        '[2] Буква A': '65,',

        '[3] Цифры 0-9': '48,49,50,51,52,53,54,55,56,57,',

        '[4] Hi!': '72,105,33,',

        '[5] Bit': '66,105,116,',

        '[6] Алфавит A-J': '65,66,67,68,69,70,71,72,73,74,',

        '[7] Esolang': '69,115,111,108,97,110,103,',

        '[8] LOL': '76,79,76,',

        '[9] ABC': '65,66,67,',

        '[10] XYZ': '88,89,90,',

        '[11] Длинная': '72,101,108,108,111,44,32,87,111,114,108,100,33,32,87,101,108,99,111,109,101,33,',

        '[12] Bitwise rocks': '66,105,116,119,105,115,101,32,114,111,99,107,115,33,',

        '[13] AND': '1210&.',

        '[14] OR': '1210|.',

        '[15] XOR': '53^.',

        '[16] AZ + az': '65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,',

        '[17] Цифры+знаки': '48,49,50,51,52,53,54,55,56,57,33,64,35,36,37,94,38,42,40,41,',

        '[18] Fox': '84,104,101,32,113,117,105,99,107,32,98,114,111,119,110,32,102,111,120,',

        '[19] Lorem': '76,111,114,101,109,32,105,112,115,117,109,32,100,111,108,111,114,32,115,105,116,',

        '[20] Mix': '65,66,67,97,98,99,49,50,51,33,',

        '[Test 1] Панграмма x2': '84,104,101,32,113,117,105,99,107,32,98,114,111,119,110,32,102,111,120,32,106,117,109,112,115,32,111,118,101,114,32,116,104,101,32,108,97,122,121,32,100,111,103,46,32,84,104,101,32,113,117,105,99,107,32,98,114,111,119,110,32,102,111,120,32,106,117,109,112,115,32,111,118,101,114,32,116,104,101,32,108,97,122,121,32,100,111,103,46,32,',

        '[Test 2] Lorem x2': '76,111,114,101,109,32,105,112,115,117,109,32,100,111,108,111,114,32,115,105,116,32,97,109,101,116,44,32,99,111,110,115,101,99,116,101,116,117,114,46,32,76,111,114,101,109,32,105,112,115,117,109,32,100,111,108,111,114,32,115,105,116,32,97,109,101,116,44,32,99,111,110,115,101,99,116,101,116,117,114,46,32,',

        '[Test 3] Всё вместе': '72,101,108,108,111,33,32,65,66,67,68,69,70,71,72,73,74,32,48,49,50,51,52,53,54,55,56,57,32,33,64,35,36,',

    }

    def execute(self, src):
        stack = []
        out = []
        i = 0
        while i < len(src):
            ch = src[i]
            if ch.isdigit():
                num = ""
                while i < len(src) and src[i].isdigit():
                    num += src[i]
                    i += 1
                stack.append(int(num))
                continue
            elif ch == '&' and len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(a & b)
            elif ch == '|' and len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(a | b)
            elif ch == '^' and len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(a ^ b)
            elif ch == '~' and stack:
                stack.append(~stack.pop() & 0xFF)
            elif ch == '<' and stack:
                stack.append(stack.pop() << 1)
            elif ch == '>' and stack:
                stack.append(stack.pop() >> 1)
            elif ch == '.' and stack:
                out.append(str(stack.pop()))
            elif ch == ',' and stack:
                out.append(chr(stack.pop() & 0xFF))
            i += 1
        return "".join(out)

    def generate_code(self, output):
        if not output:
            return ""
        return "".join(f"{ord(c)}," for c in output)


TRANSPILERS[("bitwise", "python")] = _bitwise_to_python
