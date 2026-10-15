# langs/swift.py
"""Swift — обычный язык. Классы, struct, Optionals, коллекции."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS





def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    SWIFT_MARKERS = (
        r"\.[a-zA-Z]+\(",           # .uppercased() .hasPrefix() .trimmingCharacters()
        r"\.count\b",            # .count — свойство, не метод
        r"\blet\s+",             # let x = ...
        r"\bvar\s+",             # var x = ...
        r"\bfunc\s+",            # func name()
        r"\bstruct\s+",          # struct Foo
        r"\binit\s*\(",          # init()
        r"\bguard\s+",
        r"\bself\.",             # self.x
    )
    for pat in SWIFT_MARKERS:
        if re.search(pat, src):
            return False
    if "{" not in src and "}" not in src:
        if re.search(r"^\s*print\s*\(", src, re.M):
            return True
    return False

def _swift_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnil\b", "None", e)
    e = re.sub(r"\bself\.", "self.", e)
    e = re.sub(r'("[^"]*"|\w+)\.count\b', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.isEmpty\b', r"(not \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.uppercased\(\)', r"\1.upper()", e)
    e = re.sub(r'("[^"]*"|\w+)\.lowercased\(\)', r"\1.lower()", e)
    e = re.sub(r'("[^"]*"|\w+)\.trimmingCharacters\([^)]*\)', r"\1.strip()", e)
    e = re.sub(r'("[^"]*"|\w+)\.hasPrefix\(([^)]+)\)', r"\1.startswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.hasSuffix\(([^)]+)\)', r"\1.endswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.contains\(([^)]+)\)', r"(\2 in \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.append\(([^)]+)\)', r"\1.append(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.remove\(at:\s*([^)]+)\)', r"\1.pop(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.split\(separator:\s*([^)]+)\)', r"\1.split(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.joined\(separator:\s*([^)]+)\)', r"\2.join(\1)", e)
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


def _expand_oneliners(src):
    for _ in range(5):
        new = re.sub(
            r"(\b(?:if|for|while)\b[^{}\n]*?)\s*\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new == src:
            break
        src = new
    return src


def _extract_swift_types(src):
    out = []
    lines = src.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # class Name: Base { ... }
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
            body_py, has_init = _swift_parse_body(body, cls_name)
            out.extend(body_py)
            if not has_init:
                out.append("    def __init__(self):")
                out.append("        pass")
            i += 1
            continue

        # struct Name { ... }
        m = re.match(r"struct\s+(\w+)\s*\{", line)
        if m:
            cls_name = m.group(1)
            out.append(f"class {cls_name}:")
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
            body_py, has_init = _swift_parse_body(body, cls_name)
            out.extend(body_py)
            if not has_init:
                out.append("    def __init__(self):")
                out.append("        pass")
            i += 1
            continue

        out.append(lines[i])
        i += 1

    return "\n".join(out)


def _swift_parse_body(body, cls_name):
    out = []
    has_init = False
    k = 0
    while k < len(body):
        bl = body[k].strip()

        # var/let name: Type
        fm = re.match(r"(?:var|let)\s+(\w+)(?:\s*:\s*[\w\[\]<>]+)?\s*(?:=\s*(.+?))?\s*$", bl)
        if fm and "(" not in bl and "func" not in bl:
            k += 1
            continue

        # init(args) {...}
        im = re.match(r"(?:init|convenience\s+init)\s*\(([^)]*)\)\s*\{?", bl)
        if im:
            args = ", ".join(
                a.strip().split(":")[0].strip()
                for a in im.group(1).split(",") if a.strip())
            out.append(f"    def __init__(self{', ' + args if args else ''}):")
            has_init = True
            depth2 = bl.count("{") - bl.count("}")
            k += 1
            while k < len(body) and depth2 > 0:
                inner = body[k]
                depth2 += inner.count("{") - inner.count("}")
                if depth2 <= 0:
                    break
                py = _swift_body_line(inner)
                if py:
                    out.append("        " + py)
                k += 1
            k += 1
            continue

        # func name(args) {...}
        mm = re.match(r"func\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*[\w\[\]<>?]+)?\s*\{?", bl)
        if mm and mm.group(1) != "main":
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
                py = _swift_body_line(inner)
                if py:
                    out.append("        " + py)
                k += 1
            k += 1
            continue

        k += 1
    return out, has_init


def _swift_body_line(line):
    s = line.strip()
    if not s or s in ("{", "}"):
        return None
    m = re.match(r"return\s*(.*?)\s*$", s)
    if m:
        return f"return {_swift_expr_to_py(m.group(1))}"
    m = re.match(r"print\s*\((.*)\)\s*$", s)
    if m:
        return f"print({_swift_expr_to_py(m.group(1))})"
    m = re.match(r"self\.(\w+)\s*=\s*(.+?)\s*$", s)
    if m:
        return f"self.{m.group(1)} = {_swift_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\s*=\s*(.+?)\s*$", s)
    if m:
        return f"{m.group(1)} = {_swift_expr_to_py(m.group(2))}"
    return None


# --- normal patch: swift unwrap ---
def _swift_unwrap_and_protocols(src):
    # x! → x (non-null unwrap)
    src = re.sub(r"([A-Za-z_]\w*)!(?=[\s,;)\]}.]|$)", r"\1", src)
    # protocol Name { ... } → strip
    src = re.sub(r"protocol\s+\w+\s*\{[^{}]*\}", "", src)
    return src


def _swift_to_python(src):
    src = _swift_unwrap_and_protocols(src)
    src = _expand_oneliners(src)
    src = _extract_swift_types(src)

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

        m = re.match(r"func\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*\w+)?\s*\{?$", line)
        if m and m.group(1) != "main":
            args = ", ".join(
                a.strip().split(":")[0].strip()
                for a in m.group(2).split(",") if a.strip())
            emit(f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # for i in 1...10
        m = re.match(r"for\s+(\w+)\s+in\s+(\d+)\s*\.\.\.\s*(\d+)\s*\{?$", line)
        if m:
            emit(f"for {m.group(1)} in range({m.group(2)}, {int(m.group(3)) + 1}):")
            ind += 1
            continue
        m = re.match(r"for\s+(\w+)\s+in\s+(\d+)\s*\.\.<\s*(\d+)\s*\{?$", line)
        if m:
            emit(f"for {m.group(1)} in range({m.group(2)}, {m.group(3)}):")
            ind += 1
            continue
        m = re.match(r"for\s+(\w+)\s+in\s+(.+?)\s*\{?$", line)
        if m:
            emit(f"for {m.group(1)} in {_swift_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s+(.+?)\s*\{?$", line)
        if m:
            emit(f"while {_swift_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s+(.+?)\s*\{?$", line)
        if m:
            emit(f"if {_swift_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"else\s+if\s+(.+?)\s*\{?$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_swift_expr_to_py(m.group(1))}:")
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
                emit(f"return {_swift_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"print\s*\((.*)\)$", line)
        if m:
            emit(f"print({_swift_expr_to_py(m.group(1))})")
            continue

        m = re.match(r"(?:let|var)\s+(\w+)(?:\s*:\s*[\w\[\]<>?]+)?\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_swift_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_swift_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_swift_expr_to_py(m.group(2))}")
            continue

        continue

    return "\n".join(out) + "\n"


def swift_print(text):
    if not text:
        return ""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'print({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


def swift_gen_numbers():
    return "for i in 1...10 {\n    print(i)\n}\n"


def swift_gen_squares():
    return "for i in 1...10 {\n    print(i * i)\n}\n"


def swift_gen_cubes():
    return "for i in 1...10 {\n    print(i * i * i)\n}\n"


def swift_gen_table7():
    return "for i in 1...10 {\n    print(i * 7)\n}\n"


def swift_gen_factorial():
    return ("var r = 1\n"
            "for i in 1...5 {\n"
            "    r = r * i\n"
            "}\n"
            "print(r)\n")


def swift_gen_fib():
    return ("var a = 0\n"
            "var b = 1\n"
            "for i in 1...10 {\n"
            "    print(a)\n"
            "    let c = a + b\n"
            "    a = b\n"
            "    b = c\n"
            "}\n")


def swift_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f'print("=== {k} x {k} ===")')
        for i in range(1, 6):
            parts.append(f"print({i} * {k})")
    return "\n".join(parts) + "\n"


def swift_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f'print("=== Таблица {k} ===")')
        for i in range(1, 11):
            parts.append(f"print({i} * {k})")
    return "\n".join(parts) + "\n"


def swift_generate(output):
    if not output:
        return 'print("")\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'print({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


class SwiftLang(Language):
    name = "swift"
    title = "Swift"
    category = "О"
    ext = ".swift"
    keywords = ["func", "let", "var", "if", "else", "for", "while",
                "return", "true", "false", "nil", "print", "class",
                "struct", "enum", "init", "self"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': 'print("Hello, World!")',
        '[E2] Арифметика': 'let a = 17\nlet b = 5\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)\nprint(a % b)',
        '[E3] Строки': 'let s = "Programming"\nprint(s.count)\nprint(s.uppercased())\nprint(s.lowercased())',
        '[E4] Условие': 'let x = 7\nif x % 2 == 0 {\n    print("чёт")\n} else {\n    print("нечёт")\n}',
        '[E5] Квадраты': 'let x = 7\nprint(x * x)\nprint(x * x * x)\nprint(x + 100)',
        '[M1] Цикл for': 'for i in 1...5 {\n    print(i)\n}',
        '[M2] Цикл while (факториал)': 'var n = 5\nvar fact = 1\nwhile n > 1 {\n    fact = fact * n\n    n = n - 1\n}\nprint(fact)',
        '[M3] Факториал (for)': 'var fact = 1\nfor i in 1...5 {\n    fact = fact * i\n}\nprint(fact)',
        '[M4] Sum и prod': 'var sum = 0\nvar prod = 1\nfor i in 1...6 {\n    sum = sum + i\n    prod = prod * i\n}\nprint(sum)\nprint(prod)',
        '[M5] Сумма 1..10': 'var sum = 0\nfor i in 1...10 {\n    sum = sum + i\n}\nprint(sum)',
        '[H1] Fibonacci': 'var a = 0\nvar b = 1\nfor i in 1...15 {\n    print(a)\n    let t = a + b\n    a = b\n    b = t\n}',
        '[H2] GCD (inline)': 'var a = 100\nvar b = 25\nwhile b != 0 {\n    let t = b\n    b = a % b\n    a = t\n}\nprint(a)',
        '[H3] Сумма квадратов': 'var sum = 0\nfor i in 1...10 {\n    sum = sum + i * i\n}\nprint(sum)',
        '[H4] Вложенные циклы': 'for i in 1...3 {\n    for j in 1...3 {\n        print(i * j)\n    }\n}',
        '[H5] Вложенная арифметика': 'let a = 3\nlet b = 4\nlet c = 5\nlet r1 = (a + b) * c\nlet r2 = a * b + c\nlet r3 = a * (b + c)\nprint(r1)\nprint(r2)\nprint(r3)',
        '[W1] Таблица ×7': 'let k = 7\nfor i in 1...10 {\n    print(i * k)\n}',
        '[W2] Квадраты и кубы': 'for i in 1...10 {\n    print(i * i)\n}\nfor i in 1...10 {\n    print(i * i * i)\n}',
        '[W3] Простые числа до 30': 'var n = 2\nwhile n <= 30 {\n    var prime = true\n    var d = 2\n    while d < n {\n        if n % d == 0 {\n            prime = false\n        }\n        d = d + 1\n    }\n    if prime {\n        print(n)\n    }\n    n = n + 1\n}',
        '[W4] Сумма 1..100': 'var sum = 0\nfor i in 1...100 {\n    sum = sum + i\n}\nprint(sum)',
        '[W5] Таблица 10×10': 'for i in 1...10 {\n    for j in 1...10 {\n        print(i * j)\n    }\n}',
        '[T1] Базовые конструкции': 'let a = 10\nlet b = 3\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)\nfor i in 1...3 {\n    print(i)\n}',
        '[T2] Все структуры': 'let s = "Hello"\nlet x = 10\nlet y = 20\nlet sum = x + y\nprint(s.count)\nprint(s.uppercased())\nprint(x)\nprint(y)\nprint(sum)\nprint(sum * 2)',
        '[T3] Всё вместе': 'var n = 5\nvar s = 0\nfor i in 1...5 {\n    s = s + i\n}\nlet d = s * 2\nlet label = "Result"\nprint(s)\nprint(d)\nprint(label.count)\nfor i in 1...3 {\n    print(i)\n}',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _swift_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<swift>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Swift: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        return swift_generate(output)


TRANSPILERS[("swift", "python")] = _swift_to_python
