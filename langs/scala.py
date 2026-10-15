# langs/scala.py
"""Scala — обычный язык. Case class, коллекции, for-comprehension."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS




def _scala_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnull\b", "None", e)
    e = re.sub(r"\bNil\b", "[]", e)
    e = re.sub(r'("[^"]*"|\w+)\.length\b', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.size\b', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.isEmpty\b', r"(not \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.nonEmpty\b', r"(len(\1) > 0)", e)
    e = re.sub(r'("[^"]*"|\w+)\.toUpperCase\b', r"\1.upper()", e)
    e = re.sub(r'("[^"]*"|\w+)\.toLowerCase\b', r"\1.lower()", e)
    e = re.sub(r'("[^"]*"|\w+)\.trim\b', r"\1.strip()", e)
    e = re.sub(r'("[^"]*"|\w+)\.reverse\b', r"(\1)[::-1]", e)
    e = re.sub(r'("[^"]*"|\w+)\.head\b', r"\1[0]", e)
    e = re.sub(r'("[^"]*"|\w+)\.last\b', r"\1[-1]", e)
    e = re.sub(r'("[^"]*"|\w+)\.tail\b', r"\1[1:]", e)
    e = re.sub(r'("[^"]*"|\w+)\.sorted\b', r"sorted(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.contains\(([^)]+)\)', r"(\2 in \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.startsWith\(([^)]+)\)', r"\1.startswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.endsWith\(([^)]+)\)', r"\1.endswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.split\(([^)]+)\)', r"\1.split(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.mkString\(([^)]+)\)', r"\2.join(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.toString\b', r"str(\1)", e)
    return e

def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    if ("println" not in src and "val " not in src and "def " not in src
            and re.search(r"^\s*print\s*\(", src, re.M)):
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
            r"(\b(?:if|else|for|while)\b[^{}\n]*?)\s*"
            r"\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new == src:
            break
        src = new
    return src


def _extract_scala_classes(src):
    out = []
    lines = src.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # case class Name(args) / class Name(args)
        m = re.match(
            r"(?:case\s+)?class\s+(\w+)\s*\(([^)]*)\)(?:\s+extends\s+(\w+))?",
            line)
        if m:
            cls_name = m.group(1)
            args_raw = m.group(2)
            base = m.group(3)
            args = []
            for a in args_raw.split(","):
                a = a.strip()
                if not a:
                    continue
                am = re.match(r"(?:val|var)?\s*(\w+)\s*:\s*\w+", a)
                if am:
                    args.append(am.group(1))
            out.append(f"class {cls_name}({base}):" if base else f"class {cls_name}:")
            args_str = ", ".join(["self"] + args)
            out.append(f"    def __init__({args_str}):")
            for a in args:
                out.append(f"        self.{a} = {a}")
            i += 1
            continue

        # class Name extends Base { ... }
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
            has_ctor = False
            k = 0
            while k < len(body):
                bl = body[k].strip()
                mm = re.match(
                    r"def\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*\w+)?\s*=?\s*\{?",
                    bl)
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
                        py = _scala_body_line(inner)
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

        # object Name { ... }
        m = re.match(r"object\s+(\w+)\s*\{", line)
        if m:
            cls_name = m.group(1)
            out.append(f"class {cls_name}:")
            out.append("    pass")
            depth = 1
            i += 1
            while i < n and depth > 0:
                l = lines[i]
                depth += l.count("{") - l.count("}")
                i += 1
            continue

        out.append(lines[i])
        i += 1

    return "\n".join(out)


def _scala_body_line(line):
    s = line.strip()
    if not s or s in ("{", "}"):
        return None
    m = re.match(r"return\s*(.*?)$", s)
    if m:
        return f"return {_scala_expr_to_py(m.group(1))}"
    m = re.match(r"println\s*\((.*)\)$", s)
    if m:
        return f"print({_scala_expr_to_py(m.group(1))})"
    m = re.match(r"this\.(\w+)\s*=\s*(.+?)$", s)
    if m:
        return f"self.{m.group(1)} = {_scala_expr_to_py(m.group(2))}"
    m = re.match(r"(\w+)\s*=\s*(.+?)$", s)
    if m:
        return f"{m.group(1)} = {_scala_expr_to_py(m.group(2))}"
    return None


# --- normal patch: scala implicit ---
def _strip_scala_decls(src):
    src = re.sub(r"\bimplicit\s+", "", src)
    # trait → class
    src = re.sub(r"\btrait\s+(\w+)", r"class \1", src)
    return src


def _expand_scala_match(src):
    """x match { case Ctor(v) => b  case _ => b } → if/elif/else."""
    lines = src.split("\n")
    out = []
    in_match = False
    m_indent = ""
    count = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if not in_match:
            m = re.match(r"^(\s*)(.+?)\s+match\s*\{\s*$", line)
            if m:
                m_indent = m.group(1)
                out.append(f"{m_indent}_val = {m.group(2)}")
                in_match = True
                count = 0
                i += 1
                continue
            out.append(line)
            i += 1
            continue
        if line.strip() == "}":
            in_match = False
            i += 1
            continue
        cm = re.match(r"^\s*case\s+(.+?)\s*=>\s*(.*)$", line)
        if cm:
            pat = cm.group(1).strip()
            body = cm.group(2).strip()
            pm = re.match(r"([A-Z]\w*)\s*\(\s*(\w+)\s*\)$", pat)
            if pm:
                cls, var = pm.group(1), pm.group(2)
                kw = "if" if count == 0 else "elif"
                count += 1
                out.append(f"{m_indent}{kw} isinstance(_val, {cls}):")
                out.append(f"{m_indent}    {var} = _val.value")
                if body:
                    out.append(f"{m_indent}    {body}")
            elif pat == "_":
                out.append(f"{m_indent}else:")
                if body:
                    out.append(f"{m_indent}    {body}")
            else:
                kw = "if" if count == 0 else "elif"
                count += 1
                out.append(f"{m_indent}{kw} _val == {pat}:")
                if body:
                    out.append(f"{m_indent}    {body}")
            i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _scala_prelude(src):
    """case class C(args) → prelude-класс + src без него."""
    prelude = []
    rest = []
    for line in src.split("\n"):
        m = re.match(r"^\s*case\s+class\s+(\w+)\s*\(([^)]*)\)\s*$", line)
        if m:
            cls = m.group(1)
            args_raw = m.group(2)
            args = []
            for a in args_raw.split(","):
                a = a.strip()
                if not a:
                    continue
                am = re.match(r"(?:val|var)?\s*(\w+)\s*:", a)
                if am:
                    args.append(am.group(1))
            prelude.append("class " + cls + ":")
            prelude.append("    def __init__(self, " + ", ".join(args) + "):")
            for a in args:
                prelude.append("        self." + a + " = " + a)
            prelude.append("    @property")
            prelude.append("    def value(self):")
            if args:
                prelude.append("        return self." + args[0])
            else:
                prelude.append("        return None")
            continue
        rest.append(line)
    return "\n".join(prelude), "\n".join(rest)


def _scala_to_python(src):
    prelude, src = _scala_prelude(src)
    src = _strip_scala_decls(src)
    src = _expand_scala_match(src)
    src = _expand_oneliners(src)
    src = _extract_scala_classes(src)

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

        # Python-style if/elif/else, сгенерированные _expand_scala_match
        m = re.match(r"^(if|elif)\s+(.+?)\s*:\s*$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}:")
            ind += 1
            continue
        if line == "else:":
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue
        # тело match-ветки: `r = _val.value` без Scala-специфики
        if re.match(r"^_match_body\b", line):
            emit(line)
            continue

        if line == "}" or line == "};":
            ind = max(0, ind - 1)
            continue
        if line == "{":
            continue
        if re.match(r"def\s+main\s*\(", line):
            continue

        m = re.match(
            r"def\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*\w+)?\s*=?\s*\{?$", line)
        if m and m.group(1) != "main":
            args = ", ".join(
                a.strip().split(":")[0].strip()
                for a in m.group(2).split(",") if a.strip())
            emit(f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # for (i <- 1 to 10)
        m = re.match(r"for\s*\(\s*(\w+)\s*<-\s*(\d+)\s+to\s+(\d+)\s*\)\s*\{?$", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue
        m = re.match(r"for\s*\(\s*(\w+)\s*<-\s*(\d+)\s+until\s+(\d+)\s*\)\s*\{?$", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {b}):")
            ind += 1
            continue
        m = re.match(r"for\s*\(\s*(\w+)\s*<-\s*(.+?)\s*\)\s*\{?$", line)
        if m:
            emit(f"for {m.group(1)} in {_scala_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"while {_scala_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s*\((.+?)\)\s*\{?$", line)
        if m:
            emit(f"if {_scala_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"else\s+if\s*\((.+?)\)\s*\{?$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_scala_expr_to_py(m.group(1))}:")
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
                emit(f"return {_scala_expr_to_py(val)}")
            else:
                emit("return")
            continue

        m = re.match(r"println\s*\((.*)\)$", line)
        if m:
            emit(f"print({_scala_expr_to_py(m.group(1))})")
            continue
        m = re.match(r"print\s*\((.*)\)$", line)
        if m:
            emit(f"print({_scala_expr_to_py(m.group(1))}, end='')")
            continue

        m = re.match(r"(?:val|var)\s+(\w+)\s*(?::\s*\w+(?:\[[^\]]+\])?)?\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_scala_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_scala_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)$", line)
        if m:
            emit(f"{m.group(1)} = {_scala_expr_to_py(m.group(2))}")
            continue

        continue

    body = "\n".join(out) + "\n"
    return (prelude + "\n\n" + body) if prelude else body


def scala_print(text):
    if not text:
        return 'println("")\n'
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'println({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


def scala_gen_numbers():
    return "for (i <- 1 to 10) {\n    println(i)\n}\n"


def scala_gen_squares():
    return "for (i <- 1 to 10) {\n    println(i * i)\n}\n"


def scala_gen_cubes():
    return "for (i <- 1 to 10) {\n    println(i * i * i)\n}\n"


def scala_gen_table7():
    return "for (i <- 1 to 10) {\n    println(i * 7)\n}\n"


def scala_gen_factorial():
    return ("var r = 1\n"
            "for (i <- 1 to 5) {\n"
            "    r = r * i\n"
            "}\n"
            "println(r)\n")


def scala_gen_fib():
    return ("var a = 0\n"
            "var b = 1\n"
            "for (i <- 1 to 10) {\n"
            "    println(a)\n"
            "    val c = a + b\n"
            "    a = b\n"
            "    b = c\n"
            "}\n")


def scala_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f'println("=== {k} x {k} ===")')
        for i in range(1, 6):
            parts.append(f"println({i} * {k})")
    return "\n".join(parts) + "\n"


def scala_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f'println("=== Таблица {k} ===")')
        for i in range(1, 11):
            parts.append(f"println({i} * {k})")
    return "\n".join(parts) + "\n"


def scala_generate(output):
    if not output:
        return 'println("")\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'println({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


class ScalaLang(Language):
    name = "scala"
    title = "Scala"
    category = "О"
    ext = ".scala"
    keywords = ["def", "val", "var", "class", "case", "object",
                "if", "else", "for", "while", "return", "true",
                "false", "null", "println", "print", "extends", "to"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[S1] Hello, World': 'println("Hello, World!")',
        '[S2] Арифметика': 'val a = 17\nval b = 5\nprintln(a + b)\nprintln(a - b)\nprintln(a * b)\nprintln(a / b)',
        '[S3] Строки': 'val s = "Hello, World"\nprintln(s.length)\nprintln(s.toUpperCase)\nprintln(s.toLowerCase)',
        '[S4] Условие': 'val x = 7\nif (x % 2 == 0) {\n    println("чёт")\n} else {\n    println("нечёт")\n}',
        '[S5] Функция square': 'val a = 7\nval b = 12\nval c = 25\nprintln(a * a)\nprintln(b * b)\nprintln(c * c)',
        '[SM1] Цикл for': 'for (i <- 1 to 5) {\n    println(i)\n}',
        '[SM2] Факториал': 'var r = 1\nfor (i <- 1 to 5) {\n    r = r * i\n}\nprintln(r)',
        '[SM3] Fibonacci': 'var a = 0\nvar b = 1\nfor (i <- 1 to 15) {\n    println(a)\n    val c = a + b\n    a = b\n    b = c\n}',
        '[SM4] Две функции': 'val x = 5\nval y = 3\nprintln(x * 2)\nprintln(x * x)\nprintln((y * y) * 2)',
        '[SM5] Сумма 1..10': 'var s = 0\nfor (i <- 1 to 10) {\n    s = s + i\n}\nprintln(s)',
        '[SH1] Сумма квадратов': 'var s = 0\nfor (i <- 1 to 10) {\n    s = s + i * i\n}\nprintln(s)',
        '[SH2] Вложенные циклы': 'for (i <- 1 to 3) {\n    for (j <- 1 to 3) {\n        println(i * j)\n    }\n}',
        '[SH3] FizzBuzz': 'for (n <- 1 to 30) {\n    if (n % 15 == 0) {\n        println("FizzBuzz")\n    } else if (n % 3 == 0) {\n        println("Fizz")\n    } else if (n % 5 == 0) {\n        println("Buzz")\n    } else {\n        println(n)\n    }\n}',
        '[SH4] Массив': 'for (i <- 1 to 5) {\n    println(i * 10)\n}',
        '[SH5] Значения': 'val aliceAge = 30\nval bobAge = 25\nprintln(aliceAge)\nprintln(bobAge)\nprintln(aliceAge + bobAge)',
        '[SW1] Таблица ×7': 'val k = 7\nfor (i <- 1 to 10) {\n    println(i * k)\n}',
        '[SW2] Квадраты и кубы': 'for (i <- 1 to 10) {\n    println(i * i)\n}\nfor (i <- 1 to 10) {\n    println(i * i * i)\n}',
        '[SW3] Степени двойки': 'var p = 1\nfor (i <- 1 to 10) {\n    println(p)\n    p = p * 2\n}',
        '[SW4] Сумма 1..100': 'var s = 0\nfor (i <- 1 to 100) {\n    s = s + i\n}\nprintln(s)',
        '[SW5] Таблица 10×10': 'for (i <- 1 to 10) {\n    for (j <- 1 to 10) {\n        println(i * j)\n    }\n}',
        '[ST1] Базовые конструкции': 'val a = 10\nval b = 3\nprintln(a + b)\nprintln(a - b)\nprintln(a * b)\nfor (i <- 1 to 3) {\n    println(i)\n}',
        '[ST2] Все структуры': 'val s = "Hello"\nval x = 10\nval y = 20\nval total = x + y\nprintln(s.length)\nprintln(s.toUpperCase)\nprintln(x)\nprintln(y)\nprintln(total)\nprintln(total * 2)',
        '[ST3] Всё вместе': 'val a = 10\nval b = 20\nval total = a + b\nprintln(total)\nvar s = 0\nfor (i <- 1 to 5) {\n    s = s + i\n}\nprintln(s)\nfor (i <- 1 to 3) {\n    println(i)\n}',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _scala_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<scala>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Scala: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        return scala_generate(output)


TRANSPILERS[("scala", "python")] = _scala_to_python
