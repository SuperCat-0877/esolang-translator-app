# langs/elixir.py
"""Elixir — обычный язык. Модули, pipe, do/end, case."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS



def _elixir_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnil\b", "None", e)
    if "|>" in e:
        return _elixir_pipe_to_py(e)
    e = re.sub(r"String\.length\(([^()]*)\)", r"len(\1)", e)
    e = re.sub(r"String\.upcase\(([^()]*)\)", r"(\1).upper()", e)
    e = re.sub(r"String\.downcase\(([^()]*)\)", r"(\1).lower()", e)
    e = re.sub(r"String\.trim\(([^()]*)\)", r"(\1).strip()", e)
    e = re.sub(r"String\.split\(([^,()]+),\s*([^)]+)\)",
               r"\1.split(\2)", e)
    e = re.sub(r"String\.replace\(([^,()]+),\s*([^,()]+),\s*([^)]+)\)",
               r"\1.replace(\2, \3)", e)
    e = re.sub(r"Enum\.sum\(([^()]*)\)", r"sum(\1)", e)
    e = re.sub(r"Enum\.count\(([^()]*)\)", r"len(\1)", e)
    e = re.sub(r"Enum\.sort\(([^()]*)\)", r"sorted(\1)", e)
    e = re.sub(r"Enum\.reverse\(([^()]*)\)", r"list(reversed(\1))", e)
    e = re.sub(r"Enum\.uniq\(([^()]*)\)", r"list(dict.fromkeys(\1))", e)
    e = re.sub(r"List\.first\(([^()]*)\)", r"\1[0]", e)
    e = re.sub(r"List\.last\(([^()]*)\)", r"\1[-1]", e)
    e = re.sub(r"Map\.get\(([^,()]+),\s*([^)]+)\)", r"\1[\2]", e)
    e = re.sub(r"Map\.put\(([^,()]+),\s*([^,()]+),\s*([^)]+)\)",
               r"(\1[\2] := \3)", e)
    return e


def _elixir_pipe_to_py(e):
    """Обрабатывает a |> f() |> g() — слева направо."""
    parts = _split_top_level(e, "|")
    if len(parts) <= 1:
        return e
    result = parts[0].strip()
    for p in parts[1:]:
        f = p.lstrip(">").strip()
        if not f:
            continue
        m = re.match(r"([\w.]+)\s*\(\s*\)\s*$", f)
        if m:
            f = m.group(1)
        if f == "String.upcase":
            result = f"({result}).upper()"
        elif f == "String.downcase":
            result = f"({result}).lower()"
        elif f == "String.trim":
            result = f"({result}).strip()"
        elif f == "String.length":
            result = f"len({result})"
        elif f == "IO.puts":
            result = f"print({result})"
        elif f == "IO.write":
            result = f"print({result}, end='')"
        elif f == "IO.inspect":
            result = f"print({result})"
        else:
            result = f"{f}({result})"
    return result

def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    if ("IO.puts" not in src and "IO.write" not in src
            and "defmodule" not in src
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


# --- normal patch: elixir sigils ---
def _convert_elixir_sigils(src):
    # ~w(a b c) → ["a", "b", "c"]
    def _w(m):
        return repr(m.group(1).split())
    src = re.sub(r"~w\(([^)]*)\)", _w, src)
    # ~s(...) → "..."
    src = re.sub(r"~s\(([^)]*)\)", r'"\1"', src)
    return src


def _expand_elixir_case(src):
    """case x do  pat -> body  ...  end → if/elif/else.

    Паттерн приходит уже в круглых скобках: ('ok', value).
    """
    def _split_commas(s):
        parts, buf, depth, in_str = [], [], 0, None
        for ch in s:
            if in_str:
                buf.append(ch)
                if ch == in_str:
                    in_str = None
                continue
            if ch in '"\'':
                in_str = ch; buf.append(ch)
            elif ch in "([{":
                depth += 1; buf.append(ch)
            elif ch in ")]}":
                depth -= 1; buf.append(ch)
            elif ch == "," and depth == 0:
                parts.append("".join(buf)); buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append("".join(buf))
        return parts

    lines = src.split("\n")
    out = []
    in_case = False
    c_indent = "    "
    count = 0
    i = 0
    steps = 0
    while i < len(lines):
        steps += 1
        if steps > 100000:
            break
        line = lines[i]
        if not in_case:
            m = re.match(r"^(\s*)case\s+(.+?)\s+do\s*$", line)
            if m:
                c_indent = m.group(1)
                out.append(c_indent + "_case_val = " + m.group(2))
                in_case = True
                count = 0
                i += 1
                continue
            out.append(line)
            i += 1
            continue
        if line.strip() == "end":
            in_case = False
            i += 1
            continue
        cm = re.match(r"^\s*(.+?)\s*->\s*(.*)$", line)
        if cm:
            pat = cm.group(1).strip()
            body = cm.group(2).strip()
            kw = "if" if count == 0 else "elif"
            tm = re.match(r"^\((.+)\)$", pat)
            if tm:
                parts = [x.strip() for x in _split_commas(tm.group(1))]
                conds = []
                binds = []
                for idx, part in enumerate(parts):
                    ps = part.strip()
                    if re.match(r"^([\"\']).*\1$", ps) or re.match(r"^-?\d+$", ps):
                        conds.append("_case_val[" + str(idx) + "] == " + ps)
                    elif re.match(r"^[A-Za-z_]\w*$", ps):
                        binds.append((ps, idx))
                    else:
                        conds.append("_case_val[" + str(idx) + "] == " + ps)
                cond = " and ".join(conds) if conds else "True"
                count += 1
                cond_line = (c_indent + kw + " isinstance(_case_val, tuple) and "
                             "len(_case_val) == " + str(len(parts)) + " and " + cond + ":")
                out.append(cond_line)
                for var, idx in binds:
                    out.append(c_indent + "    " + var + " = _case_val[" + str(idx) + "]")
                if body:
                    out.append(c_indent + "    " + body)
            elif pat == "_":
                out.append(c_indent + "else:")
                if body:
                    out.append(c_indent + "    " + body)
            else:
                count += 1
                out.append(c_indent + kw + " _case_val == " + pat + ":")
                if body:
                    out.append(c_indent + "    " + body)
            i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _convert_elixir_tuples(src):
    """{:ok, X} → ("ok", X) — только простые кортежи."""
    def repl(m):
        inner = m.group(1)
        # делим по верхнеуровневым запятым
        parts, buf, depth, in_str = [], [], 0, None
        for ch in inner:
            if in_str:
                buf.append(ch)
                if ch == in_str:
                    in_str = None
                continue
            if ch in '"\'':
                in_str = ch; buf.append(ch)
            elif ch in "([{":
                depth += 1; buf.append(ch)
            elif ch in ")]}":
                depth -= 1; buf.append(ch)
            elif ch == "," and depth == 0:
                parts.append("".join(buf)); buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append("".join(buf))
        out = []
        for p in parts:
            ps = p.strip()
            if re.match(r"^:[A-Za-z_]\w*$", ps):
                out.append(repr(ps[1:]))
            else:
                out.append(ps)
        return "(" + ", ".join(out) + ")"
    return re.sub(r"\{([^{}]*)\}", repl, src)


def _elixir_to_python(src):
    src = _convert_elixir_sigils(src)
    src = _convert_elixir_tuples(src)
    src = _expand_elixir_case(src)
    lines = src.splitlines()
    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    i = 0
    n = len(lines)
    _outer = 0
    while i < n:
        _outer += 1
        if _outer > 100000:
            break
        raw = lines[i]
        line = raw.strip()

        if not line or line.startswith("#"):
            i += 1
            continue

        # Python-style if/elif/else от _expand_elixir_case
        m = re.match(r"^(if|elif)\s+(.+?)\s*:\s*$", line)
        if m:
            if m.group(1) == "elif":
                ind = max(0, ind - 1)
            emit(f"{m.group(1)} {m.group(2)}:")
            ind += 1
            i += 1
            continue
        if line == "else:":
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            i += 1
            continue

        # defmodule — открываем класс
        m = re.match(r"defmodule\s+(\w+)\s+do\s*$", line)
        if m:
            emit(f"class {m.group(1)}:")
            ind += 1
            i += 1
            continue

        # def name(args) do
        m = re.match(r"def\s+(\w+)\s*\(([^)]*)\)\s+do\s*$", line)
        if m:
            args = ", ".join(
                a.strip() for a in m.group(2).split(",") if a.strip())
            if ind > 0:
                args_str = ", ".join(["self"] + ([args] if args else []))
                emit(f"def {m.group(1)}({args_str}):")
            else:
                emit(f"def {m.group(1)}({args}):")
            ind += 1
            i += 1
            continue

        # однострочный def name(args), do: expr
        m = re.match(r"def\s+(\w+)\s*\(([^)]*)\),\s*do:\s*(.+?)\s*$", line)
        if m:
            args = ", ".join(
                a.strip() for a in m.group(2).split(",") if a.strip())
            args_str = ", ".join(["self"] + ([args] if args else [])) if ind > 0 else args
            emit(f"def {m.group(1)}({args_str}):")
            emit(f"    return {_elixir_expr_to_py(m.group(3))}")
            i += 1
            continue

        # end — закрываем блок
        if line == "end":
            ind = max(0, ind - 1)
            i += 1
            continue

        # for x <- 1..10 do
        m = re.match(r"for\s+(\w+)\s*<-\s*(\d+)\.\.(\d+)\s+do\s*$", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            i += 1
            continue
        m = re.match(r"for\s+(\w+)\s*<-\s*(.+?)\s+do\s*$", line)
        if m:
            emit(f"for {m.group(1)} in {_elixir_expr_to_py(m.group(2))}:")
            ind += 1
            i += 1
            continue

        # Enum.each(1..10, fn x -> ... end)
        m = re.match(
            r"Enum\.each\((\d+)\.\.(\d+),\s+fn\s+(\w+)\s*->\s*$", line)
        if m:
            a, b, v = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            i += 1
            continue

        # if cond do / unless cond do
        m = re.match(r"if\s+(.+?)\s+do\s*$", line)
        if m:
            emit(f"if {_elixir_expr_to_py(m.group(1))}:")
            ind += 1
            i += 1
            continue
        m = re.match(r"unless\s+(.+?)\s+do\s*$", line)
        if m:
            emit(f"if not ({_elixir_expr_to_py(m.group(1))}):")
            ind += 1
            i += 1
            continue

        # else
        if line == "else":
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            i += 1
            continue

        # case x do ... end — упрощённо игнорируем
        m = re.match(r"case\s+(.+?)\s+do\s*$", line)
        if m:
            emit(f"_case_val = {_elixir_expr_to_py(m.group(1))}")
            i += 1
            continue
        # Pattern match -> expr / _ -> expr
        m = re.match(r"(.+?)\s*->\s*(.+?)\s*$", line)
        if m:
            pat = m.group(1).strip()
            body = m.group(2).strip()
            if pat == "_":
                ind = max(0, ind - 1)
                emit("else:")
                ind += 1
            else:
                kw = "if" if "_case_used" not in out else "elif"
                emit(f"{kw} _case_val == {_elixir_expr_to_py(pat)}:")
                ind += 1
            # Тело
            if body.startswith("IO.puts"):
                inner = re.match(r"IO\.puts\s*\((.*)\)$", body)
                if inner:
                    emit(f"print({inner.group(1)})")
            else:
                emit(_elixir_expr_to_py(body))
            ind = max(0, ind - 1)
            i += 1
            continue

        # IO.puts / IO.write / IO.inspect
        m = re.match(r"IO\.puts\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_elixir_expr_to_py(m.group(1))})")
            i += 1
            continue
        m = re.match(r"IO\.write\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_elixir_expr_to_py(m.group(1))}, end='')")
            i += 1
            continue
        m = re.match(r"IO\.inspect\s*\((.*)\)\s*$", line)
        if m:
            emit(f"print({_elixir_expr_to_py(m.group(1))})")
            i += 1
            continue

        # x = expr
        m = re.match(r"(\w+)\s*=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_elixir_expr_to_py(m.group(2))}")
            i += 1
            continue

        # голое выражение / pipe
        if "|>" in line:
            emit(_elixir_expr_to_py(line))
            i += 1
            continue

        i += 1

    return "\n".join(out) + "\n"


def elixir_print(text):
    if not text:
        return 'IO.puts("")\n'
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'IO.puts({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


def elixir_gen_numbers():
    return "for i <- 1..10 do\n  IO.puts(i)\nend\n"


def elixir_gen_squares():
    return "for i <- 1..10 do\n  IO.puts(i * i)\nend\n"


def elixir_gen_cubes():
    return "for i <- 1..10 do\n  IO.puts(i * i * i)\nend\n"


def elixir_gen_table7():
    return "for i <- 1..10 do\n  IO.puts(i * 7)\nend\n"


def elixir_gen_factorial():
    return ("r = 1\n"
            "for i <- 1..5 do\n"
            "  r = r * i\n"
            "end\n"
            "IO.puts(r)\n")


def elixir_gen_fib():
    return ("a = 0\n"
            "b = 1\n"
            "for i <- 1..10 do\n"
            "  IO.puts(a)\n"
            "  c = a + b\n"
            "  a = b\n"
            "  b = c\n"
            "end\n")


def elixir_gen_pipe():
    return ('"hello" |> String.upcase() |> IO.puts()')


def elixir_gen_module():
    return ("defmodule Greeter do\n"
            "  def hello(name) do\n"
            '    IO.puts(name)\n'
            "  end\n"
            "end\n"
            "Greeter.hello(\"World\")")


def elixir_gen_condition():
    return ("x = 10\n"
            "if x == 10 do\n"
            '  IO.puts("ten")\n'
            "else\n"
            '  IO.puts("other")\n'
            "end")


def elixir_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f'IO.puts("=== {k} x {k} ===")')
        for i in range(1, 6):
            parts.append(f"IO.puts({i * k})")
    return "\n".join(parts) + "\n"


def elixir_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f'IO.puts("=== Таблица {k} ===")')
        for i in range(1, 11):
            parts.append(f"IO.puts({i * k})")
    return "\n".join(parts) + "\n"


def elixir_generate(output):
    if not output:
        return 'IO.puts("")\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'IO.puts({json.dumps(ln, ensure_ascii=False)})' for ln in lines) + "\n"


class ElixirLang(Language):
    name = "elixir"
    title = "Elixir"
    category = "О"
    ext = ".ex"
    keywords = ["def", "defp", "defmodule", "if", "else", "unless",
                "for", "while", "do", "end", "true", "false", "nil",
                "IO.puts", "IO.write", "IO.inspect", "case", "fn",
                "Enum.each", "Enum.map"]
    comment_regex = r"#[^\n]*"

    templates = {
        '[E1] Hello, World': 'IO.puts("Hello, World!")',
        '[E2] Арифметика': 'a = 17\nb = 5\nIO.puts(a + b)\nIO.puts(a - b)\nIO.puts(a * b)\nIO.puts(a / b)',
        '[E3] Строки (pipe)': 'IO.puts("hello" |> String.upcase())\nIO.puts("WORLD" |> String.downcase())\nIO.puts("  spaced  " |> String.trim())\nIO.puts("hello" |> String.length())',
        '[E4] Условие': 'x = 7\nif x % 2 == 0 do\n  IO.puts("чёт")\nelse\n  IO.puts("нечёт")\nend',
        '[E5] Функция square': 'def square(x), do: x * x\n\nIO.puts(square(7))\nIO.puts(square(12))\nIO.puts(square(25))',
        '[M1] Цикл for': 'for i <- 1..5 do\n  IO.puts(i)\nend',
        '[M2] Факториал (for)': 'r = 1\nfor i <- 1..5 do\n  r = r * i\nend\nIO.puts(r)',
        '[M3] Fibonacci (for)': 'a = 0\nb = 1\nfor i <- 1..15 do\n  IO.puts(a)\n  c = a + b\n  a = b\n  b = c\nend',
        '[M4] Две функции': 'def double(x), do: x * 2\ndef square(x), do: x * x\n\nIO.puts(double(5))\nIO.puts(square(5))\nIO.puts(double(square(3)))',
        '[M5] Сумма 1..10': 's = 0\nfor i <- 1..10 do\n  s = s + i\nend\nIO.puts(s)',
        '[H1] Сумма квадратов': 's = 0\nfor i <- 1..10 do\n  s = s + i * i\nend\nIO.puts(s)',
        '[H2] Вложенные циклы': 'for i <- 1..3 do\n  for j <- 1..3 do\n    IO.puts(i * j)\n  end\nend',
        '[H3] Case с кортежем': 'result = {:ok, "Hello"}\ncase result do\n  {:ok, value} -> IO.puts(value)\n  {:error, reason} -> IO.puts(reason)\n  _ -> IO.puts("unknown")\nend',
        '[H4] Pipe chain': '"  hello, world  " |> String.trim() |> String.upcase() |> IO.puts()',
        '[H5] Три функции': 'def inc(x), do: x + 1\ndef dbl(x), do: x * 2\ndef sq(x), do: x * x\n\nIO.puts(inc(5))\nIO.puts(dbl(inc(5)))\nIO.puts(sq(dbl(inc(5))))',
        '[W1] Таблица ×7': 'k = 7\nfor i <- 1..10 do\n  IO.puts(i * k)\nend',
        '[W2] Квадраты и кубы': 'for i <- 1..10 do\n  IO.puts(i * i)\nend\nfor i <- 1..10 do\n  IO.puts(i * i * i)\nend',
        '[W3] Степени двойки': 'p = 1\nfor i <- 1..10 do\n  IO.puts(p)\n  p = p * 2\nend',
        '[W4] Сумма 1..100': 's = 0\nfor i <- 1..100 do\n  s = s + i\nend\nIO.puts(s)',
        '[W5] Таблица 10×10': 'for i <- 1..10 do\n  for j <- 1..10 do\n    IO.puts(i * j)\n  end\nend',
        '[T1] Базовые конструкции': 'a = 10\nb = 3\nIO.puts(a + b)\nIO.puts(a - b)\nIO.puts(a * b)\nIO.puts(a / b)\nfor i <- 1..3 do\n  IO.puts(i)\nend',
        '[T2] Все структуры': 's = "Hello"\nx = 10\ny = 20\ntotal = x + y\nIO.puts(s |> String.length())\nIO.puts(s |> String.upcase())\nIO.puts(x)\nIO.puts(y)\nIO.puts(total)\nIO.puts(total * 2)',
        '[T3] Всё вместе': 'def double(x), do: x * 2\n\ns = 0\nfor i <- 1..5 do\n  s = s + i\nend\nIO.puts(s)\nIO.puts(double(s))\nfor i <- 1..3 do\n  IO.puts(i)\nend',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _elixir_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<elixir>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Elixir: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        return elixir_generate(output)


TRANSPILERS[("elixir", "python")] = _elixir_to_python
