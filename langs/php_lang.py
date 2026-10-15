# langs/php_lang.py
"""PHP → Python транспайлер."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS


# ==================================================================
#  Разбиение по sep на верхнем уровне
# ==================================================================
def _split_top_level(s, sep):
    parts, depth, in_str, cur, i = [], 0, None, [], 0
    while i < len(s):
        ch = s[i]
        if in_str:
            cur.append(ch)
            if ch == '\\' and i + 1 < len(s):
                cur.append(s[i + 1]); i += 2; continue
            if ch == in_str:
                in_str = None
            i += 1; continue
        if ch in ('"', "'"):
            in_str = ch; cur.append(ch)
        elif ch in '([{':
            depth += 1; cur.append(ch)
        elif ch in ')]}':
            depth -= 1; cur.append(ch)
        elif ch == sep and depth == 0:
            prev = s[i - 1] if i > 0 else ''
            nxt = s[i + 1] if i + 1 < len(s) else ''
            if prev.isdigit() and nxt.isdigit():
                cur.append(ch)
            else:
                parts.append("".join(cur)); cur = []
        else:
            cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def _strip_dollar(s):
    result, in_str, i = [], None, 0
    while i < len(s):
        ch = s[i]
        if in_str:
            result.append(ch)
            if ch == '\\' and i + 1 < len(s):
                result.append(s[i + 1]); i += 2; continue
            if ch == in_str:
                in_str = None
            i += 1; continue
        if ch in ('"', "'"):
            in_str = ch; result.append(ch)
        elif ch == '$':
            if i + 1 < len(s) and (s[i + 1].isalnum() or s[i + 1] == '_'):
                pass
            else:
                result.append(ch)
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def _convert_php_ternary(e):
    if "??" in e:
        m = re.match(r"^(.+?)\s*\?\?\s*(.+)$", e)
        if m:
            a, b = m.group(1).strip(), m.group(2).strip()
            e = f"({a} if {a} is not None else {b})"
    if "?" in e and ":" in e and "??" not in e:
        m = re.match(r"^(.+?)\s*\?\s*(.+?)\s*:\s*(.+)$", e)
        if m:
            cond, b, c = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            e = f"({b} if {cond} else {c})"
    return e


_ARG = r'("[^"]*"|\'[^\']*\'|[^,()]+)'


def _php_expr_simple(expr):
    e = expr.strip()
    e = _strip_dollar(e)
    e = re.sub(r"\b(int|float|string|bool|array)\s+\$", "$", e)

    def _static(e):
        return re.sub(r"\b(\w+)::(\w+)", r"\1.\2", e)

    def _interp(e):
        def repl(m):
            inner = m.group(1)
            if "$" not in inner:
                return m.group(0)
            inner = re.sub(r"\$\{(\w+)\}", r"{\1}", inner)
            inner = re.sub(r"\$(\w+)", r"{\1}", inner)
            inner = inner.replace('"', '\\"')
            return 'f"' + inner + '"'
        return re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', repl, e)

    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnull\b", "None", e)
    e = re.sub(r"\bthis->", "self.", e)
    e = re.sub(r"\bnew\s+(\w+)", r"\1", e)

    e = re.sub(r"\bcount\(([^()]*)\)", r"len(\1)", e)
    e = re.sub(r"\bstrlen\(([^()]*)\)", r"len(\1)", e)
    e = re.sub(r"\bintval\(([^()]*)\)", r"int(\1)", e)
    e = re.sub(r"\bfloatval\(([^()]*)\)", r"float(\1)", e)
    e = re.sub(r"\bstrval\(([^()]*)\)", r"str(\1)", e)
    e = re.sub(r"\bstrtoupper\(([^()]*)\)", r"(\1).upper()", e)
    e = re.sub(r"\bstrtolower\(([^()]*)\)", r"(\1).lower()", e)
    e = re.sub(r"\btrim\(([^()]*)\)", r"(\1).strip()", e)
    e = re.sub(r"\bltrim\(([^()]*)\)", r"(\1).lstrip()", e)
    e = re.sub(r"\brtrim\(([^()]*)\)", r"(\1).rstrip()", e)
    e = re.sub(rf"\bstr_replace\({_ARG}\s*,\s*{_ARG}\s*,\s*{_ARG}\)",
               r"(\3).replace(\1, \2)", e)
    e = re.sub(rf"\bexplode\({_ARG}\s*,\s*{_ARG}\)", r"(\2).split(\1)", e)
    e = re.sub(rf"\bimplode\({_ARG}\s*,\s*{_ARG}\)", r"(\1).join(\2)", e)
    e = re.sub(rf"\bjoin\({_ARG}\s*,\s*{_ARG}\)", r"(\1).join(\2)", e)
    e = re.sub(r"\barray\(([^()]*)\)", r"[\1]", e)

    # Дополнительные функции
    e = re.sub(r"\bsubstr\(([^,]+),\s*([^,]+),\s*([^)]+)\)",
               r"(\1)[(\2):(\2)+(\3)]", e)
    e = re.sub(r"\bsubstr\(([^,]+),\s*([^)]+)\)", r"(\1)[(\2):]", e)
    e = re.sub(r"\bstrpos\(([^,]+),\s*([^)]+)\)", r"(\1).find(\2)", e)
    e = re.sub(r"\bstr_pad\(([^,]+),\s*([^,]+),\s*([^)]+)\)",
               r"(\1).ljust(\2, \3)", e)
    e = re.sub(r"\bstr_repeat\(([^,]+),\s*([^)]+)\)", r"(\1) * (\2)", e)
    e = re.sub(r"\bin_array\(([^,]+),\s*([^)]+)\)", r"((\1) in (\2))", e)
    e = re.sub(r"\barray_key_exists\(([^,]+),\s*([^)]+)\)",
               r"((\1) in (\2))", e)
    e = re.sub(r"\barray_sum\(([^()]+)\)", r"sum(\1)", e)
    e = re.sub(r"\bcount\(([^()]+)\)", r"len(\1)", e)
    e = re.sub(r"\bstrlen\(([^()]+)\)", r"len(\1)", e)
    e = re.sub(r"\bis_null\(([^()]+)\)", r"((\1) is None)", e)
    e = re.sub(r"\bis_array\(([^()]+)\)", r"isinstance(\1, list)", e)
    e = re.sub(r"\bis_int\(([^()]+)\)", r"isinstance(\1, int)", e)
    e = re.sub(r"\bis_string\(([^()]+)\)", r"isinstance(\1, str)", e)
    e = re.sub(r"\bimplode\(([^,]+),\s*([^)]+)\)", r"(\1).join(\2)", e)

    e = _static(e)
    e = _interp(e)
    return e.strip()


def _php_expr_to_py(expr):
    e = expr.strip()
    e = _convert_php_arrays(e)
    parts = _split_top_level(e, '.')
    if len(parts) > 1:
        result = " + ".join(
            f"str({_php_expr_simple(p.strip())})" for p in parts)
    else:
        result = _php_expr_simple(parts[0].strip())
    return _convert_php_ternary(result)


# ==================================================================
#  PHP → Python
# ==================================================================
def _convert_php_arrays(src):
    """["k" => v, ...] → {"k": v, ...}"""
    # Только массивы с `=>` считаем ассоц.
    def repl(m):
        body = m.group(1)
        parts = _split_top_level(body, ',')
        items = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if "=>" in p:
                k, v = p.split("=>", 1)
                items.append(f"{_php_expr_to_py(k.strip())}: "
                             f"{_php_expr_to_py(v.strip())}")
            else:
                items.append(_php_expr_to_py(p))
        return "{" + ", ".join(items) + "}"
    return re.sub(r"\[([^\[\]]*=>[^\[\]]*)\]", repl, src)


# --- normal patch: php refs ---
def _strip_php_refs(src):
    # &$x в объявлениях → $x
    src = re.sub(r"&\$(\w+)", r"$\1", src)
    # global $x; → global x
    src = re.sub(r"\bglobal\s+\$(\w+)\s*;", r"global \1", src)
    # static $x = ... → $x = ...
    src = re.sub(r"\bstatic\s+\$(\w+)", r"$\1", src)
    return src


def _strip_php_decls(src):
    """Убираем namespace, use, trait (stub)."""
    src = re.sub(r"\bnamespace\s+[\w\\]+\s*;", "", src)
    src = re.sub(r"\buse\s+[\w\\]+(?:\s+as\s+\w+)?\s*;", "", src)
    # trait → удаляем блок
    src = re.sub(r"\btrait\s+\w+\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
                 "", src)
    return src


def _php_to_python(src):
    src = src.replace("<?php", " ").replace("<?", " ").replace("?>", " ")
    src = _strip_php_decls(src)
    src = _strip_php_refs(src)

    SENT = "\x00S\x00"

    def protect(text):
        result, depth = [], 0
        for ch in text:
            if ch in "([":
                depth += 1; result.append(ch)
            elif ch in ")]":
                depth -= 1; result.append(ch)
            elif ch == ";" and depth > 0:
                result.append(SENT)
            else:
                result.append(ch)
        return "".join(result)

    src = protect(src)

    for kw in ("elseif", "if", "for", "foreach", "while"):
        src = re.sub(
            rf"(?<![\w])({kw}\s*\([^)]+\))\s+([^;\n{{}}]+;)",
            lambda m: m.group(1) + " { " + m.group(2) + " }", src)
    src = re.sub(r"(?<![\w])else\s+([^;\n{}]+;)",
                 lambda m: "else { " + m.group(1) + " }", src)

    # case/default → ставим ; чтобы токенайзер разрезал
    src = re.sub(r"\bcase\s+([^:;{}\n]+):\s*", r"case \1: ; ", src)
    src = re.sub(r"\bdefault\s*:\s*", r"default: ; ", src)

    # Токенизация
    tokens, buf, depth = [], [], 0
    for ch in src:
        if ch in "([":
            depth += 1; buf.append(ch)
        elif ch in ")]":
            depth -= 1; buf.append(ch)
        elif ch in "{}" and depth == 0:
            s = "".join(buf).strip()
            if s:
                tokens.append(s)
            buf = []
            tokens.append(ch)
        elif ch == ";" and depth == 0:
            buf.append(ch)
            s = "".join(buf).strip()
            if s:
                tokens.append(s)
            buf = []
        else:
            buf.append(ch)
    s = "".join(buf).strip()
    if s:
        tokens.append(s)
    tokens = [t.replace(SENT, ";") for t in tokens]

    out = []
    ind = 0
    in_class = False
    class_indent = 0
    blocks = []            # [base_ind, is_switch, has_case]
    pending_close = False

    def _emit(line):
        out.append("    " * ind + line)

    for tok in tokens:
        if tok == "{":
            continue

        if tok == "}":
            pending_close = True
            if blocks:
                ind = blocks[-1][0]
            else:
                ind = max(0, ind - 1)
            continue

        # Продолжение цепочки (else/elseif/catch/finally)?
        is_continuation = bool(
            re.match(r"elseif\s*\(", tok)
            or tok == "else"
            or re.match(r"catch\s*\(", tok)
            or tok == "finally"
        )

        if pending_close:
            if not is_continuation:
                if blocks:
                    base, _is_sw, _hc = blocks.pop()
                    ind = base
                    if in_class and ind < class_indent:
                        in_class = False
                else:
                    ind = max(0, ind - 1)
            pending_close = False

        # --- class ---
        m = re.match(r"(?:abstract\s+|final\s+)?class\s+(\w+)"
                     r"(?:\s+extends\s+(\w+))?", tok)
        if m:
            name, base = m.group(1), m.group(2)
            header = f"class {name}({base}):" if base else f"class {name}:"
            out.append("    " * ind + header)
            blocks.append([ind, False, False])
            ind += 1
            in_class = True
            class_indent = ind
            continue

        # Поля класса — пропускаем
        if (in_class
                and re.match(r"^(?:public|private|protected|static|var|"
                             r"final|abstract|readonly)\b", tok)
                and not re.search(r"\bfunction\b", tok)):
            continue

        # function __construct
        m = re.match(r"(?:(?:public|private|protected|static|abstract|final)"
                     r"\s+)*function\s+__construct\s*\(([^)]*)\)", tok)
        if m and in_class:
            args = [a.strip().lstrip("$")
                    for a in m.group(1).split(",") if a.strip()]
            out.append("    " * ind +
                       f"def __init__({', '.join(['self'] + args)}):")
            blocks.append([ind, False, False])
            ind += 1
            continue

        # function name
        m = re.match(r"(?:(?:public|private|protected|static|abstract|final)"
                     r"\s+)*function\s+(\w+)\s*\(([^)]*)\)", tok)
        if m and m.group(1) != "__construct":
            name = m.group(1)
            args = [a.strip().lstrip("$")
                    for a in m.group(2).split(",") if a.strip()]
            prefix = ["self"] if in_class else []
            out.append("    " * ind +
                       f"def {name}({', '.join(prefix + args)}):")
            blocks.append([ind, False, False])
            ind += 1
            continue

        # for
        m = re.match(r"for\s*\(\s*\$(\w+)\s*=\s*(-?\d+)\s*;\s*"
                     r"\$\1\s*<\s*(.+?)\s*;\s*\$\1\+\+\s*\)", tok)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            out.append("    " * ind +
                       f"for {v} in range({a}, {_php_expr_to_py(b)}):")
            blocks.append([ind, False, False])
            ind += 1
            continue

        # foreach $k => $v
        m = re.match(r"foreach\s*\(\s*\$(\w+)\s+as\s+\$(\w+)\s*=>\s*\$(\w+)\s*\)",
                     tok)
        if m:
            arr, k, v = m.group(1), m.group(2), m.group(3)
            out.append("    " * ind + f"for {k}, {v} in {arr}.items():")
            blocks.append([ind, False, False])
            ind += 1
            continue

        # foreach $x
        m = re.match(r"foreach\s*\(\s*\$(\w+)\s+as\s+\$(\w+)\s*\)", tok)
        if m:
            out.append("    " * ind + f"for {m.group(2)} in {m.group(1)}:")
            blocks.append([ind, False, False])
            ind += 1
            continue

        # --- switch ---
        m = re.match(r"switch\s*\(\s*(.+?)\s*\)\s*$", tok)
        if m:
            out.append("    " * ind + f"_sw = {_php_expr_to_py(m.group(1))}")
            blocks.append([ind, True, False])
            continue

        # --- case ---
        m = re.match(r"case\s+(.+?)\s*:\s*;?\s*$", tok)
        if m:
            if blocks and blocks[-1][1]:    # is switch
                base = blocks[-1][0]
                kw = "elif" if blocks[-1][2] else "if"
                out.append("    " * base +
                           f"{kw} _sw == {_php_expr_to_py(m.group(1))}:")
                blocks[-1][2] = True
                ind = base + 1
            continue

        # --- default ---
        if re.match(r"^default\s*:\s*;?\s*$", tok):
            if blocks and blocks[-1][1]:
                base = blocks[-1][0]
                out.append("    " * base + "else:")
                blocks[-1][2] = True
                ind = base + 1
            continue

        # --- break ---
        if re.match(r"^break\s*;?\s*$", tok):
            continue

        # --- анонимная функция ---
        m = re.match(r"\$(\w+)\s*=\s*function\s*\(([^)]*)\)\s*\{?", tok)
        if m:
            args = ", ".join(a.strip().lstrip("$")
                             for a in m.group(2).split(",") if a.strip())
            out.append("    " * ind + f"{m.group(1)} = lambda {args}:")
            blocks.append([ind, False, False])
            ind += 1
            continue

        # while
        m = re.match(r"while\s*\((.+?)\)\s*$", tok)
        if m:
            out.append("    " * ind +
                       f"while {_php_expr_to_py(m.group(1))}:")
            blocks.append([ind, False, False])
            ind += 1
            continue

        # if
        m = re.match(r"if\s*\((.+?)\)\s*$", tok)
        if m:
            out.append("    " * ind + f"if {_php_expr_to_py(m.group(1))}:")
            blocks.append([ind, False, False])
            ind += 1
            continue

        # elseif
        m = re.match(r"elseif\s*\((.+?)\)\s*$", tok)
        if m:
            if blocks:
                base = blocks[-1][0]
                ind = base
                out.append("    " * base +
                           f"elif {_php_expr_to_py(m.group(1))}:")
                ind = base + 1
            continue

        # else
        if tok == "else":
            if blocks:
                base = blocks[-1][0]
                ind = base
                out.append("    " * base + "else:")
                ind = base + 1
            continue

        # try / catch / finally
        if tok == "try":
            out.append("    " * ind + "try:")
            blocks.append([ind, False, False])
            ind += 1
            continue

        m = re.match(r"catch\s*\(\s*\w+\s+\$(\w+)\s*\)", tok)
        if m:
            if blocks:
                base = blocks[-1][0]
                ind = base
                out.append("    " * base +
                           f"except Exception as {m.group(1)}:")
                ind = base + 1
            continue

        if tok == "finally":
            if blocks:
                base = blocks[-1][0]
                ind = base
                out.append("    " * base + "finally:")
                ind = base + 1
            continue

        # throw
        m = re.match(r"throw\s+new\s+\w+\s*\((.*)\)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"raise Exception({_php_expr_to_py(m.group(1))})")
            continue

        # return
        m = re.match(r"return\s*(.*?)\s*;?$", tok)
        if m:
            val = m.group(1).strip()
            if val:
                out.append("    " * ind + f"return {_php_expr_to_py(val)}")
            else:
                out.append("    " * ind + "return")
            continue

        # echo / print
        m = re.match(r"(?:echo|print)\s+(.+?)\s*;?$", tok)
        if m:
            args = [a for a in _split_top_level(m.group(1), ',') if a.strip()]
            if not args:
                continue
            _BOOL_FUNCS = ("in_array", "is_null", "is_array",
                           "is_int", "is_string", "is_bool")
            if len(args) == 1:
                conv = _php_expr_to_py(args[0])
                if any(fn + "(" in args[0] for fn in _BOOL_FUNCS):
                    conv = f"int({conv})"
                out.append("    " * ind +
                           f"print({conv}, end='')")
            else:
                convs = []
                for a in args:
                    c = _php_expr_to_py(a)
                    if any(fn + "(" in a for fn in _BOOL_FUNCS):
                        c = f"int({c})"
                    convs.append(c)
                out.append("    " * ind +
                           f"print({', '.join(convs)}, sep='', end='')")
            continue

        # array_push / $arr[] / $arr[key]
        m = re.match(r"array_push\s*\(\s*\$(\w+)\s*,\s*(.+?)\s*\)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)}.append({_php_expr_to_py(m.group(2))})")
            continue
        m = re.match(r"\$(\w+)\[\]\s*=\s*(.+?)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)}.append({_php_expr_to_py(m.group(2))})")
            continue
        m = re.match(r"\$(\w+)\[([^\]]+)\]\s*=\s*(.+?)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)}[{_php_expr_to_py(m.group(2))}]"
                       f" = {_php_expr_to_py(m.group(3))}")
            continue

        # $this->field = ...
        m = re.match(r"\$this->(\w+)\s*=\s*(.+?)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"self.{m.group(1)} = {_php_expr_to_py(m.group(2))}")
            continue

        # $x = array(...) / [...]
        m = re.match(r"\$(\w+)\s*=\s*(array\(.*\)|\[.*\])\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} = {_php_expr_to_py(m.group(2))}")
            continue

        # $obj = new Class(...)
        m = re.match(r"\$(\w+)\s*=\s*new\s+(\w+)\s*\((.*)\)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} = {m.group(2)}"
                       f"({_php_expr_to_py(m.group(3))})")
            continue

        # $x op= expr
        m = re.match(r"\$(\w+)\s*([+\-*/])=\s*(.+?)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} {m.group(2)}= "
                       f"{_php_expr_to_py(m.group(3))}")
            continue

        # $x = expr
        m = re.match(r"\$(\w+)\s*=\s*(.+?)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} = {_php_expr_to_py(m.group(2))}")
            continue

        # вызов функции
        m = re.match(r"(\w+)\s*\((.*)\)\s*;?$", tok)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)}({_php_expr_to_py(m.group(2))})")
            continue

        continue

    return "\n".join(out) + "\n"


# ==================================================================
#  Генераторы тестов
# ==================================================================
def _gen_php_50():
    p = []
    for n in (5, 10, 15, 20):
        p.append(f'echo "=== Квадраты 1..{n} ===\\n";')
        p.append(f'for ($i = 1; $i < {n+1}; $i++) echo $i * $i . "\\n";')
        p.append('')
    for n in (5, 10, 15):
        p.append(f'echo "=== Факториалы 1..{n} ===\\n";')
        p.append('$f = 1;')
        p.append(f'for ($i = 1; $i < {n+1}; $i++) {{ $f = $f * $i; '
                 f'echo $f . "\\n"; }}')
        p.append('')
    for n in (5, 10):
        p.append(f'echo "=== Фибоначчи 0..{n} ===\\n";')
        p.append('$a = 0; $b = 1;')
        p.append(f'for ($i = 0; $i < {n+1}; $i++) {{ echo $a . "\\n"; '
                 f'$c = $a + $b; $a = $b; $b = $c; }}')
        p.append('')
    p.append('echo "=== Сумма 1..100 ===\\n";')
    p.append('$s = 0;')
    p.append('for ($i = 1; $i < 101; $i++) $s = $s + $i;')
    p.append('echo $s . "\\n";')
    p.append('')
    p.append('echo "Готово.\\n";')
    return "\n".join(p)


def _gen_php_200():
    p = []
    for m in (2, 3, 4, 5, 6, 7, 8, 9):
        p.append(f'echo "=== Умножение на {m} ===\\n";')
        p.append(f'for ($i = 1; $i < 11; $i++) echo $i * {m} . "\\n";')
        p.append('')
    for b, n in ((2, 15), (3, 10), (5, 8)):
        p.append(f'echo "=== Степени {b} ===\\n";')
        p.append('$p = 1;')
        p.append(f'for ($i = 0; $i < {n+1}; $i++) {{ echo $p . "\\n"; '
                 f'$p = $p * {b}; }}')
        p.append('')
    for n in (5, 10, 15, 20):
        p.append(f'echo "=== Квадраты 1..{n} ===\\n";')
        p.append(f'for ($i = 1; $i < {n+1}; $i++) echo $i * $i . "\\n";')
        p.append('')
    for n in (5, 10, 15):
        p.append(f'echo "=== Кубы 1..{n} ===\\n";')
        p.append(f'for ($i = 1; $i < {n+1}; $i++) echo $i * $i * $i . "\\n";')
        p.append('')
    for n in (5, 10, 15):
        p.append(f'echo "=== Факториалы 1..{n} ===\\n";')
        p.append('$f = 1;')
        p.append(f'for ($i = 1; $i < {n+1}; $i++) {{ $f = $f * $i; '
                 f'echo $f . "\\n"; }}')
        p.append('')
    for n in (10, 15, 20, 25):
        p.append(f'echo "=== Фибоначчи 0..{n} ===\\n";')
        p.append('$a = 0; $b = 1;')
        p.append(f'for ($i = 0; $i < {n+1}; $i++) {{ echo $a . "\\n"; '
                 f'$c = $a + $b; $a = $b; $b = $c; }}')
        p.append('')
    for n in (10, 20, 30, 40):
        p.append(f'echo "=== Треугольные 1..{n} ===\\n";')
        p.append('$t = 0;')
        p.append(f'for ($i = 1; $i < {n+1}; $i++) {{ $t = $t + $i; '
                 f'echo $t . "\\n"; }}')
        p.append('')
    p.append('echo "Готово.\\n";')
    return "\n".join(p)


class PhpLang(Language):
    name = "php"
    title = "PHP"
    category = "О"
    ext = ".php"
    keywords = [
        "function", "if", "else", "elseif", "for", "foreach", "while",
        "do", "return", "echo", "print", "true", "false", "null",
        "class", "public", "private", "protected", "new", "array",
        "try", "catch", "finally", "throw", "extends", "abstract",
        "array_push", "count", "strlen", "strtoupper", "strtolower",
        "explode", "implode", "str_replace", "trim", "switch", "case",
        "default", "break",
    ]
    types = ["int", "float", "string", "bool", "array", "object"]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': '<?php\necho "Hello, World!\\n";\n?>',
        '[E2] Арифметика': '<?php\n$a = 17;\n$b = 5;\necho $a + $b . "\\n";\necho $a - $b . "\\n";\necho $a * $b . "\\n";\necho $a / $b . "\\n";\necho $a % $b . "\\n";\n?>',
        '[E3] Строки': '<?php\n$s = "Programming";\necho strlen($s) . "\\n";\necho strtoupper($s) . "\\n";\necho strtolower($s) . "\\n";\necho substr($s, 0, 4) . "\\n";\n?>',
        '[E4] Условие': '<?php\n$x = 7;\nif ($x % 2 == 0) {\n    echo "чёт\\n";\n} else {\n    echo "нечёт\\n";\n}\n?>',
        '[E5] Функция square': '<?php\nfunction square($x) {\n    return $x * $x;\n}\necho square(7) . "\\n";\necho square(12) . "\\n";\necho square(25) . "\\n";\n?>',
        '[M1] Цикл for': '<?php\nfor ($i = 1; $i < 6; $i++) {\n    echo $i . "\\n";\n}\n?>',
        '[M2] Цикл while (факториал)': '<?php\n$n = 5;\n$fact = 1;\nwhile ($n > 1) {\n    $fact = $fact * $n;\n    $n = $n - 1;\n}\necho $fact . "\\n";\n?>',
        '[M3] Рекурсия': '<?php\nfunction fact($n) {\n    if ($n <= 1) {\n        return 1;\n    }\n    return $n * fact($n - 1);\n}\necho fact(5) . "\\n";\necho fact(7) . "\\n";\necho fact(10) . "\\n";\n?>',
        '[M4] Две функции': '<?php\nfunction add($a, $b) {\n    return $a + $b;\n}\nfunction mul($a, $b) {\n    return $a * $b;\n}\necho add(3, 4) . "\\n";\necho mul(3, 4) . "\\n";\n?>',
        '[M5] Сумма 1..10': '<?php\n$sum = 0;\nfor ($i = 1; $i < 11; $i++) {\n    $sum = $sum + $i;\n}\necho $sum . "\\n";\n?>',
        '[H1] GCD': '<?php\nfunction gcd($a, $b) {\n    while ($b != 0) {\n        $t = $b;\n        $b = $a % $b;\n        $a = $t;\n    }\n    return $a;\n}\necho gcd(12, 8) . "\\n";\necho gcd(100, 25) . "\\n";\necho gcd(17, 5) . "\\n";\n?>',
        '[H2] Fibonacci (итеративный)': '<?php\n$a = 0;\n$b = 1;\nfor ($i = 0; $i < 15; $i++) {\n    echo $a . "\\n";\n    $t = $a + $b;\n    $a = $b;\n    $b = $t;\n}\n?>',
        '[H3] Сумма квадратов': '<?php\n$sum = 0;\nfor ($i = 1; $i < 11; $i++) {\n    $sum = $sum + $i * $i;\n}\necho $sum . "\\n";\n?>',
        '[H4] Вложенные циклы': '<?php\nfor ($i = 1; $i < 4; $i++) {\n    for ($j = 1; $j < 4; $j++) {\n        echo $i * $j . "\\n";\n    }\n}\n?>',
        '[H5] Три функции': '<?php\nfunction add($a, $b) {\n    return $a + $b;\n}\nfunction sq($x) {\n    return $x * $x;\n}\nfunction sumSq() {\n    $s = 0;\n    for ($i = 1; $i < 6; $i++) {\n        $s = add($s, sq($i));\n    }\n    return $s;\n}\necho sumSq() . "\\n";\n?>',
        '[W1] Таблица ×7': '<?php\n$k = 7;\nfor ($i = 1; $i < 11; $i++) {\n    echo $i * $k . "\\n";\n}\n?>',
        '[W2] Квадраты и кубы': '<?php\nfor ($i = 1; $i < 11; $i++) {\n    echo $i * $i . "\\n";\n}\nfor ($i = 1; $i < 11; $i++) {\n    echo $i * $i * $i . "\\n";\n}\n?>',
        '[W3] Простые числа до 30': '<?php\n$n = 2;\nwhile ($n <= 30) {\n    $prime = true;\n    $d = 2;\n    while ($d < $n) {\n        if ($n % $d == 0) {\n            $prime = false;\n        }\n        $d = $d + 1;\n    }\n    if ($prime) {\n        echo $n . "\\n";\n    }\n    $n = $n + 1;\n}\n?>',
        '[W4] Сумма 1..100': '<?php\n$sum = 0;\nfor ($i = 1; $i < 101; $i++) {\n    $sum = $sum + $i;\n}\necho $sum . "\\n";\n?>',
        '[W5] Таблица 10×10': '<?php\nfor ($i = 1; $i < 11; $i++) {\n    for ($j = 1; $j < 11; $j++) {\n        echo $i * $j . "\\n";\n    }\n}\n?>',
        '[T1] Базовые конструкции': '<?php\n$a = 10;\n$b = 3;\necho $a + $b . "\\n";\necho $a - $b . "\\n";\necho $a * $b . "\\n";\necho $a / $b . "\\n";\nfor ($i = 0; $i < 3; $i++) {\n    echo $i . "\\n";\n}\n?>',
        '[T2] Все структуры': '<?php\n$s = "Hello";\n$x = 10;\n$y = 20;\n$sum = $x + $y;\necho strlen($s) . "\\n";\necho strtoupper($s) . "\\n";\necho $x . "\\n";\necho $y . "\\n";\necho $sum . "\\n";\necho $sum * 2 . "\\n";\n?>',
        '[T3] Всё вместе': '<?php\nfunction sumTo5() {\n    $s = 0;\n    for ($i = 1; $i < 6; $i++) {\n        $s = $s + $i;\n    }\n    return $s;\n}\nfunction doubleIt($x) {\n    return $x * 2;\n}\n$s = sumTo5();\n$d = doubleIt($s);\n$label = "Result";\necho $s . "\\n";\necho $d . "\\n";\necho strlen($label) . "\\n";\nfor ($i = 0; $i < 3; $i++) {\n    echo $i . "\\n";\n}\n?>',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if re.search(r"\b(include|require)(?:_once)?\b", src):
            return "# PHP: include/require не поддержаны (нужен AST)"
        py = _php_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<php>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// PHP: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return '<?php echo ""; ?>\n'
        parts = output.split("\n")
        body = []
        for i, ln in enumerate(parts):
            if ln:
                body.append(f'echo {json.dumps(ln)};')
            if i < len(parts) - 1:
                body.append('echo "\\n";')
        if not body:
            body = ['echo "";']
        return '<?php\n' + "\n".join(body) + '\n?>\n'


TRANSPILERS[("php", "python")] = _php_to_python
