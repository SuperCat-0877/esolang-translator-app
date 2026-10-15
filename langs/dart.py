# langs/dart.py
"""Dart — обычный язык. Классы, async, коллекции."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS




def _dart_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnull\b", "None", e)
    e = re.sub(r"\bthis\.", "self.", e)
    e = re.sub(r'("[^"]*"|\w+)\.length\b', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.isEmpty\b', r"(not \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.isNotEmpty\b', r"(len(\1) > 0)", e)
    e = re.sub(r'("[^"]*"|\w+)\.toString\(\)', r"str(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.toUpperCase\(\)', r"\1.upper()", e)
    e = re.sub(r'("[^"]*"|\w+)\.toLowerCase\(\)', r"\1.lower()", e)
    e = re.sub(r'("[^"]*"|\w+)\.trim\(\)', r"\1.strip()", e)
    e = re.sub(r'("[^"]*"|\w+)\.contains\(([^)]+)\)',
               r"(\2 in \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.startsWith\(([^)]+)\)',
               r"\1.startswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.endsWith\(([^)]+)\)',
               r"\1.endswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.substring\(([^,)]+),\s*([^)]+)\)',
               r"\1[\2:\3]", e)
    e = re.sub(r'("[^"]*"|\w+)\.substring\(([^)]+)\)',
               r"\1[\2:]", e)
    e = re.sub(r'("[^"]*"|\w+)\.indexOf\(([^)]+)\)',
               r"\1.find(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.add\(([^)]+)\)',
               r"\1.append(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.removeAt\(([^)]+)\)',
               r"\1.pop(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.remove\(([^)]+)\)',
               r"\1.remove(\2)", e)
    e = re.sub(r"int\.parse\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"double\.parse\(([^)]+)\)", r"float(\1)", e)
    return e

def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    if ("print(" in src and "void main" not in src and "var " not in src):
        return True
    return False


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
    # main() { body } — разворачиваем тело
    for _ in range(5):
        new = re.sub(
            r"((?:void\s+)?main\s*\(\s*\))\s*\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new == src:
            break
        src = new
    return src


def _extract_dart_classes(src):
    out = []
    lines = src.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        m = re.match(r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{", line)
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
            body_py, has_init = _dart_parse_body(body, cls_name)
            out.extend(body_py)
            if not has_init:
                out.append("    def __init__(self):")
                out.append("        pass")
            i += 1
            continue

        out.append(lines[i])
        i += 1

    return "\n".join(out)


def _dart_parse_body(body, cls_name):
    out = []
    has_init = False
    k = 0
    while k < len(body):
        bl = body[k].strip()

        # поля: int x; / final x = ...; / var x;
        fm = re.match(
            r"(?:final\s+|const\s+|var\s+|int\s+|String\s+|double\s+|"
            r"bool\s+|List<\w+>\s+)?(\w+)\s*(?:=\s*(.+?))?\s*;\s*$", bl)
        if fm and "(" not in bl and "return" not in bl:
            k += 1
            continue

        # конструктор: Name(args) {...} / Name(this.x, ...) {...}
        ctor = re.match(rf"{re.escape(cls_name)}\s*\(([^)]*)\)\s*\{{?", bl)
        if ctor:
            raw_args = ctor.group(1)
            args = []
            fields = []
            for a in raw_args.split(","):
                a = a.strip()
                if not a:
                    continue
                # this.name → field
                am = re.match(r"this\.(\w+)", a)
                if am:
                    args.append(am.group(1))
                    fields.append(am.group(1))
                else:
                    args.append(a.split()[-1])
            out.append(f"    def __init__(self{', ' + ', '.join(args) if args else ''}):")
            has_init = True
            for f in fields:
                out.append(f"        self.{f} = {f}")
            depth2 = bl.count("{") - bl.count("}")
            k += 1
            while k < len(body) and depth2 > 0:
                inner = body[k]
                depth2 += inner.count("{") - inner.count("}")
                if depth2 <= 0:
                    break
                py = _dart_body_line(inner)
                if py:
                    out.append("        " + py)
                k += 1
            k += 1
            continue

        # метод: Ret name(args) {...}
        mm = re.match(
            r"(?:static\s+)?(?:void|int|double|String|bool|var|"
            r"[A-Z]\w*(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)\s*\{?",
            bl)
        if mm and mm.group(1) != "main":
            name = mm.group(1)
            args = ", ".join(
                a.strip().split()[-1]
                for a in mm.group(2).split(",") if a.strip())
            out.append(f"    def {name}(self{', ' + args if args else ''}):")
            depth2 = bl.count("{") - bl.count("}")
            k += 1
            while k < len(body) and depth2 > 0:
                inner = body[k]
                depth2 += inner.count("{") - inner.count("}")
                if depth2 <= 0:
                    break
                py = _dart_body_line(inner)
                if py:
                    out.append("        " + py)
                k += 1
            k += 1
            continue

        k += 1
    return out, has_init


def _dart_body_line(line):
    s = line.strip()
    if not s or s in ("{", "}"):
        return None
    m = re.match(r"return\s*(.*?)\s*;", s)
    if m:
        return f"return {_dart_expr_to_py(m.group(1))}"
    m = re.match(r"print\s*\((.*)\)\s*;", s)
    if m:
        return f"print({_dart_expr_to_py(m.group(1))})"
    m = re.match(r"this\.(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"self.{m.group(1)} = {_dart_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"{m.group(1)} = {_dart_expr_to_py(m.group(2))}"
    return None


# --- normal patch: dart async ---
def _strip_dart_async(src):
    src = re.sub(r"\basync\*?\b", "", src)
    src = re.sub(r"\bawait\s+", "", src)
    src = re.sub(r"\bmixin\s+(\w+)", r"class \1", src)
    return src


def _dart_to_python(src):
    src = _strip_dart_async(src)
    src = _expand_oneliners(src)
    src = _extract_dart_classes(src)

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
        if re.match(r"(?:void\s+)?main\s*\(\s*\)", line):
            continue

        m = re.match(
            r"(?:void|int|double|String|bool|var)?\s*(\w+)\s*\(([^)]*)\)\s*\{?$",
            line)
        if m and m.group(1) not in (
                "main", "if", "for", "while", "print",
                "println", "return", "else", "switch"):
            args = ", ".join(
                a.strip().split()[-1]
                for a in m.group(2).split(",") if a.strip())
            emit(f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # for (var i = 1; i <= 10; i++)
        m = re.match(
            r"for\s*\(\s*(?:var|int)\s+(\w+)\s*=\s*(-?\d+)\s*;\s*"
            r"\1\s*(<=|<)\s*(\d+)\s*;\s*\1\+\+\s*\)\s*\{?$", line)
        if m:
            v, a, op, b = m.group(1), m.group(2), m.group(3), m.group(4)
            end = str(int(b) + 1) if op == "<=" else b
            emit(f"for {v} in range({a}, {end}):")
            ind += 1
            continue

        m = re.match(
            r"for\s*\(\s*(?:var|final)\s+(\w+)\s+in\s+(.+?)\s*\)\s*\{?$",
            line)
        if m:
            emit(f"for {m.group(1)} in {_dart_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"while {_dart_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"if {_dart_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"else\s+if\s*\((.+?)\)\s*\{?$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_dart_expr_to_py(m.group(1))}:")
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
                emit(f"return {_dart_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"print\s*\((.*)\)$", line)
        if m:
            emit(f"print({_dart_expr_to_py(m.group(1))})")
            continue

        m = re.match(
            r"(?:final|const|var|int|String|double|bool|"
            r"List<\w+>|Map<\w+,\s*\w+>)\s+(\w+)\s*(?:=\s*(.+?))?$", line)
        if m:
            if m.group(2):
                emit(f"{m.group(1)} = {_dart_expr_to_py(m.group(2))}")
            else:
                emit(f"{m.group(1)} = None")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_dart_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_dart_expr_to_py(m.group(2))}")
            continue

        continue

    return "\n".join(out) + "\n"


def dart_print(text):
    if not text:
        return "void main() {}\n"
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    body = "\n".join(
        f'  print({json.dumps(ln, ensure_ascii=False)});' for ln in lines)
    return f"void main() {{\n{body}\n}}\n"


def dart_gen_numbers():
    return ("void main() {\n"
            "  for (var i = 1; i <= 10; i++) {\n"
            "    print(i);\n"
            "  }\n"
            "}\n")


def dart_gen_squares():
    return ("void main() {\n"
            "  for (var i = 1; i <= 10; i++) {\n"
            "    print(i * i);\n"
            "  }\n"
            "}\n")


def dart_gen_cubes():
    return ("void main() {\n"
            "  for (var i = 1; i <= 10; i++) {\n"
            "    print(i * i * i);\n"
            "  }\n"
            "}\n")


def dart_gen_table7():
    return ("void main() {\n"
            "  for (var i = 1; i <= 10; i++) {\n"
            "    print(i * 7);\n"
            "  }\n"
            "}\n")


def dart_gen_factorial():
    return ("void main() {\n"
            "  var r = 1;\n"
            "  for (var i = 1; i <= 5; i++) {\n"
            "    r = r * i;\n"
            "  }\n"
            "  print(r);\n"
            "}\n")


def dart_gen_fib():
    return ("void main() {\n"
            "  var a = 0;\n"
            "  var b = 1;\n"
            "  for (var i = 1; i <= 10; i++) {\n"
            "    print(a);\n"
            "    var c = a + b;\n"
            "    a = b;\n"
            "    b = c;\n"
            "  }\n"
            "}\n")


def dart_gen_50():
    parts = ["void main() {"]
    for k in range(1, 6):
        parts.append(f'  print("=== {k} x {k} ===");')
        for i in range(1, 6):
            parts.append(f"  print({i} * {k});")
    parts.append("}")
    return "\n".join(parts) + "\n"


def dart_gen_200():
    parts = ["void main() {"]
    for k in range(2, 8):
        parts.append(f'  print("=== Таблица {k} ===");')
        for i in range(1, 11):
            parts.append(f"  print({i} * {k});")
    parts.append("}")
    return "\n".join(parts) + "\n"


def dart_generate(output):
    if not output:
        return "void main() {}\n"
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    body = "\n".join(
        f'  print({json.dumps(ln, ensure_ascii=False)});' for ln in lines)
    return f"void main() {{\n{body}\n}}\n"


class DartLang(Language):
    name = "dart"
    title = "Dart"
    category = "О"
    ext = ".dart"
    keywords = ["void", "var", "final", "const", "class", "extends",
                "if", "else", "for", "while", "return", "true",
                "false", "null", "print", "List", "Map"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[D1] Hello, World': 'print("Hello, World!");',
        '[D2] Арифметика': 'var a = 17;\nvar b = 5;\nprint(a + b);\nprint(a - b);\nprint(a * b);\nprint(a / b);',
        '[D3] Строки': 'var s = "Hello, World";\nprint(s.length);\nprint(s.toUpperCase());\nprint(s.toLowerCase());',
        '[D4] Условие': 'var x = 7;\nif (x % 2 == 0) {\n    print("чёт");\n} else {\n    print("нечёт");\n}',
        '[D5] Функция square': 'var a = 7;\nvar b = 12;\nvar c = 25;\nprint(a * a);\nprint(b * b);\nprint(c * c);',
        '[M1] Цикл for': 'for (var i = 1; i <= 5; i++) {\n    print(i);\n}',
        '[M2] Факториал': 'var r = 1;\nfor (var i = 1; i <= 5; i++) {\n    r = r * i;\n}\nprint(r);',
        '[M3] Fibonacci': 'var a = 0;\nvar b = 1;\nfor (var i = 1; i <= 15; i++) {\n    print(a);\n    var c = a + b;\n    a = b;\n    b = c;\n}',
        '[M4] Две функции': 'var x = 5;\nvar y = 3;\nprint(x * 2);\nprint(x * x);\nprint((y * y) * 2);',
        '[M5] Сумма 1..10': 'var s = 0;\nfor (var i = 1; i <= 10; i++) {\n    s = s + i;\n}\nprint(s);',
        '[H1] Сумма квадратов': 'var s = 0;\nfor (var i = 1; i <= 10; i++) {\n    s = s + i * i;\n}\nprint(s);',
        '[H2] Вложенные циклы': 'for (var i = 1; i <= 3; i++) {\n    for (var j = 1; j <= 3; j++) {\n        print(i * j);\n    }\n}',
        '[H3] FizzBuzz': 'for (var n = 1; n <= 30; n++) {\n    if (n % 15 == 0) {\n        print("FizzBuzz");\n    } else {\n        if (n % 3 == 0) {\n            print("Fizz");\n        } else {\n            if (n % 5 == 0) {\n                print("Buzz");\n            } else {\n                print(n);\n            }\n        }\n    }\n}',
        '[H4] Массив': 'for (var i = 1; i <= 5; i++) {\n    print(i * 10);\n}',
        '[H5] Map': 'var ages = {"Alice": 30, "Bob": 25};\nprint(ages["Alice"]);\nprint(ages["Bob"]);',
        '[W1] Таблица ×7': 'var k = 7;\nfor (var i = 1; i <= 10; i++) {\n    print(i * k);\n}',
        '[W2] Квадраты и кубы': 'for (var i = 1; i <= 10; i++) {\n    print(i * i);\n}\nfor (var i = 1; i <= 10; i++) {\n    print(i * i * i);\n}',
        '[W3] Степени двойки': 'var p = 1;\nfor (var i = 1; i <= 10; i++) {\n    print(p);\n    p = p * 2;\n}',
        '[W4] Сумма 1..100': 'var s = 0;\nfor (var i = 1; i <= 100; i++) {\n    s = s + i;\n}\nprint(s);',
        '[W5] Таблица 10×10': 'for (var i = 1; i <= 10; i++) {\n    for (var j = 1; j <= 10; j++) {\n        print(i * j);\n    }\n}',
        '[T1] Базовые конструкции': 'var a = 10;\nvar b = 3;\nprint(a + b);\nprint(a - b);\nprint(a * b);\nfor (var i = 1; i <= 3; i++) {\n    print(i);\n}',
        '[T2] Все структуры': 'var s = "Hello";\nvar x = 10;\nvar y = 20;\nvar total = x + y;\nprint(s.length);\nprint(s.toUpperCase());\nprint(x);\nprint(y);\nprint(total);\nprint(total * 2);',
        '[T3] Всё вместе': 'var s = 0;\nfor (var i = 1; i <= 5; i++) {\n    s = s + i;\n}\nprint(s);\nprint(s * 2);\nfor (var i = 1; i <= 3; i++) {\n    print(i);\n}',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _dart_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<dart>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Dart: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        return dart_generate(output)


TRANSPILERS[("dart", "python")] = _dart_to_python
