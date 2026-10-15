# langs/arnoldc.py
"""ArnoldC — язык из фраз Шварценеггера."""

import re
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS


PHRASES = {
    "IT'S SHOWTIME": None,
    "YOU HAVE BEEN TERMINATED": None,
    "TALK TO THE HAND": "print",
    "I NEED YOUR CLOTHES, YOUR BOOTS AND YOUR MOTORCYCLE": "input",
    "GET TO THE CHOPPER": "assign",
    "HERE IS MY INVITATION": "expr",
    "LET'S ROCK": "endif",
    "ENOUGH TALK": "end_assign",
    "I'LL BE BACK": "return",
    "GET UP": "plus",
    "GET DOWN": "minus",
    "YOU'RE FIRED": "mul",
    "HE HAD TO SPLIT": "div",
    "I LET HIM GO": "mod",
    "CONSIDER THAT A DIVORCE": "or",
    "KNOCK KNOCK": "eq",
}


def _arnoldc_to_python(src):
    lines = src.splitlines()
    out = []
    ind = 0
    pending_var = None
    expr_parts = []

    def emit(s):
        out.append("    " * ind + s)

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line == "IT'S SHOWTIME":
            continue
        if line == "YOU HAVE BEEN TERMINATED":
            break
        if line.startswith("I'LL BE BACK"):
            emit("return")
            continue

        m = re.match(r"TALK TO THE HAND\s+(.+)$", line)
        if m:
            arg = m.group(1).strip()
            if arg == '""':
                emit("print()")           # пустая строка = \n
            else:
                emit(f"print({arg}, end='')")
            continue
        if line == "TALK TO THE HAND":
            emit("print()")
            continue

        m = re.match(
            r"I NEED YOUR CLOTHES,\s*YOUR BOOTS AND YOUR MOTORCYCLE\s+(.+)$",
            line)
        if m:
            emit(f"{m.group(1).strip()} = input()")
            continue

        m = re.match(r"GET TO THE CHOPPER\s+(\w+)$", line)
        if m:
            pending_var = m.group(1)
            continue

        m = re.match(r"HERE IS MY INVITATION\s+(.+)$", line)
        if m:
            expr_parts = [m.group(1).strip()]
            continue

        if line == "ENOUGH TALK":
            if pending_var is not None:
                expr = " ".join(expr_parts)
                emit(f"{pending_var} = {expr}")
                pending_var = None
                expr_parts = []
            continue

        if line == "GET UP":
            expr_parts.append("+ 1")
            continue
        if line == "GET DOWN":
            expr_parts.append("- 1")
            continue
        if line == "YOU'RE FIRED":
            expr_parts.append("*")
            continue
        if line == "HE HAD TO SPLIT":
            expr_parts.append("/")
            continue
        if line == "I LET HIM GO":
            expr_parts.append("%")
            continue
        if line == "CONSIDER THAT A DIVORCE":
            expr_parts.append("|")
            continue
        if line == "KNOCK KNOCK":
            expr_parts.append("==")
            continue

        m = re.match(r"BECAUSE I'M GOING TO SAY PLEASE\s+(.+)$", line)
        if m:
            cond = " ".join(expr_parts) if expr_parts else m.group(1)
            emit(f"if {cond}:")
            ind += 1
            expr_parts = []
            continue
        if line == "BULLSHIT":
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue
        if line == "YOU HAVE NO RESPECT FOR LOGIC":
            ind = max(0, ind - 1)
            continue

        if line == "STICK AROUND":
            cond = " ".join(expr_parts) if expr_parts else "True"
            emit(f"while {cond}:")
            ind += 1
            expr_parts = []
            continue
        if line == "CHILL":
            ind = max(0, ind - 1)
            continue

        if line.startswith("@NO PROBLEMO"):
            expr_parts.append("True")
            continue
        if line.startswith("@I LIED"):
            expr_parts.append("False")
            continue

        if re.match(r"^-?\d+$", line):
            expr_parts.append(line)
            continue
        if re.match(r"^[A-Z][A-Z0-9_]*$", line):
            expr_parts.append(line.lower())
            continue

        emit(f"# ArnoldC: не поддержано: {line}")

    return "\n".join(out) + "\n"


def _arnoldc_print(text):
    """ArnoldC-программа, печатающая текст посимвольно.

    Символ '\n' → TALK TO THE HAND "" (даёт перевод строки).
    Символ '"'  → TALK TO THE HAND "\"" (экранированная).
    Остальные    → TALK TO THE HAND "X".
    """
    parts = ["IT'S SHOWTIME"]
    for ch in text:
        if ch == '"':
            parts.append('TALK TO THE HAND "\\""')
        elif ch == "\n":
            parts.append('TALK TO THE HAND ""')
        elif ch == "\\":
            parts.append('TALK TO THE HAND "\\\\"')
        else:
            parts.append(f'TALK TO THE HAND "{ch}"')
    parts.append("YOU HAVE BEEN TERMINATED")
    return "\n".join(parts) + "\n"


class ArnoldCLang(Language):
    name = "arnoldc"
    title = "ArnoldC"
    category = "Э"
    ext = ".arnoldc"
    keywords = list(PHRASES.keys())
    comment_regex = r"#[^\n]*"

    templates = {

        '[1] Hello, World': 'IT\'S SHOWTIME\nTALK TO THE HAND "H"\nTALK TO THE HAND "e"\nTALK TO THE HAND "l"\nTALK TO THE HAND "l"\nTALK TO THE HAND "o"\nTALK TO THE HAND ","\nTALK TO THE HAND " "\nTALK TO THE HAND "W"\nTALK TO THE HAND "o"\nTALK TO THE HAND "r"\nTALK TO THE HAND "l"\nTALK TO THE HAND "d"\nTALK TO THE HAND "!"\nYOU HAVE BEEN TERMINATED\n',

        '[2] Буква A': 'IT\'S SHOWTIME\nTALK TO THE HAND "A"\nYOU HAVE BEEN TERMINATED\n',

        '[3] Цифры 0-9': 'IT\'S SHOWTIME\nTALK TO THE HAND "0"\nTALK TO THE HAND "1"\nTALK TO THE HAND "2"\nTALK TO THE HAND "3"\nTALK TO THE HAND "4"\nTALK TO THE HAND "5"\nTALK TO THE HAND "6"\nTALK TO THE HAND "7"\nTALK TO THE HAND "8"\nTALK TO THE HAND "9"\nYOU HAVE BEEN TERMINATED\n',

        '[4] Hi!': 'IT\'S SHOWTIME\nTALK TO THE HAND "H"\nTALK TO THE HAND "i"\nTALK TO THE HAND "!"\nYOU HAVE BEEN TERMINATED\n',

        '[5] Arnold': 'IT\'S SHOWTIME\nTALK TO THE HAND "A"\nTALK TO THE HAND "r"\nTALK TO THE HAND "n"\nTALK TO THE HAND "o"\nTALK TO THE HAND "l"\nTALK TO THE HAND "d"\nYOU HAVE BEEN TERMINATED\n',

        '[6] Алфавит A-J': 'IT\'S SHOWTIME\nTALK TO THE HAND "A"\nTALK TO THE HAND "B"\nTALK TO THE HAND "C"\nTALK TO THE HAND "D"\nTALK TO THE HAND "E"\nTALK TO THE HAND "F"\nTALK TO THE HAND "G"\nTALK TO THE HAND "H"\nTALK TO THE HAND "I"\nTALK TO THE HAND "J"\nYOU HAVE BEEN TERMINATED\n',

        '[7] Esolang': 'IT\'S SHOWTIME\nTALK TO THE HAND "E"\nTALK TO THE HAND "s"\nTALK TO THE HAND "o"\nTALK TO THE HAND "l"\nTALK TO THE HAND "a"\nTALK TO THE HAND "n"\nTALK TO THE HAND "g"\nYOU HAVE BEEN TERMINATED\n',

        '[8] LOL': 'IT\'S SHOWTIME\nTALK TO THE HAND "L"\nTALK TO THE HAND "O"\nTALK TO THE HAND "L"\nYOU HAVE BEEN TERMINATED\n',

        '[9] ABC': 'IT\'S SHOWTIME\nTALK TO THE HAND "A"\nTALK TO THE HAND "B"\nTALK TO THE HAND "C"\nYOU HAVE BEEN TERMINATED\n',

        '[10] XYZ': 'IT\'S SHOWTIME\nTALK TO THE HAND "X"\nTALK TO THE HAND "Y"\nTALK TO THE HAND "Z"\nYOU HAVE BEEN TERMINATED\n',

        '[11] Длинная фраза': 'IT\'S SHOWTIME\nTALK TO THE HAND "H"\nTALK TO THE HAND "e"\nTALK TO THE HAND "l"\nTALK TO THE HAND "l"\nTALK TO THE HAND "o"\nTALK TO THE HAND ","\nTALK TO THE HAND " "\nTALK TO THE HAND "W"\nTALK TO THE HAND "o"\nTALK TO THE HAND "r"\nTALK TO THE HAND "l"\nTALK TO THE HAND "d"\nTALK TO THE HAND "!"\nTALK TO THE HAND " "\nTALK TO THE HAND "W"\nTALK TO THE HAND "e"\nTALK TO THE HAND "l"\nTALK TO THE HAND "c"\nTALK TO THE HAND "o"\nTALK TO THE HAND "m"\nTALK TO THE HAND "e"\nTALK TO THE HAND "!"\nYOU HAVE BEEN TERMINATED\n',

        '[12] ArnoldC rocks': 'IT\'S SHOWTIME\nTALK TO THE HAND "A"\nTALK TO THE HAND "r"\nTALK TO THE HAND "n"\nTALK TO THE HAND "o"\nTALK TO THE HAND "l"\nTALK TO THE HAND "d"\nTALK TO THE HAND "C"\nTALK TO THE HAND " "\nTALK TO THE HAND "r"\nTALK TO THE HAND "o"\nTALK TO THE HAND "c"\nTALK TO THE HAND "k"\nTALK TO THE HAND "s"\nTALK TO THE HAND "!"\nYOU HAVE BEEN TERMINATED\n',

        '[13] Esolang is fun': 'IT\'S SHOWTIME\nTALK TO THE HAND "E"\nTALK TO THE HAND "s"\nTALK TO THE HAND "o"\nTALK TO THE HAND "l"\nTALK TO THE HAND "a"\nTALK TO THE HAND "n"\nTALK TO THE HAND "g"\nTALK TO THE HAND " "\nTALK TO THE HAND "i"\nTALK TO THE HAND "s"\nTALK TO THE HAND " "\nTALK TO THE HAND "f"\nTALK TO THE HAND "u"\nTALK TO THE HAND "n"\nYOU HAVE BEEN TERMINATED\n',

        '[14] Hello from Arnold': 'IT\'S SHOWTIME\nTALK TO THE HAND "H"\nTALK TO THE HAND "e"\nTALK TO THE HAND "l"\nTALK TO THE HAND "l"\nTALK TO THE HAND "o"\nTALK TO THE HAND " "\nTALK TO THE HAND "f"\nTALK TO THE HAND "r"\nTALK TO THE HAND "o"\nTALK TO THE HAND "m"\nTALK TO THE HAND " "\nTALK TO THE HAND "A"\nTALK TO THE HAND "r"\nTALK TO THE HAND "n"\nTALK TO THE HAND "o"\nTALK TO THE HAND "l"\nTALK TO THE HAND "d"\nYOU HAVE BEEN TERMINATED\n',

        '[15] Nice to meet you': 'IT\'S SHOWTIME\nTALK TO THE HAND "N"\nTALK TO THE HAND "i"\nTALK TO THE HAND "c"\nTALK TO THE HAND "e"\nTALK TO THE HAND " "\nTALK TO THE HAND "t"\nTALK TO THE HAND "o"\nTALK TO THE HAND " "\nTALK TO THE HAND "m"\nTALK TO THE HAND "e"\nTALK TO THE HAND "e"\nTALK TO THE HAND "t"\nTALK TO THE HAND " "\nTALK TO THE HAND "y"\nTALK TO THE HAND "o"\nTALK TO THE HAND "u"\nYOU HAVE BEEN TERMINATED\n',

        '[16] AZ + az': 'IT\'S SHOWTIME\nTALK TO THE HAND "A"\nTALK TO THE HAND "B"\nTALK TO THE HAND "C"\nTALK TO THE HAND "D"\nTALK TO THE HAND "E"\nTALK TO THE HAND "F"\nTALK TO THE HAND "G"\nTALK TO THE HAND "H"\nTALK TO THE HAND "I"\nTALK TO THE HAND "J"\nTALK TO THE HAND "K"\nTALK TO THE HAND "L"\nTALK TO THE HAND "M"\nTALK TO THE HAND "N"\nTALK TO THE HAND "O"\nTALK TO THE HAND "P"\nTALK TO THE HAND "Q"\nTALK TO THE HAND "R"\nTALK TO THE HAND "S"\nTALK TO THE HAND "T"\nTALK TO THE HAND "U"\nTALK TO THE HAND "V"\nTALK TO THE HAND "W"\nTALK TO THE HAND "X"\nTALK TO THE HAND "Y"\nTALK TO THE HAND "Z"\nTALK TO THE HAND "a"\nTALK TO THE HAND "b"\nTALK TO THE HAND "c"\nTALK TO THE HAND "d"\nTALK TO THE HAND "e"\nTALK TO THE HAND "f"\nTALK TO THE HAND "g"\nTALK TO THE HAND "h"\nTALK TO THE HAND "i"\nTALK TO THE HAND "j"\nTALK TO THE HAND "k"\nTALK TO THE HAND "l"\nTALK TO THE HAND "m"\nTALK TO THE HAND "n"\nTALK TO THE HAND "o"\nTALK TO THE HAND "p"\nTALK TO THE HAND "q"\nTALK TO THE HAND "r"\nTALK TO THE HAND "s"\nTALK TO THE HAND "t"\nTALK TO THE HAND "u"\nTALK TO THE HAND "v"\nTALK TO THE HAND "w"\nTALK TO THE HAND "x"\nTALK TO THE HAND "y"\nTALK TO THE HAND "z"\nYOU HAVE BEEN TERMINATED\n',

        '[17] Цифры+знаки': 'IT\'S SHOWTIME\nTALK TO THE HAND "0"\nTALK TO THE HAND "1"\nTALK TO THE HAND "2"\nTALK TO THE HAND "3"\nTALK TO THE HAND "4"\nTALK TO THE HAND "5"\nTALK TO THE HAND "6"\nTALK TO THE HAND "7"\nTALK TO THE HAND "8"\nTALK TO THE HAND "9"\nTALK TO THE HAND "!"\nTALK TO THE HAND "@"\nTALK TO THE HAND "#"\nTALK TO THE HAND "$"\nTALK TO THE HAND "%"\nTALK TO THE HAND "^"\nTALK TO THE HAND "&"\nTALK TO THE HAND "*"\nTALK TO THE HAND "("\nTALK TO THE HAND ")"\nYOU HAVE BEEN TERMINATED\n',

        '[18] Панграмма (короткая)': 'IT\'S SHOWTIME\nTALK TO THE HAND "T"\nTALK TO THE HAND "h"\nTALK TO THE HAND "e"\nTALK TO THE HAND " "\nTALK TO THE HAND "q"\nTALK TO THE HAND "u"\nTALK TO THE HAND "i"\nTALK TO THE HAND "c"\nTALK TO THE HAND "k"\nTALK TO THE HAND " "\nTALK TO THE HAND "b"\nTALK TO THE HAND "r"\nTALK TO THE HAND "o"\nTALK TO THE HAND "w"\nTALK TO THE HAND "n"\nTALK TO THE HAND " "\nTALK TO THE HAND "f"\nTALK TO THE HAND "o"\nTALK TO THE HAND "x"\nYOU HAVE BEEN TERMINATED\n',

        '[19] Lorem (короткий)': 'IT\'S SHOWTIME\nTALK TO THE HAND "L"\nTALK TO THE HAND "o"\nTALK TO THE HAND "r"\nTALK TO THE HAND "e"\nTALK TO THE HAND "m"\nTALK TO THE HAND " "\nTALK TO THE HAND "i"\nTALK TO THE HAND "p"\nTALK TO THE HAND "s"\nTALK TO THE HAND "u"\nTALK TO THE HAND "m"\nTALK TO THE HAND " "\nTALK TO THE HAND "d"\nTALK TO THE HAND "o"\nTALK TO THE HAND "l"\nTALK TO THE HAND "o"\nTALK TO THE HAND "r"\nTALK TO THE HAND " "\nTALK TO THE HAND "s"\nTALK TO THE HAND "i"\nTALK TO THE HAND "t"\nYOU HAVE BEEN TERMINATED\n',

        '[20] Смесь': 'IT\'S SHOWTIME\nTALK TO THE HAND "A"\nTALK TO THE HAND "B"\nTALK TO THE HAND "C"\nTALK TO THE HAND "a"\nTALK TO THE HAND "b"\nTALK TO THE HAND "c"\nTALK TO THE HAND "1"\nTALK TO THE HAND "2"\nTALK TO THE HAND "3"\nTALK TO THE HAND "!"\nYOU HAVE BEEN TERMINATED\n',

        '[Test 1] Панграмма x2': 'IT\'S SHOWTIME\nTALK TO THE HAND "T"\nTALK TO THE HAND "h"\nTALK TO THE HAND "e"\nTALK TO THE HAND " "\nTALK TO THE HAND "q"\nTALK TO THE HAND "u"\nTALK TO THE HAND "i"\nTALK TO THE HAND "c"\nTALK TO THE HAND "k"\nTALK TO THE HAND " "\nTALK TO THE HAND "b"\nTALK TO THE HAND "r"\nTALK TO THE HAND "o"\nTALK TO THE HAND "w"\nTALK TO THE HAND "n"\nTALK TO THE HAND " "\nTALK TO THE HAND "f"\nTALK TO THE HAND "o"\nTALK TO THE HAND "x"\nTALK TO THE HAND " "\nTALK TO THE HAND "j"\nTALK TO THE HAND "u"\nTALK TO THE HAND "m"\nTALK TO THE HAND "p"\nTALK TO THE HAND "s"\nTALK TO THE HAND " "\nTALK TO THE HAND "o"\nTALK TO THE HAND "v"\nTALK TO THE HAND "e"\nTALK TO THE HAND "r"\nTALK TO THE HAND " "\nTALK TO THE HAND "t"\nTALK TO THE HAND "h"\nTALK TO THE HAND "e"\nTALK TO THE HAND " "\nTALK TO THE HAND "l"\nTALK TO THE HAND "a"\nTALK TO THE HAND "z"\nTALK TO THE HAND "y"\nTALK TO THE HAND " "\nTALK TO THE HAND "d"\nTALK TO THE HAND "o"\nTALK TO THE HAND "g"\nTALK TO THE HAND "."\nTALK TO THE HAND " "\nTALK TO THE HAND "T"\nTALK TO THE HAND "h"\nTALK TO THE HAND "e"\nTALK TO THE HAND " "\nTALK TO THE HAND "q"\nTALK TO THE HAND "u"\nTALK TO THE HAND "i"\nTALK TO THE HAND "c"\nTALK TO THE HAND "k"\nTALK TO THE HAND " "\nTALK TO THE HAND "b"\nTALK TO THE HAND "r"\nTALK TO THE HAND "o"\nTALK TO THE HAND "w"\nTALK TO THE HAND "n"\nTALK TO THE HAND " "\nTALK TO THE HAND "f"\nTALK TO THE HAND "o"\nTALK TO THE HAND "x"\nTALK TO THE HAND " "\nTALK TO THE HAND "j"\nTALK TO THE HAND "u"\nTALK TO THE HAND "m"\nTALK TO THE HAND "p"\nTALK TO THE HAND "s"\nTALK TO THE HAND " "\nTALK TO THE HAND "o"\nTALK TO THE HAND "v"\nTALK TO THE HAND "e"\nTALK TO THE HAND "r"\nTALK TO THE HAND " "\nTALK TO THE HAND "t"\nTALK TO THE HAND "h"\nTALK TO THE HAND "e"\nTALK TO THE HAND " "\nTALK TO THE HAND "l"\nTALK TO THE HAND "a"\nTALK TO THE HAND "z"\nTALK TO THE HAND "y"\nTALK TO THE HAND " "\nTALK TO THE HAND "d"\nTALK TO THE HAND "o"\nTALK TO THE HAND "g"\nTALK TO THE HAND "."\nTALK TO THE HAND " "\nYOU HAVE BEEN TERMINATED\n',

        '[Test 2] Lorem x2': 'IT\'S SHOWTIME\nTALK TO THE HAND "L"\nTALK TO THE HAND "o"\nTALK TO THE HAND "r"\nTALK TO THE HAND "e"\nTALK TO THE HAND "m"\nTALK TO THE HAND " "\nTALK TO THE HAND "i"\nTALK TO THE HAND "p"\nTALK TO THE HAND "s"\nTALK TO THE HAND "u"\nTALK TO THE HAND "m"\nTALK TO THE HAND " "\nTALK TO THE HAND "d"\nTALK TO THE HAND "o"\nTALK TO THE HAND "l"\nTALK TO THE HAND "o"\nTALK TO THE HAND "r"\nTALK TO THE HAND " "\nTALK TO THE HAND "s"\nTALK TO THE HAND "i"\nTALK TO THE HAND "t"\nTALK TO THE HAND " "\nTALK TO THE HAND "a"\nTALK TO THE HAND "m"\nTALK TO THE HAND "e"\nTALK TO THE HAND "t"\nTALK TO THE HAND ","\nTALK TO THE HAND " "\nTALK TO THE HAND "c"\nTALK TO THE HAND "o"\nTALK TO THE HAND "n"\nTALK TO THE HAND "s"\nTALK TO THE HAND "e"\nTALK TO THE HAND "c"\nTALK TO THE HAND "t"\nTALK TO THE HAND "e"\nTALK TO THE HAND "t"\nTALK TO THE HAND "u"\nTALK TO THE HAND "r"\nTALK TO THE HAND "."\nTALK TO THE HAND " "\nTALK TO THE HAND "L"\nTALK TO THE HAND "o"\nTALK TO THE HAND "r"\nTALK TO THE HAND "e"\nTALK TO THE HAND "m"\nTALK TO THE HAND " "\nTALK TO THE HAND "i"\nTALK TO THE HAND "p"\nTALK TO THE HAND "s"\nTALK TO THE HAND "u"\nTALK TO THE HAND "m"\nTALK TO THE HAND " "\nTALK TO THE HAND "d"\nTALK TO THE HAND "o"\nTALK TO THE HAND "l"\nTALK TO THE HAND "o"\nTALK TO THE HAND "r"\nTALK TO THE HAND " "\nTALK TO THE HAND "s"\nTALK TO THE HAND "i"\nTALK TO THE HAND "t"\nTALK TO THE HAND " "\nTALK TO THE HAND "a"\nTALK TO THE HAND "m"\nTALK TO THE HAND "e"\nTALK TO THE HAND "t"\nTALK TO THE HAND ","\nTALK TO THE HAND " "\nTALK TO THE HAND "c"\nTALK TO THE HAND "o"\nTALK TO THE HAND "n"\nTALK TO THE HAND "s"\nTALK TO THE HAND "e"\nTALK TO THE HAND "c"\nTALK TO THE HAND "t"\nTALK TO THE HAND "e"\nTALK TO THE HAND "t"\nTALK TO THE HAND "u"\nTALK TO THE HAND "r"\nTALK TO THE HAND "."\nTALK TO THE HAND " "\nYOU HAVE BEEN TERMINATED\n',

        '[Test 3] Всё вместе': 'IT\'S SHOWTIME\nTALK TO THE HAND "H"\nTALK TO THE HAND "e"\nTALK TO THE HAND "l"\nTALK TO THE HAND "l"\nTALK TO THE HAND "o"\nTALK TO THE HAND "!"\nTALK TO THE HAND " "\nTALK TO THE HAND "A"\nTALK TO THE HAND "B"\nTALK TO THE HAND "C"\nTALK TO THE HAND "D"\nTALK TO THE HAND "E"\nTALK TO THE HAND "F"\nTALK TO THE HAND "G"\nTALK TO THE HAND "H"\nTALK TO THE HAND "I"\nTALK TO THE HAND "J"\nTALK TO THE HAND " "\nTALK TO THE HAND "0"\nTALK TO THE HAND "1"\nTALK TO THE HAND "2"\nTALK TO THE HAND "3"\nTALK TO THE HAND "4"\nTALK TO THE HAND "5"\nTALK TO THE HAND "6"\nTALK TO THE HAND "7"\nTALK TO THE HAND "8"\nTALK TO THE HAND "9"\nTALK TO THE HAND " "\nTALK TO THE HAND "!"\nTALK TO THE HAND "@"\nTALK TO THE HAND "#"\nTALK TO THE HAND "$"\nYOU HAVE BEEN TERMINATED\n',

    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        py = _arnoldc_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<arnoldc>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// ArnoldC: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return "IT'S SHOWTIME\nYOU HAVE BEEN TERMINATED\n"
        return _arnoldc_print(output)


TRANSPILERS[("arnoldc", "python")] = _arnoldc_to_python
