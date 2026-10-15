# langs/kotlin.py
"""Kotlin — обычный язык. Классы, data class, when, лямбды."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS


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


def _expand_oneliners(src):
    for _ in range(5):
        new = re.sub(
            r"(\b(?:if|for|while)\b[^{}\n]*?)\s*\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new == src:
            break
        src = new
    # Однострочные функции: fun name(args) { body }
    for _ in range(5):
        new = re.sub(
            r"(fun\s+\w+\s*\([^)]*\)[^{}\n]*?)\s*\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new == src:
            break
        src = new
    return src


def _kotlin_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnull\b", "None", e)
    e = re.sub(r"\bthis\.", "self.", e)
    e = re.sub(r"(\w+)\.length\b", r"len(\1)", e)
    e = re.sub(r"(\w+)\.size\b", r"len(\1)", e)
    e = re.sub(r"(\w+)\.toString\(\)", r"str(\1)", e)
    e = re.sub(r"(\w+)\.toUpperCase\(\)", r"\1.upper()", e)
    e = re.sub(r"(\w+)\.toLowerCase\(\)", r"\1.lower()", e)
    e = re.sub(r"(\w+)\.trim\(\)", r"\1.strip()", e)
    e = re.sub(r"(\w+)\.add\(([^)]+)\)", r"\1.append(\2)", e)
    e = re.sub(r"(\w+)\.contains\(([^)]+)\)", r"(\2 in \1)", e)
    return e


def _extract_classes(src):
    out = []
    lines = src.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # data class Name(val x: T, val y: T)
        m = re.match(
            r"(?:data\s+)?class\s+(\w+)\s*\(([^)]*)\)", line)
        if m:
            cls_name = m.group(1)
            args = []
            for a in m.group(2).split(","):
                a = a.strip()
                if not a:
                    continue
                am = re.match(r"(?:val|var)\s+(\w+)\s*:\s*\w+", a)
                if am:
                    args.append(am.group(1))
            out.append(f"class {cls_name}:")
            args_str = ", ".join(["self"] + args)
            out.append(f"    def __init__({args_str}):")
            for a in args:
                out.append(f"        self.{a} = {a}")
            i += 1
            # Пропускаем тело `{ ... }`, если есть
            depth = 1 if "{" in line else 0
            if depth:
                while i < n:
                    l = lines[i]
                    depth += l.count("{") - l.count("}")
                    if depth <= 0:
                        i += 1
                        break
                    i += 1
            continue

        # class Name { ... }
        m = re.match(r"class\s+(\w+)(?:\s*:\s*(\w+))?\s*\{", line)
        if m:
            cls_name = m.group(1)
            base = m.group(2)
            out.append(f"class {cls_name}({base}):" if base else f"class {cls_name}:")
            depth = 1
            body = []
            i += 1
            while i < n and depth > 0:
                l = lines[i]
                depth += l.count("{") - l.count("}")
                if depth <= 0:
                    if l.strip() and l.strip() != "}":
                        body.append(l)
                    break
                body.append(l)
                i += 1

            has_ctor = False
            k = 0
            while k < len(body):
                bl = body[k].strip()
                # конструктор
                ctor = re.match(rf"(?:constructor\s*\()?([^)]*)\)\s*\{{?", bl)
                if re.match(rf"{re.escape(cls_name)}\s*\(", bl):
                    cm = re.match(rf"{re.escape(cls_name)}\s*\(([^)]*)\)\s*\{{?", bl)
                    args = ", ".join(
                        a.strip().split(":")[0].strip().lstrip("val ").lstrip("var ")
                        for a in cm.group(1).split(",") if a.strip())
                    out.append(f"    def __init__(self{', ' + args if args else ''}):")
                    has_ctor = True
                    depth2 = bl.count("{") - bl.count("}")
                    k += 1
                    while k < len(body) and depth2 > 0:
                        inner = body[k]
                        depth2 += inner.count("{") - inner.count("}")
                        if depth2 <= 0:
                            break
                        py = _kotlin_body_line(inner)
                        if py:
                            out.append("        " + py)
                        k += 1
                    k += 1
                    continue
                # метод: fun name(args) {...}
                mm = re.match(r"fun\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*\w+)?\s*\{?", bl)
                if mm:
                    name = mm.group(1)
                    args = ", ".join(
                        a.strip().split(":")[0].strip()
                        for a in mm.group(2).split(",") if a.strip())
                    out.append(f"    def {name}(self{', ' + args if args else ''}):")
                    depth2 = bl.count("{") - bl.count("}")
                    k += 1
                    while k < len(body) and depth2 > 0:
                        inner = body[k]
                        depth2 += inner.count("{") - inner.count("}")
                        if depth2 <= 0:
                            break
                        py = _kotlin_body_line(inner)
                        if py:
                            out.append("        " + py)
                        k += 1
                    k += 1
                    continue
                k += 1

            if not has_ctor:
                out.append("    def __init__(self):")
                out.append("        pass")
            i += 1
            continue

        out.append(lines[i])
        i += 1

    return "\n".join(out)


def _kotlin_body_line(line):
    s = line.strip()
    if not s or s in ("{", "}"):
        return None
    m = re.match(r"return\s*(.*?)$", s)
    if m:
        return f"return {_kotlin_expr_to_py(m.group(1))}"
    m = re.match(r"println\s*\((.*)\)$", s)
    if m:
        return f"print({_kotlin_expr_to_py(m.group(1))})"
    m = re.match(r"this\.(\w+)\s*=\s*(.+?)$", s)
    if m:
        return f"self.{m.group(1)} = {_kotlin_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\s*=\s*(.+?)$", s)
    if m:
        return f"{m.group(1)} = {_kotlin_expr_to_py(m.group(2))}"
    return None


# --- normal patch: kotlin extension ---
def _expand_kotlin_extension(src):
    # fun Type.name(args) → fun name(self, args)
    def repl(m):
        typ = m.group(1)
        name = m.group(2)
        args = m.group(3)
        new_args = f"self: {typ}, {args}" if args.strip() else f"self: {typ}"
        return f"fun {name}({new_args})"
    return re.sub(
        r"fun\s+([A-Z]\w*)\.(\w+)\s*\(([^)]*)\)",
        repl, src)


def _kotlin_to_python(src):
    src = _expand_kotlin_extension(src)
    src = _expand_oneliners(src)
    src = _extract_classes(src)

    lines = []
    for line in src.split("\n"):
        for ch in _split_top_level(line, ";"):
            ch = ch.strip()
            if ch:
                lines.append(ch)

    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    for line in lines:
        if not line or line.startswith("//"):
            continue
        if line == "}" or line == "};":
            ind = max(0, ind - 1)
            continue
        if line == "{":
            continue
        if re.match(r"fun\s+main\s*\(", line):
            continue

        m = re.match(r"fun\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*\w+)?\s*\{?$", line)
        if m and m.group(1) != "main":
            args = ", ".join(
                a.strip().split(":")[0].strip()
                for a in m.group(2).split(",") if a.strip())
            emit(f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # for (i in 1..10)
        m = re.match(r"for\s*\(\s*(\w+)\s+in\s+(\d+)\s*\.\.\s*(\d+)\s*\)\s*\{?$", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue
        m = re.match(r"for\s*\(\s*(\w+)\s+in\s+(\d+)\s+until\s+(\d+)\s*\)\s*\{?$", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {b}):")
            ind += 1
            continue
        m = re.match(r"for\s*\(\s*(\w+)\s+in\s+(.+?)\s*\)\s*\{?$", line)
        if m:
            emit(f"for {m.group(1)} in {_kotlin_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"while {_kotlin_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"if {_kotlin_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"else\s+if\s*\((.+?)\)\s*\{?$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_kotlin_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        if re.match(r"else\s*\{?$", line):
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        m = re.match(r"return\s*(.*?)$", line)
        if m:
            val = m.group(1).strip()
            if val:
                emit(f"return {_kotlin_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"println\s*\((.*)\)$", line)
        if m:
            emit(f"print({_kotlin_expr_to_py(m.group(1))})")
            continue
        m = re.match(r"print\s*\((.*)\)$", line)
        if m:
            emit(f"print({_kotlin_expr_to_py(m.group(1))}, end='')")
            continue

        m = re.match(r"(?:val|var)\s+(\w+)\s*(?::\s*\w+(?:<[^>]+>)?)?\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_kotlin_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_kotlin_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_kotlin_expr_to_py(m.group(2))}")
            continue

        continue

    return "\n".join(out) + "\n"


def kotlin_print(text):
    if not text:
        return "fun main() {\n}\n"
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    body = "\n".join(
        f'    println({json.dumps(ln, ensure_ascii=False)})' for ln in lines)
    return f"fun main() {{\n{body}\n}}\n"


def kotlin_gen_numbers():
    return "fun main() {\n    for (i in 1..10) {\n        println(i)\n    }\n}\n"


def kotlin_gen_squares():
    return "fun main() {\n    for (i in 1..10) {\n        println(i * i)\n    }\n}\n"


def kotlin_gen_cubes():
    return "fun main() {\n    for (i in 1..10) {\n        println(i * i * i)\n    }\n}\n"


def kotlin_gen_table7():
    return "fun main() {\n    for (i in 1..10) {\n        println(i * 7)\n    }\n}\n"


def kotlin_gen_factorial():
    return ("fun main() {\n"
            "    var r = 1\n"
            "    for (i in 1..5) {\n"
            "        r = r * i\n"
            "    }\n"
            "    println(r)\n"
            "}\n")


def kotlin_gen_fib():
    return ("fun main() {\n"
            "    var a = 0\n"
            "    var b = 1\n"
            "    for (i in 1..10) {\n"
            "        println(a)\n"
            "        var c = a + b\n"
            "        a = b\n"
            "        b = c\n"
            "    }\n"
            "}\n")


def kotlin_gen_50():
    parts = ["fun main() {"]
    for k in range(1, 6):
        parts.append(f'    println("=== {k} x {k} ===")')
        for i in range(1, 6):
            parts.append(f"    println({i} * {k})")
    parts.append("}")
    return "\n".join(parts) + "\n"


def kotlin_gen_200():
    parts = ["fun main() {"]
    for k in range(2, 8):
        parts.append(f'    println("=== Таблица {k} ===")')
        for i in range(1, 11):
            parts.append(f"    println({i} * {k})")
    parts.append("}")
    return "\n".join(parts) + "\n"


def kotlin_generate(output):
    if not output:
        return "fun main() {\n}\n"
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    body = "\n".join(
        f'    println({json.dumps(ln, ensure_ascii=False)})' for ln in lines)
    return f"fun main() {{\n{body}\n}}\n"


class KotlinLang(Language):
    name = "kotlin"
    title = "Kotlin"
    category = "О"
    ext = ".kt"
    keywords = ["fun", "val", "var", "if", "else", "for", "while",
                "return", "true", "false", "null", "println", "print",
                "class", "data", "when"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': 'fun main() {\n    println("Hello, World!")\n}',
        '[E2] Арифметика': 'fun main() {\n    val a = 17\n    val b = 5\n    println(a + b)\n    println(a - b)\n    println(a * b)\n    println(a / b)\n    println(a % b)\n}',
        '[E3] Строки': 'fun main() {\n    val s = "Programming"\n    println(s.length)\n    println(s.toUpperCase())\n    println(s.toLowerCase())\n}',
        '[E4] Условие': 'fun main() {\n    val x = 7\n    if (x % 2 == 0) {\n        println("чёт")\n    } else {\n        println("нечёт")\n    }\n}',
        '[E5] Функция square': 'fun square(x: Int): Int {\n    return x * x\n}\n\nfun main() {\n    println(square(7))\n    println(square(12))\n    println(square(25))\n}',
        '[M1] Цикл for': 'fun main() {\n    for (i in 1..5) {\n        println(i)\n    }\n}',
        '[M2] Цикл while (факториал)': 'fun main() {\n    var n = 5\n    var fact = 1\n    while (n > 1) {\n        fact = fact * n\n        n = n - 1\n    }\n    println(fact)\n}',
        '[M3] Рекурсия': 'fun fact(n: Int): Int {\n    if (n <= 1) {\n        return 1\n    }\n    return n * fact(n - 1)\n}\n\nfun main() {\n    println(fact(5))\n    println(fact(7))\n    println(fact(10))\n}',
        '[M4] Две функции': 'fun add(a: Int, b: Int): Int {\n    return a + b\n}\n\nfun mul(a: Int, b: Int): Int {\n    return a * b\n}\n\nfun main() {\n    println(add(3, 4))\n    println(mul(3, 4))\n    println(add(mul(2, 5), 7))\n}',
        '[M5] Сумма 1..10': 'fun main() {\n    var sum = 0\n    for (i in 1..10) {\n        sum = sum + i\n    }\n    println(sum)\n}',
        '[H1] GCD': 'fun gcd(a: Int, b: Int): Int {\n    var x = a\n    var y = b\n    while (y != 0) {\n        val t = y\n        y = x % y\n        x = t\n    }\n    return x\n}\n\nfun main() {\n    println(gcd(12, 8))\n    println(gcd(100, 25))\n    println(gcd(17, 5))\n}',
        '[H2] Fibonacci (итеративный)': 'fun main() {\n    var a = 0\n    var b = 1\n    for (i in 1..15) {\n        println(a)\n        val t = a + b\n        a = b\n        b = t\n    }\n}',
        '[H3] Сумма квадратов': 'fun main() {\n    var sum = 0\n    for (i in 1..10) {\n        sum = sum + i * i\n    }\n    println(sum)\n}',
        '[H4] Вложенные циклы': 'fun main() {\n    for (i in 1..3) {\n        for (j in 1..3) {\n            println(i * j)\n        }\n    }\n}',
        '[H5] Три функции': 'fun add(a: Int, b: Int): Int {\n    return a + b\n}\n\nfun sq(x: Int): Int {\n    return x * x\n}\n\nfun sumSq5(): Int {\n    var s = 0\n    for (i in 1..5) {\n        s = add(s, sq(i))\n    }\n    return s\n}\n\nfun main() {\n    println(sumSq5())\n}',
        '[W1] Таблица ×7': 'fun main() {\n    val k = 7\n    for (i in 1..10) {\n        println(i * k)\n    }\n}',
        '[W2] Квадраты и кубы': 'fun main() {\n    for (i in 1..10) {\n        println(i * i)\n    }\n    for (i in 1..10) {\n        println(i * i * i)\n    }\n}',
        '[W3] Простые числа до 30': 'fun main() {\n    var n = 2\n    while (n <= 30) {\n        var prime = true\n        var d = 2\n        while (d < n) {\n            if (n % d == 0) {\n                prime = false\n            }\n            d = d + 1\n        }\n        if (prime) {\n            println(n)\n        }\n        n = n + 1\n    }\n}',
        '[W4] Сумма 1..100': 'fun main() {\n    var sum = 0\n    for (i in 1..100) {\n        sum = sum + i\n    }\n    println(sum)\n}',
        '[W5] Таблица 10×10': 'fun main() {\n    for (i in 1..10) {\n        for (j in 1..10) {\n            println(i * j)\n        }\n    }\n}',
        '[T1] Базовые конструкции': 'fun main() {\n    val a = 10\n    val b = 3\n    println(a + b)\n    println(a - b)\n    println(a * b)\n    println(a / b)\n    for (i in 1..3) {\n        println(i)\n    }\n}',
        '[T2] Все структуры': 'fun main() {\n    val s = "Hello"\n    val x = 10\n    val y = 20\n    val sum = x + y\n    println(s.length)\n    println(s.toUpperCase())\n    println(x)\n    println(y)\n    println(sum)\n    println(sum * 2)\n}',
        '[T3] Всё вместе': 'fun sumTo5(): Int {\n    var s = 0\n    for (i in 1..5) {\n        s = s + i\n    }\n    return s\n}\n\nfun doubleIt(x: Int): Int {\n    return x * 2\n}\n\nfun main() {\n    val s = sumTo5()\n    val d = doubleIt(s)\n    val label = "Result"\n    println(s)\n    println(d)\n    println(label.length)\n    for (i in 1..3) {\n        println(i)\n    }\n}',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        py = _kotlin_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<kotlin>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Kotlin: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        return kotlin_generate(output)


TRANSPILERS[("kotlin", "python")] = _kotlin_to_python
