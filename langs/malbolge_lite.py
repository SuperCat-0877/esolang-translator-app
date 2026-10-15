# langs/malbolge_lite.py
"""
Malbolge-lite — упрощённый эзотерический язык.

Инструкции:
    i   — counter += 1
    d   — counter -= 1
    o   — print(chr(counter))
    O   — print(chr(counter)); counter = 0
    c   — counter = 0
    p   — print(counter)
    n   — перевод строки
    s   — пробел
    #   — комментарий
    _   — конец программы
"""

from core.base import Language


def mb_make(text):
    return "".join("i" * (ord(c) & 0xFF) + "O" for c in text)


def mb_make_counted(text):
    parts = []
    prev = 0
    for ch in text:
        target = ord(ch) & 0xFF
        diff = target - prev
        if diff > 0:
            parts.append("i" * diff)
        elif diff < 0:
            parts.append("d" * (-diff))
        parts.append("o")
        prev = target
    return "".join(parts)


def _mb_multiline(text, width=60):
    code = mb_make_counted(text)
    return "\n".join(code[i:i + width]
                     for i in range(0, len(code), width))


class MalbolgeLiteLang(Language):
    name = "malbolge_lite"
    title = "Malbolge-lite"
    category = "Э"
    ext = ".mbl"
    keywords = ["i", "d", "o", "O", "c", "p", "n", "s", "_"]
    comment_regex = r"#[^\n]*"
    templates = {}

    def __init__(self):
        pangram = "The quick brown fox jumps over the lazy dog. "
        long_text = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        )

        self.templates = {

            '[1] Hello, World': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiooiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiioiiioddddddoddddddddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddo\n',

            '[2] Буква A': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiio\n',

            '[3] Цифры 0-9': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioioioioioioioioio\n',

            '[4] Hi!': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddo\n',

            '[5] Short': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioio\n',

            '[6] Алфавит A-J': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioioioioioioioioio\n',

            '[7] Esolang': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioddddodddodddddddddddoiiiiiiiiiiiiiodddddddo\n',

            '[8] LOL': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiodddo\n',

            '[9] ABC': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioio\n',

            '[10] XYZ': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioio\n',

            '[11] Длинная': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiooiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiioiiioddddddoddddddddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddodoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiioiiiiiiiodddddddddoiiiiiiiiiiiioddoddddddddoddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddo\n',

            '[12] Fox': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiodddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiioddddddddddddoddddddoiiiiiiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiodddoiiiiiiiiodddddddddoddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiioiiiiiiiiio\n',

            '[13] Lorem': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiodddddddddddddoiiiiiiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiioiiioiioddddddddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiodddoiiioiiioddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioddddddddddoiiiiiiiiiiio\n',

            '[14] Mix': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioioiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioioddddddddddddddddddddddddddddddddddddddddddddddddddoioioddddddddddddddddddo\n',

            '[15] Symbols': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiodddddddddddddddddddddddddddddoioioiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiioddoio\n',

            '[16] AZ+az': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioioioioioioioioioioioioioioioioioioioioioioioioioiiiiiiioioioioioioioioioioioioioioioioioioioioioioioioioio\n',

            '[17] Digital': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioioioioioioioioioddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiodddddddddddddddddddddddddddddo\n',

            '[18] Pan x1': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiodddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiioddddddddddddoddddddoiiiiiiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiodddoiiiiiiiiodddddddddoddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiioiiiiiiiiioddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiioddddddddoiiioiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiodddddddddddddddddoiiiiiiiiiiiiioddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioddddddddddddodddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiodddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiododddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiioddddddddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddo\n',

            '[19] Hello+': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiooiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiioiiioddddddoddddddddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddodoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiooiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiioiiioddddddoddddddddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddo\n',

            '[20] Numbers': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioioioioioioioiodddddddddo\n',

            '[Test 1] Панграмма x2': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiodddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiioddddddddddddoddddddoiiiiiiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiodddoiiiiiiiiodddddddddoddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiioiiiiiiiiio\n',

            '[Test 2] Lorem x2': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiodddddddddddddoiiiiiiiiodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiioiiioiioddddddddodddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiodddoiiioiiio\n',

            '[Test 3] Всё вместе': 'iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiiiiiiiiiiiiiiiiiiiiiiioiiiiiiiooiiioddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddodoiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiioioio\n',

        }

    def execute(self, src):
        if src is None:
            return ""
        out = []
        counter = 0
        stop = False

        for raw_line in src.splitlines():
            line = raw_line.split("#", 1)[0]
            for ch in line:
                if stop:
                    break
                if ch in " \t":
                    continue
                if ch == "i":
                    counter += 1
                elif ch == "d":
                    counter = (counter - 1) & 0xFF
                elif ch == "o":
                    out.append(chr(counter & 0xFF))
                elif ch == "O":
                    out.append(chr(counter & 0xFF))
                    counter = 0
                elif ch == "c":
                    counter = 0
                elif ch == "p":
                    out.append(str(counter))
                elif ch == "n":
                    out.append("\n")
                elif ch == "s":
                    out.append(" ")
                elif ch == "_":
                    counter = 0
                    stop = True
            if stop:
                break
        return "".join(out)

    def generate_code(self, output):
        if not output:
            return "# пустой вывод\n"
        return mb_make_counted(output) + "\n"

    # ==================================================================
    #  Malbolge-lite → Python (настоящий линейный транспайлер)
    # ==================================================================
    def _mb_to_python(src):
        """Malbolge-lite → Python: линейная трансляция."""
        lines = ["_c = 0", "_out = []"]
        stop = False

        for raw_line in src.splitlines():
            if stop:
                break
            line = raw_line.split("#", 1)[0]
            for ch in line:
                if ch in " \t":
                    continue
                if ch == "i":
                    lines.append("_c += 1")
                elif ch == "d":
                    lines.append("_c = (_c - 1) & 0xFF")
                elif ch == "o":
                    lines.append("_out.append(chr(_c & 0xFF))")
                elif ch == "O":
                    lines.append("_out.append(chr(_c & 0xFF))")
                    lines.append("_c = 0")
                elif ch == "c":
                    lines.append("_c = 0")
                elif ch == "p":
                    lines.append("_out.append(str(_c))")
                elif ch == "n":
                    lines.append("_out.append('\\n')")
                elif ch == "s":
                    lines.append("_out.append(' ')")
                elif ch == "_":
                    stop = True
                    break

        lines.append("print(''.join(_out), end='')")
        return "\n".join(lines) + "\n"

    try:
        from core.translate import TRANSPILERS
        TRANSPILERS[("malbolge_lite", "python")] = _mb_to_python
    except Exception:
        pass
