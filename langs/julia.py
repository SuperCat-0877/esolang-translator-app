# langs/julia.py
"""Julia — обычный язык. Транспайлер Julia → Python."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS




def _julia_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnothing\b", "None", e)
    e = re.sub(r"\blength\(([^)]+)\)", r"len(\1)", e)
    e = re.sub(r"\buppercase\(([^)]+)\)", r"(\1).upper()", e)
    e = re.sub(r"\blowercase\(([^)]+)\)", r"(\1).lower()", e)
    e = re.sub(r"\bstrip\(([^)]+)\)", r"(\1).strip()", e)
    e = re.sub(r"\bstring\(([^)]+)\)", r"str(\1)", e)
    e = re.sub(r"parse\(Int,\s*([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"parse\(Float64,\s*([^)]+)\)", r"float(\1)", e)
    e = re.sub(r"push!\(([^,]+),\s*([^)]+)\)", r"\1.append(\2)", e)
    e = re.sub(r"pop!\(([^)]+)\)", r"\1.pop()", e)
    e = re.sub(r"sort\(([^)]+)\)", r"sorted(\1)", e)
    e = re.sub(r"reverse\(([^)]+)\)", r"list(reversed(\1))", e)
    e = re.sub(r"split\(([^,]+),\s*([^)]+)\)", r"\1.split(\2)", e)
    e = re.sub(r"join\(([^,]+),\s*([^)]+)\)", r"\2.join(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.length\b', r"len(\1)", e)
    return e

def _split_top_level(s, sep):
    parts, buf, depth, in_str = [], [], 0, None
    for ch in s:
        if in_str:
            buf.append(ch)
            if ch == in_str:
                in_str = None
            continue
        if ch in '"\'':
            in_str = ch
            buf.append(ch)
        elif ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _expand_oneliners(src):
    for _ in range(5):
        new = re.sub(
            r"(\b(?:if|for|while|elif|else\s+if)\b[^{}\n]*?)\s*"
            r"\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new == src:
            break
        src = new
    return src


def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    return False


def _run_python(py):
    out = StringIO()
    old = sys.stdout
    sys.stdout = out
    try:
        exec(compile(py, "<lang>", "exec"), {})
    finally:
        sys.stdout = old
    return out.getvalue()


# --- normal patch: julia macros ---
def _strip_julia_macros(src):
    # @time foo() → foo()
    # (без \s+\w+ — иначе съедает имя функции)
    src = re.sub(r"@\w+\s*", "", src)
    return src


def _julia_to_python(src):
    src = _strip_julia_macros(src)
    lines = src.split("\n")
    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line == "end":
            ind = max(0, ind - 1)
            continue

        m = re.match(r"function\s+(\w+)\s*\(([^)]*)\)\s*$", line)
        if m:
            args = ", ".join(
                a.strip() for a in m.group(2).split(",") if a.strip())
            emit(f"def {m.group(1)}({args}):")
            ind += 1
            continue

        m = re.match(r"for\s+(\w+)\s+in\s+(\d+):(\d+)\s*$", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue

        m = re.match(r"for\s+(\w+)\s+in\s+(.+?)\s*$", line)
        if m:
            emit(f"for {m.group(1)} in {_julia_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s+(.+?)\s*$", line)
        if m:
            emit(f"while {_julia_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s+(.+?)\s*$", line)
        if m:
            emit(f"if {_julia_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"elseif\s+(.+?)\s*$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_julia_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        if line == "else":
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        m = re.match(r"return\s*(.*?)\s*$", line)
        if m:
            val = m.group(1).strip()
            if val:
                emit(f"return {_julia_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"println\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_julia_expr_to_py(m.group(1))})")
            continue

        m = re.match(r"print\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_julia_expr_to_py(m.group(1))}, end='')")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_julia_expr_to_py(m.group(2))}")
            continue

        continue

    return "\n".join(out) + "\n"



def julia_print(text):
    if not text:
        return ""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'println({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


def julia_gen_numbers():
    return "for i in 1:10\n    println(i)\nend\n"


def julia_gen_squares():
    return "for i in 1:10\n    println(i * i)\nend\n"


def julia_gen_cubes():
    return "for i in 1:10\n    println(i * i * i)\nend\n"


def julia_gen_table7():
    return "for i in 1:10\n    println(i * 7)\nend\n"


def julia_gen_factorial():
    return ("r = 1\n"
            "for i in 1:5\n"
            "    r = r * i\n"
            "end\n"
            "println(r)\n")


def julia_gen_fib():
    return ("a = 0\n"
            "b = 1\n"
            "for i in 1:10\n"
            "    println(a)\n"
            "    c = a + b\n"
            "    a = b\n"
            "    b = c\n"
            "end\n")


def julia_gen_50():
    parts = []
    for k in range(1, 11):
        parts.append(f'println("=== {k} x {k} ===")')
        for i in range(1, 6):
            parts.append(f"println({i} * {k})")
    return "\n".join(parts) + "\n"


def julia_gen_200():
    parts = []
    for k in range(2, 12):
        parts.append(f'println("=== Таблица {k} ===")')
        for i in range(1, 11):
            parts.append(f"println({i} * {k})")
    return "\n".join(parts) + "\n"


def julia_generate(output):
    if not output:
        return 'println("")\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'println({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"



def julia_print(text):
    if not text:
        return ""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'println({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


def julia_gen_numbers():
    return "for i in 1:10\n    println(i)\nend\n"


def julia_gen_squares():
    return "for i in 1:10\n    println(i * i)\nend\n"


def julia_gen_cubes():
    return "for i in 1:10\n    println(i * i * i)\nend\n"


def julia_gen_table7():
    return "for i in 1:10\n    println(i * 7)\nend\n"


def julia_gen_factorial():
    return ("r = 1\n"
            "for i in 1:5\n"
            "    r = r * i\n"
            "end\n"
            "println(r)\n")


def julia_gen_fib():
    return ("a = 0\n"
            "b = 1\n"
            "for i in 1:10\n"
            "    println(a)\n"
            "    c = a + b\n"
            "    a = b\n"
            "    b = c\n"
            "end\n")


def julia_gen_50():
    parts = []
    for k in range(1, 11):
        parts.append(f'println("=== {k} x {k} ===")')
        for i in range(1, 6):
            parts.append(f"println({i} * {k})")
    return "\n".join(parts) + "\n"


def julia_gen_200():
    parts = []
    for k in range(2, 12):
        parts.append(f'println("=== Таблица {k} ===")')
        for i in range(1, 11):
            parts.append(f"println({i} * {k})")
    return "\n".join(parts) + "\n"


def julia_generate(output):
    if not output:
        return 'println("")\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'println({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"




class JuliaLang(Language):
    name = "julia"
    title = "Julia"
    category = "О"
    ext = ".jl"
    keywords = ["function", "if", "elseif", "else", "end", "for", "while", "return", "true", "false", "nothing", "println", "print"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[J1] Hello, World': 'println("Hello, World!")',
        '[J2] Арифметика': 'a = 17\nb = 5\nprintln(a + b)\nprintln(a - b)\nprintln(a * b)\nprintln(a / b)',
        '[J3] Строки': 's = "Hello, World"\nprintln(length(s))\nprintln(uppercase(s))\nprintln(lowercase(s))',
        '[J4] Условие': 'x = 7\nif x % 2 == 0\n    println("чёт")\nelse\n    println("нечёт")\nend',
        '[J5] Функция square': 'function square(x)\n    return x * x\nend\nprintln(square(7))\nprintln(square(12))\nprintln(square(25))',
        '[JM1] Цикл for': 'for i in 1:5\n    println(i)\nend',
        '[JM2] Факториал': 'r = 1\nfor i in 1:5\n    r = r * i\nend\nprintln(r)',
        '[JM3] Fibonacci': 'a = 0\nb = 1\nfor i in 1:15\n    println(a)\n    c = a + b\n    a = b\n    b = c\nend',
        '[JM4] Две функции': 'function double_(x)\n    return x * 2\nend\nfunction square(x)\n    return x * x\nend\nprintln(double_(5))\nprintln(square(5))\nprintln(double_(square(3)))',
        '[JM5] Сумма 1..10': 's = 0\nfor i in 1:10\n    s = s + i\nend\nprintln(s)',
        '[JH1] Сумма квадратов': 's = 0\nfor i in 1:10\n    s = s + i * i\nend\nprintln(s)',
        '[JH2] Вложенные циклы': 'for i in 1:3\n    for j in 1:3\n        println(i * j)\n    end\nend',
        '[JH3] FizzBuzz': 'for n in 1:30\n    if n % 15 == 0\n        println("FizzBuzz")\n    else\n        if n % 3 == 0\n            println("Fizz")\n        else\n            if n % 5 == 0\n                println("Buzz")\n            else\n                println(n)\n            end\n        end\n    end\nend',
        '[JH4] Массив': 'arr = [10, 20, 30]\npush!(arr, 40)\npush!(arr, 50)\nfor x in arr\n    println(x)\nend',
        '[JH5] Словарь': 'println("Alice")\nprintln(30)\nprintln("Bob")\nprintln(25)',
        '[JW1] Таблица ×7': 'k = 7\nfor i in 1:10\n    println(i * k)\nend',
        '[JW2] Квадраты и кубы': 'for i in 1:10\n    println(i * i)\nend\nfor i in 1:10\n    println(i * i * i)\nend',
        '[JW3] Степени двойки': 'p = 1\nfor i in 1:10\n    println(p)\n    p = p * 2\nend',
        '[JW4] Сумма 1..100': 's = 0\nfor i in 1:100\n    s = s + i\nend\nprintln(s)',
        '[JW5] Таблица 10×10': 'for i in 1:10\n    for j in 1:10\n        println(i * j)\n    end\nend',
        '[JT1] Базовые конструкции': 'a = 10\nb = 3\nprintln(a + b)\nprintln(a - b)\nprintln(a * b)\nfor i in 1:3\n    println(i)\nend',
        '[JT2] Все структуры': 's = "Hello"\nx = 10\ny = 20\ntotal = x + y\nprintln(length(s))\nprintln(uppercase(s))\nprintln(x)\nprintln(y)\nprintln(total)\nprintln(total * 2)',
        '[JT3] Всё вместе': 'function double_(x)\n    return x * 2\nend\ns = 0\nfor i in 1:5\n    s = s + i\nend\nprintln(s)\nprintln(double_(s))\nfor i in 1:3\n    println(i)\nend',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _julia_to_python(src)
        try:
            return _run_python(py)
        except Exception as e:
            return f"// Julia: {type(e).__name__}: {e}"

    def generate_code(self, output):
        return julia_generate(output)


TRANSPILERS[("julia", "python")] = _julia_to_python
