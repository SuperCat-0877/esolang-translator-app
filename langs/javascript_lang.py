# langs/javascript_lang.py
"""JavaScript — обычный язык. Транспайлер JS → Python.

Возможности:
  * конкатенация строк с авто-`str()`;
  * шаблонные строки `...${x}...` → f-строки;
  * `===` / `!==`, `&&` / `||` / `!` → питоновские аналоги;
  * `Math.*`, `parseInt/Float`, методы массивов и строк;
  * `.length`, `.toLowerCase()`, `.trim()` и др. на любом выражении,
    в т.ч. на цепочках (`"a,b".split(",").length`);
  * `while`, `for`, `for-of`, `for-in`;
  * классы, конструкторы, методы, arrow-функции;
  * `try/catch/finally`, `throw`;
  * `i++`, `i--`, `++i`, `--i`;
  * `this.value = ...`, `obj.field = ...`, `arr[i] = ...`.
Все замены идентификаторов делаются ВНЕ строковых литералов.
"""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS
from core.test_gen import gen_js_50, gen_js_200
from core.standard_templates import std_js

# ==================================================================
#  Регулярка для строковых литералов
# ==================================================================
_STRING_RE = re.compile(
    r'"(?:\\.|[^"\\])*"'
    r"|'(?:\\.|[^'\\])*'"
    r"|`(?:\\.|[^`\\])*`"
)

def _map_outside_strings(e, fn):
    """Применяет fn ко всем фрагментам ВНЕ строковых литералов."""
    result = []
    last = 0
    for m in _STRING_RE.finditer(e):
        result.append(fn(e[last:m.start()]))
        result.append(m.group(0))
        last = m.end()
    result.append(fn(e[last:]))
    return "".join(result)

def _has_string_literal(e):
    return bool(_STRING_RE.search(e))

# ==================================================================
#  Разбиение по sep на верхнем уровне
# ==================================================================
def _split_top_level(s, sep):
    parts, buf, depth = [], [], 0
    in_str = None
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
        if ch in ('"', "'", "`"):
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
        i += 1
    parts.append("".join(buf))
    return parts

# ==================================================================
#  Шаблонные строки
# ==================================================================
def _convert_template_literal(e):
    def repl(m):
        inner = m.group(1)
        inner = inner.replace("\\`", "`").replace("\\$", "$")
        inner = re.sub(r"\$\{([^{}]*)\}", r"{\1}", inner)
        inner = inner.replace('"', '\\"')
        return 'f"' + inner + '"'
    return re.sub(r"`([^`]*)`", repl, e)

# ==================================================================
#  Авто-str при конкатенации
# ==================================================================
def _auto_str_concat(e):
    if not _has_string_literal(e):
        return e
    parts = _split_top_level(e, "+")
    if len(parts) <= 1:
        return e
    out = []
    for p in parts:
        ps = p.strip()
        if not ps:
            continue
        if (_has_string_literal(ps)
                or ps.startswith("str(")
                or ps.startswith('f"')
                or ps.startswith("f'")):
            out.append(ps)
        else:
            out.append("str(" + ps + ")")
    return " + ".join(out)

# ==================================================================
#  Object literals  {a: 1, b: "x"}  →  {"a": 1, "b": "x"}
# ==================================================================
def _convert_object_literals(e):
    """Преобразует `{key: value}` в `{"key": value}` (только верхний
    уровень, без вложенных фигурных скобок)."""
    def repl(m):
        inner = m.group(1).strip()
        if not inner:
            return "{}"
        parts = _split_top_level(inner, ',')
        converted = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # Ищем `key: value` на верхнем уровне
            depth = 0
            in_str = None
            colon = -1
            i = 0
            while i < len(p):
                ch = p[i]
                if in_str:
                    if ch == "\\" and i + 1 < len(p):
                        i += 2
                        continue
                    if ch == in_str:
                        in_str = None
                    i += 1
                    continue
                if ch in ('"', "'", "`"):
                    in_str = ch
                elif ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
                elif ch == ":" and depth == 0:
                    colon = i
                    break
                i += 1
            if colon == -1:
                converted.append(p)
                continue
            k = p[:colon].strip()
            v = p[colon + 1:].strip()
            if re.match(r"^\w+$", k) and not k.startswith(('"', "'")):
                converted.append(f'"{k}": {_js_expr_to_py(v)}')
            elif k.startswith(('[', '{"')) or k.startswith("'"):
                converted.append(f'{k}: {_js_expr_to_py(v)}')
            else:
                converted.append(f'{_js_expr_to_py(k)}: {_js_expr_to_py(v)}')
        return "{" + ", ".join(converted) + "}"
    # Не заходим во вложенные {}
    return re.sub(r"\{([^{}]*)\}", repl, e)

# ==================================================================
#  Optional chaining  a?.b  →  (a.b if a is not None else None)
#  Nullish            a ?? b →  (a if a is not None else b)
# ==================================================================
def _convert_nullish(e):
    """Простой случай: `X ?? Y` → `(X if X is not None else Y)`."""
    if "??" not in e:
        return e
    parts = _split_top_level(e, "?")
    # Наивно: ищем единственный `??`
    if len(parts) == 2 and parts[1].startswith("?"):
        left = parts[0].strip()
        right = parts[1][1:].strip()
        return f"({left} if {left} is not None else {right})"
    return e

def _convert_optional_chain(e):
    """`a?.b` → `(a.b if a is not None else None)` для простого ident. """
    if "?." not in e:
        return e
    def repl(m):
        obj = m.group(1)
        field = m.group(2)
        return f"({obj}.{field} if {obj} is not None else None)"
    return re.sub(r"\b(\w+)\?\.(\w+)", repl, e)

# ==================================================================
#  Методы массивов
# ==================================================================
def _convert_array_methods(e):
    """arr.map(x => body)  →  [body for x in arr]"""
    def _arrow_var(arg_str):
        a = arg_str.strip()
        if a.startswith("(") and a.endswith(")"):
            a = a[1:-1].strip()
        return a

    # .map(x => expr)
    def repl_map(m):
        arr, arg, body = m.group(1), m.group(2), m.group(3)
        return f"[{body} for {arg} in {arr}]"
    e = re.sub(
        r"(\w+)\.map\s*\(\s*\(?(\w+)\)?\s*=>\s*([^()]+?)\)",
        repl_map, e)

    # .filter(x => cond)
    def repl_filter(m):
        arr, arg, body = m.group(1), m.group(2), m.group(3)
        return f"[{arg} for {arg} in {arr} if {body}]"
    e = re.sub(
        r"(\w+)\.filter\s*\(\s*\(?(\w+)\)?\s*=>\s*([^()]+?)\)",
        repl_filter, e)

    # .forEach(x => stmt)
    def repl_foreach(m):
        arr, arg, body = m.group(1), m.group(2), m.group(3)
        return f"[{body} for {arg} in {arr}]"
    e = re.sub(
        r"(\w+)\.forEach\s*\(\s*\(?(\w+)\)?\s*=>\s*([^()]+?)\)",
        repl_foreach, e)

    # .reduce((a, b) => expr, init)
    def repl_reduce(m):
        arr, a, b, body, init = (m.group(1), m.group(2),
                                 m.group(3), m.group(4), m.group(5))
        return (f"__import__('functools').reduce("
                f"lambda {a}, {b}: {body}, {arr}, {init})")
    e = re.sub(
        r"(\w+)\.reduce\s*\(\s*\((\w+),\s*(\w+)\)\s*=>\s*([^,()]+?)\s*,"
        r"\s*([^()]+?)\)",
        repl_reduce, e)

    # .find(x => cond)
    def repl_find(m):
        arr, arg, body = m.group(1), m.group(2), m.group(3)
        return f"next(({arg} for {arg} in {arr} if {body}), None)"
    e = re.sub(
        r"(\w+)\.find\s*\(\s*\(?(\w+)\)?\s*=>\s*([^()]+?)\)",
        repl_find, e)

    # .some(x => cond) / .every(x => cond)
    def repl_some(m):
        arr, arg, body = m.group(1), m.group(2), m.group(3)
        return f"any({body} for {arg} in {arr})"
    def repl_every(m):
        arr, arg, body = m.group(1), m.group(2), m.group(3)
        return f"all({body} for {arg} in {arr})"
    e = re.sub(
        r"(\w+)\.some\s*\(\s*\(?(\w+)\)?\s*=>\s*([^()]+?)\)",
        repl_some, e)
    e = re.sub(
        r"(\w+)\.every\s*\(\s*\(?(\w+)\)?\s*=>\s*([^()]+?)\)",
        repl_every, e)

    return e

# ==================================================================
#  Scanner: .length / .method() на ЛЮБОМ выражении
# ==================================================================

_ZERO_ARG_METHODS = {
    "toLowerCase": "{}.lower()",
    "toUpperCase": "{}.upper()",
    "trim":        "{}.strip()",
    "trimStart":   "{}.lstrip()",
    "trimEnd":     "{}.rstrip()",
    "trimLeft":    "{}.lstrip()",
    "trimRight":   "{}.rstrip()",
    "toString":    "str({})",
    "pop":         "{}.pop()",
    "shift":       "{}.pop(0)",
}

_ARG_METHODS = {
    "repeat":     "({0}) * ({1})",
    "padStart":   "({0}).rjust({1}, {2})",
    "padEnd":     "({0}).ljust({1}, {2})",
    "charCodeAt": "ord(({0})[{1}])",
}


def _find_expr_start(s):
    """Возвращает индекс начала самого длинного постфикс-выражения,
    оканчивающегося на последнем символе s, или None.
    Понимает: identifier, "str", (...), [...], цепочки .method(args).
    """
    j = len(s) - 1
    while j >= 0 and s[j] in " \t":
        j -= 1
    if j < 0:
        return None

    while True:
        if j < 0:
            return 0
        ch = s[j]

        if ch == ")":
            depth = 1
            k = j - 1
            while k >= 0 and depth > 0:
                if s[k] == ")":
                    depth += 1
                elif s[k] == "(":
                    depth -= 1
                k -= 1
            if depth != 0:
                return j + 1
            j = k
            # после `)` может быть identifier (имя метода) перед `.`
            if j >= 0 and (s[j].isalnum() or s[j] in "_$"):
                while j >= 0 and (s[j].isalnum() or s[j] in "_$"):
                    j -= 1

        elif ch == "]":
            depth = 1
            k = j - 1
            while k >= 0 and depth > 0:
                if s[k] == "]":
                    depth += 1
                elif s[k] == "[":
                    depth -= 1
                k -= 1
            if depth != 0:
                return j + 1
            j = k

        elif ch in ('"', "'", "`"):
            quote = ch
            k = j - 1
            while k >= 0:
                if s[k] == "\\" and k - 1 >= 0:
                    k -= 2
                    continue
                if s[k] == quote:
                    break
                k -= 1
            if k < 0:
                return j + 1
            j = k - 1

        elif ch.isalnum() or ch in "_$":
            k = j
            while k >= 0 and (s[k].isalnum() or s[k] in "_$"):
                k -= 1
            j = k

        else:
            return j + 1

        # после каждой "единицы" проверяем, есть ли перед ней `.`
        if j >= 0 and s[j] == ".":
            j -= 1
            continue
        return j + 1

def _expand_then_foreach_expr(e):
    """a.then(cb) → (cb)(a); a.forEach(cb) → [(cb)(_it) for _it in a]."""
    while True:
        found = None
        i = 0
        n = len(e)
        in_str = None
        while i < n:
            ch = e[i]
            if in_str:
                if ch == "\\" and i + 1 < n:
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
                i += 1
                continue
            if ch in ('"', "'", "`"):
                in_str = ch
                i += 1
                continue
            if e[i:i + 6] == ".then(":
                found = ("then", i, i + 6)
                break
            if e[i:i + 9] == ".forEach(":
                found = ("forEach", i, i + 9)
                break
            i += 1
        if found is None:
            break
        kind, dot_pos, arg_start = found
        rcv_start = _find_expr_start(e[:dot_pos])
        if rcv_start is None:
            break
        depth = 1
        j = arg_start
        in_str = None
        while j < n:
            ch = e[j]
            if in_str:
                if ch == "\\" and j + 1 < n:
                    j += 2
                    continue
                if ch == in_str:
                    in_str = None
                j += 1
                continue
            if ch in ('"', "'", "`"):
                in_str = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            break
        receiver = e[rcv_start:dot_pos]
        cb = e[arg_start:j]
        if kind == "then":
            new_expr = f"({cb})({receiver})"
        else:
            new_expr = f"[({cb})(_it) for _it in {receiver}]"
        e = e[:rcv_start] + new_expr + e[j + 1:]
    return e


def _replace_methods_outside_strings(e):
    out = []
    i = 0
    n = len(e)
    while i < n:
        ch = e[i]
        if ch in ('"', "'", "`"):
            j = i + 1
            while j < n:
                if e[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if e[j] == ch:
                    break
                j += 1
            out.append(e[i:j + 1])
            i = j + 1
            continue
        if ch == ".":
            m = re.match(r"\.(\w+)(\(([^()]*)\))?", e[i:])
            if m:
                name = m.group(1)
                has_parens = m.group(2) is not None
                args = m.group(3) or ""

                # Методы с 1-2 аргументами
                if has_parens and name in _ARG_METHODS:
                    joined = "".join(out)
                    start = _find_expr_start(joined)
                    if start is not None:
                        expr = joined[start:]
                        args_list = [a.strip() for a in args.split(",")
                                     if a.strip()]
                        try:
                            repl = _ARG_METHODS[name].format(
                                expr, *args_list)
                        except (IndexError, KeyError):
                            repl = None
                        if repl:
                            out = [joined[:start], repl]
                            i += m.end()
                            continue

                # Методы с 0 аргументов
                template = None
                if name == "length" and not has_parens:
                    template = "len({})"
                elif has_parens and name in _ZERO_ARG_METHODS:
                    template = _ZERO_ARG_METHODS[name]
                if template is not None:
                    joined = "".join(out)
                    start = _find_expr_start(joined)
                    if start is not None:
                        expr = joined[start:]
                        out = [joined[:start], template.format(expr)]
                        i += m.end()
                        continue
            out.append(".")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)
def _fix_chunk(chunk):
    chunk = re.sub(r"\btrue\b", "True", chunk)
    chunk = re.sub(r"\bfalse\b", "False", chunk)
    chunk = re.sub(r"\bnull\b", "None", chunk)
    chunk = re.sub(r"\bundefined\b", "None", chunk)

    chunk = chunk.replace("!==", "!=").replace("===", "==")
    chunk = re.sub(r"&&", " and ", chunk)
    chunk = re.sub(r"\|\|", " or ", chunk)
    chunk = re.sub(r"!(?!=)", " not ", chunk)

    # Map / Set — ДО общего new X (иначе new съест Map)
    chunk = re.sub(r"\bnew\s+Map\s*\(\s*\)", "{}", chunk)
    chunk = re.sub(r"\bnew\s+Set\s*\(\s*\)", "set()", chunk)

    chunk = re.sub(r"\bthis\b", "self", chunk)
    chunk = re.sub(r"\bnew\s+(\w+)", r"\1", chunk)

    # typeof x → type(x).__name__
    chunk = re.sub(r"\btypeof\s+([\w.]+)",
                   r"type(\1).__name__", chunk)

    chunk = re.sub(r"Math\.floor\(([^()]*)\)", r"int(\1)", chunk)
    chunk = re.sub(r"Math\.ceil\(([^()]*)\)",
                   r"__import__('math').ceil(\1)", chunk)
    chunk = re.sub(r"Math\.round\(([^()]*)\)", r"round(\1)", chunk)
    chunk = re.sub(r"Math\.sqrt\(([^()]*)\)", r"((\1) ** 0.5)", chunk)
    chunk = re.sub(r"Math\.abs\(([^()]*)\)", r"abs(\1)", chunk)
    chunk = re.sub(r"Math\.pow\(([^,()]*),\s*([^()]*)\)",
                   r"(\1 ** \2)", chunk)
    chunk = re.sub(r"Math\.max\(([^()]*)\)", r"max(\1)", chunk)
    chunk = re.sub(r"Math\.min\(([^()]*)\)", r"min(\1)", chunk)
    chunk = re.sub(r"Math\.random\(\)",
                   r"__import__('random').random()", chunk)
    chunk = re.sub(r"Math\.PI\b", r"__import__('math').pi", chunk)
    # --- normal patch: js extras ---
    chunk = re.sub(r"\bvoid\s+0\b", "None", chunk)
    chunk = re.sub(r"(\w+)\s+instanceof\s+(\w+)",
                   r"isinstance(\1, \2)", chunk)
    chunk = re.sub(r"Math\.E\b", r"__import__('math').e", chunk)

    chunk = re.sub(r"\bparseInt\(([^()]*)\)", r"int(\1)", chunk)
    chunk = re.sub(r"\bparseFloat\(([^()]*)\)", r"float(\1)", chunk)
    chunk = re.sub(r"\bNumber\(([^()]*)\)", r"float(\1)", chunk)
    chunk = re.sub(r"\bString\(([^()]*)\)", r"str(\1)", chunk)
    chunk = re.sub(r"\bBoolean\(([^()]*)\)", r"bool(\1)", chunk)

    chunk = re.sub(r"(\w+)\.push\(([^()]*)\)", r"\1.append(\2)", chunk)
    chunk = re.sub(r"(\w+)\.shift\(\)", r"\1.pop(0)", chunk)
    chunk = re.sub(r"(\w+)\.unshift\(([^()]*)\)",
                   r"\1.insert(0, \2)", chunk)
    chunk = re.sub(r"(\w+)\.indexOf\(([^()]*)\)", r"\1.index(\2)", chunk)
    chunk = re.sub(r"(\w+)\.includes\(([^()]*)\)", r"(\2 in \1)", chunk)

    # --- Map / Set ---
    chunk = re.sub(r"(\w+)\.set\(([^,()]+),\s*([^()]+)\)",
                   r"\1[\2] = \3", chunk)
    chunk = re.sub(r"(\w+)\.get\(([^()]+)\)", r"\1[\2]", chunk)
    chunk = re.sub(r"(\w+)\.has\(([^()]+)\)", r"(\2 in \1)", chunk)
    chunk = re.sub(r"(\w+)\.size\b", r"len(\1)", chunk)
    chunk = re.sub(r"(\w+)\.delete\(([^()]+)\)",
                   r"__import__('builtins').getattr(\1, 'pop', lambda k, d=None: None)(\2, None)", chunk)

    # --- Object.* ---
    chunk = re.sub(r"Object\.keys\(([^()]+)\)",
                   r"list(\1.keys())", chunk)
    chunk = re.sub(r"Object\.values\(([^()]+)\)",
                   r"list(\1.values())", chunk)
    chunk = re.sub(r"Object\.entries\(([^()]+)\)",
                   r"list(\1.items())", chunk)

    # --- Array.* ---
    chunk = re.sub(r"Array\.isArray\(([^()]+)\)",
                   r"isinstance(\1, list)", chunk)
    chunk = re.sub(r"Array\.from\(([^()]+)\)", r"list(\1)", chunk)

    # --- Number.* ---
    chunk = re.sub(r"Number\.isInteger\(([^()]+)\)",
                   r"isinstance(\1, int)", chunk)
    chunk = re.sub(r"Number\.isNaN\(([^()]+)\)",
                   r"__import__('math').isnan(\1)", chunk)

    # --- String methods ---
    chunk = re.sub(r"(\w+)\.repeat\(([^()]+)\)", r"\1 * \2", chunk)
    chunk = re.sub(r"(\w+)\.padStart\(([^,()]+),\s*([^()]+)\)",
                   r"\1.rjust(\2, \3)", chunk)
    chunk = re.sub(r"(\w+)\.padEnd\(([^,()]+),\s*([^()]+)\)",
                   r"\1.ljust(\2, \3)", chunk)
    chunk = re.sub(r"(\w+)\.charCodeAt\(([^()]+)\)",
                   r"ord(\1[\2])", chunk)

    # --- Array.slice(a, b) → a[a:b] ---
    def _slice_repl(m):
        target = m.group(1)
        args = m.group(2)
        if "," in args:
            a, b = args.split(",", 1)
            return f"{target}[{a.strip()}:{b.strip()}]"
        return f"{target}[{args.strip()}:]"
    chunk = re.sub(r"(\w+)\.slice\(([^()]*)\)", _slice_repl, chunk)

    return chunk

def _convert_arrow(e):
    """`x => body` или `(x, y) => body` → `lambda`."""
    m = re.match(r"^\(\s*([^()]*?)\s*\)\s*=>\s*(.+)$", e)
    if m:
        args = m.group(1).strip()
        body = _js_expr_to_py(m.group(2))
        return f"lambda {args}: {body}"
    m = re.match(r"^(\w+)\s*=>\s*(.+)$", e)
    if m:
        arg = m.group(1)
        body = _js_expr_to_py(m.group(2))
        return f"lambda {arg}: {body}"
    return e


def _js_expr_to_py(expr):
    e = expr.strip()
    if not e:
        return e
    # console.log(...) → print(...)
    e = re.sub(
        r"console\.(?:log|error|warn|info)\s*\(([^()]*)\)",
        r"print(\1)", e)
    e = re.sub(r"\bSymbol\s*\([^)]*\)", "object()", e)
    if "`" in e:
        e = _convert_template_literal(e)

    # array-методы ПЕРВЫМИ — внутри них может быть arrow
    e = _convert_array_methods(e)

    # arrow-функции
    if "=>" in e:
        e = _convert_arrow(e)

    # .then(cb) / .forEach(cb) как expression
    m = re.match(r"^(.+?)\.then\s*\((.*)\)\s*$", e)
    if m:
        _r = _js_expr_to_py(m.group(1))
        _c = _js_expr_to_py(m.group(2))
        return f"({_c})({_r})"
    m = re.match(r"^(.+?)\.forEach\s*\((.*)\)\s*$", e)
    if m:
        _a = _js_expr_to_py(m.group(1))
        _c = _js_expr_to_py(m.group(2))
        return f"[({_c})(_it) for _it in {_a}]"

    e = _replace_methods_outside_strings(e)
    e = _map_outside_strings(e, _fix_chunk)
    e = re.sub(r"[ \t]+", " ", e).strip()
    e = _auto_str_concat(e)
    e = _convert_nullish(e)
    e = _convert_optional_chain(e)
    e = _convert_object_literals(e)
    e = re.sub(r"\[\s*\.\.\.(\w+)\s*\]", r"\1", e)
    e = re.sub(r"\[\s*\.\.\.(\w+)\s*,", r"(\1 + [", e)
    e = re.sub(r",\s*\.\.\.(\w+)\s*\]", r"] + \1)", e)
    return e.strip()



# ==================================================================
#  Препроцессинг
# ==================================================================
def _preprocess_js(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"\basync\s+function\s+", "function ", src)
    # Раскрываем однострочные `function name(args) { body }`
    for _ in range(5):
        new_inner = re.sub(
            r"(function\s+\w+\s*\([^)]*\))\s*\{\s*([^{}\n]+?)\s*\}",
            r"\1 {\n\2\n}", src)
        if new_inner == src:
            break
        src = new_inner
    src = re.sub(r"\basync\s+(\([^)]*\)\s*=>)", r"\1", src)
    src = re.sub(r"\basync\s+(\w+\s*=>)", r"\1", src)
    src = re.sub(r"\bawait\s+", "", src)
    src = re.sub(r"(\w+)\.then\s*\(\s*(\w+)\s*\)", r"\2(\1)", src)


    # Однострочное тело без {} → оборачиваем в {} с переводами строк
    src = re.sub(r"(for\s*\([^)]*\))\s+([^;{\n]+);",
                 r"\1 {\n\2;\n}", src)
    src = re.sub(r"(if\s*\([^)]*\))\s+([^;{\n]+);",
                 r"\1 {\n\2;\n}", src)
    src = re.sub(r"(while\s*\([^)]*\))\s+([^;{\n]+);",
                 r"\1 {\n\2;\n}", src)

    cleaned = []
    for line in src.split("\n"):
        if "//" in line:
            # PATCH: string-aware cut комментария
            from core.str_utils import cut_line_comment as _jsl_cut
            line = _jsl_cut(line, "//")
        line = re.sub(r"\}\s*(else\s+if)\b", r"}\n\1", line)
        line = re.sub(r"\}\s*(else)\b", r"}\n\1", line)
        line = re.sub(r"\}\s*(catch)\b", r"}\n\1", line)
        line = re.sub(r"\}\s*(finally)\b", r"}\n\1", line)
        cleaned.extend(line.split("\n"))
    result = []
    for line in cleaned:
        parts = _split_top_level(line, ";")
        for p in parts:
            p = p.strip()
            if p:
                result.append(p)
    return result

# ==================================================================
#  JS → Python
# ==================================================================
def _js_to_python(src):
    lines = _preprocess_js(src)
    out = []
    ind = 0
    in_class = False
    class_indent = 0

    for line in lines:
        if not line:
            continue
        if line.startswith("import ") or line.startswith("from "):
            continue

        # .then/.forEach — приоритетно, до общего «вызов как оператор»
        if ".then(" in line or ".forEach(" in line:
            m = re.match(r"^(.+?)\.then\s*\((.*)\)\s*$", line)
            if m:
                recv = _js_expr_to_py(m.group(1))
                cb = _js_expr_to_py(m.group(2))
                out.append("    " * ind + f"({cb})({recv})")
                continue
            m = re.match(r"^(.+?)\.forEach\s*\((.*)\)\s*$", line)
            if m:
                arr = _js_expr_to_py(m.group(1))
                cb = _js_expr_to_py(m.group(2))
                out.append("    " * ind + f"[({cb})(_it) for _it in {arr}]")
                continue
        line = _expand_then_foreach_expr(line)

        # class Foo [extends Bar] {
        m = re.match(r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{?", line)
        if m:
            name = m.group(1)
            base = m.group(2)
            header = f"class {name}({base}):" if base else f"class {name}:"
            out.append("    " * ind + header)
            ind += 1
            in_class = True
            class_indent = ind
            continue

        # constructor(args) {
        m = re.match(r"constructor\s*\(([^)]*)\)\s*\{?", line)
        if m and in_class:
            args = [a.strip() for a in m.group(1).split(",") if a.strip()]
            args_str = ", ".join(["self"] + args)
            out.append("    " * ind + f"def __init__({args_str}):")
            ind += 1
            continue

        # function name(args) {
        m = re.match(r"function\s+(\w+)\s*\(([^)]*)\)\s*\{?", line)
        if m:
            args = ", ".join(a.strip()
                             for a in m.group(2).split(",") if a.strip())
            out.append("    " * ind + f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # метод класса: name(args) {
        m = re.match(r"(\w+)\s*\(([^)]*)\)\s*\{?\s*$", line)
        if m and in_class and m.group(1) not in (
                "if", "for", "while", "switch", "catch"):
            args = [a.strip() for a in m.group(2).split(",") if a.strip()]
            args_str = ", ".join(["self"] + args)
            out.append("    " * ind + f"def {m.group(1)}({args_str}):")
            ind += 1
            continue

        # arrow с блоком
        m = re.match(
            r"(?:let|var|const)\s+(\w+)\s*=\s*\(?([^()=]*)\)?\s*=>\s*\{\s*$",
            line)
        if m:
            args = ", ".join(a.strip()
                             for a in m.group(2).split(",") if a.strip())
            out.append("    " * ind + f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # arrow с выражением
        m = re.match(
            r"(?:let|var|const)\s+(\w+)\s*=\s*\(?([^()=]*)\)?\s*=>\s*(.+?)$",
            line)
        if m:
            args = ", ".join(a.strip()
                             for a in m.group(2).split(",") if a.strip())
            body = _js_expr_to_py(m.group(3))
            out.append("    " * ind +
                       f"{m.group(1)} = lambda {args}: {body}")
            continue

        # for (let i = A; i < B; i++)  /  i <= B
        m = re.match(
            r"for\s*\(\s*(?:let|var|const|int)\s+(\w+)\s*=\s*(.+?)\s*;\s*"
            r"\1\s*(<=|<)\s*(.+?)\s*;\s*\1\+\+\s*\)\s*\{?\s*$", line)
        if m:
            v = m.group(1)
            start = _js_expr_to_py(m.group(2))
            op = m.group(3)
            end = _js_expr_to_py(m.group(4))
            if op == "<=":
                end = f"({end}) + 1"
            out.append("    " * ind +
                       f"for {v} in range({start}, {end}):")
            ind += 1
            continue

        # for (let i = A; i > B; i--)
        m = re.match(
            r"for\s*\(\s*(?:let|var|const|int)\s+(\w+)\s*=\s*(.+?)\s*;\s*"
            r"\1\s*>\s*(.+?)\s*;\s*\1--\s*\)\s*\{?\s*$", line)
        if m:
            out.append("    " * ind +
                       f"for {m.group(1)} in range("
                       f"{m.group(2)}, {m.group(3)}, -1):")
            ind += 1
            continue

        # for (let x of arr) / for (let k in obj)
        m = re.match(
            r"for\s*\(\s*(?:let|var|const)\s+(\w+)\s+(?:of|in)\s+"
            r"(.+?)\s*\)\s*\{?\s*$", line)
        if m:
            out.append("    " * ind +
                       f"for {m.group(1)} in {_js_expr_to_py(m.group(2))}:")
            ind += 1
            continue

        # while
        m = re.match(r"while\s*\((.+?)\)\s*\{?\s*$", line)
        if m:
            out.append("    " * ind + f"while {_js_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        # if
        m = re.match(r"if\s*\((.+?)\)\s*\{?\s*$", line)
        if m:
            out.append("    " * ind + f"if {_js_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        # else if
        m = re.match(r"(?:\}\s*)?else\s+if\s*\((.+?)\)\s*\{?\s*$", line)
        if m:
            out.append("    " * ind + f"elif {_js_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        # else
        if re.match(r"(?:\}\s*)?else\s*\{?\s*$", line):
            out.append("    " * ind + "else:")
            ind += 1
            continue

        # catch
        m = re.match(r"(?:\}\s*)?catch\s*\(\s*(\w+)\s*\)\s*\{?\s*$", line)
        if m:
            out.append("    " * ind +
                       f"except Exception as {m.group(1)}:")
            ind += 1
            continue

        # finally
        if re.match(r"(?:\}\s*)?finally\s*\{?\s*$", line):
            out.append("    " * ind + "finally:")
            ind += 1
            continue

        # try
        if line in ("try {", "try"):
            out.append("    " * ind + "try:")
            ind += 1
            continue

        # throw
        m = re.match(r"throw\s+(.+?)\s*$", line)
        if m:
            out.append("    " * ind +
                       f"raise Exception({_js_expr_to_py(m.group(1))})")
            continue

        # return
        m = re.match(r"return\s*(.*?)\s*$", line)
        if m:
            val = m.group(1).strip()
            if val:
                out.append("    " * ind + f"return {_js_expr_to_py(val)}")
            else:
                out.append("    " * ind + "return")
            continue

        # console.log / error / warn / info
        m = re.match(r"console\.(?:log|error|warn|info)\s*\((.*)\)\s*$",
                     line)
        if m:
            args = [a for a in _split_top_level(m.group(1), ",") if a.strip()]
            converted = ", ".join(_js_expr_to_py(a) for a in args)
            out.append("    " * ind + f"print({converted})")
            continue

        # i++; / i--;
        m = re.match(r"(\w+)\+\+\s*$", line)
        if m:
            out.append("    " * ind + f"{m.group(1)} += 1")
            continue
        m = re.match(r"(\w+)--\s*$", line)
        if m:
            out.append("    " * ind + f"{m.group(1)} -= 1")
            continue

        # ++i; / --i;
        m = re.match(r"\+\+(\w+)\s*$", line)
        if m:
            out.append("    " * ind + f"{m.group(1)} += 1")
            continue
        m = re.match(r"--(\w+)\s*$", line)
        if m:
            out.append("    " * ind + f"{m.group(1)} -= 1")
            continue

        # obj.set → obj[k] = v    # obj.set → obj[k] = v
        m = re.match(r"([\w.]+)\.set\s*\((.*)\)\s*$", line)
        if m:
            args = _split_top_level(m.group(2), ",")
            if len(args) >= 2:
                obj = _js_expr_to_py(m.group(1))
                k = _js_expr_to_py(args[0])
                v = _js_expr_to_py(", ".join(args[1:]))
                out.append("    " * ind + f"{obj}[{k}] = {v}")
                continue

        # obj.add(x)
        m = re.match(r"([\w.]+)\.add\s*\((.*)\)\s*$", line)
        if m:
            obj = _js_expr_to_py(m.group(1))
            args = _js_expr_to_py(m.group(2))
            out.append("    " * ind + f"{obj}.add({args})")
            continue

        # obj.delete(k)
        m = re.match(r"([\w.]+)\.delete\s*\((.*)\)\s*$", line)
        if m:
            obj = _js_expr_to_py(m.group(1))
            k = _js_expr_to_py(m.group(2))
            out.append("    " * ind +
                       f"if {k} in {obj}: del {obj}[{k}]")
            continue

        # arr.push / arr.pop
        m = re.match(r"(\w+)\.push\s*\((.*)\)\s*$", line)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)}.append({_js_expr_to_py(m.group(2))})")
            continue
        m = re.match(r"(\w+)\.pop\s*\(\s*\)\s*$", line)
        if m:
            out.append("    " * ind + f"{m.group(1)}.pop()")
            continue

        # } (закрытие блока)
        # --- switch (x) { ---
        m = re.match(r"switch\s*\((.+?)\)\s*\{?\s*$", line)
        if m:
            switch_var = "_switch_val"
            out.append("    " * ind +
                       f"{switch_var} = {_js_expr_to_py(m.group(1))}")
            # Заменяем последующие case на if/elif
            ind += 1
            continue

        # --- case X: ---
        m = re.match(r"case\s+(.+?)\s*:\s*$", line)
        if m:
            val = _js_expr_to_py(m.group(1))
            prefix = "if" if "_switch_used" not in out else "elif"
            out.append("    " * ind)
            out.append(f"if _switch_val == {val}:")
            out[-2] = "    " * (ind - 1) + (
                "if _switch_val == " + val + ":")
            ind += 1
            continue

        # --- default: ---
        if line.strip() == "default:":
            ind -= 1
            out.append("    " * ind + "else:")
            ind += 1
            continue

        # --- break; (внутри switch) ---
        if line == "break":
            continue

        # --- do { ---
        if line in ("do {", "do"):
            out.append("    " * ind + "while True:")
            ind += 1
            continue

        # --- } while (cond); ---
        m = re.match(r"\}\s*while\s*\((.+?)\)\s*$", line)
        if m:
            ind -= 1
            out.append("    " * ind +
                       f"if not ({_js_expr_to_py(m.group(1))}): break")
            continue
        if line in ("}", "};"):
            ind = max(0, ind - 1)
            if in_class and ind < class_indent:
                in_class = False
            continue

        # --- let a = 0, b = 1; ---
        m = re.match(r"(?:let|var|const)\s+(.+)$", line)
        if m and "," in m.group(1):
            decls = _split_top_level(m.group(1), ",")
            if len(decls) > 1 and all("=" in d for d in decls):
                for d in decls:
                    d = d.strip()
                    k, _, v = d.partition("=")
                    k = k.strip()
                    v = _js_expr_to_py(v.strip())
                    out.append("    " * ind + f"{k} = {v}")
                continue

        # let/const/var x = [...]
        m = re.match(r"(?:let|var|const)\s+(\w+)\s*=\s*\[(.*)\]$", line)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} = [{m.group(2)}]")
            continue

        # let/const/var x = expr
        m = re.match(r"(?:let|var|const)\s+(\w+)\s*=\s*(.+?)$", line)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)} = {_js_expr_to_py(m.group(2))}")
            continue

        # let x;
        m = re.match(r"(?:let|var|const)\s+(\w+)\s*$", line)
        if m:
            out.append("    " * ind + f"{m.group(1)} = None")
            continue

        # x += / -= / *= / /=
        m = re.match(r"([\w.\[\]]+)\s*([+\-*/])=\s*(?!=)(.+?)$", line)
        if m:
            target = _js_expr_to_py(m.group(1))
            out.append("    " * ind +
                       f"{target} {m.group(2)}= "
                       f"{_js_expr_to_py(m.group(3))}")
            continue

        # x = expr  (target: this.value, obj.field, arr[i])
        m = re.match(r"([\w.\[\]]+)\s*=\s*(?!=)(.+?)$", line)
        if m:
            target = _js_expr_to_py(m.group(1))
            out.append("    " * ind +
                       f"{target} = {_js_expr_to_py(m.group(2))}")
            continue

        # вызов как оператор
        m = re.match(r"(\w+)\s*\((.*)\)\s*$", line)
        if m:
            out.append("    " * ind +
                       f"{m.group(1)}({_js_expr_to_py(m.group(2))})")
            continue

        # fallback — expression statement
        _conv = _js_expr_to_py(line)
        out.append("    " * ind + _conv)
        continue

    return "\n".join(out) + "\n"

# ==================================================================
#  Класс языка
# ==================================================================
class JavaScriptLang(Language):
    name = "javascript"
    title = "JavaScript"
    category = "О"
    ext = ".js"
    keywords = [
        "let", "var", "const", "if", "else", "for", "while", "function",
        "return", "console", "true", "false", "null", "undefined", "new",
        "this", "class", "try", "catch", "finally", "throw",
    ]
    comment_regex = r"//[^\n]*"

    templates = {
        '[E1] Hello, World': 'console.log("Hello, World!");',
        '[E2] Арифметика': 'const a = 17, b = 5;\nconsole.log(a + b, a - b, a * b, Math.floor(a / b), a % b, a ** b);',
        '[E3] Template literals': 'const n = "World";\nconsole.log(`Hello, ${n}! 2+2=${2 + 2}`);',
        '[E4] Стрелочные функции': 'const sq = x => x * x;\nconst add = (a, b) => a + b;\nconsole.log(sq(7), add(3, 4));',
        '[E5] Условие': 'let x = 7;\nif (x % 2 === 0) {\n  console.log("чёт");\n} else {\n  console.log("нечёт");\n}',
        '[M1] Циклы': 'for (let i = 1; i <= 5; i++) {\n  console.log(i, i * i);\n}\nfor (const x of [10, 20, 30]) {\n  console.log(x);\n}',
        '[M2] Методы массива': 'const xs = [1, 2, 3, 4, 5];\nconst sq = xs.map(x => x * x);\nconsole.log(sq);',
        '[M3] Строковые методы': 'const s = "Hello, World";\nconsole.log(s.toUpperCase());\nconsole.log(s.toLowerCase());\nconsole.log(s.length);',
        '[M4] Map': 'const m = new Map();\nm.set("a", 1);\nm.set("b", 2);\nconsole.log(m.get("a"));\nconsole.log(m.get("b"));',
        '[M5] try/catch/finally': 'try {\n  throw new Error("boom");\n} catch (e) {\n  console.log("Caught");\n} finally {\n  console.log("done");\n}',
        '[H1] Классы': 'class Point {\n  constructor(x, y) {\n    this.x = x;\n    this.y = y;\n  }\n  sum() {\n    return this.x + this.y;\n  }\n}\nconst p = new Point(3, 4);\nconsole.log(p.sum());',
        '[H2] Наследование': 'class Animal {\n  constructor(name) {\n    this.name = name;\n  }\n  speak() {\n    return this.name + " makes a sound";\n  }\n}\nclass Dog extends Animal {\n  speak() {\n    return this.name + " barks";\n  }\n}\nconst d = new Dog("Rex");\nconsole.log(d.speak());',
        '[H3] Замыкания и карри': 'const mkAdd = x => y => x + y;\nconst add5 = mkAdd(5);\nconsole.log(add5(3));\nconsole.log(add5(10));',
        '[H4] Композиция функций': 'const compose = (f, g) => x => f(g(x));\nconst inc = x => x + 1;\nconst dbl = x => x * 2;\nconst sq = x => x * x;\nconst step = compose(dbl, inc);\nconst result = compose(sq, step)(3);\nconsole.log(result);',
        '[H5] Итератор по массиву': 'const results = [];\nfor (let i = 1; i <= 5; i++) {\n  results.push(i * i);\n}\nconsole.log(results);',
        '[W1] Мемоизация Fibonacci': 'function fib(n) {\n  if (n < 2) return n;\n  let a = 0;\n  let b = 1;\n  for (let i = 2; i <= n; i++) {\n    const t = a + b;\n    a = b;\n    b = t;\n  }\n  return b;\n}\nfor (let i = 0; i < 15; i++) {\n  console.log(fib(i));\n}',
        '[W2] Конвейер': 'const inc = x => x + 1;\nconst dbl = x => x * 2;\nconst sq = x => x * x;\nlet r = 5;\nr = inc(r);\nr = dbl(r);\nr = sq(r);\nconsole.log(r);',
        '[W3] Рекурсия (Ackermann)': 'function ackermann(m, n) {\n  if (m === 0) return n + 1;\n  if (n === 0) return ackermann(m - 1, 1);\n  return ackermann(m - 1, ackermann(m, n - 1));\n}\nconsole.log(ackermann(2, 3));',
        '[W4] Свёртка': 'const nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];\nconst factorial = nums.reduce((a, b) => a * b, 1);\nconst sum = nums.reduce((a, b) => a + b, 0);\nconsole.log(factorial);\nconsole.log(sum);',
        '[W5] Сортировка': 'const words = ["banana", "apple", "cherry", "date"];\nwords.sort();\nconsole.log(words);',
        '[T1] Базовые конструкции': 'function gcd(a, b) {\n  while (b) {\n    const t = b;\n    b = a % b;\n    a = t;\n  }\n  return a;\n}\nconsole.log(gcd(12, 8));\nconsole.log(gcd(100, 25));\nconsole.log(gcd(17, 5));',
        '[T2] Все структуры': 'const arr = [1, 2, 3];\nconst obj = {};\nobj["a"] = 1;\nobj["b"] = 2;\nconsole.log(arr.length);\nconsole.log(obj["a"] + obj["b"]);',
        '[T3] Всё вместе': 'class Counter {\n  constructor() {\n    this.n = 0;\n  }\n  inc() {\n    this.n = this.n + 1;\n    return this.n;\n  }\n}\nconst c = new Counter();\nconsole.log(c.inc());\nconsole.log(c.inc());\nconsole.log(c.inc());',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        # generators всё ещё требуют AST
        if re.search(r"function\s*\*", src):
            return "// JS: generators не поддержаны (нужен AST)"
        py = _js_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<js>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// JS: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        if not output:
            return "// пустой вывод\n"
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        return "\n".join(
            f"console.log({json.dumps(ln, ensure_ascii=False)});"
            for ln in lines
        ) + "\n"
