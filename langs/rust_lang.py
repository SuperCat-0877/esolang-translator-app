# langs/rust_lang.py
"""Rust — обычный язык. Транспайлер Rust → Python со struct/enum/match."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS
from core.standard_templates import std_rust





# --- normal patch: rust traits ---
def _strip_rust_traits(src):
    # Только `: impl Trait` в позиции типа → `: Trait`
    # (а не `impl Foo { }` — те обрабатываются отдельно)
    src = re.sub(r":\s*impl\s+(?:dyn\s+)?([A-Z]\w*)",
                 r": \1", src)
    src = re.sub(r"\bdyn\s+[A-Z]\w*", "object", src)
    # `let x: T = ...` → `let x = ...` (тип strip)
    src = re.sub(r"let\s+(mut\s+)?(\w+)\s*:\s*[\w<>:, ]+\s*=",
                 r"let \1\2 =", src)
    return src


def _rust_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bNone\b", "None", e)
    e = re.sub(r"vec!\[([^\]]*)\]", r"[\1]", e)
    e = re.sub(r'format!\("([^"]*)"(?:,\s*([^)]*))?\)',
               lambda m: _rust_format(m.group(1), m.group(2)), e)
    e = re.sub(r'"([^"]*)"\s*\.parse::<(?:i32|i64|u32|usize)>\(\)\s*\.unwrap\(\)',
               r'int("\1")', e)
    e = re.sub(r'"([^"]*)"\s*\.parse::<(?:f32|f64)>\(\)\s*\.unwrap\(\)',
               r'float("\1")', e)
    e = re.sub(r'"([^"]*)"\s*\.parse\(\)\s*\.unwrap\(\)',
               r'int("\1")', e)
    e = re.sub(r'("[^"]*"|\w+)\.to_uppercase\(\)', r"\1.upper()", e)
    e = re.sub(r'("[^"]*"|\w+)\.to_lowercase\(\)', r"\1.lower()", e)
    e = re.sub(r'("[^"]*"|\w+)\.trim\(\)', r"\1.strip()", e)
    e = re.sub(r'("[^"]*"|\w+)\.len\(\)', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.chars\(\)', r"list(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.bytes\(\)',
               r"[ord(c) for c in \1]", e)
    e = re.sub(r'("[^"]*"|\w+)\.contains\(([^)]+)\)',
               r"(\2 in \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.starts_with\(([^)]+)\)',
               r"\1.startswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.ends_with\(([^)]+)\)',
               r"\1.endswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.push\(([^)]+)\)',
               r"\1.append(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.pop\(\)', r"\1.pop()", e)
    e = re.sub(r"\.clone\(\)", "", e)
    e = re.sub(r"\.unwrap\(\)", "", e)
    e = re.sub(r"\.iter\(\)", "", e)
    return e


def _rust_format(fmt, args):
    """format!("Hello, {}", x) → f"Hello, {x}"."""
    if not args:
        return f'"{fmt}"'
    parts = [a.strip() for a in args.split(",") if a.strip()]
    result = fmt
    for p in parts:
        result = result.replace("{}", "{" + p + "}", 1)
    return f'f"{result}"'

def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    return False


def _expand_oneliners(src):
    for _ in range(5):
        new = re.sub(
            r"(\b(?:if|else|for|while|match)\b[^{}\n]*?)\s*"
            r"\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new == src:
            break
        src = new
    return src


def _extract_rust_struct_enum(src):
    """struct/enum → простой Python."""
    out = []
    lines = src.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # struct Name { field: T, ... }
        m = re.match(r"(?:pub\s+)?struct\s+(\w+)\s*\{", line)
        if m:
            name = m.group(1)
            out.append(f"class {name}:")
            out.append("    def __init__(self):")
            depth = line.count("{") - line.count("}")
            i += 1
            while i < n and depth > 0:
                inner = lines[i].strip()
                depth += inner.count("{") - inner.count("}")
                if depth <= 0:
                    i += 1
                    break
                # поле name: T,
                fm = re.match(r"(?:pub\s+)?(\w+)\s*:\s*(.+?),?\s*$", inner)
                if fm:
                    out.append(f"        self.{fm.group(1)} = None")
                i += 1
            continue

        # enum Name { A, B, C }
        m = re.match(r"(?:pub\s+)?enum\s+(\w+)\s*\{", line)
        if m:
            name = m.group(1)
            out.append(f"class {name}:")
            out.append("    def __init__(self, variant=None, value=None):")
            out.append("        self.variant = variant")
            out.append("        self.value = value")
            out.append(f"    @staticmethod")
            out.append(f"    def _variants():")
            out.append(f"        return []")
            depth = line.count("{") - line.count("}")
            i += 1
            while i < n and depth > 0:
                inner = lines[i].strip()
                depth += inner.count("{") - inner.count("}")
                if depth <= 0:
                    i += 1
                    break
                i += 1
            continue

        # impl Name { methods }
        m = re.match(r"impl\s+(\w+)\s*\{", line)
        if m:
            cls_name = m.group(1)
            depth = line.count("{") - line.count("}")
            i += 1
            while i < n and depth > 0:
                inner = lines[i].strip()
                depth += inner.count("{") - inner.count("}")
                # fn name(args) -> Ret { ... }
                fm = re.match(r"(?:pub\s+)?fn\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*\w+)?\s*\{?", inner)
                if fm:
                    method = fm.group(1)
                    args = ", ".join(
                        a.strip().split(":")[0].strip()
                        for a in fm.group(2).split(",") if a.strip())
                    out.append(f"    def {method}(self{', ' + args if args else ''}):")
                    # Тело метода — до закрывающей `}`
                    depth2 = inner.count("{") - inner.count("}")
                    i += 1
                    while i < n and depth2 > 0:
                        body_line = lines[i]
                        depth2 += body_line.count("{") - body_line.count("}")
                        if depth2 <= 0:
                            break
                        bm = _rust_body_line(body_line)
                        if bm:
                            out.append("        " + bm)
                        i += 1
                    i += 1
                    continue
                i += 1
            continue

        out.append(lines[i])
        i += 1

    return "\n".join(out)


def _rust_body_line(line):
    s = line.strip()
    if not s or s in ("{", "}"):
        return None
    m = re.match(r"return\s*(.*?)\s*;?\s*$", s)
    if m:
        return f"return {_rust_expr_to_py(m.group(1))}"
    m = re.match(r"println!\s*\((.*)\)\s*;?\s*$", s)
    if m:
        return f"print({m.group(1)})"
    m = re.match(r"self\.(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"self.{m.group(1)} = {_rust_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"{m.group(1)} = {_rust_expr_to_py(m.group(2))}"
    return None


def _rust_to_python(src):
    src = _strip_rust_traits(src)
    src = _expand_oneliners(src)
    src = _extract_rust_struct_enum(src)
    lines = src.splitlines()
    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("use ") or line.startswith("extern crate"):
            continue

        if re.match(r"fn\s+main\s*\(\s*\)\s*\{?\s*$", line):
            continue

        m = re.match(
            r"fn\s+(\w+)\s*\(([^)]*)\)\s*"
            r"(?:->\s*[\w<>:, ]+)?\s*\{?\s*\}?\s*$", line)
        if m and m.group(1) != "main":
            args = ", ".join(
                a.strip().split(":")[0].strip()
                for a in m.group(2).split(",") if a.strip())
            emit(f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # for i in A..B / A..=B
        m = re.match(r"for\s+(\w+)\s+in\s+(-?\d+)\s*\.\.=\s*(-?\d+)", line)
        if m:
            emit(f"for {m.group(1)} in range({m.group(2)}, {int(m.group(3)) + 1}):")
            ind += 1
            continue
        m = re.match(r"for\s+(\w+)\s+in\s+(-?\d+)\s*\.\.\s*(-?\d+)", line)
        if m:
            emit(f"for {m.group(1)} in range({m.group(2)}, {m.group(3)}):")
            ind += 1
            continue
        m = re.match(r"for\s+(\w+)\s+in\s+(.+?)(?:\.iter\(\))?\s*\{?\s*$", line)
        if m:
            emit(f"for {m.group(1)} in {m.group(2)}:")
            ind += 1
            continue

        # while cond
        m = re.match(r"while\s+(.+?)\s*\{?\s*$", line)
        if m:
            emit(f"while {_rust_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        # if / else if / else
        m = re.match(r"if\s+(.+?)\s*\{?\s*$", line)
        if m:
            emit(f"if {_rust_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"(?:\}\s*)?else\s+if\s+(.+?)\s*\{?\s*$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_rust_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        if re.match(r"(?:\}\s*)?else\s*\{?\s*$", line):
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        # match → if/elif (упрощённо)
        m = re.match(r"match\s+(.+?)\s*\{", line)
        if m:
            emit(f"_match_val = {_rust_expr_to_py(m.group(1))}")
            ind += 1
            continue
        m = re.match(r"(.+?)\s*=>\s*(.+?),?\s*$", line)
        if m:
            pattern = m.group(1).strip()
            body = m.group(2).strip()
            if pattern == "_":
                ind = max(0, ind - 1)
                emit("else:")
                ind += 1
            else:
                kw = "if" if "_match_used" not in out else "elif"
                emit(f"{kw} _match_val == {_rust_expr_to_py(pattern)}:")
                ind += 1
            # Тело
            if body.startswith("print"):
                emit(body)
            else:
                emit(f"pass")
            ind = max(0, ind - 1)
            continue

        m = re.match(r"return\s*(.*?)\s*;?\s*$", line)
        if m:
            val = m.group(1).strip()
            if val:
                emit(f"return {_rust_expr_to_py(val)}")
            else:
                emit("return")
            continue

        # println!/print!
        m = re.match(r"(println|print)!\s*\((.*)\)\s*;?\s*$", line)
        if m:
            kind = m.group(1)
            args = m.group(2).strip()
            parts, depth, cur = [], 0, []
            for ch in args:
                if ch == "(":
                    depth += 1
                    cur.append(ch)
                elif ch == ")":
                    depth -= 1
                    cur.append(ch)
                elif ch == "," and depth == 0:
                    parts.append("".join(cur).strip())
                    cur = []
                else:
                    cur.append(ch)
            if cur:
                parts.append("".join(cur).strip())
            if parts and parts[0].startswith('"') and "{" in parts[0]:
                parts = parts[1:]
            if not parts:
                parts = ['""']
            joined = ", ".join(parts)
            if kind == "println":
                emit(f"print({_rust_expr_to_py(joined)})")
            else:
                emit(f"print({_rust_expr_to_py(joined)}, end='')")
            continue

        m = re.match(r"let\s+mut\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(.+?)\s*;", line)
        if m:
            emit(f"{m.group(1)} = {_rust_expr_to_py(m.group(2))}")
            continue
        m = re.match(r"let\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(.+?)\s*;", line)
        if m:
            emit(f"{m.group(1)} = {_rust_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)\s*;", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_rust_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)\s*;", line)
        if m:
            emit(f"{m.group(1)} = {_rust_expr_to_py(m.group(2))}")
            continue

        if re.match(r"^\}\s*;?\s*$", line):
            ind = max(0, ind - 1)
            continue

        continue

    return "\n".join(out) + "\n"


def _rust_to_js(src):
    from langs.python_lang import _py_to_js
    return _py_to_js(_rust_to_python(src))


def _rust_to_cpp(src):
    from langs.python_lang import _py_to_cpp
    return _py_to_cpp(_rust_to_python(src))


def _rust_to_lua(src):
    from langs.python_lang import _py_to_lua
    return _py_to_lua(_rust_to_python(src))


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


class RustLang(Language):
    name = "rust"
    title = "Rust"
    category = "О"
    ext = ".rs"
    keywords = [
        "fn", "let", "mut", "const", "static", "if", "else", "match",
        "for", "in", "while", "loop", "return", "break", "continue",
        "struct", "enum", "impl", "trait", "pub", "use", "mod", "crate",
        "self", "Self", "true", "false", "None", "Some", "Ok", "Err",
    ]
    types = ["i32", "i64", "u32", "u64", "f32", "f64", "bool",
             "String", "str", "Vec", "Option", "Result"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': 'fn main() {\n    println!("Hello, World!");\n}',
        '[E2] Арифметика': 'fn main() {\n    let a = 17;\n    let b = 5;\n    println!("{}", a + b);\n    println!("{}", a - b);\n    println!("{}", a * b);\n    println!("{}", a / b);\n    println!("{}", a % b);\n}',
        '[E3] Строки': 'fn main() {\n    let s = "Programming";\n    println!("{}", s.len());\n    println!("{}", s.to_uppercase());\n    println!("{}", s.to_lowercase());\n}',
        '[E4] Условие': 'fn main() {\n    let x = 7;\n    if x % 2 == 0 {\n        println!("чёт");\n    } else {\n        println!("нечёт");\n    }\n}',
        '[E5] Функция square': 'fn square(x: i32) -> i32 {\n    return x * x;\n}\n\nfn main() {\n    println!("{}", square(7));\n    println!("{}", square(12));\n    println!("{}", square(25));\n}',
        '[M1] Цикл for': 'fn main() {\n    for i in 1..=5 {\n        println!("{}", i);\n    }\n}',
        '[M2] Цикл while (факториал)': 'fn main() {\n    let mut n = 5;\n    let mut fact = 1;\n    while n > 1 {\n        fact = fact * n;\n        n = n - 1;\n    }\n    println!("{}", fact);\n}',
        '[M3] Рекурсия': 'fn fact(n: i32) -> i32 {\n    if n <= 1 {\n        return 1;\n    }\n    return n * fact(n - 1);\n}\n\nfn main() {\n    println!("{}", fact(5));\n    println!("{}", fact(7));\n    println!("{}", fact(10));\n}',
        '[M4] Две функции': 'fn add(a: i32, b: i32) -> i32 {\n    return a + b;\n}\n\nfn mul(a: i32, b: i32) -> i32 {\n    return a * b;\n}\n\nfn main() {\n    println!("{}", add(3, 4));\n    println!("{}", mul(3, 4));\n    println!("{}", add(mul(2, 5), 7));\n}',
        '[M5] Сумма 1..10': 'fn main() {\n    let mut sum = 0;\n    for i in 1..=10 {\n        sum = sum + i;\n    }\n    println!("{}", sum);\n}',
        '[H1] GCD': 'fn gcd(a: i32, b: i32) -> i32 {\n    let mut x = a;\n    let mut y = b;\n    while y != 0 {\n        let t = y;\n        y = x % y;\n        x = t;\n    }\n    return x;\n}\n\nfn main() {\n    println!("{}", gcd(12, 8));\n    println!("{}", gcd(100, 25));\n    println!("{}", gcd(17, 5));\n}',
        '[H2] Fibonacci (итеративный)': 'fn main() {\n    let mut a = 0;\n    let mut b = 1;\n    for i in 1..=15 {\n        println!("{}", a);\n        let t = a + b;\n        a = b;\n        b = t;\n    }\n}',
        '[H3] Сумма квадратов': 'fn main() {\n    let mut sum = 0;\n    for i in 1..=10 {\n        sum = sum + i * i;\n    }\n    println!("{}", sum);\n}',
        '[H4] Вложенные циклы': 'fn main() {\n    for i in 1..=3 {\n        for j in 1..=3 {\n            println!("{}", i * j);\n        }\n    }\n}',
        '[H5] Три функции': 'fn add(a: i32, b: i32) -> i32 {\n    return a + b;\n}\n\nfn sq(x: i32) -> i32 {\n    return x * x;\n}\n\nfn sumSq() -> i32 {\n    let mut s = 0;\n    for i in 1..=5 {\n        s = add(s, sq(i));\n    }\n    return s;\n}\n\nfn main() {\n    println!("{}", sumSq());\n}',
        '[W1] Таблица ×7': 'fn main() {\n    let k = 7;\n    for i in 1..=10 {\n        println!("{}", i * k);\n    }\n}',
        '[W2] Квадраты и кубы': 'fn main() {\n    for i in 1..=10 {\n        println!("{}", i * i);\n    }\n    for i in 1..=10 {\n        println!("{}", i * i * i);\n    }\n}',
        '[W3] Простые числа до 30': 'fn main() {\n    let mut n = 2;\n    while n <= 30 {\n        let mut prime = true;\n        let mut d = 2;\n        while d < n {\n            if n % d == 0 {\n                prime = false;\n            }\n            d = d + 1;\n        }\n        if prime {\n            println!("{}", n);\n        }\n        n = n + 1;\n    }\n}',
        '[W4] Сумма 1..100': 'fn main() {\n    let mut sum = 0;\n    for i in 1..=100 {\n        sum = sum + i;\n    }\n    println!("{}", sum);\n}',
        '[W5] Таблица 10×10': 'fn main() {\n    for i in 1..=10 {\n        for j in 1..=10 {\n            println!("{}", i * j);\n        }\n    }\n}',
        '[T1] Базовые конструкции': 'fn main() {\n    let a = 10;\n    let b = 3;\n    println!("{}", a + b);\n    println!("{}", a - b);\n    println!("{}", a * b);\n    println!("{}", a / b);\n    for i in 1..=3 {\n        println!("{}", i);\n    }\n}',
        '[T2] Все структуры': 'fn main() {\n    let s = "Hello";\n    let x = 10;\n    let y = 20;\n    let sum = x + y;\n    println!("{}", s.len());\n    println!("{}", s.to_uppercase());\n    println!("{}", x);\n    println!("{}", y);\n    println!("{}", sum);\n    println!("{}", sum * 2);\n}',
        '[T3] Всё вместе': 'fn sumTo5() -> i32 {\n    let mut s = 0;\n    for i in 1..=5 {\n        s = s + i;\n    }\n    return s;\n}\n\nfn doubleIt(x: i32) -> i32 {\n    return x * 2;\n}\n\nfn main() {\n    let s = sumTo5();\n    let d = doubleIt(s);\n    let label = "Result";\n    println!("{}", s);\n    println!("{}", d);\n    println!("{}", label.len());\n    for i in 1..=3 {\n        println!("{}", i);\n    }\n}',
    }
    def execute(self, src):
        if not src or not src.strip():
            return ""
        src = _expand_oneliners_brace(src)   # PATCH
        if _looks_like_python(src):
            py = src
        else:
            py = _rust_to_python(src)
        py = _ensure_main_called(py)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<rust>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Rust: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return "fn main() {\n}\n"
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        body = "\n".join(
            f'    println!("{{}}", {json.dumps(ln, ensure_ascii=False)});'
            for ln in lines)
        return "fn main() {\n" + body + "\n}\n"


TRANSPILERS[("rust", "python")] = _rust_to_python
TRANSPILERS[("rust", "javascript")] = _rust_to_js
TRANSPILERS[("rust", "cpp")] = _rust_to_cpp
TRANSPILERS[("rust", "lua")] = _rust_to_lua
