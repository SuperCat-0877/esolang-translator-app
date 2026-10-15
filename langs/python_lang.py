# langs/python_lang.py
"""Python — обычный язык. Транспайлеры Python → {JS, TS, C++, Lua, Rivulet}."""

import re
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS
from core.idioms import (
    py_expr_to_js, py_expr_to_cpp, py_expr_to_lua,
    map_python_line_to_js, map_python_line_to_cpp, map_python_line_to_lua,
)
from core.standard_templates import std_python


# ==================================================================
#  КЛАСС
# ==================================================================
class PythonLang(Language):
    name = "python"
    title = "Python"
    category = "О"
    ext = ".py"

    keywords = [
        "def", "class", "if", "elif", "else", "for", "while", "return",
        "import", "from", "as", "print", "True", "False", "None",
        "and", "or", "not", "in", "is", "try", "except", "finally",
        "with", "lambda", "yield", "pass", "break", "continue",
    ]
    types = ["int", "str", "float", "bool", "list", "dict", "set", "tuple"]
    comment_regex = r"#[^\n]*"

    templates = {
        '[E1] Hello, World': 'print("Hello, World!")',
        '[E2] Арифметика': 'a, b = 17, 5\nprint(a+b, a-b, a*b, a//b, a%b, a**b)',
        '[E3] Строки и срезы': 's = "Python"\nprint(s[0], s[-1], s[1:4], s[::-1], len(s))',
        '[E4] Списки': 'xs = [3, 1, 4, 1, 5]\nprint(sum(xs), max(xs), min(xs), sorted(xs))',
        '[E5] Условие': 'x = 7\nprint("чёт" if x % 2 == 0 else "нечёт")',
        '[M1] Цикл for и range': 'for i in range(1, 6):\n    print(i, i*i)',
        '[M2] Функции и рекурсия': 'def fact(n):\n    return 1 if n <= 1 else n * fact(n-1)\nprint(fact(5))',
        '[M3] List comprehension': 'sq = [x*x for x in range(10)]\nev = [x for x in sq if x % 2 == 0]\nprint(sq, ev)',
        '[M4] Словари и множества': 'd = {"a": 1, "b": 2}\ns = {1, 2, 3}\nprint(d, s | {3,4}, d.get("c", 0))',
        '[M5] Исключения и finally': 'try:\n    x = 1 / 0\nexcept ZeroDivisionError as e:\n    print(f"Ошибка: {e}")\nfinally:\n    print("готово")',
        '[H1] Классы и магические методы': 'class Point:\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n    def __repr__(self):\n        return f"P({self.x},{self.y})"\n    def __add__(self, o):\n        return Point(self.x+o.x, self.y+o.y)\nprint(Point(1, 2) + Point(3, 4))',
        '[H2] Генераторы и yield': 'def fib():\n    a, b = 0, 1\n    while True:\n        yield a\n        a, b = b, a+b\nf = fib()\nprint([next(f) for _ in range(10)])',
        '[H3] Декораторы': 'import functools\ndef log(f):\n    @functools.wraps(f)\n    def w(*a, **k):\n        r = f(*a, **k)\n        print(f"{f.__name__}({a}) = {r}")\n        return r\n    return w\n@log\ndef add(x, y): return x + y\nadd(3, 4)',
        '[H4] itertools и collections': 'from itertools import combinations\nfrom collections import Counter\nprint(list(combinations("abc", 2)))\nprint(Counter("mississippi").most_common(3))',
        '[H5] Контекстный менеджер': 'class Ctx:\n    def __enter__(self):\n        print("enter"); return self\n    def __exit__(self, *a):\n        print("exit")\nwith Ctx() as c:\n    print("body")',
        '[W1] Метаклассы': 'class Meta(type):\n    def __new__(mcs, name, bases, d):\n        d["greet"] = lambda self: f"Hello from {name}"\n        return super().__new__(mcs, name, bases, d)\nclass A(metaclass=Meta): pass\nprint(A().greet())',
        '[W2] Асинхронность asyncio': 'import asyncio\nasync def fetch(i):\n    await asyncio.sleep(0.01)\n    return i*i\nasync def main():\n    r = await asyncio.gather(*[fetch(i) for i in range(5)])\n    print(r)\nasyncio.run(main())',
        '[W3] Дескрипторы': 'class Pos:\n    def __set_name__(self, owner, name): self.name = name\n    def __set__(self, obj, v):\n        if v < 0: raise ValueError("neg")\n        obj.__dict__[self.name] = v\n    def __get__(self, obj, _): return obj.__dict__[self.name]\nclass P:\n    x = Pos()\n    def __init__(self, x): self.x = x\nprint(P(5).x)',
        '[W4] Функциональщина': 'from functools import reduce, partial\nadd = lambda x, y: x + y\ninc = partial(add, 1)\nprint(list(map(inc, [1,2,3])), reduce(add, range(1,11)))',
        '[W5] type() и eval': 'MyClass = type("MyClass", (), {"x": 42, "hi": lambda self: "hi"})\nprint(MyClass().x, MyClass().hi())\nprint(eval("3 + 4 * 2"))',
        '[T1] Все базовые конструкции': 'def gcd(a, b):\n    while b: a, b = b, a%b\n    return a\nfor x, y in [(12,8),(17,5),(100,25)]:\n    print(x, y, gcd(x, y))',
        '[T2] Все структуры данных': 'xs = [1,2,3]\nt = (1,2,3)\ns = {1,2,3}\nd = {"a": 1}\ng = (x*x for x in range(5))\nprint(xs, t, s, d, list(g))',
        '[T3] Всё вместе': 'import functools, asyncio\nclass Cache:\n    def __init__(self): self.d = {}\n    def __call__(self, f):\n        @functools.wraps(f)\n        def w(*a):\n            if a not in self.d: self.d[a] = f(*a)\n            return self.d[a]\n        return w\n@Cache()\ndef fib(n): return n if n < 2 else fib(n-1)+fib(n-2)\nasync def go():\n    await asyncio.sleep(0)\n    return [fib(i) for i in range(10)]\nprint(asyncio.run(go()))',
    }

    def execute(self, src):
        if not src:
            return ""
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(src, "<src>", "exec"), {"__name__": "__main__"})
        except Exception as e:
            sys.stdout = old
            return f"// Python: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return "# исходный код не дал вывода\n"
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        return "\n".join(f"print({ln!r})" for ln in lines) + "\n"


# ==================================================================
#  УТИЛИТЫ
# ==================================================================
def _indent(level):
    return "    " * level


def _split_args(s):
    parts = []
    depth = 0
    cur = ""
    for ch in s:
        if ch in "([":
            depth += 1
            cur += ch
        elif ch in ")]":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _parse_range(args_str):
    parts = _split_args(args_str)
    if len(parts) == 1:
        return "0", parts[0]
    return parts[0], parts[1]


def _convert_expr_js(expr):
    return py_expr_to_js(expr)


def _convert_expr_cpp(expr):
    return py_expr_to_cpp(expr)


def _convert_expr_lua(expr):
    return py_expr_to_lua(expr)


# ==================================================================
#  PYTHON → JavaScript
# ==================================================================
def _py_to_js(src):
    lines = src.splitlines()
    out = []
    ind = 0
    declared = set()

    def emit(s):
        out.append(_indent(ind) + s)

    for raw in lines:
        line = raw.strip()
        if not line:
            out.append("")
            continue
        if line.startswith("#"):
            emit("// " + line[1:].strip())
            continue
        if line.startswith("import ") or line.startswith("from "):
            emit("// " + line)
            continue

        # class
        m = re.match(r"class\s+(\w+)(?:\(([^)]*)\))?\s*:", line)
        if m:
            name = m.group(1)
            base = m.group(2) or ""
            emit(f"class {name} extends {base} {{" if base else f"class {name} {{")
            ind += 1
            continue

        # def
        m = re.match(r"def\s+(\w+)\s*\(([^)]*)\)\s*:", line)
        if m:
            args = ", ".join(a.strip() for a in m.group(2).split(",") if a.strip())
            emit(f"function {m.group(1)}({args}) {{")
            ind += 1
            continue

        # for i in range(...)
        m = re.match(r"for\s+(\w+)\s+in\s+range\s*\((.+)\)\s*:\s*$", line)
        if m:
            v = m.group(1)
            start, end = _parse_range(m.group(2))
            emit(f"for (let {v} = {start}; {v} < {end}; {v}++) {{")
            ind += 1
            continue

        # for x in data:
        m = re.match(r"for\s+(\w+)\s+in\s+(\w+)\s*:\s*$", line)
        if m:
            v, coll = m.group(1), m.group(2)
            emit(f"for (let {v} of {coll}) {{")
            ind += 1
            continue

        # while
        m = re.match(r"while\s+(.+?)\s*:", line)
        if m:
            emit(f"while ({_convert_expr_js(m.group(1))}) {{")
            ind += 1
            continue

        # if / elif / else
        m = re.match(r"if\s+(.+?)\s*:", line)
        if m:
            emit(f"if ({_convert_expr_js(m.group(1))}) {{")
            ind += 1
            continue
        m = re.match(r"elif\s+(.+?)\s*:", line)
        if m:
            ind -= 1
            emit(f"}} else if ({_convert_expr_js(m.group(1))}) {{")
            ind += 1
            continue
        if line == "else:":
            ind -= 1
            emit("} else {")
            ind += 1
            continue

        # return
        m = re.match(r"return\s*(.*)$", line)
        if m:
            emit(f"return {_convert_expr_js(m.group(1))};")
            continue

        # print
        m = re.match(r"print\s*\((.*)\)\s*$", line)
        if m:
            emit(f"console.log({_convert_expr_js(m.group(1))});")
            continue

        # методы списков
        mapped = map_python_line_to_js(line)
        if mapped != line:
            m = re.match(r"(\w+(?:\.\w+)?)\s*=\s*(.+)$", mapped)
            if m:
                emit(f"let {m.group(1)} = {_convert_expr_js(m.group(2))};")
            else:
                emit(_convert_expr_js(mapped) + ";")
            continue

        # x = [список]
        m = re.match(r"(\w+)\s*=\s*\[(.*)\]$", line)
        if m:
            emit(f"let {m.group(1)} = [{m.group(2)}];")
            declared.add(m.group(1))
            continue

        # x += / -=
        m = re.match(r"(\w+(?:\[[^\]]+\])?)\s*([+\-*/])=\s*(.+)$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_convert_expr_js(m.group(3))};")
            continue

        # x = expr
        m = re.match(r"(\w+(?:\[[^\]]+\])?)\s*=\s*(.+)$", line)
        if m:
            target = m.group(1)
            expr = _convert_expr_js(m.group(2))
            base = target.split("[")[0]
            if base not in declared and "[" not in target:
                emit(f"let {target} = {expr};")
                declared.add(base)
            else:
                emit(f"{target} = {expr};")
            continue

        # вызов
        m = re.match(r"(\w+)\s*\((.*)\)\s*$", line)
        if m:
            emit(f"{m.group(1)}({_convert_expr_js(m.group(2))});")
            continue

        continue

    while ind > 0:
        ind -= 1
        out.append(_indent(ind) + "}")

    return "\n".join(out) + "\n"


# ==================================================================
#  PYTHON → C++
# ==================================================================
def _py_to_cpp(src):
    lines = src.splitlines()
    out = []
    ind = 1
    declared = set()
    list_vars = set()

    def emit(s):
        out.append(_indent(ind) + s)

    for raw in lines:
        line = raw.strip()
        if not line:
            out.append("")
            continue
        if line.startswith("#"):
            emit("// " + line[1:].strip())
            continue
        if line.startswith("import ") or line.startswith("from "):
            emit("// " + line)
            continue

        m = re.match(r"class\s+(\w+)(?:\(([^)]*)\))?\s*:", line)
        if m:
            base = m.group(2) or ""
            emit(f"class {m.group(1)}" + (f" : public {base}" if base else "") + " {")
            ind += 1
            continue

        m = re.match(r"def\s+(\w+)\s*\(([^)]*)\)\s*:", line)
        if m:
            args = ", ".join(f"int {a.strip()}"
                             for a in m.group(2).split(",") if a.strip())
            emit(f"int {m.group(1)}({args}) {{")
            ind += 1
            continue

        m = re.match(r"for\s+(\w+)\s+in\s+range\s*\((.+)\)\s*:\s*$", line)
        if m:
            v = m.group(1)
            start, end = _parse_range(m.group(2))
            emit(f"for (int {v} = {start}; {v} < {end}; {v}++) {{")
            ind += 1
            continue

        m = re.match(r"for\s+(\w+)\s+in\s+(\w+)\s*:\s*$", line)
        if m:
            emit(f"for (auto {m.group(1)} : {m.group(2)}) {{")
            ind += 1
            continue

        m = re.match(r"while\s+(.+?)\s*:", line)
        if m:
            emit(f"while ({_convert_expr_cpp(m.group(1))}) {{")
            ind += 1
            continue

        m = re.match(r"if\s+(.+?)\s*:", line)
        if m:
            emit(f"if ({_convert_expr_cpp(m.group(1))}) {{")
            ind += 1
            continue
        m = re.match(r"elif\s+(.+?)\s*:", line)
        if m:
            ind -= 1
            emit(f"}} else if ({_convert_expr_cpp(m.group(1))}) {{")
            ind += 1
            continue
        if line == "else:":
            ind -= 1
            emit("} else {")
            ind += 1
            continue

        m = re.match(r"return\s*(.*)$", line)
        if m:
            emit(f"return {_convert_expr_cpp(m.group(1))};")
            continue

        m = re.match(r"print\s*\((.*)\)\s*$", line)
        if m:
            arg = m.group(1).strip()
            if arg in list_vars:
                emit(f"for (auto v : {arg}) std::cout << v << \" \";")
                emit("std::cout << std::endl;")
            elif "," in arg and not any(c in arg for c in "(["):
                parts = [p.strip() for p in arg.split(",")]
                body = ' << " " << '.join(_convert_expr_cpp(p) for p in parts)
                emit(f"std::cout << {body} << std::endl;")
            else:
                emit(f"std::cout << {_convert_expr_cpp(arg)} << std::endl;")
            continue

        if (line.count("=") == 1 and "==" not in line and "<=" not in line
                and ">=" not in line and "!=" not in line and "=" in line):
            lhs_str, rhs_str = line.split("=", 1)
            if "," in lhs_str and "," in rhs_str:
                lhs_items = _split_args(lhs_str)
                rhs_items = _split_args(rhs_str)
                if len(lhs_items) == 2 and len(rhs_items) == 2:
                    if lhs_items[0] == rhs_items[1] and lhs_items[1] == rhs_items[0]:
                        emit(f"std::swap({lhs_items[0]}, {lhs_items[1]});")
                    else:
                        emit(f"auto _t1 = {_convert_expr_cpp(rhs_items[0])};")
                        emit(f"auto _t2 = {_convert_expr_cpp(rhs_items[1])};")
                        emit(f"{lhs_items[0]} = _t1;")
                        emit(f"{lhs_items[1]} = _t2;")
                    continue

        mapped = map_python_line_to_cpp(line)
        if mapped != line:
            m = re.match(r"(\w+)\.(\w+)\(.*\)$", mapped)
            if m:
                emit(_convert_expr_cpp(mapped) + ";")
            else:
                emit(mapped + ";")
            continue

        m = re.match(r"(\w+(?:\[[^\]]+\])?)\s*([+\-*/])=\s*(.+)$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_convert_expr_cpp(m.group(3))};")
            continue

        m = re.match(r"(\w+)\s*=\s*\[(.*)\]$", line)
        if m:
            emit(f"std::vector<int> {m.group(1)} = {{{m.group(2)}}};")
            declared.add(m.group(1))
            list_vars.add(m.group(1))
            continue

        m = re.match(r"(\w+(?:\[[^\]]+\])?)\s*=\s*(.+)$", line)
        if m:
            target = m.group(1)
            expr = _convert_expr_cpp(m.group(2))
            base = target.split("[")[0]
            if base not in declared and "[" not in target:
                emit(f"auto {target} = {expr};")
                declared.add(base)
            else:
                emit(f"{target} = {expr};")
            continue

        m = re.match(r"(\w+)\s*\((.*)\)\s*$", line)
        if m:
            emit(f"{m.group(1)}({_convert_expr_cpp(m.group(2))});")
            continue

        continue

    while ind > 1:
        ind -= 1
        out.append(_indent(ind) + "}")

    header = (
        "#include <iostream>\n"
        "#include <string>\n"
        "#include <vector>\n"
        "#include <algorithm>\n"
        "#include <utility>\n\n"
    )
    return header + "int main() {\n" + "\n".join(out) + "\n    return 0;\n}\n"


# ==================================================================
#  PYTHON → Lua
# ==================================================================
def _py_to_lua(src):
    lines = src.splitlines()
    out = []
    ind = 0

    def emit(s):
        out.append(_indent(ind) + s)

    for raw in lines:
        line = raw.strip()
        if not line:
            out.append("")
            continue
        if line.startswith("#"):
            emit("-- " + line[1:].strip())
            continue
        if line.startswith("import ") or line.startswith("from "):
            emit("-- " + line)
            continue

        m = re.match(r"def\s+(\w+)\s*\(([^)]*)\)\s*:", line)
        if m:
            args = ", ".join(a.strip() for a in m.group(2).split(",") if a.strip())
            emit(f"function {m.group(1)}({args})")
            ind += 1
            continue

        m = re.match(r"for\s+(\w+)\s+in\s+range\s*\((.+)\)\s*:\s*$", line)
        if m:
            v = m.group(1)
            start, end = _parse_range(m.group(2))
            emit(f"for {v} = {start}, ({end}) - 1 do")
            ind += 1
            continue

        m = re.match(r"for\s+(\w+)\s+in\s+(\w+)\s*:\s*$", line)
        if m:
            emit(f"for _, {m.group(1)} in ipairs({m.group(2)}) do")
            ind += 1
            continue

        m = re.match(r"while\s+(.+?)\s*:", line)
        if m:
            emit(f"while {_convert_expr_lua(m.group(1))} do")
            ind += 1
            continue

        m = re.match(r"if\s+(.+?)\s*:", line)
        if m:
            emit(f"if {_convert_expr_lua(m.group(1))} then")
            ind += 1
            continue
        m = re.match(r"elif\s+(.+?)\s*:", line)
        if m:
            ind -= 1
            emit(f"elseif {_convert_expr_lua(m.group(1))} then")
            ind += 1
            continue
        if line == "else:":
            ind -= 1
            emit("else")
            ind += 1
            continue

        m = re.match(r"return\s*(.*)$", line)
        if m:
            emit(f"return {_convert_expr_lua(m.group(1))}")
            continue

        m = re.match(r"print\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_convert_expr_lua(m.group(1))})")
            continue

        mapped = map_python_line_to_lua(line)
        if mapped != line:
            emit(mapped)
            continue

        m = re.match(r"(\w+)\s*=\s*\[(.*)\]$", line)
        if m:
            emit(f"local {m.group(1)} = {{{m.group(2)}}}")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+)$", line)
        if m:
            tgt, op, rhs = m.group(1), m.group(2), _convert_expr_lua(m.group(3))
            emit(f"{tgt} = {tgt} {op} {rhs}")
            continue

        m = re.match(r"(\w+(?:\[[^\]]+\])?)\s*=\s*(.+)$", line)
        if m:
            target = m.group(1)
            expr = _convert_expr_lua(m.group(2))
            if "[" not in target:
                emit(f"local {target} = {expr}")
            else:
                emit(f"{target} = {expr}")
            continue

        m = re.match(r"(\w+)\s*\((.*)\)\s*$", line)
        if m:
            emit(f"{m.group(1)}({_convert_expr_lua(m.group(2))})")
            continue

        continue

    while ind > 0:
        ind -= 1
        out.append(_indent(ind) + "end")

    return "\n".join(out) + "\n"


# ==================================================================
#  РЕГИСТРАЦИЯ
# ==================================================================
TRANSPILERS[("python", "javascript")] = _py_to_js
TRANSPILERS[("python", "typescript")] = _py_to_js
TRANSPILERS[("python", "cpp")] = _py_to_cpp
TRANSPILERS[("python", "lua")] = _py_to_lua

try:
    from core.py_to_rivulet import py_to_rivulet as _py_to_riv
    TRANSPILERS[("python", "rivulet")] = _py_to_riv
except Exception:
    pass
