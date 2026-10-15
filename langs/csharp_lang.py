# langs/csharp_lang.py
"""C# — обычный язык. Свойства, generics, коллекции."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS
from core.standard_templates import std_cs


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
            r"(\b(?:foreach|while|for|if)\s*\([^()]*\))\s+([^;{}\n]+);",
            r"\1 {\n\2;\n}", src)
        if new == src:
            break
        src = new
    return src


def _looks_like_python(src):
    """True, если источник — Python (общий тест-шаблон)."""
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    if ("Console." not in src
            and "System.out" not in src
            and re.search(r"^\s*print\s*\(", src, re.M)):
        return True
    return False



def _convert_collections(src):
    """List<T>, Dictionary<K,V>, HashSet<T>, T[] → Python."""
    # new List<int>() → []
    src = re.sub(r"new\s+List<\w+>\s*\(\s*\)", r"[]", src)
    src = re.sub(r"new\s+Dictionary<\w+,\s*\w+>\s*\(\s*\)", r"{}", src)
    src = re.sub(r"new\s+HashSet<\w+>\s*\(\s*\)", r"set()", src)
    # List<int> x = new List<int>() → x = []
    src = re.sub(
        r"(?:List<\w+>|Dictionary<\w+,\s*\w+>|HashSet<\w+>)\s+(\w+)\s*=\s*[^;]+;",
        lambda m: f"{m.group(1)} = None;", src)
    # int[] x = new int[N]
    src = re.sub(r"(?:int|string|double|bool|var)\[\]\s+(\w+)\s*=\s*new\s+\w+\[(\d+)\]\s*;",
                 r"\1 = [0] * \2;", src)
    return src


# --- normal patch: linq ---
def _convert_linq(src):
    # from x in list [where cond] select expr  →  [expr for x in list if cond]
    def repl(m):
        var = m.group(1)
        coll = m.group(2)
        rest = m.group(3)
        where = ""
        wm = re.search(r"where\s+(.+?)(?:\s+select\s+|$)", rest)
        if wm:
            where = f" if {wm.group(1).strip()}"
        sm = re.search(r"select\s+(.+)$", rest)
        sel = sm.group(1).strip() if sm else var
        return f"[{sel} for {var} in {coll}{where}]"
    return re.sub(
        r"from\s+(\w+)\s+in\s+(\w+)\s+(.+?)(?=;|$)",
        repl, src)


def _cs_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnull\b", "None", e)
    e = re.sub(r"\bthis\.", "self.", e)
    e = re.sub(r"\bnew\s+(\w+)", r"\1", e)
    e = re.sub(r"(\w+)\.Length\b", r"len(\1)", e)
    e = re.sub(r"(\w+)\.Count\b", r"len(\1)", e)
    e = re.sub(r"(\w+)\.Add\(([^)]+)\)", r"\1.append(\2)", e)
    e = re.sub(r"(\w+)\.ToString\(\)", r"str(\1)", e)
    e = re.sub(r"(\w+)\.ToUpper\(\)", r"\1.upper()", e)
    e = re.sub(r"(\w+)\.ToLower\(\)", r"\1.lower()", e)
    e = re.sub(r"(\w+)\.Trim\(\)", r"\1.strip()", e)
    e = re.sub(r"(\w+)\.Substring\(([^,)]+)\)", r"\1[\2:]", e)
    e = re.sub(r"(\w+)\.IndexOf\(([^)]+)\)", r"\1.index(\2)", e)
    e = re.sub(r"(\w+)\.StartsWith\(([^)]+)\)", r"\1.startswith(\2)", e)
    e = re.sub(r"(\w+)\.EndsWith\(([^)]+)\)", r"\1.endswith(\2)", e)
    e = re.sub(r"(\w+)\.Contains\(([^)]+)\)", r"(\2 in \1)", e)
    e = re.sub(r"(\w+)\.Split\(([^)]+)\)", r"\1.split(\2)", e)
    e = re.sub(r"(\w+)\.First\(\)", r"\1[0]", e)
    e = re.sub(r"(\w+)\.Last\(\)", r"\1[-1]", e)
    e = re.sub(r"(\w+)\.Any\(\)", r"(len(\1) > 0)", e)
    e = re.sub(r"(\w+)\.RemoveAt\(([^)]+)\)", r"\1.pop(\2)", e)
    e = re.sub(r"(\w+)\.Clear\(\)", r"\1.clear()", e)
    e = re.sub(r"string\.IsNullOrEmpty\(([^)]+)\)", r"(not \1)", e)
    e = re.sub(r"string\.Join\(([^,]+),\s*([^)]+)\)", r"\1.join(\2)", e)
    e = re.sub(r"int\.Parse\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"double\.Parse\(([^)]+)\)", r"float(\1)", e)
    return e

def _extract_main_blocks(src, pattern):
    """Вырезает тело Main() из src, возвращает (src_without_main, main_body_lines)."""
    import re as _re
    lines = src.split("\n")
    kept, extracted = [], []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if _re.search(pattern, ln):
            depth = ln.count("{") - ln.count("}")
            i += 1
            while i < len(lines) and depth > 0:
                l2 = lines[i]
                depth += l2.count("{") - l2.count("}")
                if depth == 0:
                    i += 1
                    break
                extracted.append(l2)
                i += 1
            continue
        kept.append(ln)
        i += 1
    return "\n".join(kept), extracted


def _extract_classes(src):
    out = []
    lines = src.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()
        m = re.match(
            r"(?:public|private|internal)?\s*"
            r"(?:static\s+|abstract\s+|sealed\s+)?"
            r"class\s+(\w+)(?:\s*:\s*(\w+))?", line)
        if not m:
            out.append(lines[i])
            i += 1
            continue

        cls_name = m.group(1)
        base = m.group(2)
        out.append(f"class {cls_name}({base}):" if base else f"class {cls_name}:")

        # Собираем тело класса
        depth = 1 if "{" in line else 0
        j = i + 1
        body = []
        while j < n:
            l = lines[j]
            depth += l.count("{") - l.count("}")
            if depth <= 0:
                if l.strip() and l.strip() != "}":
                    body.append(l)
                break
            body.append(l)
            j += 1

        # Разбор тела
        has_ctor = False
        k = 0
        while k < len(body):
            bl = body[k].strip()

            # Свойство: public int X { get; set; }
            pm = re.match(
                r"(?:public|private|protected|internal)\s+"
                r"(?:static\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\{\s*get",
                bl)
            if pm:
                k += 1
                continue

            # Поле: public int x;
            fm = re.match(
                r"(?:public|private|protected|internal)\s+"
                r"(?:static\s+|readonly\s+|const\s+)?"
                r"(\w+(?:<[^>]+>)?(?:\[\])?)\s+(\w+)\s*(?:=\s*(.+?))?\s*;",
                bl)
            if fm and "(" not in bl:
                k += 1
                continue

            # Конструктор
            ctor = re.match(
                rf"(?:public|private|protected|internal)?\s*"
                rf"{re.escape(cls_name)}\s*\(([^)]*)\)\s*\{{?",
                bl)
            if ctor:
                args = ", ".join(
                    a.strip().split()[-1]
                    for a in ctor.group(1).split(",") if a.strip())
                out.append(f"    def __init__(self{', ' + args if args else ''}):")
                has_ctor = True
                depth2 = bl.count("{") - bl.count("}")
                k += 1
                while k < len(body) and depth2 > 0:
                    inner = body[k]
                    depth2 += inner.count("{") - inner.count("}")
                    if depth2 <= 0:
                        break
                    py = _cs_body_line(inner)
                    if py:
                        out.append("        " + py)
                    k += 1
                k += 1
                continue

            # Метод
            mm = re.match(
                r"(?:public|private|protected|internal)?\s*"
                r"(?:static\s+|async\s+|override\s+|virtual\s+)?"
                r"(?:void|int|long|double|float|string|bool|char|var|"
                r"[A-Z]\w*(?:<[^>]+>)?)\s+"
                r"(\w+)\s*\(([^)]*)\)\s*\{?",
                bl)
            if mm and mm.group(1) != "Main":
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
                    py = _cs_body_line(inner)
                    if py:
                        out.append("        " + py)
                    k += 1
                k += 1
                continue

            k += 1

        if not has_ctor:
            out.append("    def __init__(self):")
            out.append("        pass")

        i = j + 1

    return "\n".join(out)


def _cs_body_line(line):
    s = line.strip()
    if not s or s in ("{", "}"):
        return None
    m = re.match(r"return\s*(.*?)\s*;", s)
    if m:
        return f"return {_cs_expr_to_py(m.group(1))}"
    m = re.match(r"Console\.WriteLine\s*\((.*)\)\s*;", s)
    if m:
        return f"print({_cs_expr_to_py(m.group(1))})"
    m = re.match(r"Console\.Write\s*\((.*)\)\s*;", s)
    if m:
        return f"print({_cs_expr_to_py(m.group(1))}, end='')"
    m = re.match(r"this\.(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"self.{m.group(1)} = {_cs_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"{m.group(1)} = {_cs_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\+\+\s*;", s)
    if m:
        return f"{m.group(1)} += 1"
    return None


def _split_multi_decl_cs(src):
    """int a = 0, b = 1;  →  int a = 0; int b = 1;"""
    def repl(m):
        typ = m.group(1)
        rest = m.group(2)
        parts = _split_top_level(rest, ",")
        if len(parts) > 1 and all("=" in p for p in parts):
            return "\n".join(f"{typ} {p.strip()};" for p in parts)
        return m.group(0)
    return re.sub(
        r"\b(int|long|double|float|string|bool|var|char)\s+([^;]+);",
        repl, src)


def _cs_to_python(src):
    src = _convert_linq(src)
    src = _expand_oneliners(src)
    src = _convert_collections(src)
    src, main_body = _extract_main_blocks(
        src, r"(?:public|private|internal)?\s*static\s+void\s+Main\s*\(\s*\)")
    src = _extract_classes(src)
    if main_body:
        src = src + "\n" + "\n".join(main_body)
    src = _split_multi_decl_cs(src)

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

        if line.startswith("using ") or line.startswith("namespace "):
            continue
        if re.match(r"^\}\s*$", line):
            ind = max(0, ind - 1)
            continue
        if line == "{":
            continue
        if re.match(r"^\}\s*else", line):
            line = line[1:].strip()

        if re.match(r"public\s+static\s+void\s+Main\s*\(", line):
            continue
        if re.match(r"static\s+void\s+Main\s*\(", line):
            continue

        # for
        m = re.match(
            r"for\s*\(\s*int\s+(\w+)\s*=\s*(-?\d+)\s*;\s*"
            r"\1\s*(<=|<)\s*(.+?)\s*;\s*\1\+\+\s*\)\s*\{?", line)
        if m:
            v, a, op, b = m.group(1), m.group(2), m.group(3), _cs_expr_to_py(m.group(4))
            if op == "<=":
                b = f"({b}) + 1"
            emit(f"for {v} in range({a}, {b}):")
            ind += 1
            continue

        # foreach
        m = re.match(
            r"foreach\s*\(\s*(?:var|\w+(?:<[^>]+>)?)\s+(\w+)\s+in\s+(.+?)\s*\)\s*\{?",
            line)
        if m:
            emit(f"for {m.group(1)} in {_cs_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"while {_cs_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"if {_cs_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"else\s+if\s*\((.+?)\)\s*\{?$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_cs_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        if re.match(r"else\s*\{?$", line):
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        m = re.match(r"return\s*(.*?)\s*$", line)
        if m:
            val = m.group(1).strip()
            if val:
                emit(f"return {_cs_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"Console\.WriteLine\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_cs_expr_to_py(m.group(1))})")
            continue
        m = re.match(r"Console\.Write\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_cs_expr_to_py(m.group(1))}, end='')")
            continue

        # var x = expr / int x = expr / List<int> x = ...
        m = re.match(
            r"(?:int|long|double|float|string|bool|var|char|"
            r"List<\w+>|Dictionary<\w+,\s*\w+>|HashSet<\w+>|"
            r"\w+\[\])\s+(\w+)\s*(?:=\s*(.+?))?\s*$", line)
        if m and m.group(2) is not None:
            emit(f"{m.group(1)} = {_cs_expr_to_py(m.group(2))}")
            continue
        if m and m.group(2) is None:
            emit(f"{m.group(1)} = None")
            continue

        # x op= expr
        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_cs_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_cs_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\+\+\s*$", line)
        if m:
            emit(f"{m.group(1)} += 1")
            continue

        continue

    return "\n".join(out) + "\n"


def _cs_to_js(src):
    from langs.python_lang import _py_to_js
    return _py_to_js(_cs_to_python(src))


def _cs_to_cpp(src):
    from langs.python_lang import _py_to_cpp
    return _py_to_cpp(_cs_to_python(src))


def _cs_to_lua(src):
    from langs.python_lang import _py_to_lua
    return _py_to_lua(_cs_to_python(src))


class CSharpLang(Language):
    name = "csharp"
    title = "C#"
    category = "О"
    ext = ".cs"
    keywords = [
        "using", "namespace", "class", "struct", "interface", "enum",
        "public", "private", "protected", "internal", "static", "readonly",
        "const", "void", "int", "long", "double", "float", "string",
        "bool", "char", "var", "new", "return", "if", "else", "for",
        "foreach", "while", "do", "switch", "case", "default", "break",
        "continue", "try", "catch", "finally", "throw", "this", "base",
        "null", "true", "false", "Console", "Main", "List", "Dictionary",
    ]
    types = ["int", "long", "double", "float", "string", "bool", "char",
             "object", "byte", "short", "decimal", "List", "Dictionary"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': 'using System;\nclass Program {\n    static void Main() {\n        Console.WriteLine("Hello, World!");\n    }\n}',
        '[E2] Арифметика': 'using System;\nclass Program {\n    static void Main() {\n        int a = 17;\n        int b = 5;\n        Console.WriteLine(a + b);\n        Console.WriteLine(a - b);\n        Console.WriteLine(a * b);\n        Console.WriteLine(a / b);\n        Console.WriteLine(a % b);\n    }\n}',
        '[E3] Строки': 'using System;\nclass Program {\n    static void Main() {\n        string s = "Programming";\n        Console.WriteLine(s.Length);\n        Console.WriteLine(s.ToUpper());\n        Console.WriteLine(s.ToLower());\n    }\n}',
        '[E4] Условие': 'using System;\nclass Program {\n    static void Main() {\n        int x = 7;\n        if (x % 2 == 0) {\n            Console.WriteLine("чёт");\n        } else {\n            Console.WriteLine("нечёт");\n        }\n    }\n}',
        '[E5] Квадрат и куб': 'using System;\nclass Program {\n    static void Main() {\n        int x = 7;\n        Console.WriteLine(x * x);\n        Console.WriteLine(x * x * x);\n        Console.WriteLine(x + 100);\n    }\n}',
        '[M1] Цикл for': 'using System;\nclass Program {\n    static void Main() {\n        for (int i = 1; i <= 5; i++) {\n            Console.WriteLine(i);\n        }\n    }\n}',
        '[M2] Цикл while': 'using System;\nclass Program {\n    static void Main() {\n        int i = 1;\n        while (i <= 5) {\n            Console.WriteLine(i);\n            i++;\n        }\n    }\n}',
        '[M3] Факториал (цикл)': 'using System;\nclass Program {\n    static void Main() {\n        int r = 1;\n        for (int i = 1; i <= 5; i++) {\n            r = r * i;\n        }\n        Console.WriteLine(r);\n    }\n}',
        '[M4] Sum и prod': 'using System;\nclass Program {\n    static void Main() {\n        int sum = 0;\n        int prod = 1;\n        for (int i = 1; i <= 6; i++) {\n            sum = sum + i;\n            prod = prod * i;\n        }\n        Console.WriteLine(sum);\n        Console.WriteLine(prod);\n    }\n}',
        '[M5] Сумма 1..10': 'using System;\nclass Program {\n    static void Main() {\n        int sum = 0;\n        for (int i = 1; i <= 10; i++) {\n            sum = sum + i;\n        }\n        Console.WriteLine(sum);\n    }\n}',
        '[H1] Fibonacci': 'using System;\nclass Program {\n    static void Main() {\n        int a = 0;\n        int b = 1;\n        for (int i = 0; i < 15; i++) {\n            Console.WriteLine(a);\n            int t = a + b;\n            a = b;\n            b = t;\n        }\n    }\n}',
        '[H2] GCD (inline)': 'using System;\nclass Program {\n    static void Main() {\n        int a = 100;\n        int b = 25;\n        while (b != 0) {\n            int t = b;\n            b = a % b;\n            a = t;\n        }\n        Console.WriteLine(a);\n    }\n}',
        '[H3] Сумма квадратов': 'using System;\nclass Program {\n    static void Main() {\n        int sum = 0;\n        for (int i = 1; i <= 10; i++) {\n            sum = sum + i * i;\n        }\n        Console.WriteLine(sum);\n    }\n}',
        '[H4] Вложенная арифметика': 'using System;\nclass Program {\n    static void Main() {\n        int a = 3;\n        int b = 4;\n        int c = 5;\n        int r1 = (a + b) * c;\n        int r2 = a * b + c;\n        int r3 = a * (b + c);\n        Console.WriteLine(r1);\n        Console.WriteLine(r2);\n        Console.WriteLine(r3);\n    }\n}',
        '[H5] Много строк': 'using System;\nclass Program {\n    static void Main() {\n        Console.WriteLine("Строка 1");\n        Console.WriteLine("Строка 2");\n        Console.WriteLine("Строка 3");\n        Console.WriteLine("Строка 4");\n        Console.WriteLine("Строка 5");\n        Console.WriteLine("Строка 6");\n        Console.WriteLine("Строка 7");\n        Console.WriteLine("Строка 8");\n    }\n}',
        '[W1] Таблица ×7': 'using System;\nclass Program {\n    static void Main() {\n        int k = 7;\n        for (int i = 1; i <= 10; i++) {\n            Console.WriteLine(i * k);\n        }\n    }\n}',
        '[W2] Квадраты и кубы': 'using System;\nclass Program {\n    static void Main() {\n        for (int i = 1; i <= 10; i++) {\n            Console.WriteLine(i * i);\n        }\n        for (int i = 1; i <= 10; i++) {\n            Console.WriteLine(i * i * i);\n        }\n    }\n}',
        '[W3] Простые числа до 30': 'using System;\nclass Program {\n    static void Main() {\n        for (int n = 2; n <= 30; n++) {\n            bool prime = true;\n            for (int d = 2; d < n; d++) {\n                if (n % d == 0) {\n                    prime = false;\n                }\n            }\n            if (prime) Console.WriteLine(n);\n        }\n    }\n}',
        '[W4] Сумма 1..100': 'using System;\nclass Program {\n    static void Main() {\n        int sum = 0;\n        for (int i = 1; i <= 100; i++) {\n            sum = sum + i;\n        }\n        Console.WriteLine(sum);\n    }\n}',
        '[W5] Таблица умножения 10×10': 'using System;\nclass Program {\n    static void Main() {\n        for (int i = 1; i <= 10; i++) {\n            for (int j = 1; j <= 10; j++) {\n                Console.WriteLine(i * j);\n            }\n        }\n    }\n}',
        '[T1] Базовые конструкции': 'using System;\nclass Program {\n    static void Main() {\n        int a = 10;\n        int b = 3;\n        Console.WriteLine(a + b);\n        Console.WriteLine(a - b);\n        Console.WriteLine(a * b);\n        Console.WriteLine(a / b);\n        for (int i = 0; i < 3; i++) {\n            Console.WriteLine(i);\n        }\n    }\n}',
        '[T2] Все структуры': 'using System;\nclass Program {\n    static void Main() {\n        string s = "Hello";\n        int x = 10;\n        int y = 20;\n        int sum = x + y;\n        Console.WriteLine(s.Length);\n        Console.WriteLine(s.ToUpper());\n        Console.WriteLine(x);\n        Console.WriteLine(y);\n        Console.WriteLine(sum);\n    }\n}',
        '[T3] Всё вместе': 'using System;\nclass Program {\n    static void Main() {\n        int n = 5;\n        int sum = 0;\n        for (int i = 1; i <= n; i++) {\n            sum = sum + i;\n        }\n        int double_it = sum * 2;\n        string s = "Result";\n        Console.WriteLine(sum);\n        Console.WriteLine(double_it);\n        Console.WriteLine(s.Length);\n    }\n}',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _cs_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<csharp>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// C#: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return ('using System;\n\npublic class Program {\n'
                    '    public static void Main() {\n    }\n}\n')
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        body = "\n".join(
            f'        Console.WriteLine({json.dumps(ln, ensure_ascii=False)});'
            for ln in lines)
        return ('using System;\n\npublic class Program {\n'
                '    public static void Main() {\n'
                + body + '\n    }\n}\n')


TRANSPILERS[("csharp", "python")] = _cs_to_python
TRANSPILERS[("csharp", "javascript")] = _cs_to_js
TRANSPILERS[("csharp", "cpp")] = _cs_to_cpp
TRANSPILERS[("csharp", "lua")] = _cs_to_lua
