# langs/r_lang.py
"""R — обычный язык. Транспайлер R → Python."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS



def _r_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\bTRUE\b", "True", e)
    e = re.sub(r"\bFALSE\b", "False", e)
    e = re.sub(r"\bNULL\b", "None", e)
    e = re.sub(r"\bNA\b", "None", e)
    e = re.sub(r"\blength\(([^)]+)\)", r"len(\1)", e)
    e = re.sub(r"\bnchar\(([^)]+)\)", r"len(\1)", e)
    e = re.sub(r"\bas\.character\(([^)]+)\)", r"str(\1)", e)
    e = re.sub(r"\bas\.integer\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"\bas\.numeric\(([^)]+)\)", r"float(\1)", e)
    e = re.sub(r"\btoupper\(([^)]+)\)", r"(\1).upper()", e)
    e = re.sub(r"\btolower\(([^)]+)\)", r"(\1).lower()", e)
    e = re.sub(r"\btrimws\(([^)]+)\)", r"(\1).strip()", e)
    e = re.sub(r"\bsubstr\(([^,]+),\s*([^,]+),\s*([^)]+)\)",
               r"\1[(\2)-1:(\3)]", e)
    e = re.sub(r"\bgsub\(([^,]+),\s*([^,]+),\s*([^)]+)\)",
               r"\3.replace(\1, \2)", e)
    e = re.sub(r"\bstrsplit\(([^,]+),\s*([^)]+)\)", r"\1.split(\2)", e)
    e = re.sub(r"\bpaste0\(([^)]+)\)", r"''.join(map(str, [\1]))", e)
    e = re.sub(r"\bsort\(([^)]+)\)", r"sorted(\1)", e)
    e = re.sub(r"\brev\(([^)]+)\)", r"list(reversed(\1))", e)
    e = re.sub(r"\bunique\(([^)]+)\)", r"list(dict.fromkeys(\1))", e)
    e = re.sub(r"\bsum\(([^)]+)\)", r"sum(\1)", e)
    e = re.sub(r"\bmean\(([^)]+)\)", r"(sum(\1) / len(\1))", e)
    e = e.replace("<-", "=")
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
            r"(\b(?:if|for|while)\b[^{}\n]*?)\s*\{\s*([^{}\n]+?)\s*\}",
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


# --- normal patch: r apply ---
def _convert_r_apply(src):
    # lapply(x, f) → [f(_i) for _i in x]
    src = re.sub(r"lapply\((\w+),\s*(\w+)\)",
                 r"[\2(_i) for _i in \1]", src)
    src = re.sub(r"sapply\((\w+),\s*(\w+)\)",
                 r"[\2(_i) for _i in \1]", src)
    return src


def _r_to_python(src):
    src = _convert_r_apply(src)
    lines = src.split("\n")
    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line == "}":
            ind = max(0, ind - 1)
            continue

        m = re.match(r"for\s*\(\s*(\w+)\s+in\s+(\d+):(\d+)\s*\)\s*\{?$", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue

        m = re.match(r"for\s*\(\s*(\w+)\s+in\s+(.+?)\s*\)\s*\{?$", line)
        if m:
            emit(f"for {m.group(1)} in {_r_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"while {_r_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"if {_r_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"\}?\s*else\s+if\s*\((.+?)\)\s*\{?$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_r_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        if re.match(r"\}?\s*else\s*\{?$", line):
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        m = re.match(r"print\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_r_expr_to_py(m.group(1))})")
            continue

        m = re.match(r"cat\s*\((.*)\)\s*$", line)
        if m:
            args = _split_top_level(m.group(1), ",")
            emit(f'print("".join(str(a) for a in [{", ".join(a.strip() for a in args)}]))')
            continue

        m = re.match(r"(\w+)\s*<-\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_r_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_r_expr_to_py(m.group(2))}")
            continue

        continue

    return "\n".join(out) + "\n"



def r_print(text):
    if not text:
        return 'print("")\n'
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'print({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


def r_gen_numbers():
    return 'for (i in 1:10) {\n    print(i)\n}\n'


def r_gen_squares():
    return 'for (i in 1:10) {\n    print(i * i)\n}\n'


def r_gen_cubes():
    return 'for (i in 1:10) {\n    print(i * i * i)\n}\n'


def r_gen_table7():
    return 'for (i in 1:10) {\n    print(i * 7)\n}\n'


def r_gen_factorial():
    return ('r <- 1\n'
            'for (i in 1:5) {\n'
            '    r <- r * i\n'
            '}\n'
            'print(r)\n')


def r_gen_fib():
    return ('a <- 0\n'
            'b <- 1\n'
            'for (i in 1:10) {\n'
            '    print(a)\n'
            '    c <- a + b\n'
            '    a <- b\n'
            '    b <- c\n'
            '}\n')


def r_gen_50():
    parts = []
    for k in range(1, 11):
        parts.append(f'print("=== {k} x {k} ===")')
        for i in range(1, 6):
            parts.append(f"print({i} * {k})")
    return "\n".join(parts) + "\n"


def r_gen_200():
    parts = []
    for k in range(2, 12):
        parts.append(f'print("=== Таблица {k} ===")')
        for i in range(1, 11):
            parts.append(f"print({i} * {k})")
    return "\n".join(parts) + "\n"


def r_generate(output):
    if not output:
        return 'print("")\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'print({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"



class RlangLang(Language):
    name = "r_lang"
    title = "R"
    category = "О"
    ext = ".r"
    keywords = ["function", "if", "else", "for", "while", "return", "TRUE", "FALSE", "NULL", "print", "cat"]
    comment_regex = r"#[^\n]*"

    templates = {
        '[E1] Hello, World': 'print("Hello, World!")',
        '[E2] Арифметика': 'a <- 17\nb <- 5\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)\nprint(a % b)',
        '[E3] Строки': 's <- "Programming"\nprint(length(s))\nprint(toupper(s))\nprint(tolower(s))\nprint(substr(s, 1, 4))',
        '[E4] Условие': 'x <- 7\nif (x % 2 == 0) {\n    print("чёт")\n} else {\n    print("нечёт")\n}',
        '[E5] Квадраты': 'x <- 7\nprint(x * x)\nprint(x * x * x)\nprint(x + 100)',
        '[M1] Цикл for': 'for (i in 1:5) {\n    print(i)\n}',
        '[M2] Цикл while (факториал)': 'n <- 5\nfact <- 1\nwhile (n > 1) {\n    fact <- fact * n\n    n <- n - 1\n}\nprint(fact)',
        '[M3] Факториал (for)': 'fact <- 1\nfor (i in 1:5) {\n    fact <- fact * i\n}\nprint(fact)',
        '[M4] Sum и prod': 's <- 0\np <- 1\nfor (i in 1:6) {\n    s <- s + i\n    p <- p * i\n}\nprint(s)\nprint(p)',
        '[M5] Сумма 1..10': 's <- 0\nfor (i in 1:10) {\n    s <- s + i\n}\nprint(s)',
        '[H1] Fibonacci': 'a <- 0\nb <- 1\nfor (i in 1:15) {\n    print(a)\n    t <- a + b\n    a <- b\n    b <- t\n}',
        '[H2] GCD (inline)': 'a <- 100\nb <- 25\nwhile (b != 0) {\n    t <- b\n    b <- a % b\n    a <- t\n}\nprint(a)',
        '[H3] Сумма квадратов': 's <- 0\nfor (i in 1:10) {\n    s <- s + i * i\n}\nprint(s)',
        '[H4] Вложенные циклы': 'for (i in 1:3) {\n    for (j in 1:3) {\n        print(i * j)\n    }\n}',
        '[H5] Вложенная арифметика': 'a <- 3\nb <- 4\nc <- 5\nr1 <- (a + b) * c\nr2 <- a * b + c\nr3 <- a * (b + c)\nprint(r1)\nprint(r2)\nprint(r3)',
        '[W1] Таблица ×7': 'k <- 7\nfor (i in 1:10) {\n    print(i * k)\n}',
        '[W2] Квадраты и кубы': 'for (i in 1:10) {\n    print(i * i)\n}\nfor (i in 1:10) {\n    print(i * i * i)\n}',
        '[W3] Простые числа до 30': 'n <- 2\nwhile (n <= 30) {\n    prime <- TRUE\n    d <- 2\n    while (d < n) {\n        if (n % d == 0) {\n            prime <- FALSE\n        }\n        d <- d + 1\n    }\n    if (prime) {\n        print(n)\n    }\n    n <- n + 1\n}',
        '[W4] Сумма 1..100': 's <- 0\nfor (i in 1:100) {\n    s <- s + i\n}\nprint(s)',
        '[W5] Таблица 10×10': 'for (i in 1:10) {\n    for (j in 1:10) {\n        print(i * j)\n    }\n}',
        '[T1] Базовые конструкции': 'a <- 10\nb <- 3\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)\nfor (i in 1:3) {\n    print(i)\n}',
        '[T2] Все структуры': 's <- "Hello"\nx <- 10\ny <- 20\ntotal <- x + y\nprint(length(s))\nprint(toupper(s))\nprint(x)\nprint(y)\nprint(total)\nprint(total * 2)',
        '[T3] Всё вместе': 'n <- 5\ns <- 0\nfor (i in 1:5) {\n    s <- s + i\n}\nd <- s * 2\nlabel <- "Result"\nprint(s)\nprint(d)\nprint(length(label))\nfor (i in 1:3) {\n    print(i)\n}',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _r_to_python(src)
        try:
            return _run_python(py)
        except Exception as e:
            return f"// R: {type(e).__name__}: {e}"

    def generate_code(self, output):
        return r_generate(output)


TRANSPILERS[("r_lang", "python")] = _r_to_python
