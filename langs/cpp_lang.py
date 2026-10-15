# langs/cpp_lang.py
"""C++ — обычный язык. Транспайлер C++ → Python со STL и классами."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS
from core.test_gen import gen_cpp_50, gen_cpp_200
from core.c_trans import cpp_to_python
from core.standard_templates import std_cpp



def _convert_stl(src):
    """std::vector<T>, std::map<K,V>, std::string → Python."""
    S = r"(?:std::)?"
    src = re.sub(rf"{S}vector<\w+>\s+(\w+)\s*=\s*\{{([^}}]*)\}}\s*;",
                 r"\1 = [\2];", src)
    src = re.sub(rf"{S}vector<\w+>\s+(\w+)\s*;", r"\1 = [];", src)
    src = re.sub(rf"{S}map<\w+,\s*\w+>\s+(\w+)\s*;", r"\1 = {};", src)
    src = re.sub(rf"{S}set<\w+>\s+(\w+)\s*;", r"\1 = set();", src)
    src = re.sub(rf"{S}string\s+(\w+)\s*=\s*", r"\1 = ", src)
    src = re.sub(rf"{S}string\s+(\w+)\s*;", r"\1 = '';", src)
    src = re.sub(rf"{S}pair<\w+,\s*\w+>\s+(\w+)\s*=\s*\{{([^,}}]+),\s*([^}}]+)\}}\s*;",
                 r"\1 = (\2, \3);", src)
    return src


def _split_by_op(s, op):
    """Разбивает по многосимвольному op вне строк и скобок."""
    parts, buf, depth, in_str = [], [], 0, None
    i = 0
    while i < len(s):
        ch = s[i]
        if in_str:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(s):
                buf.append(s[i + 1])
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
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
        elif depth == 0 and s.startswith(op, i):
            parts.append("".join(buf))
            buf = []
            i += len(op)
            continue
        else:
            buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf))
    return parts


def _protect_cpp_strings(src):
    """Заменяет ; и << внутри строк на маркеры. Возвращает (текст, словарь)."""
    MARK_SEMI = "\x01S\x01"
    MARK_LT   = "\x01L\x01"
    out = []
    in_str = None
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if in_str:
            if c == "\\" and i + 1 < n:
                out.append(c); out.append(src[i + 1])
                i += 2; continue
            if c == in_str:
                in_str = None
                out.append(c); i += 1; continue
            if src.startswith(";", i):
                out.append(MARK_SEMI); i += 1; continue
            if src.startswith("<<", i):
                out.append(MARK_LT); i += 2; continue
            out.append(c); i += 1; continue
        if c == '"' or c == "'":
            in_str = c; out.append(c); i += 1; continue
        out.append(c); i += 1
    return "".join(out), MARK_SEMI, MARK_LT


def _restore_cpp_strings(text, mark_semi, mark_lt):
    return text.replace(mark_semi, ";").replace(mark_lt, "<<")


def _rewrite_cout(src):
    """cout << A << "B; C"; → print(A, "B; C", sep='', end='')

    PATCH: ; и << внутри строк защищены маркерами, чтобы regex
    не рвал выражение по ; и не путал << внутри строк с оператором.
    """
    protected, M_SEMI, M_LT = _protect_cpp_strings(src)

    def repl(m):
        body = m.group(1)
        # Восстановить << для корректного split
        body_for_split = body.replace(M_LT, "<<")
        parts = _split_by_op(body_for_split, "<<")
        args = []
        for p in parts:
            if not p.strip():
                continue
            # Восстановить оригинальные ; и << в аргументе
            p2 = p.replace(M_SEMI, ";").replace(M_LT, "<<")
            args.append(_cpp_expr(p2.strip()))
        return f"print({', '.join(args)}, sep='', end='')"

    result = re.sub(r"(?:std::)?cout\s*<<\s*(.+?)\s*;", repl, protected)
    return _restore_cpp_strings(result, M_SEMI, M_LT)


def _convert_std(src):
    """std::stoi/stod/to_string/abs/min/max → Python."""
    S = r"(?:std::)?"
    src = re.sub(rf"\b{S}stoi\(([^)]+)\)", r"int(\1)", src)
    src = re.sub(rf"\b{S}stod\(([^)]+)\)", r"float(\1)", src)
    src = re.sub(rf"\b{S}stof\(([^)]+)\)", r"float(\1)", src)
    src = re.sub(rf"\b{S}to_string\(([^)]+)\)", r"str(\1)", src)
    src = re.sub(rf"\b{S}abs\(([^)]+)\)", r"abs(\1)", src)
    src = re.sub(rf"\b{S}min\(([^,]+),\s*([^)]+)\)", r"min(\1, \2)", src)
    src = re.sub(rf"\b{S}max\(([^,]+),\s*([^)]+)\)", r"max(\1, \2)", src)
    return src


# --- normal patch: cpp templates ---
def _strip_cpp_templates(src):
    src = re.sub(r"template\s*<[^>]*>", "", src)
    return src


def _preprocess_cpp(src):
    src = _strip_cpp_templates(src)
    src = _expand_oneliners(src)
    src = _convert_stl(src)
    src = _convert_std(src)
    src = _rewrite_cout(src)
    src = _extract_classes(src)

    lines_out = []
    for line in src.split("\n"):
        for ch in _split_top_level(line, ";"):
            ch = ch.strip()
            if ch:
                lines_out.append(ch)

    final = []
    for line in lines_out:
        m = re.match(
            r"((?:unsigned\s+|signed\s+|const\s+|static\s+)*"
            r"(?:int|long|short|char|bool|double|float|string|auto|size_t))"
            r"\s+(.+)$", line)
        if m and "," in m.group(2):
            typ = m.group(1)
            decls = _split_top_level(m.group(2), ",")
            if len(decls) > 1 and all("=" in d for d in decls):
                for d in decls:
                    final.append(f"{typ} {d.strip()};")
                continue
        final.append(line + ("" if line.endswith((";", "{", "}"))
                             else ";"))
    return "\n".join(final)

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
    # while/for/if с одним выражением
    for _ in range(5):
        new = re.sub(
            r"(\b(?:while|for|if)\s*\([^()]*\))\s+([^;{}\n]+);",
            r"\1 {\n\2;\n}", src)
        if new == src:
            break
        src = new
    # PATCH: функции — тип имя(args) { body }
    # Регулярка ищет ЛЮБУЮ последовательность идентификаторов/типов,
    # потом имя, потом (args), потом { body } без вложенных {}.
    for _ in range(3):
        new = re.sub(
            r"((?:[\w:<>\*&\s]+?)\s+\w+\s*\([^)]*\))\s*"
            r"\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n    \2\n}", src)
        if new == src:
            break
        src = new
    return src


# --- STL-типы → Python ---
def _extract_classes(src):
    """Находит `class Foo { ... };` и превращает в Python-класс."""
    out = []
    lines = src.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()
        m = re.match(r"(?:class|struct)\s+(\w+)\s*(?::\s*public\s+(\w+))?\s*\{?", line)
        if not m:
            out.append(lines[i])
            i += 1
            continue

        cls_name = m.group(1)
        base = m.group(2)
        # Собираем тело класса до `};`
        body_lines = []
        depth = 1 if "{" in line else 0
        j = i + 1
        while j < n:
            l = lines[j]
            depth += l.count("{") - l.count("}")
            if depth <= 0:
                # Конец класса
                stripped = l.strip()
                if stripped and stripped != "};":
                    body_lines.append(l)
                break
            body_lines.append(l)
            j += 1

        # Разбираем тело
        py_lines = []
        py_lines.append(f"class {cls_name}({base}):" if base else f"class {cls_name}:")
        py_lines.append("    __slots__ = ()")

        # Поля и методы
        current_access = "public"
        constructor_done = False
        method_bodies = []
        fields = []

        k = 0
        while k < len(body_lines):
            bl = body_lines[k].strip()
            if bl in ("public:", "private:", "protected:"):
                current_access = bl.rstrip(":")
                k += 1
                continue

            # конструктор: Foo(args) { ... }
            cm = re.match(rf"{cls_name}\s*\(([^)]*)\)\s*\{{?", bl)
            if cm:
                args = ", ".join(
                    a.strip().split()[-1]
                    for a in cm.group(1).split(",") if a.strip())
                method_bodies.append(f"    def __init__(self{', ' + args if args else ''}):")
                constructor_done = True
                # Тело — до закрывающей `}`
                depth2 = 1
                k += 1
                while k < len(body_lines) and depth2 > 0:
                    inner = body_lines[k]
                    depth2 += inner.count("{") - inner.count("}")
                    if depth2 <= 0:
                        break
                    # Переводим тело
                    inner_py = _cpp_method_line(inner)
                    if inner_py:
                        method_bodies.append("        " + inner_py)
                    k += 1
                k += 1
                continue

            # метод: Ret name(args) { ... }
            mm = re.match(
                r"(?:static\s+)?(?:int|void|double|float|bool|string|"
                r"auto|[A-Z]\w*)\s+(\w+)\s*\(([^)]*)\)\s*(?:const)?\s*\{?",
                bl)
            if mm:
                method_name = mm.group(1)
                args = ", ".join(
                    a.strip().split()[-1]
                    for a in mm.group(2).split(",") if a.strip())
                method_bodies.append(
                    f"    def {method_name}(self{', ' + args if args else ''}):")
                depth2 = 1
                k += 1
                while k < len(body_lines) and depth2 > 0:
                    inner = body_lines[k]
                    depth2 += inner.count("{") - inner.count("}")
                    if depth2 <= 0:
                        break
                    inner_py = _cpp_method_line(inner)
                    if inner_py:
                        method_bodies.append("        " + inner_py)
                    k += 1
                k += 1
                continue

            # поле: int x; / string name;
            fm = re.match(
                r"(?:const\s+|static\s+)?"
                r"(?:int|long|short|char|bool|double|float|string|"
                r"vector<\w+>|map<\w+,\s*\w+>)\s+(\w+)\s*(?:=\s*(.+?))?\s*;",
                bl)
            if fm:
                field = fm.group(1)
                default = fm.group(2)
                if default:
                    fields.append((field, default))
                else:
                    fields.append((field, None))
                k += 1
                continue

            k += 1

        if not constructor_done:
            py_lines.append("    def __init__(self):")
            for name, default in fields:
                if default is not None:
                    py_lines.append(f"        self.{name} = {default}")
                else:
                    py_lines.append(f"        self.{name} = None")
        if method_bodies:
            # Убираем дублирующий __slots__
            pass

        py_lines = [py_lines[0], *method_bodies] if method_bodies else py_lines
        out.extend(py_lines)
        i = j + 1

    return "\n".join(out)


def _cpp_method_line(line):
    """Транслирует одну строку тела метода C++ в Python."""
    s = line.strip()
    if not s or s in ("{", "}"):
        return None
    # return expr;
    m = re.match(r"return\s*(.*?)\s*;?\s*$", s)
    if m:
        return f"return {_cpp_expr(m.group(1))}"
    # cout << ...
    m = re.match(r"(?:std::)?cout\s*<<\s*(.+?)\s*;", s)
    if m:
        return f"print({_cpp_expr(m.group(1))})"
    # this->x = expr
    m = re.match(r"this->(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"self.{m.group(1)} = {_cpp_expr(m.group(2))}"
    # x = expr
    m = re.match(r"(\w+)\s*=\s*(.+?)\s*;", s)
    if m:
        return f"{m.group(1)} = {_cpp_expr(m.group(2))}"
    # x++ / x--
    m = re.match(r"(\w+)\+\+\s*;", s)
    if m:
        return f"{m.group(1)} += 1"
    m = re.match(r"(\w+)--\s*;", s)
    if m:
        return f"{m.group(1)} -= 1"
    return None


def _cpp_expr(e):
    e = e.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnullptr\b", "None", e)
    # PATCH: endl → символ перевода строки как литерал "\n" (2 символа)
    def _repl_endl(m):
        return '"' + chr(92) + 'n"'
    e = re.sub(r"(?:std::)?endl\b", _repl_endl, e)
    e = re.sub(r"(?:std::)?cout", "print", e)
    e = re.sub(r"\bthis->", "self.", e)
    e = re.sub(r"(\w+)\.size\(\)", r"len(\1)", e)
    e = re.sub(r"(\w+)\.length\(\)", r"len(\1)", e)
    e = re.sub(r"(\w+)\.push_back\(([^()]*)\)", r"\1.append(\2)", e)
    e = re.sub(r"(\w+)\.pop_back\(\)", r"\1.pop()", e)
    e = re.sub(r"(\w+)\.empty\(\)", r"(len(\1) == 0)", e)
    e = re.sub(r"(\w+)\.front\(\)", r"\1[0]", e)
    e = re.sub(r"(\w+)\.back\(\)", r"\1[-1]", e)
    e = re.sub(r"(\w+)\.find\(([^)]+)\)\s*!=\s*\w+\.end\(\)",
               r"(\2 in \1)", e)
    e = re.sub(r"(\w+)\.insert\(\1\.begin\(\),\s*([^)]+)\)",
               r"\1.insert(0, \2)", e)
    e = re.sub(r"(\w+)\.substr\(([^,]+),\s*([^)]+)\)",
               r"\1[\2:\2+\3]", e)
    e = re.sub(r"(\w+)\.substr\(([^)]+)\)", r"\1[\2:]", e)
    e = re.sub(r"(\w+)\.at\(([^)]+)\)", r"\1[\2]", e)
    e = re.sub(r"(\w+)\.erase\(([^,]+),\s*([^)]+)\)",
               r"del \1[\2:\2+\3]", e)
    e = re.sub(r"(\w+)\.erase\(([^)]+)\)", r"\1.pop(\2)", e)
    e = re.sub(r"(\w+)\.clear\(\)", r"\1.clear()", e)
    e = re.sub(r"(?:std::)?stoi\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"(?:std::)?stod\(([^)]+)\)", r"float(\1)", e)
    e = re.sub(r"(?:std::)?stof\(([^)]+)\)", r"float(\1)", e)
    e = re.sub(r"(?:std::)?to_string\(([^)]+)\)", r"str(\1)", e)
    e = re.sub(r"(?:std::)?abs\(([^)]+)\)", r"abs(\1)", e)
    e = re.sub(r"(?:std::)?min\(([^,]+),\s*([^)]+)\)", r"min(\1, \2)", e)
    e = re.sub(r"(?:std::)?max\(([^,]+),\s*([^)]+)\)", r"max(\1, \2)", e)
    e = re.sub(r"(?:std::)?swap\(([^,]+),\s*([^)]+)\)",
               r"\1, \2 = \2, \1", e)
    e = re.sub(r"(?:std::)?sort\(([^,]+)\.begin\(\),\s*\1\.end\(\)\)",
               r"\1.sort()", e)
    e = re.sub(r"(?:std::)?reverse\(([^,]+)\.begin\(\),\s*\1\.end\(\)\)",
               r"\1.reverse()", e)
    return e

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


class CppLang(Language):
    name = "cpp"
    title = "C++"
    category = "О"
    ext = ".cpp"
    keywords = ["int", "float", "double", "char", "bool", "void", "long",
                "short", "if", "else", "for", "while", "do", "return",
                "switch", "case", "break", "continue", "class", "struct",
                "public", "private", "protected", "namespace", "using",
                "std", "cout", "cin", "endl", "const", "static",
                "vector", "map", "set", "string", "pair", "auto"]
    types = ["string", "vector", "map", "set", "pair", "auto", "size_t"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': '#include <iostream>\nusing namespace std;\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}',
        '[E2] Арифметика': '#include <iostream>\nusing namespace std;\nint main() {\n    int a = 17, b = 5;\n    cout << a + b << " " << a - b << " " << a * b << " " << a / b << " " << a % b << endl;\n    return 0;\n}',
        '[E3] Строки': '#include <iostream>\n#include <string>\nusing namespace std;\nint main() {\n    string s = "Hello, World";\n    cout << s.size() << endl;\n    cout << s.substr(0, 5) << endl;\n    return 0;\n}',
        '[E4] Вывод нескольких значений': '#include <iostream>\nusing namespace std;\nint main() {\n    int x = 7;\n    cout << "x = " << x << endl;\n    cout << "x * x = " << x * x << endl;\n    cout << "x + 100 = " << x + 100 << endl;\n    return 0;\n}',
        '[E5] Функция square': '#include <iostream>\nusing namespace std;\nint square(int x) {\n    return x * x;\n}\nint main() {\n    cout << square(7) << endl;\n    cout << square(12) << endl;\n    return 0;\n}',
        '[M1] Цикл while (числа и квадраты)': '#include <iostream>\nusing namespace std;\nint main() {\n    int i = 1;\n    while (i <= 5) {\n        cout << i << " " << i * i << endl;\n        i = i + 1;\n    }\n    return 0;\n}',
        '[M2] Цикл while': '#include <iostream>\nusing namespace std;\nint main() {\n    int n = 5;\n    int fact = 1;\n    while (n > 1) {\n        fact = fact * n;\n        n = n - 1;\n    }\n    cout << fact << endl;\n    return 0;\n}',
        '[M3] Вектор': '#include <iostream>\n#include <vector>\nusing namespace std;\nint main() {\n    vector<int> v = {10, 20, 30, 40, 50};\n    cout << v.size() << endl;\n    cout << v[0] + v[1] + v[2] + v[3] + v[4] << endl;\n    return 0;\n}',
        '[M4] Строковые методы': '#include <iostream>\n#include <string>\nusing namespace std;\nint main() {\n    string s = "Programming";\n    cout << s.size() << endl;\n    cout << s.substr(0, 4) << endl;\n    cout << s.substr(4, 7) << endl;\n    return 0;\n}',
        '[M5] Рекурсия': '#include <iostream>\nusing namespace std;\nint fact(int n) {\n    if (n <= 1) return 1;\n    return n * fact(n - 1);\n}\nint main() {\n    cout << fact(5) << endl;\n    cout << fact(7) << endl;\n    return 0;\n}',
        '[H1] Структура Point': '#include <iostream>\nusing namespace std;\nstruct Point {\n    int x;\n    int y;\n};\nint main() {\n    Point p;\n    p.x = 3;\n    p.y = 4;\n    cout << p.x + p.y << endl;\n    return 0;\n}',
        '[H2] Две функции': '#include <iostream>\nusing namespace std;\nint double_it(int x) {\n    return x * 2;\n}\nint square(int x) {\n    return x * x;\n}\nint main() {\n    cout << double_it(5) << endl;\n    cout << square(5) << endl;\n    cout << double_it(square(3)) << endl;\n    return 0;\n}',
        '[H3] Vector push_back': '#include <iostream>\n#include <vector>\nusing namespace std;\nint main() {\n    vector<int> v;\n    v.push_back(10);\n    v.push_back(20);\n    v.push_back(30);\n    cout << v.size() << endl;\n    cout << v[0] << endl;\n    cout << v[2] << endl;\n    return 0;\n}',
        '[H4] Вложенные вызовы': '#include <iostream>\nusing namespace std;\nint add(int a, int b) {\n    return a + b;\n}\nint mul(int a, int b) {\n    return a * b;\n}\nint main() {\n    cout << add(3, mul(4, 5)) << endl;\n    cout << mul(add(1, 2), 6) << endl;\n    return 0;\n}',
        '[H5] Функции min/max': '#include <iostream>\nusing namespace std;\nint main() {\n    int a = 17;\n    int b = 42;\n    cout << min(a, b) << endl;\n    cout << max(a, b) << endl;\n    return 0;\n}',
        '[W1] Fibonacci (while)': '#include <iostream>\nusing namespace std;\nint main() {\n    int a = 0;\n    int b = 1;\n    int i = 0;\n    while (i < 15) {\n        cout << a << endl;\n        int t = a + b;\n        a = b;\n        b = t;\n        i = i + 1;\n    }\n    return 0;\n}',
        '[W2] GCD': '#include <iostream>\nusing namespace std;\nint gcd(int a, int b) {\n    while (b) {\n        int t = b;\n        b = a % b;\n        a = t;\n    }\n    return a;\n}\nint main() {\n    cout << gcd(12, 8) << endl;\n    cout << gcd(100, 25) << endl;\n    cout << gcd(17, 5) << endl;\n    return 0;\n}',
        '[W3] Ackermann': '#include <iostream>\nusing namespace std;\nint ackermann(int m, int n) {\n    if (m == 0) return n + 1;\n    if (n == 0) return ackermann(m - 1, 1);\n    return ackermann(m - 1, ackermann(m, n - 1));\n}\nint main() {\n    cout << ackermann(2, 3) << endl;\n    return 0;\n}',
        '[W4] Сумма 1..10': '#include <iostream>\nusing namespace std;\nint main() {\n    int sum = 0;\n    int i = 1;\n    while (i <= 10) {\n        sum = sum + i;\n        i = i + 1;\n    }\n    cout << sum << endl;\n    return 0;\n}',
        '[W5] Таблица ×7': '#include <iostream>\nusing namespace std;\nint main() {\n    int k = 7;\n    int i = 1;\n    while (i <= 10) {\n        cout << i * k << endl;\n        i = i + 1;\n    }\n    return 0;\n}',
        '[T1] Базовые конструкции': '#include <iostream>\nusing namespace std;\nint main() {\n    int a = 10;\n    int b = 3;\n    cout << a + b << endl;\n    cout << a - b << endl;\n    cout << a * b << endl;\n    cout << a / b << endl;\n    return 0;\n}',
        '[T2] Все структуры': '#include <iostream>\n#include <vector>\n#include <string>\nusing namespace std;\nint main() {\n    int arr[3] = {1, 2, 3};\n    vector<int> v = {10, 20, 30};\n    string s = "abc";\n    cout << v.size() << endl;\n    cout << s.size() << endl;\n    cout << v[0] + v[1] + v[2] << endl;\n    return 0;\n}',
        '[T3] Всё вместе': '#include <iostream>\n#include <vector>\n#include <string>\nusing namespace std;\nint double_it(int x) {\n    return x * 2;\n}\nint main() {\n    vector<int> v = {1, 2, 3, 4, 5};\n    int sum = v[0] + v[1] + v[2] + v[3] + v[4];\n    cout << sum << endl;\n    cout << double_it(sum) << endl;\n    cout << v.size() << endl;\n    return 0;\n}',
    }
    def execute(self, src):
        if not src or not src.strip():
            return ""
        src = _preprocess_cpp(src)
        py = cpp_to_python(src)
        py = _ensure_main_called(py)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<cpp>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// C++: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return "// пустой вывод\n"
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        body = "\n".join(
            f'    std::cout << {json.dumps(ln, ensure_ascii=False)}'
            f' << "\\n";'
            for ln in lines
        )
        return ("#include <iostream>\n#include <vector>\n#include <string>\n"
                "int main() {\n"
                + body + "\n    return 0;\n}\n")


TRANSPILERS[("cpp", "python")] = cpp_to_python
