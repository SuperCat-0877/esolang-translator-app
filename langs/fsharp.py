# langs/fsharp.py
"""F# — обычный язык. Модули, pipe, match, Option."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS





def _fsharp_pipe_to_py(e):
    parts = _split_by_op(e, "|")
    if len(parts) <= 1:
        return e
    result = parts[0].strip()
    for p in parts[1:]:
        f = p.lstrip(">").strip()
        if not f:
            continue
        m = re.match(r"fun\s+(\w+)\s*->\s*(.+)$", f)
        if m:
            var = m.group(1)
            body = m.group(2)
            body_py = _fsharp_expr_to_py(body)
            # подставляем result вместо var
            result = re.sub(rf"\b{re.escape(var)}\b",
                            f"({result})", body_py)
            continue
        m = re.match(r'printfn\s+"([^"]*)"\s*$', f)
        if m:
            result = f"print({result})"
            continue
        m = re.match(r'printf\s+"([^"]*)"\s*$', f)
        if m:
            result = f"print({result}, end='')"
            continue
        if f in ("String.length", "String.Length"):
            result = f"len({result})"
            continue
        if f.endswith(".ToUpper"):
            result = f"({result}).upper()"
            continue
        if f.endswith(".ToLower"):
            result = f"({result}).lower()"
            continue
        if f.endswith(".Trim"):
            result = f"({result}).strip()"
            continue
        result = f"{f}({result})"
    return result

def _fsharp_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bNone\b", "None", e)
    e = re.sub(r"\bSome\s*\(([^)]+)\)", r"\1", e)
    if "|>" in e:
        return _fsharp_pipe_to_py(e)
    e = re.sub(r'String\.length\s+(\w+)', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.Length\b', r"len(\1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.ToUpper\(\)', r"\1.upper()", e)
    e = re.sub(r'("[^"]*"|\w+)\.ToLower\(\)', r"\1.lower()", e)
    e = re.sub(r'("[^"]*"|\w+)\.Trim\(\)', r"\1.strip()", e)
    e = re.sub(r'("[^"]*"|\w+)\.StartsWith\(([^)]+)\)', r"\1.startswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.EndsWith\(([^)]+)\)', r"\1.endswith(\2)", e)
    e = re.sub(r'("[^"]*"|\w+)\.Contains\(([^)]+)\)', r"(\2 in \1)", e)
    e = re.sub(r'("[^"]*"|\w+)\.Split\(([^)]+)\)', r"\1.split(\2)", e)
    e = re.sub(r'String\.Join\(([^,]+),\s*([^)]+)\)', r"\1.join(\2)", e)
    e = re.sub(r'List\.length\s+(\w+)', r"len(\1)", e)
    e = re.sub(r'List\.head\s+(\w+)', r"\1[0]", e)
    e = re.sub(r'List\.tail\s+(\w+)', r"\1[1:]", e)
    e = re.sub(r'List\.rev\s+(\w+)', r"list(reversed(\1))", e)
    return e


def _split_by_op(s, op):
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
        if ch in ('"', "'"):
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

def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    if ("printfn" not in src and "printf" not in src
            and "let " not in src
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


def _handle_printf(line, kind):
    """printfn "%d" expr → print(expr)."""
    m = re.match(rf'{kind}\s+"([^"]*)"\s+(.+?)\s*$', line)
    if m:
        rest = m.group(2).strip()
        # Если аргумент в скобках — оставляем
        return _fsharp_expr_to_py(rest)
    m = re.match(rf'{kind}\s+"([^"]*)"\s*$', line)
    if m:
        return json.dumps(m.group(1), ensure_ascii=False)
    m = re.match(rf"{kind}\s+(.+?)\s*$", line)
    if m:
        return _fsharp_expr_to_py(m.group(1))
    return None



def _join_pipes(lines):
    """Склеивает строки, начинающиеся с |>, с предыдущей строкой."""
    out = []
    for line in lines:
        s = line.strip()
        if s.startswith("|>") and out and out[-1].strip():
            out[-1] = out[-1].rstrip() + " " + s
        else:
            out.append(line)
    return out

def _convert_fsharp_du(src):
    """type Shape = | C of T | D → (prelude, transformed_src)."""
    lines = src.split("\n")
    rest = []
    prelude = []
    mapping = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\s*type\s+(\w+)\s*=\s*$", line)
        if not m:
            rest.append(line)
            i += 1
            continue
        name = m.group(1)
        prelude.append("class " + name + ":")
        prelude.append("    pass")
        i += 1
        while i < len(lines) and re.match(r"^\s*\|", lines[i]):
            vline = lines[i].strip()[1:].strip()
            vm = re.match(r"(\w+)(?:\s+of\s+(.+))?$", vline)
            if vm:
                ctor = vm.group(1)
                cname = name + "_" + ctor
                mapping[ctor] = cname
                fields = vm.group(2)
                prelude.append("class " + cname + "(" + name + "):")
                if fields:
                    field_list = [f.strip()
                                  for f in re.split(r"\s*\*\s*", fields)]
                    args = ", ".join("_" + str(k)
                                     for k in range(len(field_list)))
                    prelude.append("    def __init__(self, " + args + "):")
                    for k in range(len(field_list)):
                        prelude.append(
                            "        self.f" + str(k) + " = _" + str(k))
                    prelude.append("    @property")
                    prelude.append("    def value(self):")
                    prelude.append("        return self.f0")
                else:
                    prelude.append("    pass")
            i += 1
        continue

    result = "\n".join(rest)
    for ctor, cname in mapping.items():
        # паттерн без f-string: собираем через конкатенацию
        pat = r"\b" + re.escape(ctor) + r"\s+([^\s,;)\]}]+)"
        new_lines = []
        for ln in result.split("\n"):
            if re.match(r"^\s*\|", ln):
                # | Circle r -> ...   →   | Shape_Circle r -> ...
                ln2 = re.sub(
                    r"(\|\s*)" + re.escape(ctor) + r"\b",
                    (lambda _cn: (lambda mm: mm.group(1) + _cn))(cname),
                    ln)
                new_lines.append(ln2)
                continue
            repl_fn = (lambda _cn: (lambda mm: _cn + "(" + mm.group(1) + ")"))(cname)
            new_lines.append(re.sub(pat, repl_fn, ln))
        result = "\n".join(new_lines)
    return "\n".join(prelude), result


def _fsharp_to_python(src):
    prelude, src = _convert_fsharp_du(src)
    lines = _join_pipes(src.splitlines())
    out = []
    ind = 0

    _pattern_count = [0]

    def emit(s):
        out.append("    " * ind + s)

    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = raw.strip()
        i += 1

        if not line or line.startswith("//"):
            continue

        # module — открываем класс
        m = re.match(r"module\s+(\w+)\s*$", line)
        if m:
            emit(f"class {m.group(1)}:")
            ind += 1
            continue

        # let f arg1 arg2 = body (или = do ... )
        m = re.match(r"let\s+rec\s+(\w+)\s+(.*?)\s*=\s*$", line)
        if m:
            continue

        # let f args =    (тело на следующих строках)
        m = re.match(r"let\s+(\w+)\s+([\w\s]+?)\s*=\s*$", line)
        if m:
            name = m.group(1)
            args_part = m.group(2).strip()
            args = ", ".join(args_part.split())
            emit(f"def {name}({args}):")
            ind += 1
            continue

        m = re.match(r"let\s+mutable\s+(\w+)\s*=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_fsharp_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"let\s+(\w+)\s+([\w\s]+?)\s*=\s*(.+?)\s*$", line)
        if m:
            name = m.group(1)
            args_part = m.group(2).strip()
            body = m.group(3).strip()
            if args_part and not args_part.startswith("("):
                args = ", ".join(args_part.split())
                if ind > 0:
                    args_str = ", ".join(["self"] + args.split(", "))
                    emit(f"def {name}({args_str}):")
                else:
                    emit(f"def {name}({args}):")
                ind += 1
                emit(f"return {_fsharp_expr_to_py(body)}")
                ind = max(0, ind - 1)
                continue

        m = re.match(r"let\s+(\w+)\s*=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_fsharp_expr_to_py(m.group(2))}")
            continue

        # for i in A..B do
        m = re.match(r"for\s+(\w+)\s+in\s+(\d+)\s*\.\.\s*(\d+)\s+do\s*$", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue
        m = re.match(r"for\s+(\w+)\s+in\s+(.+?)\s+do\s*$", line)
        if m:
            emit(f"for {m.group(1)} in {_fsharp_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        m = re.match(r"while\s+(.+?)\s+do\s*$", line)
        if m:
            emit(f"while {_fsharp_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s+(.+?)\s+then\s*$", line)
        if m:
            cond = _fsharp_expr_to_py(m.group(1))
            cond = re.sub(r"(?<![=!<>])=(?!=)", "==", cond)
            emit(f"if {cond}:")
            ind += 1
            continue
        m = re.match(r"elif\s+(.+?)\s+then\s*$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_fsharp_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        if re.match(r"^else\s*$", line):
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        # match x with
        m = re.match(r"match\s+(.+?)\s+with\s*$", line)
        if m:
            emit(f"_match_val = {_fsharp_expr_to_py(m.group(1))}")
            _pattern_count[0] = 0
            continue
        # | Ctor var -> body
        m = re.match(r"\|\s*([A-Z]\w*)\s+(\w+)\s*->\s*(.+?)\s*$", line)
        if m:
            ctor, var, body = m.group(1), m.group(2), m.group(3).strip()
            kw = "if" if _pattern_count[0] == 0 else "elif"
            _pattern_count[0] += 1
            emit(f"{kw} isinstance(_match_val, {ctor}):")
            ind += 1
            emit(f"{var} = _match_val.value")
            if body.startswith("printfn"):
                arg = _handle_printf(body, "printfn")
                if arg is not None:
                    emit(f"print({arg})")
            else:
                emit(_fsharp_expr_to_py(body))
            ind = max(0, ind - 1)
            continue
        # | value -> body  /  | _ -> body
        m = re.match(r"\|\s*(.+?)\s*->\s*(.+?)\s*$", line)
        if m:
            pat = m.group(1).strip()
            body = m.group(2).strip()
            if pat == "_":
                ind = max(0, ind - 1)
                emit("else:")
                ind += 1
            else:
                kw = "if" if _pattern_count[0] == 0 else "elif"
                _pattern_count[0] += 1
                emit(f"{kw} _match_val == {_fsharp_expr_to_py(pat)}:")
                ind += 1
            if body.startswith("printfn"):
                arg = _handle_printf(body, "printfn")
                if arg is not None:
                    emit(f"print({arg})")
            else:
                emit(_fsharp_expr_to_py(body))
            ind = max(0, ind - 1)
            continue

        # printfn / printf
        arg = _handle_printf(line, "printfn")
        if arg is not None:
            emit(f"print({arg})")
            continue
        arg = _handle_printf(line, "printf")
        if arg is not None:
            emit(f"print({arg}, end='')")
            continue

        # x <- expr
        m = re.match(r"(\w+)\s*<-\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_fsharp_expr_to_py(m.group(2))}")
            continue

        m = re.match(r"(\w+)\s*([+\-*/])=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} {m.group(2)}= {_fsharp_expr_to_py(m.group(3))}")
            continue

        m = re.match(r"(\w+)\s*=\s*(.+?)\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_fsharp_expr_to_py(m.group(2))}")
            continue

        # pipe как выражение (без let)
        if "|>" in line:
            emit(_fsharp_expr_to_py(line))
            continue

        continue

    body = "\n".join(out) + "\n"
    return (prelude + "\n\n" + body) if prelude else body


def fsharp_print(text):
    if not text:
        return 'printfn ""\n'
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'printfn {json.dumps(ln, ensure_ascii=False)}' for ln in lines) + "\n"


def fsharp_gen_numbers():
    return 'for i in 1..10 do\n    printfn "%d" i\n'


def fsharp_gen_squares():
    return 'for i in 1..10 do\n    printfn "%d" (i * i)\n'


def fsharp_gen_cubes():
    return 'for i in 1..10 do\n    printfn "%d" (i * i * i)\n'


def fsharp_gen_table7():
    return 'for i in 1..10 do\n    printfn "%d" (i * 7)\n'


def fsharp_gen_factorial():
    return ('let mutable r = 1\n'
            'for i in 1..5 do\n'
            '    r <- r * i\n'
            'printfn "%d" r\n')


def fsharp_gen_fib():
    return ('let mutable a = 0\n'
            'let mutable b = 1\n'
            'for i in 1..10 do\n'
            '    printfn "%d" a\n'
            '    let c = a + b\n'
            '    a <- b\n'
            '    b <- c\n')


def fsharp_gen_pipe():
    return ('"hello"\n'
            '|> fun s -> s.ToUpper()\n'
            '|> printfn "%s"\n')


def fsharp_gen_match():
    return ('let x = 3\n'
            'match x with\n'
            '| 1 -> printfn "one"\n'
            '| 2 -> printfn "two"\n'
            '| _ -> printfn "other"\n')


def fsharp_gen_module():
    return ('module Greeter\n'
            'let hello name =\n'
            '    printfn "%s" name\n')


def fsharp_gen_condition():
    return ('let x = 10\n'
            'if x = 10 then\n'
            '    printfn "ten"\n'
            'else\n'
            '    printfn "other"\n')


def fsharp_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f'printfn "=== {k} x {k} ==="')
        for i in range(1, 6):
            parts.append(f'printfn "%d" ({i} * {k})')
    return "\n".join(parts) + "\n"


def fsharp_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f'printfn "=== Таблица {k} ==="')
        for i in range(1, 11):
            parts.append(f'printfn "%d" ({i} * {k})')
    return "\n".join(parts) + "\n"


def fsharp_generate(output):
    if not output:
        return 'printfn ""\n'
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'printfn {json.dumps(ln, ensure_ascii=False)}' for ln in lines) + "\n"


class FsharpLang(Language):
    name = "fsharp"
    title = "F#"
    category = "О"
    ext = ".fs"
    keywords = ["let", "mutable", "if", "then", "else", "elif", "for",
                "while", "do", "match", "with", "module", "printfn",
                "printf"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': 'printfn "Hello, World!"',
        '[E2] Арифметика': 'let a = 17\nlet b = 5\nprintfn "%d" (a + b)\nprintfn "%d" (a - b)\nprintfn "%d" (a * b)\nprintfn "%d" (a / b)\nprintfn "%d" (a % b)',
        '[E3] Строки': 'let s = "Programming"\nprintfn "%d" s.Length\nprintfn "%s" (s.ToUpper())\nprintfn "%s" (s.ToLower())',
        '[E4] Условие': 'let x = 7\nif x % 2 = 0 then\n    printfn "чёт"\nelse\n    printfn "нечёт"',
        '[E5] Функция square': 'let square x = x * x\n7 |> square |> printfn "%d"\n12 |> square |> printfn "%d"\n25 |> square |> printfn "%d"',
        '[M1] Цикл for': 'for i in 1..5 do\n    printfn "%d" i',
        '[M2] Цикл while (факториал)': 'let mutable n = 5\nlet mutable fact = 1\nwhile n > 1 do\n    fact <- fact * n\n    n <- n - 1\nprintfn "%d" fact',
        '[M3] Факториал (for)': 'let mutable fact = 1\nfor i in 1..5 do\n    fact <- fact * i\nprintfn "%d" fact',
        '[M4] Две функции': 'let double x = x * 2\nlet square x = x * x\n5 |> double |> printfn "%d"\n5 |> square |> printfn "%d"',
        '[M5] Сумма 1..10': 'let mutable sum = 0\nfor i in 1..10 do\n    sum <- sum + i\nprintfn "%d" sum',
        '[H1] Fibonacci': 'let mutable a = 0\nlet mutable b = 1\nfor i in 1..15 do\n    printfn "%d" a\n    let t = a + b\n    a <- b\n    b <- t',
        '[H2] GCD (inline)': 'let mutable a = 100\nlet mutable b = 25\nwhile b != 0 do\n    let t = b\n    b <- a % b\n    a <- t\nprintfn "%d" a',
        '[H3] Сумма квадратов': 'let mutable sum = 0\nfor i in 1..10 do\n    sum <- sum + i * i\nprintfn "%d" sum',
        '[H4] Вложенные циклы': 'for i in 1..3 do\n    for j in 1..3 do\n        printfn "%d" (i * j)',
        '[H5] Три функции (pipe)': 'let inc x = x + 1\nlet double x = x * 2\nlet square x = x * x\n3 |> inc |> double |> square |> printfn "%d"',
        '[W1] Таблица ×7': 'let k = 7\nfor i in 1..10 do\n    printfn "%d" (i * k)',
        '[W2] Квадраты и кубы': 'for i in 1..10 do\n    printfn "%d" (i * i)\nfor i in 1..10 do\n    printfn "%d" (i * i * i)',
        '[W3] Степени двойки': 'let mutable p = 1\nfor i in 1..10 do\n    printfn "%d" p\n    p <- p * 2',
        '[W4] Сумма 1..100': 'let mutable sum = 0\nfor i in 1..100 do\n    sum <- sum + i\nprintfn "%d" sum',
        '[W5] Таблица 10×10': 'for i in 1..10 do\n    for j in 1..10 do\n        printfn "%d" (i * j)',
        '[T1] Базовые конструкции': 'let a = 10\nlet b = 3\nprintfn "%d" (a + b)\nprintfn "%d" (a - b)\nprintfn "%d" (a * b)\nprintfn "%d" (a / b)\nfor i in 1..3 do\n    printfn "%d" i',
        '[T2] Все структуры': 'let s = "Hello"\nlet x = 10\nlet y = 20\nlet total = x + y\nprintfn "%d" s.Length\nprintfn "%s" (s.ToUpper())\nprintfn "%d" x\nprintfn "%d" y\nprintfn "%d" total\nprintfn "%d" (total * 2)',
        '[T3] Всё вместе': 'let doubleIt x = x * 2\nlet mutable s = 0\nfor i in 1..5 do\n    s <- s + i\nprintfn "%d" s\ns |> doubleIt |> printfn "%d"',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _fsharp_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<fsharp>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// F#: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        return fsharp_generate(output)


TRANSPILERS[("fsharp", "python")] = _fsharp_to_python
