# langs/ruby.py
"""Ruby — обычный язык. Транспайлер Ruby → Python."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS




def _ruby_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnil\b", "None", e)
    e = re.sub(r'("[^"]*"|\w+)\.upcase\b', r"\1.upper()", e)
    e = re.sub(r'("[^"]*"|\w+)\.downcase\b', r"\1.lower()", e)
    e = re.sub(r'("[^"]*"|\w+)\.strip\b', r"\1.strip()", e)
    e = re.sub(r'("[^"]*"|\w+)\.chomp\b', r"\1.rstrip()", e)
    e = re.sub(r'("[^"]*"|\w+)\.length\b', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.size\b', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.to_i\b', r"int(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.to_s\b', r"str(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.to_f\b', r"float(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.first\b', r"\1[0]", e)
    e = re.sub(r'("[^"]*"|\w+)\.last\b', r"\1[-1]", e)
    e = re.sub(r'("[^"]*"|\w+)\.empty\?', r"(not \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.nil\?', r"(\1 is None)", e)
    e = re.sub(r'("[^"]*"|\w+)\.sort\b', r"sorted(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.reverse\b', r"(\1)[::-1]", e)
    e = re.sub(r'("[^"]*"|\w+)\.uniq\b',
               r"list(dict.fromkeys(\1))", e)
    e = re.sub(r'("[^"]*"|\w+)\.min\b', r"min(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.max\b', r"max(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.sum\b', r"sum(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.include\?\(([^)]+)\)',
               r"(\2 in \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.start_with\?\(([^)]+)\)',
               r"\1.startswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.end_with\?\(([^)]+)\)',
               r"\1.endswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.split\(([^)]+)\)',
               r"\1.split(\2)", e)
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


def _ruby_to_python(src):
    src = _expand_oneliners(src)
    lines = src.split("\n")
    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue

        if raw == "end":
            ind = max(0, ind - 1)
            continue

        m = re.match(r"def\s+(\w+)\s*\(?([^)]*?)\)?\s*$", raw)
        if m:
            args = ", ".join(
                a.strip() for a in m.group(2).split(",") if a.strip())
            emit(f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # --- normal patch: ruby module ---
        m = re.match(r"module\s+(\w+)\s*$", raw)
        if m:
            emit(f"class {m.group(1)}:")
            ind += 1
            continue

        m = re.match(r"for\s+(\w+)\s+in\s+(\d+)\.\.(\d+)\s*$", raw)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue

        m = re.match(r"for\s+(\w+)\s+in\s+(\d+)\.\.\.(\d+)\s*$", raw)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {b}):")
            ind += 1
            continue

        m = re.match(r"\(\s*(\d+)\.\.(\d+)\s*\)\.each\s+do\s*\|(\w+)\|\s*$", raw)
        if m:
            a, b, v = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue

        m = re.match(r"while\s+(.+?)\s*$", raw)
        if m:
            emit(f"while {_ruby_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s+(.+?)\s*$", raw)
        if m:
            emit(f"if {_ruby_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"elsif\s+(.+?)\s*$", raw)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_ruby_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        if raw == "else":
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        m = re.match(r"return\s*(.*?)\s*$", raw)
        if m:
            val = m.group(1).strip()
            if val:
                emit(f"return {_ruby_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"puts\s+(.+?)\s*$", raw)
        if m:
            arg = m.group(1).strip()
            if arg.startswith(("\"", "'")):
                emit(f"print({_ruby_expr_to_py(arg)})")
            else:
                emit(f"print({_ruby_expr_to_py(arg)})")
            continue

        m = re.match(r"print\s+(.+?)\s*$", raw)
        if m:
            emit(f"print({_ruby_expr_to_py(m.group(1))}, end='')")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)$", raw)
        if m:
            emit(f"{m.group(1)} = {_ruby_expr_to_py(m.group(2))}")
            continue

        continue

    return "\n".join(out) + "\n"



def ruby_print(text):
    if not text:
        return ""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'puts {json.dumps(ln, ensure_ascii=False)}' for ln in lines) + "\n"


def ruby_gen_numbers():
    return "for i in 1..10\n  puts i\nend\n"


def ruby_gen_squares():
    return "for i in 1..10\n  puts i * i\nend\n"


def ruby_gen_cubes():
    return "for i in 1..10\n  puts i * i * i\nend\n"


def ruby_gen_table7():
    return "for i in 1..10\n  puts i * 7\nend\n"


def ruby_gen_factorial():
    return ("r = 1\n"
            "for i in 1..5\n"
            "  r = r * i\n"
            "end\n"
            "puts r\n")


def ruby_gen_fib():
    return ("a = 0\n"
            "b = 1\n"
            "for i in 1..10\n"
            "  puts a\n"
            "  c = a + b\n"
            "  a = b\n"
            "  b = c\n"
            "end\n")


def ruby_gen_50():
    parts = []
    for k in range(1, 11):
        parts.append(f'puts "=== {k} x {k} ==="')
        for i in range(1, 6):
            parts.append(f"puts {i} * {k}")
    return "\n".join(parts) + "\n"


def ruby_gen_200():
    parts = []
    for k in range(2, 12):
        parts.append(f'puts "=== Таблица {k} ==="')
        for i in range(1, 11):
            parts.append(f"puts {i} * {k}")
    return "\n".join(parts) + "\n"


def ruby_generate(output):
    if not output:
        return 'puts ""\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'puts {json.dumps(ln, ensure_ascii=False)}' for ln in lines) + "\n"



def ruby_print(text):
    if not text:
        return ""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'puts {json.dumps(ln, ensure_ascii=False)}' for ln in lines) + "\n"


def ruby_gen_numbers():
    return "for i in 1..10\n  puts i\nend\n"


def ruby_gen_squares():
    return "for i in 1..10\n  puts i * i\nend\n"


def ruby_gen_cubes():
    return "for i in 1..10\n  puts i * i * i\nend\n"


def ruby_gen_table7():
    return "for i in 1..10\n  puts i * 7\nend\n"


def ruby_gen_factorial():
    return ("r = 1\n"
            "for i in 1..5\n"
            "  r = r * i\n"
            "end\n"
            "puts r\n")


def ruby_gen_fib():
    return ("a = 0\n"
            "b = 1\n"
            "for i in 1..10\n"
            "  puts a\n"
            "  c = a + b\n"
            "  a = b\n"
            "  b = c\n"
            "end\n")


def ruby_gen_50():
    parts = []
    for k in range(1, 11):
        parts.append(f'puts "=== {k} x {k} ==="')
        for i in range(1, 6):
            parts.append(f"puts {i} * {k}")
    return "\n".join(parts) + "\n"


def ruby_gen_200():
    parts = []
    for k in range(2, 12):
        parts.append(f'puts "=== Таблица {k} ==="')
        for i in range(1, 11):
            parts.append(f"puts {i} * {k}")
    return "\n".join(parts) + "\n"


def ruby_generate(output):
    if not output:
        return 'puts ""\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'puts {json.dumps(ln, ensure_ascii=False)}' for ln in lines) + "\n"




class RubyLang(Language):
    name = "ruby"
    title = "Ruby"
    category = "О"
    ext = ".rb"
    keywords = ["def", "if", "elsif", "else", "end", "for", "while", "return", "true", "false", "nil", "puts", "print"]
    comment_regex = r"//[^\n]*"

    templates = {

        '[R1] Hello, World': 'puts "Hello, World!"',

        '[R2] Буква A': 'puts "A"',

        '[R3] Цифры 0-9': 'puts "0123456789"',

        '[R4] Hi!': 'puts "Hi!"',

        '[R5] Ruby': 'puts "Ruby"',

        '[R6] Алфавит A-J': 'puts "ABCDEFGHIJ"',

        '[R7] Арифметика': 'a = 17\nb = 5\nputs a + b\nputs a - b\nputs a * b\nputs a / b',

        '[R8] Условие': 'x = 7\nif x % 2 == 0\n  puts "чёт"\nelse\n  puts "нечёт"\nend',

        '[R9] Цикл for': 'for i in 1..5\n  puts i\nend',

        '[R10] Сумма 1..10': 's = 0\nfor i in 1..10\n  s = s + i\nend\nputs s',

        '[R11] Функция square': 'def square(x)\n  return x * x\nend\nputs square(7)\nputs square(12)\nputs square(25)',

        '[R12] Две функции': 'def double_(x)\n  return x * 2\nend\ndef square(x)\n  return x * x\nend\nputs double_(5)\nputs square(5)\nputs double_(square(3))',

        '[R13] Факториал': 'r = 1\nfor i in 1..5\n  r = r * i\nend\nputs r',

        '[R14] Fibonacci': 'a = 0\nb = 1\nfor i in 1..15\n  puts a\n  c = a + b\n  a = b\n  b = c\nend',

        '[R15] Сумма квадратов': 's = 0\nfor i in 1..10\n  s = s + i * i\nend\nputs s',

        '[R16] Вложенные циклы': 'for i in 1..3\n  for j in 1..3\n    puts i * j\n  end\nend',

        '[R17] Таблица ×7': 'k = 7\nfor i in 1..10\n  puts i * k\nend',

        '[R18] Степени двойки': 'p = 1\nfor i in 1..10\n  puts p\n  p = p * 2\nend',

        '[R19] Сумма 1..100': 's = 0\nfor i in 1..100\n  s = s + i\nend\nputs s',

        '[R20] Таблица 10×10': 'for i in 1..10\n  for j in 1..10\n    puts i * j\n  end\nend',

        '[Test 1] Базовые конструкции': 'a = 10\nb = 3\nputs a + b\nputs a - b\nputs a * b\nfor i in 1..3\n  puts i\nend',

        '[Test 2] Всё в одном': 's = "Hello"\nx = 10\ny = 20\ntotal = x + y\nputs s.length\nputs s.upcase\nputs x\nputs y\nputs total\nputs total * 2',

        '[Test 3] Функции + циклы': 'def double_(x)\n  return x * 2\nend\ns = 0\nfor i in 1..5\n  s = s + i\nend\nputs s\nputs double_(s)\nfor i in 1..3\n  puts i\nend',

    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _ruby_to_python(src)
        try:
            return _run_python(py)
        except Exception as e:
            return f"// Ruby: {type(e).__name__}: {e}"

    def generate_code(self, output):
        return ruby_generate(output)


TRANSPILERS[("ruby", "python")] = _ruby_to_python
