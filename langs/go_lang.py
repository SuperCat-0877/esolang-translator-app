# langs/go_lang.py
"""Go — обычный язык. Транспайлер Go → Python со slice/map/struct."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS
from core.standard_templates import std_go



# --- normal patch: go types ---
def _strip_go_types(src):
    # chan T → list
    src = re.sub(r"\bchan\s+\w+", "list", src)
    # interface{} → object
    src = re.sub(r"\binterface\s*\{\s*\}", "object", src)
    return src


def _go_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnil\b", "None", e)
    e = re.sub(r"\blen\(([^)]+)\)", r"len(\1)", e)
    e = re.sub(r"make\(\[\]\w+,\s*(\d+)\)", r"([0] * \1)", e)
    e = re.sub(r"make\(map\[\w+\]\w+\)", r"{}", e)
    e = re.sub(r"strings\.Split\(([^,]+),\s*([^)]+)\)", r"\1.split(\2)", e)
    e = re.sub(r"strings\.Join\(([^,]+),\s*([^)]+)\)", r"\2.join(\1)", e)
    e = re.sub(r"strings\.Replace\(([^,]+),\s*([^,]+),\s*([^,]+),\s*[^)]+\)", r"\1.replace(\2, \3)", e)
    e = re.sub(r"strings\.HasPrefix\(([^,]+),\s*([^)]+)\)", r"\1.startswith(\2)", e)
    e = re.sub(r"strings\.HasSuffix\(([^,]+),\s*([^)]+)\)", r"\1.endswith(\2)", e)
    e = re.sub(r"strings\.Index\(([^,]+),\s*([^)]+)\)", r"\1.find(\2)", e)
    e = re.sub(r"strings\.Repeat\(([^,]+),\s*([^)]+)\)", r"\1 * \2", e)
    e = re.sub(r"strings\.TrimSpace\(([^)]+)\)", r"\1.strip()", e)
    e = re.sub(r"strings\.ToUpper\(([^)]+)\)", r"\1.upper()", e)
    e = re.sub(r"strings\.ToLower\(([^)]+)\)", r"\1.lower()", e)
    e = re.sub(r"strings\.Contains\(([^,]+),\s*([^)]+)\)", r"(\2 in \1)", e)
    e = re.sub(r"strconv\.Itoa\(([^)]+)\)", r"str(\1)", e)
    e = re.sub(r"strconv\.Atoi\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"strconv\.ParseFloat\(([^,)]+),\s*[^)]+\)", r"float(\1)", e)
    e = re.sub(r"math\.Abs\(([^)]+)\)", r"abs(\1)", e)
    e = re.sub(r"math\.Max\(([^,]+),\s*([^)]+)\)", r"max(\1, \2)", e)
    e = re.sub(r"math\.Min\(([^,]+),\s*([^)]+)\)", r"min(\1, \2)", e)
    e = re.sub(r"math\.Floor\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"math\.Ceil\(([^)]+)\)", r"__import__('math').ceil(\1)", e)
    e = re.sub(r"math\.Sqrt\(([^)]+)\)", r"((\1) ** 0.5)", e)
    e = re.sub(r"math\.Pow\(([^,]+),\s*([^)]+)\)", r"(\1 ** \2)", e)
    e = re.sub(r"sort\.Ints\(([^)]+)\)", r"\1.sort()", e)
    e = re.sub(r"sort\.Strings\(([^)]+)\)", r"\1.sort()", e)
    return e

def _split_top_level(s, sep):
    parts, buf, depth, in_str = [], [], 0, None
    for ch in s:
        if in_str:
            buf.append(ch)
            if ch == in_str:
                in_str = None
            continue
        if ch in '"\'"':
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


def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    return False


def _go_struct_to_class(src):
    """struct → простой класс-контейнер."""
    out = []
    lines = src.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        m = re.match(r"type\s+(\w+)\s+struct\s*\{", line)
        if not m:
            out.append(lines[i])
            i += 1
            continue
        name = m.group(1)
        out.append(f"class {name}:")
        out.append(f"    def __init__(self):")
        depth = line.count("{") - line.count("}")
        i += 1
        while i < n and depth > 0:
            inner = lines[i].strip()
            depth += inner.count("{") - inner.count("}")
            if depth <= 0:
                i += 1
                break
            # поле: Name Type
            fm = re.match(r"(\w+)\s+[\w\[\]\*]+", inner)
            if fm:
                out.append(f"        self.{fm.group(1)} = None")
            i += 1
    return "\n".join(out)


# --- PATCH: expand func oneliners ---
def _expand_oneliners(src):
    for _ in range(5):
        new = re.sub(
            r"(\b(?:if|else|for)\b[^{}\n]*?)\s*\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new == src:
            break
        src = new
    # func name(args){ body } → многострочно
    src = re.sub(
        r"(func\s+\w+\s*\([^)]*\)[^{\n]*?)\s*\{\s*([^{}\n]+?)\s*\}",
        r"\1 {\n\2\n}", src)
    return src
# --- /PATCH ---


def _go_to_python(src):
    src = _strip_go_types(src)
    src = _expand_oneliners(src)
    src = _go_struct_to_class(src)
    lines = src.splitlines()
    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("package ") or line.startswith("import "):
            continue
        if line.startswith("type ") and "struct" in line:
            # уже обработано выше
            continue

        if re.match(r"func\s+main\s*\(\s*\)\s*\{?\s*$", line):
            continue

        m = re.match(
            r"func\s+(\w+)\s*\(([^)]*)\)\s*(?:\w+\s*)?\{?\s*$", line)
        if m and m.group(1) != "main":
            args = ", ".join(
                a.strip().split()[-1]
                for a in m.group(2).split(",") if a.strip())
            emit(f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # for i := A; i < B; i++
        m = re.match(
            r"for\s+(\w+)\s*:=\s*(-?\d+)\s*;\s*\1\s*(<=|<)\s*(.+?)\s*;\s*"
            r"\1\+\+\s*\{?\s*$", line)
        if m:
            v, a, op, b = m.group(1), m.group(2), m.group(3), _go_expr_to_py(m.group(4))
            if op == "<=":
                b = f"({b}) + 1"
            emit(f"for {v} in range({a}, {b}):")
            ind += 1
            continue

        # for x := range coll
        m = re.match(r"for\s+(\w+)\s*:=\s*range\s+(.+?)\s*\{?\s*$", line)
        if m:
            emit(f"for {m.group(1)} in {_go_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        # for cond
        m = re.match(r"for\s+(.+?)\s*\{?\s*$", line)
        if m:
            emit(f"while {_go_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s+(.+?)\s*\{?\s*$", line)
        if m:
            emit(f"if {_go_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"(?:\}\s*)?else\s+if\s+(.+?)\s*\{?\s*$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_go_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        if re.match(r"(?:\}\s*)?else\s*\{?\s*$", line):
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        m = re.match(r"return\s*(.*?)\s*$", line)
        if m:
            val = m.group(1).strip()
            if val:
                emit(f"return {_go_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"fmt\.Println\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_go_expr_to_py(m.group(1))})")
            continue
        m = re.match(r"fmt\.Printf\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_go_expr_to_py(m.group(1))})")
            continue
        m = re.match(r"fmt\.Print\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_go_expr_to_py(m.group(1))}, end='')")
            continue

        # defer f() — заглушка
        m = re.match(r"defer\s+(.+?)\s*$", line)
        if m:
            emit(f"# defer: {m.group(1)}")
            continue

        # var x T = expr
        m = re.match(r"var\s+(\w+)\s+\w+\s*=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_go_expr_to_py(m.group(2))}")
            continue

        # var x T
        m = re.match(r"var\s+(\w+)\s+\w+\s*$", line)
        if m:
            emit(f"{m.group(1)} = None")
            continue

        # x := expr
        m = re.match(r"(\w+)\s*:=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_go_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_go_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_go_expr_to_py(m.group(2))}")
            continue

        if line == "}":
            ind = max(0, ind - 1)
            continue

        continue

    return "\n".join(out) + "\n"


def _go_to_js(src):
    from langs.python_lang import _py_to_js
    return _py_to_js(_go_to_python(src))


def _go_to_cpp(src):
    from langs.python_lang import _py_to_cpp
    return _py_to_cpp(_go_to_python(src))


def _go_to_lua(src):
    from langs.python_lang import _py_to_lua
    return _py_to_lua(_go_to_python(src))


class GoLang(Language):
    name = "go"
    title = "Go"
    category = "О"
    ext = ".go"
    keywords = [
        "package", "import", "func", "var", "const", "if", "else",
        "for", "range", "return", "go", "defer", "chan", "select",
        "type", "struct", "interface", "map", "switch", "case",
        "default", "break", "continue", "true", "false", "nil",
    ]
    types = ["int", "int64", "float64", "string", "bool", "byte", "rune", "error"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': 'package main\nimport "fmt"\nfunc main() {\n    fmt.Println("Hello, World!")\n}',
        '[E2] Арифметика': 'package main\nimport "fmt"\nfunc main() {\n    a := 17\n    b := 5\n    fmt.Println(a + b)\n    fmt.Println(a - b)\n    fmt.Println(a * b)\n    fmt.Println(a / b)\n    fmt.Println(a % b)\n}',
        '[E3] Строки': 'package main\nimport "fmt"\nfunc main() {\n    s := "Programming"\n    fmt.Println(len(s))\n    fmt.Println(s + "!")\n}',
        '[E4] Условие': 'package main\nimport "fmt"\nfunc main() {\n    x := 7\n    if x % 2 == 0 {\n        fmt.Println("чёт")\n    } else {\n        fmt.Println("нечёт")\n    }\n}',
        '[E5] Квадраты': 'package main\nimport "fmt"\nfunc main() {\n    x := 7\n    fmt.Println(x * x)\n    fmt.Println(x * x * x)\n    fmt.Println(x + 100)\n}',
        '[M1] Цикл for': 'package main\nimport "fmt"\nfunc main() {\n    for i := 1; i <= 5; i++ {\n        fmt.Println(i)\n    }\n}',
        '[M2] Цикл while (факториал)': 'package main\nimport "fmt"\nfunc main() {\n    n := 5\n    fact := 1\n    for n > 1 {\n        fact = fact * n\n        n = n - 1\n    }\n    fmt.Println(fact)\n}',
        '[M3] Факториал (for)': 'package main\nimport "fmt"\nfunc main() {\n    fact := 1\n    for i := 1; i <= 5; i++ {\n        fact = fact * i\n    }\n    fmt.Println(fact)\n}',
        '[M4] Sum и prod': 'package main\nimport "fmt"\nfunc main() {\n    sum := 0\n    prod := 1\n    for i := 1; i <= 6; i++ {\n        sum = sum + i\n        prod = prod * i\n    }\n    fmt.Println(sum)\n    fmt.Println(prod)\n}',
        '[M5] Сумма 1..10': 'package main\nimport "fmt"\nfunc main() {\n    sum := 0\n    for i := 1; i <= 10; i++ {\n        sum = sum + i\n    }\n    fmt.Println(sum)\n}',
        '[H1] Fibonacci': 'package main\nimport "fmt"\nfunc main() {\n    a := 0\n    b := 1\n    for i := 0; i < 15; i++ {\n        fmt.Println(a)\n        t := a + b\n        a = b\n        b = t\n    }\n}',
        '[H2] GCD (inline)': 'package main\nimport "fmt"\nfunc main() {\n    a := 100\n    b := 25\n    for b != 0 {\n        t := b\n        b = a % b\n        a = t\n    }\n    fmt.Println(a)\n}',
        '[H3] Сумма квадратов': 'package main\nimport "fmt"\nfunc main() {\n    sum := 0\n    for i := 1; i <= 10; i++ {\n        sum = sum + i * i\n    }\n    fmt.Println(sum)\n}',
        '[H4] Вложенные циклы': 'package main\nimport "fmt"\nfunc main() {\n    for i := 1; i <= 3; i++ {\n        for j := 1; j <= 3; j++ {\n            fmt.Println(i * j)\n        }\n    }\n}',
        '[H5] Вложенная арифметика': 'package main\nimport "fmt"\nfunc main() {\n    a := 3\n    b := 4\n    c := 5\n    r1 := (a + b) * c\n    r2 := a * b + c\n    r3 := a * (b + c)\n    fmt.Println(r1)\n    fmt.Println(r2)\n    fmt.Println(r3)\n}',
        '[W1] Таблица ×7': 'package main\nimport "fmt"\nfunc main() {\n    k := 7\n    for i := 1; i <= 10; i++ {\n        fmt.Println(i * k)\n    }\n}',
        '[W2] Квадраты и кубы': 'package main\nimport "fmt"\nfunc main() {\n    for i := 1; i <= 10; i++ {\n        fmt.Println(i * i)\n    }\n    for i := 1; i <= 10; i++ {\n        fmt.Println(i * i * i)\n    }\n}',
        '[W3] Простые числа до 30': 'package main\nimport "fmt"\nfunc main() {\n    for n := 2; n <= 30; n++ {\n        prime := true\n        for d := 2; d < n; d++ {\n            if n % d == 0 {\n                prime = false\n            }\n        }\n        if prime {\n            fmt.Println(n)\n        }\n    }\n}',
        '[W4] Сумма 1..100': 'package main\nimport "fmt"\nfunc main() {\n    sum := 0\n    for i := 1; i <= 100; i++ {\n        sum = sum + i\n    }\n    fmt.Println(sum)\n}',
        '[W5] Таблица 10×10': 'package main\nimport "fmt"\nfunc main() {\n    for i := 1; i <= 10; i++ {\n        for j := 1; j <= 10; j++ {\n            fmt.Println(i * j)\n        }\n    }\n}',
        '[T1] Базовые конструкции': 'package main\nimport "fmt"\nfunc main() {\n    a := 10\n    b := 3\n    fmt.Println(a + b)\n    fmt.Println(a - b)\n    fmt.Println(a * b)\n    fmt.Println(a / b)\n    for i := 0; i < 3; i++ {\n        fmt.Println(i)\n    }\n}',
        '[T2] Все структуры': 'package main\nimport "fmt"\nfunc main() {\n    s := "Hello"\n    x := 10\n    y := 20\n    sum := x + y\n    fmt.Println(len(s))\n    fmt.Println(s + "!")\n    fmt.Println(x)\n    fmt.Println(y)\n    fmt.Println(sum)\n    fmt.Println(sum * 2)\n}',
        '[T3] Всё вместе': 'package main\nimport "fmt"\nfunc main() {\n    n := 5\n    s := 0\n    for i := 1; i <= n; i++ {\n        s = s + i\n    }\n    d := s * 2\n    label := "Result"\n    fmt.Println(s)\n    fmt.Println(d)\n    fmt.Println(len(label))\n    for i := 0; i < 3; i++ {\n        fmt.Println(i)\n    }\n}',
    }
    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _go_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<go>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Go: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return 'package main\n\nimport "fmt"\n\nfunc main() {\n}\n'
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        body = "\n".join(
            f'    fmt.Println({json.dumps(ln, ensure_ascii=False)})'
            for ln in lines)
        return ('package main\n\nimport "fmt"\n\nfunc main() {\n'
                + body + "\n}\n")


TRANSPILERS[("go", "python")] = _go_to_python
TRANSPILERS[("go", "javascript")] = _go_to_js
TRANSPILERS[("go", "cpp")] = _go_to_cpp
TRANSPILERS[("go", "lua")] = _go_to_lua
