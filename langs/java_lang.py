# langs/java_lang.py
"""Java — обычный язык. Generics, коллекции, интерфейсы."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS
from core.standard_templates import std_java


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


# --- normal patch: java annotations ---
def _strip_java_annotations(src):
    src = re.sub(r"@\w+(?:\([^)]*\))?", "", src)
    return src


def _expand_oneliners(src):
    for _ in range(5):
        new = re.sub(
            r"(\b(?:while|for|if)\s*\([^()]*\))\s+([^;{}\n]+);",
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
    src = re.sub(r"new\s+ArrayList<\w+>\s*\(\s*\)", r"[]", src)
    src = re.sub(r"new\s+ArrayList\s*\(\s*\)", r"[]", src)
    src = re.sub(r"new\s+HashMap<\w+,\s*\w+>\s*\(\s*\)", r"{}", src)
    src = re.sub(r"new\s+HashMap\s*\(\s*\)", r"{}", src)
    src = re.sub(r"new\s+HashSet<\w+>\s*\(\s*\)", r"set()", src)
    src = re.sub(r"new\s+HashSet\s*\(\s*\)", r"set()", src)
    return src


def _java_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnull\b", "None", e)
    e = re.sub(r"\bthis\.", "self.", e)
    e = re.sub(r"\bnew\s+(\w+)", r"\1", e)
    e = re.sub(r"(\w+)\.length\(\)", r"len(\1)", e)
    e = re.sub(r"(\w+)\.length\b", r"len(\1)", e)
    e = re.sub(r"(\w+)\.size\(\)", r"len(\1)", e)
    e = re.sub(r"(\w+)\.add\(([^)]+)\)", r"\1.append(\2)", e)
    e = re.sub(r"(\w+)\.get\(([^)]+)\)", r"\1[\2]", e)
    e = re.sub(r"(\w+)\.put\(([^,]+),\s*([^)]+)\)", r"\1[\2] = \3", e)
    e = re.sub(r"(\w+)\.containsKey\(([^)]+)\)", r"(\2 in \1)", e)
    e = re.sub(r"(\w+)\.toUpperCase\(\)", r"\1.upper()", e)
    e = re.sub(r"(\w+)\.toLowerCase\(\)", r"\1.lower()", e)
    e = re.sub(r"(\w+)\.trim\(\)", r"\1.strip()", e)
    e = re.sub(r"(\w+)\.substring\(([^,)]+)\)", r"\1[\2:]", e)
    e = re.sub(r"(\w+)\.indexOf\(([^)]+)\)", r"\1.index(\2)", e)
    e = re.sub(r"(\w+)\.equals\(([^)]+)\)", r"\1 == \2", e)
    e = re.sub(r"Integer\.parseInt\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"Double\.parseDouble\(([^)]+)\)", r"float(\1)", e)
    e = re.sub(r"String\.valueOf\(([^)]+)\)", r"str(\1)", e)
    e = re.sub(r"(\w+)\.isEmpty\(\)", r"(not \1)", e)
    e = re.sub(r"(\w+)\.startsWith\(([^)]+)\)", r"\1.startswith(\2)", e)
    e = re.sub(r"(\w+)\.endsWith\(([^)]+)\)", r"\1.endswith(\2)", e)
    e = re.sub(r"(\w+)\.contains\(([^)]+)\)", r"(\2 in \1)", e)
    e = re.sub(r"(\w+)\.replace\(([^,]+),\s*([^)]+)\)",
               r"\1.replace(\2, \3)", e)
    e = re.sub(r"(\w+)\.split\(([^)]+)\)", r"\1.split(\2)", e)
    e = re.sub(r"(\w+)\.remove\((\d+)\)", r"\1.pop(\2)", e)
    e = re.sub(r"(\w+)\.clear\(\)", r"\1.clear()", e)
    e = re.sub(
        r"""String\.join\(\s*("[^"]*"|'[^']*')\s*,\s*(.+)\)""",
        r"\1.join([\2])", e)
    e = re.sub(r"Arrays\.asList\(([^)]+)\)", r"[\1]", e)
    e = re.sub(r"Collections\.sort\(([^)]+)\)", r"\1.sort()", e)
    return e

def _extract_main_blocks(src, pattern):
    """Вырезает тело main() из src, возвращает (src_without_main, main_body_lines)."""
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
            r"(?:public|private|protected)?\s*"
            r"(?:abstract\s+|final\s+)?"
            r"class\s+(\w+)(?:\s+extends\s+(\w+))?", line)
        if not m:
            out.append(lines[i])
            i += 1
            continue

        cls_name = m.group(1)
        base = m.group(2)
        out.append(f"class {cls_name}({base}):" if base else f"class {cls_name}:")

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

        has_ctor = False
        k = 0
        while k < len(body):
            bl = body[k].strip()

            # поле
            fm = re.match(
                r"(?:public|private|protected)\s+"
                r"(?:static\s+|final\s+)?"
                r"(\w+(?:<[^>]+>)?(?:\[\])?)\s+(\w+)\s*(?:=\s*(.+?))?\s*;",
                bl)
            if fm and "(" not in bl:
                k += 1
                continue

            # конструктор
            ctor = re.match(
                rf"(?:public|private|protected)?\s*"
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
                    py = _java_body_line(inner)
                    if py:
                        out.append("        " + py)
                    k += 1
                k += 1
                continue

            # метод
            mm = re.match(
                r"(?:public|private|protected)?\s*"
                r"(?:static\s+|final\s+|abstract\s+)?"
                r"(?:void|int|long|double|float|boolean|char|byte|short|String|"
                r"[A-Z]\w*(?:<[^>]+>)?(?:\[\])?)\s+"
                r"(\w+)\s*\(([^)]*)\)\s*(?:throws\s+\w+)?\s*\{?",
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
                    py = _java_body_line(inner)
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


def _java_body_line(line):
    s = line.strip()
    if not s or s in ("{", "}"):
        return None
    m = re.match(r"return\s*(.*?)\s*;", s)
    if m:
        return f"return {_java_expr_to_py(m.group(1))}"
    m = re.match(r"System\.out\.println\s*\((.*)\)\s*;", s)
    if m:
        return f"print({_java_expr_to_py(m.group(1))})"
    m = re.match(r"System\.out\.print\s*\((.*)\)\s*;", s)
    if m:
        return f"print({_java_expr_to_py(m.group(1))}, end='')"
    m = re.match(r"this\.(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"self.{m.group(1)} = {_java_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"{m.group(1)} = {_java_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\+\+\s*;", s)
    if m:
        return f"{m.group(1)} += 1"
    return None


def _split_multi_decl_java(src):
    """int a = 0, b = 1;  →  int a = 0; int b = 1;"""
    def repl(m):
        typ = m.group(1)
        rest = m.group(2)
        parts = _split_top_level(rest, ",")
        if len(parts) > 1 and all("=" in p for p in parts):
            return "\n".join(f"{typ} {p.strip()};" for p in parts)
        return m.group(0)
    return re.sub(
        r"\b(int|long|double|float|boolean|String|var)\s+([^;]+);",
        repl, src)


def _java_to_python(src):
    src = _strip_java_annotations(src)
    src = _expand_oneliners(src)
    src = _convert_collections(src)
    src, main_body = _extract_main_blocks(
        src, r"public\s+static\s+void\s+main\s*\([^)]*\)")
    src = _extract_classes(src)
    if main_body:
        src = src + "\n" + "\n".join(main_body)
    src = _split_multi_decl_java(src)

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
        if line.startswith("package ") or line.startswith("import "):
            continue
        if re.match(r"^\}\s*$", line):
            ind = max(0, ind - 1)
            continue
        if line == "{":
            continue
        if re.match(r"^\}\s*else", line):
            line = line[1:].strip()

        if re.match(r"public\s+static\s+void\s+main\s*\(", line):
            continue

        m = re.match(
            r"for\s*\(\s*int\s+(\w+)\s*=\s*(-?\d+)\s*;\s*"
            r"\1\s*(<=|<)\s*(.+?)\s*;\s*\1\+\+\s*\)\s*\{?", line)
        if m:
            v, a, op, b = m.group(1), m.group(2), m.group(3), _java_expr_to_py(m.group(4))
            if op == "<=":
                b = f"({b}) + 1"
            emit(f"for {v} in range({a}, {b}):")
            ind += 1
            continue

        m = re.match(
            r"for\s*\(\s*(?:var|\w+(?:<[^>]+>)?)\s+(\w+)\s*:\s*(.+?)\s*\)\s*\{?",
            line)
        if m:
            emit(f"for {m.group(1)} in {_java_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"while {_java_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"if {_java_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"else\s+if\s*\((.+?)\)\s*\{?$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_java_expr_to_py(m.group(1))}:")
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
                emit(f"return {_java_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"System\.out\.println\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_java_expr_to_py(m.group(1))})")
            continue
        m = re.match(r"System\.out\.print\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_java_expr_to_py(m.group(1))}, end='')")
            continue

        # объявления
        m = re.match(
            r"(?:int|long|double|float|boolean|char|byte|short|String|var|"
            r"List<\w+>|ArrayList<\w+>|Map<\w+,\s*\w+>|HashMap<\w+,\s*\w+>|"
            r"Set<\w+>|HashSet<\w+>)\s+(\w+)\s*(?:=\s*(.+?))?\s*$", line)
        if m:
            if m.group(2):
                emit(f"{m.group(1)} = {_java_expr_to_py(m.group(2))}")
            else:
                emit(f"{m.group(1)} = None")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_java_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_java_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\+\+\s*$", line)
        if m:
            emit(f"{m.group(1)} += 1")
            continue

        continue

    return "\n".join(out) + "\n"


def _java_to_js(src):
    from langs.python_lang import _py_to_js
    return _py_to_js(_java_to_python(src))


def _java_to_cpp(src):
    from langs.python_lang import _py_to_cpp
    return _py_to_cpp(_java_to_python(src))


def _java_to_lua(src):
    from langs.python_lang import _py_to_lua
    return _py_to_lua(_java_to_python(src))


# --- PATCH: call-main ---
import re as _re_main

def _ensure_main_called(py_code: str) -> str:
    """Если в коде определён `def main(): ...` и нигде не вызван —
    добавляем `main()` в конец. Идемпотентно."""
    if not isinstance(py_code, str) or not py_code:
        return py_code
    # есть ли определение main
    if not _re_main.search(r"^def\s+main\s*\(\s*\)\s*:",
                           py_code, _re_main.MULTILINE):
        return py_code
    # уже есть вызов main()?
    if _re_main.search(r"^main\s*\(\s*\)\s*$",
                       py_code, _re_main.MULTILINE):
        return py_code
    # не добавляем, если есть if __name__ == "__main__"
    if "__main__" in py_code:
        return py_code
    return py_code.rstrip() + "\n\nmain()\n"
# --- /PATCH ---


# --- PATCH: expand-oneliners-smart ---

def _expand_oneliners_brace(src):
    """
    Разворачивает однострочные блоки `keyword ... { body }` в
    многострочный вид. Учитывает строковые литералы (не считает
    фигурные скобки внутри строк), поддерживает вложенность.

    Работает посимвольно, чтобы корректно обрабатывать случаи
    вида `fn main(){ println!("{}", x); }`, где `{}` внутри строки.
    """
    if not isinstance(src, str) or "{" not in src:
        return src

    out = []
    i = 0
    n = len(src)
    # стек открытых { — точнее, стек позиций в out, где мы открыли блок
    stack = []
    # отслеживаем, где начинается незакрытая "строка"
    in_str = None  # None | '"' | "'"
    in_escape = False

    def _is_short_block(start_idx):
        """Есть ли { в src[start_idx] с закрывающей } до \n?"""
        j = start_idx
        depth = 0
        while j < n:
            c = src[j]
            if c == "\n" and depth == 0:
                return False
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return True
            elif c in '"\'':
                # пропускаем строку
                q = c
                j += 1
                while j < n and src[j] != q:
                    if src[j] == "\\":
                        j += 1
                    j += 1
            j += 1
        return False

    while i < n:
        c = src[i]

        # строковый литерал — копируем как есть
        if in_str:
            out.append(c)
            if in_escape:
                in_escape = False
            elif c == "\\":
                in_escape = True
            elif c == in_str:
                in_str = None
            i += 1
            continue

        if c in '"\'':
            in_str = c
            out.append(c)
            i += 1
            continue

        # открывающая { без \n внутри до закрывающей }
        if c == "{" and _is_short_block(i):
            # найти парную }
            j = i
            depth = 0
            while j < n:
                cc = src[j]
                if cc in '"\'':
                    q = cc
                    j += 1
                    while j < n and src[j] != q:
                        if src[j] == "\\":
                            j += 1
                        j += 1
                    j += 1
                    continue
                if cc == "{":
                    depth += 1
                elif cc == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j < n:
                body = src[i + 1:j]
                # многострочно
                out.append("{\n")
                out.append(body.strip())
                out.append("\n}")
                i = j + 1
                continue

        out.append(c)
        i += 1

    return "".join(out)
# --- /PATCH ---


# --- PATCH: fix-java-concat ---
import re as _re_concat


def _fix_java_str_concat(py_code):
    """В Python `"..." + int_var` падает. Заменяем на `"..." + str(var)`.
    Только когда справа — простое имя, не arr[...], не obj.attr."""
    if not isinstance(py_code, str) or not py_code:
        return py_code
    pat = _re_concat.compile(
        r'("(?:[^"\\]|\\.)*")'
        r'\s*\+\s*'
        r'([A-Za-z_][A-Za-z0-9_]*)'
        r'(?!\s*[\[\.])'
    )
    return pat.sub(r'\1 + str(\2)', py_code)
# --- /PATCH ---


class JavaLang(Language):
    name = "java"
    title = "Java"
    category = "О"
    ext = ".java"
    keywords = [
        "public", "private", "protected", "static", "final", "void",
        "class", "interface", "extends", "implements", "new", "return",
        "if", "else", "for", "while", "do", "switch", "case",
        "default", "break", "continue", "try", "catch", "finally",
        "throw", "throws", "import", "package", "this", "super",
        "true", "false", "null", "List", "ArrayList", "Map", "HashMap",
    ]
    types = ["int", "long", "double", "float", "boolean", "char",
             "byte", "short", "String", "Object", "List", "Map"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
        '[E2] Арифметика': 'public class Main {\n    public static void main(String[] args) {\n        int a = 17;\n        int b = 5;\n        System.out.println(a + b);\n        System.out.println(a - b);\n        System.out.println(a * b);\n        System.out.println(a / b);\n        System.out.println(a % b);\n    }\n}',
        '[E3] Строки': 'public class Main {\n    public static void main(String[] args) {\n        String s = "Programming";\n        System.out.println(s.length());\n        System.out.println(s.toUpperCase());\n        System.out.println(s.toLowerCase());\n        System.out.println(s.substring(0));\n    }\n}',
        '[E4] Условие': 'public class Main {\n    public static void main(String[] args) {\n        int x = 7;\n        if (x % 2 == 0) {\n            System.out.println("чёт");\n        } else {\n            System.out.println("нечёт");\n        }\n    }\n}',
        '[E5] Квадраты': 'public class Main {\n    public static void main(String[] args) {\n        int x = 7;\n        System.out.println(x * x);\n        System.out.println(x * x * x);\n        System.out.println(x + 100);\n    }\n}',
        '[M1] Цикл for': 'public class Main {\n    public static void main(String[] args) {\n        for (int i = 1; i <= 5; i++) {\n            System.out.println(i);\n        }\n    }\n}',
        '[M2] Цикл while (факториал)': 'public class Main {\n    public static void main(String[] args) {\n        int n = 5;\n        int fact = 1;\n        while (n > 1) {\n            fact = fact * n;\n            n = n - 1;\n        }\n        System.out.println(fact);\n    }\n}',
        '[M3] Факториал (for)': 'public class Main {\n    public static void main(String[] args) {\n        int fact = 1;\n        for (int i = 1; i <= 5; i++) {\n            fact = fact * i;\n        }\n        System.out.println(fact);\n    }\n}',
        '[M4] Sum и prod': 'public class Main {\n    public static void main(String[] args) {\n        int sum = 0;\n        int prod = 1;\n        for (int i = 1; i <= 6; i++) {\n            sum = sum + i;\n            prod = prod * i;\n        }\n        System.out.println(sum);\n        System.out.println(prod);\n    }\n}',
        '[M5] Сумма 1..10': 'public class Main {\n    public static void main(String[] args) {\n        int sum = 0;\n        for (int i = 1; i <= 10; i++) {\n            sum = sum + i;\n        }\n        System.out.println(sum);\n    }\n}',
        '[H1] Fibonacci': 'public class Main {\n    public static void main(String[] args) {\n        int a = 0;\n        int b = 1;\n        for (int i = 0; i < 15; i++) {\n            System.out.println(a);\n            int t = a + b;\n            a = b;\n            b = t;\n        }\n    }\n}',
        '[H2] GCD (inline)': 'public class Main {\n    public static void main(String[] args) {\n        int a = 100;\n        int b = 25;\n        while (b != 0) {\n            int t = b;\n            b = a % b;\n            a = t;\n        }\n        System.out.println(a);\n    }\n}',
        '[H3] Сумма квадратов': 'public class Main {\n    public static void main(String[] args) {\n        int sum = 0;\n        for (int i = 1; i <= 10; i++) {\n            sum = sum + i * i;\n        }\n        System.out.println(sum);\n    }\n}',
        '[H4] Вложенные циклы': 'public class Main {\n    public static void main(String[] args) {\n        for (int i = 1; i <= 3; i++) {\n            for (int j = 1; j <= 3; j++) {\n                System.out.println(i * j);\n            }\n        }\n    }\n}',
        '[H5] Вложенная арифметика': 'public class Main {\n    public static void main(String[] args) {\n        int a = 3;\n        int b = 4;\n        int c = 5;\n        int r1 = (a + b) * c;\n        int r2 = a * b + c;\n        int r3 = a * (b + c);\n        System.out.println(r1);\n        System.out.println(r2);\n        System.out.println(r3);\n    }\n}',
        '[W1] Таблица ×7': 'public class Main {\n    public static void main(String[] args) {\n        int k = 7;\n        for (int i = 1; i <= 10; i++) {\n            System.out.println(i * k);\n        }\n    }\n}',
        '[W2] Квадраты и кубы': 'public class Main {\n    public static void main(String[] args) {\n        for (int i = 1; i <= 10; i++) {\n            System.out.println(i * i);\n        }\n        for (int i = 1; i <= 10; i++) {\n            System.out.println(i * i * i);\n        }\n    }\n}',
        '[W3] Простые числа до 30': 'public class Main {\n    public static void main(String[] args) {\n        for (int n = 2; n <= 30; n++) {\n            boolean prime = true;\n            for (int d = 2; d < n; d++) {\n                if (n % d == 0) {\n                    prime = false;\n                }\n            }\n            if (prime) {\n                System.out.println(n);\n            }\n        }\n    }\n}',
        '[W4] Сумма 1..100': 'public class Main {\n    public static void main(String[] args) {\n        int sum = 0;\n        for (int i = 1; i <= 100; i++) {\n            sum = sum + i;\n        }\n        System.out.println(sum);\n    }\n}',
        '[W5] Таблица 10×10': 'public class Main {\n    public static void main(String[] args) {\n        for (int i = 1; i <= 10; i++) {\n            for (int j = 1; j <= 10; j++) {\n                System.out.println(i * j);\n            }\n        }\n    }\n}',
        '[T1] Базовые конструкции': 'public class Main {\n    public static void main(String[] args) {\n        int a = 10;\n        int b = 3;\n        System.out.println(a + b);\n        System.out.println(a - b);\n        System.out.println(a * b);\n        System.out.println(a / b);\n        for (int i = 0; i < 3; i++) {\n            System.out.println(i);\n        }\n    }\n}',
        '[T2] Все структуры': 'public class Main {\n    public static void main(String[] args) {\n        String s = "Hello";\n        int x = 10;\n        int y = 20;\n        int sum = x + y;\n        System.out.println(s.length());\n        System.out.println(s.toUpperCase());\n        System.out.println(s.toLowerCase());\n        System.out.println(x);\n        System.out.println(y);\n        System.out.println(sum);\n        System.out.println(sum * 2);\n    }\n}',
        '[T3] Всё вместе': 'public class Main {\n    public static void main(String[] args) {\n        int n = 5;\n        int s = 0;\n        for (int i = 1; i <= n; i++) {\n            s = s + i;\n        }\n        int d = s * 2;\n        String label = "Result";\n        System.out.println(s);\n        System.out.println(d);\n        System.out.println(label.length());\n        for (int i = 0; i < 3; i++) {\n            System.out.println(i);\n        }\n    }\n}',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        src = _expand_oneliners_brace(src)     # PATCH-A
        if _looks_like_python(src):
            py = src
        else:
            py = _java_to_python(src)
        py = _fix_java_str_concat(py)          # PATCH-B
        py = _ensure_main_called(py)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<java>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Java: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return ('public class Main {\n'
                    '    public static void main(String[] args) {\n'
                    '    }\n}\n')
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        body = "\n".join(
            f'        System.out.println({json.dumps(ln, ensure_ascii=False)});'
            for ln in lines)
        return ('public class Main {\n'
                '    public static void main(String[] args) {\n'
                + body + '\n    }\n}\n')


TRANSPILERS[("java", "python")] = _java_to_python
TRANSPILERS[("java", "javascript")] = _java_to_js
TRANSPILERS[("java", "cpp")] = _java_to_cpp
TRANSPILERS[("java", "lua")] = _java_to_lua
