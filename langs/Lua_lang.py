# langs/Lua_lang.py
"""Lua — обычный язык."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS
from core.test_gen import gen_lua_50, gen_lua_200
from core.standard_templates import std_lua



def _lua_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnil\b", "None", e)
    e = re.sub(r"#(\w+)", r"len(\1)", e)
    e = e.replace("~=", "!=")
    e = re.sub(r"string\.upper\(([^)]+)\)", r"(\1).upper()", e)
    e = re.sub(r"string\.lower\(([^)]+)\)", r"(\1).lower()", e)
    e = re.sub(r"string\.len\(([^)]+)\)", r"len(\1)", e)
    e = re.sub(r"string\.sub\(([^,]+),\s*([^,)]+),\s*([^)]+)\)", r"\1[\2-1:\3]", e)
    e = re.sub(r"string\.sub\(([^,]+),\s*([^)]+)\)", r"\1[\2-1:]", e)
    e = re.sub(r"string\.find\(([^,]+),\s*([^)]+)\)", r"\1.find(\2)", e)
    e = re.sub(r"string\.gsub\(([^,]+),\s*([^,]+),\s*([^)]+)\)", r"\1.replace(\2, \3)", e)
    e = re.sub(r"string\.rep\(([^,]+),\s*([^)]+)\)", r"\1 * \2", e)
    e = re.sub(r"tonumber\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"tostring\(([^)]+)\)", r"str(\1)", e)
    e = re.sub(r"math\.floor\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"math\.ceil\(([^)]+)\)", r"__import__('math').ceil(\1)", e)
    e = re.sub(r"math\.abs\(([^)]+)\)", r"abs(\1)", e)
    e = re.sub(r"math\.min\(([^,]+),\s*([^)]+)\)", r"min(\1, \2)", e)
    e = re.sub(r"math\.max\(([^,]+),\s*([^)]+)\)", r"max(\1, \2)", e)
    e = re.sub(r"math\.sqrt\(([^)]+)\)", r"((\1) ** 0.5)", e)
    e = re.sub(r"table\.concat\(([^,]+),\s*([^)]+)\)", r"\2.join(\1)", e)
    e = re.sub(r"table\.sort\(([^)]+)\)", r"\1.sort()", e)
    return e

def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    return False


def _expand_oneliners(src):
    """`if cond then stmt end` → `if cond then\\nstmt\\nend`."""
    for _ in range(5):
        new = re.sub(
            r"(\b(?:if|for|while)\b[^\n]*?\b(?:then|do))\s+"
            r"([^\n]+?)\s+(end)\b",
            r"\1\n\2\n\3", src)
        if new == src:
            break
        src = new
    return src


# --- normal patch: lua metatable ---
def _stub_lua_meta(src):
    src = re.sub(r"setmetatable\s*\(([^,]+),\s*([^)]+)\)",
                 r"# setmetatable(\1, \2)", src)
    return src


def _lua_to_python(src):
    src = _stub_lua_meta(src)
    src = _expand_oneliners(src)
    lines = src.splitlines()
    out = []
    ind = 0

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("--"):
            continue

        m = re.match(
            r"for\s+(\w+)\s*=\s*(.+?)\s*,\s*(.+?)\s+do\s*$", line)
        if m:
            var = m.group(1)
            a = _lua_expr_to_py(m.group(2))
            b = _lua_expr_to_py(m.group(3))
            out.append("    " * ind +
                       f"for {var} in range({a}, ({b}) + 1):")
            ind += 1
            continue

        m = re.match(
            r"for\s+_,\s*(\w+)\s+in\s+ipairs\((\w+)\)\s+do\s*$", line)
        if m:
            out.append("    " * ind + f"for {m.group(1)} in {m.group(2)}:")
            ind += 1
            continue

        m = re.match(r"while\s+(.+?)\s+do\s*$", line)
        if m:
            out.append("    " * ind +
                       f"while {_lua_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s+(.+?)\s+then\s*$", line)
        if m:
            out.append("    " * ind +
                       f"if {_lua_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"elseif\s+(.+?)\s+then\s*$", line)
        if m:
            ind = max(0, ind - 1)
            out.append("    " * ind +
                       f"elif {_lua_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        if line == "else":
            ind = max(0, ind - 1)
            out.append("    " * ind + "else:")
            ind += 1
            continue

        if line == "end":
            ind = max(0, ind - 1)
            continue

        m = re.match(
            r"local\s+(\w+)\s*,\s*(\w+)\s*=\s*(.+?)\s*,\s*(.+)$", line)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} = {_lua_expr_to_py(m.group(3))}")
            out.append("    " * ind +
                       f"{m.group(2)} = {_lua_expr_to_py(m.group(4))}")
            continue

        m = re.match(r"local\s+(\w+)\s*=\s*(.+)$", line)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} = {_lua_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"print\s*\((.*)\)\s*$", line)
        if m:
            out.append("    " * ind +
                       f"print({_lua_expr_to_py(m.group(1))})")
            continue

        m = re.match(r"return\s+(.+)$", line)
        if m:
            out.append("    " * ind +
                       f"return {_lua_expr_to_py(m.group(1))}")
            continue

        m = re.match(r"table\.insert\((\w+),\s*(.+)\)", line)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)}.append({_lua_expr_to_py(m.group(2))})")
            continue

        m = re.match(r"table\.remove\((\w+)\)", line)
        if m:
            out.append("    " * ind + f"{m.group(1)}.pop()")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+)$", line)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} = {_lua_expr_to_py(m.group(2))}")
            continue

        continue

    return "\n".join(out) + "\n"


class LuaLang(Language):
    name = "lua"
    title = "Lua"
    category = "О"
    ext = ".lua"
    keywords = [
        "local", "function", "if", "then", "else", "elseif", "end",
        "for", "while", "do", "return", "print",
        "true", "false", "nil", "and", "or", "not",
    ]
    comment_regex = r"--[^\n]*"

    templates = {
        '[E1] Hello, World': 'print("Hello, World!")',
        '[E2] Арифметика': 'local a = 17\nlocal b = 5\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)\nprint(a % b)',
        '[E3] Строки': 'local s = "Programming"\nprint(#s)\nprint(string.upper(s))\nprint(string.lower(s))\nprint(string.sub(s, 1, 4))',
        '[E4] Условие': 'local x = 7\nif x % 2 == 0 then\n    print("чёт")\nelse\n    print("нечёт")\nend',
        '[E5] Квадраты': 'local x = 7\nprint(x * x)\nprint(x * x * x)\nprint(x + 100)',
        '[M1] Цикл for': 'for i = 1, 5 do\n    print(i)\nend',
        '[M2] Цикл while (факториал)': 'local n = 5\nlocal fact = 1\nwhile n > 1 do\n    fact = fact * n\n    n = n - 1\nend\nprint(fact)',
        '[M3] Факториал (for)': 'local fact = 1\nfor i = 1, 5 do\n    fact = fact * i\nend\nprint(fact)',
        '[M4] Sum и prod': 'local sum = 0\nlocal prod = 1\nfor i = 1, 6 do\n    sum = sum + i\n    prod = prod * i\nend\nprint(sum)\nprint(prod)',
        '[M5] Сумма 1..10': 'local sum = 0\nfor i = 1, 10 do\n    sum = sum + i\nend\nprint(sum)',
        '[H1] Fibonacci (итеративный)': 'local a = 0\nlocal b = 1\nfor i = 1, 15 do\n    print(a)\n    local t = a + b\n    a = b\n    b = t\nend',
        '[H2] GCD (inline)': 'local a = 100\nlocal b = 25\nwhile b ~= 0 do\n    local t = b\n    b = a % b\n    a = t\nend\nprint(a)',
        '[H3] Сумма квадратов': 'local sum = 0\nfor i = 1, 10 do\n    sum = sum + i * i\nend\nprint(sum)',
        '[H4] Вложенные циклы': 'for i = 1, 3 do\n    for j = 1, 3 do\n        print(i * j)\n    end\nend',
        '[H5] Вложенная арифметика': 'local a = 3\nlocal b = 4\nlocal c = 5\nlocal r1 = (a + b) * c\nlocal r2 = a * b + c\nlocal r3 = a * (b + c)\nprint(r1)\nprint(r2)\nprint(r3)',
        '[W1] Таблица ×7': 'local k = 7\nfor i = 1, 10 do\n    print(i * k)\nend',
        '[W2] Квадраты и кубы': 'for i = 1, 10 do\n    print(i * i)\nend\nfor i = 1, 10 do\n    print(i * i * i)\nend',
        '[W3] Простые числа до 30': 'local n = 2\nwhile n <= 30 do\n    local prime = true\n    local d = 2\n    while d < n do\n        if n % d == 0 then\n            prime = false\n        end\n        d = d + 1\n    end\n    if prime then\n        print(n)\n    end\n    n = n + 1\nend',
        '[W4] Сумма 1..100': 'local sum = 0\nfor i = 1, 100 do\n    sum = sum + i\nend\nprint(sum)',
        '[W5] Таблица 10×10': 'for i = 1, 10 do\n    for j = 1, 10 do\n        print(i * j)\n    end\nend',
        '[T1] Базовые конструкции': 'local a = 10\nlocal b = 3\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)\nfor i = 1, 3 do\n    print(i)\nend',
        '[T2] Все структуры': 'local s = "Hello"\nlocal x = 10\nlocal y = 20\nlocal sum = x + y\nprint(#s)\nprint(string.upper(s))\nprint(x)\nprint(y)\nprint(sum)\nprint(sum * 2)',
        '[T3] Всё вместе': 'local n = 5\nlocal s = 0\nfor i = 1, 5 do\n    s = s + i\nend\nlocal d = s * 2\nlocal label = "Result"\nprint(s)\nprint(d)\nprint(#label)\nfor i = 1, 3 do\n    print(i)\nend',
    }
    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _lua_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<lua>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Lua: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return 'print("")\n'
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        return "\n".join(
            f"print({json.dumps(ln, ensure_ascii=False)})"
            for ln in lines) + "\n"


TRANSPILERS[("lua", "python")] = _lua_to_python
