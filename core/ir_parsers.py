# core/ir_parsers.py
"""Парсеры: код языка → IR."""
import re
from .ir import (
    Program, Assign, Print, ForLoop, While,
    Num, Str, Var, BinOp, Compare, UnsupportedConstruct,
)


# ---------------------------------------------------------------------------
# Выражения
# ---------------------------------------------------------------------------

def parse_expr(s: str):
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()

    # сравнения (один раз, верхний уровень)
    for op in ("==", "!=", ">=", "<=", ">", "<"):
        depth = 0
        i = 0
        while i < len(s):
            c = s[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            elif depth == 0 and s.startswith(op, i):
                left = s[:i].strip()
                right = s[i + len(op):].strip()
                if left and right:
                    return Compare(op, parse_expr(left), parse_expr(right))
            i += 1

    m = re.fullmatch(r'-?\d+', s)
    if m:
        return Num(int(s))
    m = re.fullmatch(r'-?\d+\.\d+', s)
    if m:
        return Num(float(s))

    m = re.fullmatch(r'"(.*)"', s) or re.fullmatch(r"'(.*)'", s)
    if m:
        return Str(m.group(1))

    # бинарные + - * /
    depth = 0
    for i in range(len(s) - 1, -1, -1):
        c = s[i]
        if c == ')':
            depth += 1
        elif c == '(':
            depth -= 1
        elif depth == 0 and c in '+-*/':
            if c == '-' and (i == 0 or s[i - 1] in '+-*/('):
                continue
            return BinOp(c, parse_expr(s[:i]), parse_expr(s[i + 1:]))

    m = re.fullmatch(r'[A-Za-z_]\w*', s)
    if m:
        return Var(s)

    raise UnsupportedConstruct(f"не понимаю выражение: {s!r}")


def _split_lines(code):
    return [l.rstrip() for l in code.splitlines()]


def _indent(line):
    return len(line) - len(line.lstrip())


# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------

_PRINT_PATTERNS = [
    r'print\((.+)\)\s*;?\s*$',
    r'println\((.+)\)\s*;?\s*$',
    r'console\.log\((.+)\)\s*;?\s*$',
    r'fmt\.Println\((.+)\)\s*$',
    r'printfn\s+"%d"\s+\(?(.+?)\)?\s*$',
    r'IO\.puts\((.+)\)\s*$',
    r'Console\.WriteLine\((.+)\)\s*;?\s*$',
    r'System\.out\.println\((.+)\)\s*;?\s*$',
    r'(?:std::)?cout\s*<<\s*(.+?)\s*<<\s*(?:endl|"\\n")\s*;\s*$',
    r'(?:std::)?cout\s*<<\s*(.+?)\s*;\s*$',
    r'puts\s+\(?(.+?)\)?\s*$',
    r'print\s+\(?(.+?)\)?\s*;?\s*$',
    r'echo\s+(.+?)\s*;\s*$',
    r'println!\([^,]+,\s*(.+?)\)\s*;?\s*$',
    r'println!\("(.+?)"\)\s*;?\s*$',
]


def _try_parse_print(line):
    for pat in _PRINT_PATTERNS:
        m = re.match(pat, line.strip())
        if m:
            try:
                return Print(parse_expr(m.group(1).strip()))
            except UnsupportedConstruct:
                return None
    return None


# ---------------------------------------------------------------------------
# Assign
# ---------------------------------------------------------------------------

_ASSIGN_PATTERNS = [
    r'^\$\s*(\w+)\s*=\s*(.+?)\s*;\s*$',                 # php $x
    r'^let\s+mut\s+(\w+)\s*=\s*(.+?)\s*;\s*$',          # rust
    r'^let\s+(\w+)\s*=\s*(.+?)\s*;?\s*$',
    r'^val\s+(\w+)\s*=\s*(.+?)\s*;?\s*$',
    r'^var\s+(\w+)\s*=\s*(.+?)\s*;?\s*$',
    r'^const\s+(\w+)\s*=\s*(.+?)\s*;?\s*$',
    r'^final\s+(\w+)\s*=\s*(.+?)\s*;?\s*$',
    r'^int\s+(\w+)\s*=\s*(.+?)\s*;\s*$',
    r'^long\s+(\w+)\s*=\s*(.+?)\s*;\s*$',
    r'^double\s+(\w+)\s*=\s*(.+?)\s*;\s*$',
    r'^float\s+(\w+)\s*=\s*(.+?)\s*;\s*$',
    r'^string\s+(\w+)\s*=\s*(.+?)\s*;\s*$',
    r'^my\s+\$\s*(\w+)\s*=\s*(.+?)\s*;\s*$',            # perl
    r'^(\w+)\s*=\s*(.+?)\s*;?\s*$',                     # universal
]


def _try_parse_assign(line):
    s = line.strip()
    for pat in _ASSIGN_PATTERNS:
        m = re.match(pat, s)
        if m:
            name, val = m.group(1), m.group(2).strip()
            try:
                return Assign(name, parse_expr(val))
            except UnsupportedConstruct:
                continue
    return None


# ---------------------------------------------------------------------------
# for
# ---------------------------------------------------------------------------

def _try_parse_for_header(line):
    s = line.strip()
    m = re.match(r'for\s+(\w+)\s+in\s+range\((\d+)\s*,\s*(\d+)\s*\)\s*:?\s*$', s)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3)) - 1

    m = re.match(r'for\s+(\w+)\s+in\s+(\d+)\s*\.\.=?(\d+)\s*\{?\s*$', s)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))

    m = re.match(r'for\s+(\w+)\s*<-\s*(\d+)\.\.(\d+)\s+do\s*$', s)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))

    m = re.match(r'for\s+(\w+)\s+in\s+(\d+)\.\.(\d+)\s+do\s*$', s)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))

    m = re.match(r'for\s+(\w+)\s*=\s*(\d+)\s*,\s*(\d+)\s+do\s*$', s)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))

    m = re.match(
        r'for\s*\(\s*(?:int\s+|let\s+|var\s+|const\s+)?\$?(\w+)\s*=\s*(\d+)\s*;'
        r'\s*\1\s*<=\s*(\d+)\s*;\s*\1\+\+\s*\)\s*\{?\s*$', s)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))

    return None


# ---------------------------------------------------------------------------
# while
# ---------------------------------------------------------------------------

def _try_parse_while_header(line):
    s = line.strip()
    # while (cond) {
    m = re.match(r'while\s*\(\s*(.+?)\s*\)\s*\{?\s*$', s)
    if m:
        return m.group(1)
    # while cond: / while cond do / while cond { / while cond
    m = re.match(r'while\s+(.+?)\s*(?::|do|\{)?\s*$', s)
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Блок
# ---------------------------------------------------------------------------

def _parse_block(lines, i, header_indent, closer=None):
    body = []
    n = len(lines)

    if closer is not None:
        depth = 0
        while i < n:
            line = lines[i]
            s = line.strip()
            if s == "":
                i += 1
                continue
            if s == closer and depth == 0:
                return body, i + 1
            if s.startswith(closer):
                return body, i + 1
            if "{" in s:
                depth += 1
            if "}" in s:
                depth -= 1
            stmt = _parse_statement(lines, i, header_indent, closer)
            if stmt is None:
                i += 1
                continue
            node, i = stmt
            body.append(node)
        return body, i

    # отступом
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _indent(line) <= header_indent:
            break
        stmt = _parse_statement(lines, i, header_indent, closer)
        if stmt is None:
            i += 1
            continue
        node, i = stmt
        body.append(node)
    return body, i


def _parse_statement(lines, i, header_indent, closer):
    """
    Возвращает (node, next_i) или None, если строка не распознана.
    Обновляет i с учётом вложенных блоков.
    """
    raw = lines[i]
    s = raw.strip()

    # for
    hdr = _try_parse_for_header(s)
    if hdr is not None:
        var, start, end = hdr
        body, next_i = _parse_block(lines, i + 1, _indent(raw), closer)
        return ForLoop(var, Num(start), Num(end), body), next_i

    # while
    cond_src = _try_parse_while_header(s)
    if cond_src is not None:
        body, next_i = _parse_block(lines, i + 1, _indent(raw), closer)
        return While(parse_expr(cond_src), body), next_i

    # print
    p = _try_parse_print(raw)
    if p is not None:
        return p, i + 1

    # assign
    a = _try_parse_assign(raw)
    if a is not None:
        return a, i + 1

    return None


# ---------------------------------------------------------------------------
# Общий C-подобный парсер
# ---------------------------------------------------------------------------

def _parse_c_like(code):
    lines = _split_lines(code)
    prog = Program()
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i]
        s = raw.strip()
        if not s:
            i += 1
            continue

        if s in ("{", "}"):
            i += 1
            continue

        # пропускаем обёртки
        if re.match(r'^(package|import|using|#include|public|private|'
                    r'class\s|object\s|static\s|namespace|'
                    r'fun\s+main|func\s+main|void\s+main|int\s+main|'
                    r'return\b)', s):
            i += 1
            continue

        node = _parse_statement(lines, i, _indent(raw), "}")
        if node is None:
            i += 1
            continue
        n_stmt, next_i = node
        prog.body.append(n_stmt)
        i = next_i
    return prog


# ---------------------------------------------------------------------------
# Публичные парсеры
# ---------------------------------------------------------------------------

def parse_python(code):
    lines = _split_lines(code)
    prog = Program()
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        node = _parse_statement(lines, i, _indent(lines[i]), None)
        if node is None:
            i += 1
            continue
        n_stmt, next_i = node
        prog.body.append(n_stmt)
        i = next_i
    return prog


def parse_go(code):
    m = re.search(r'func\s+main\s*\(\s*\)\s*\{(.*)\}\s*$', code, re.S)
    return _parse_c_like(m.group(1) if m else code)


def parse_kotlin(code):
    m = re.search(r'fun\s+main\s*\(\s*\)\s*\{(.*)\}\s*$', code, re.S)
    return _parse_c_like(m.group(1) if m else code)


def parse_rust(code):
    return _parse_c_like(code)

def parse_cpp(code):
    return _parse_c_like(code)

def parse_java(code):
    return _parse_c_like(code)

def parse_csharp(code):
    return _parse_c_like(code)

def parse_js(code):
    return _parse_c_like(code)

def parse_php(code):
    return _parse_c_like(code)

def parse_scala(code):
    return _parse_c_like(code)

def parse_swift(code):
    return _parse_c_like(code)

parse_dart = parse_js
parse_typescript = parse_js


def parse_fsharp(code):
    return _parse_block_lang(code, none_end=False)

def parse_elixir(code):
    return _parse_block_lang(code, none_end=True)

def parse_lua(code):
    return _parse_block_lang(code, none_end=True)

def parse_ruby(code):
    return _parse_block_lang(code, none_end=True)

def parse_perl(code):
    return _parse_block_lang(code, none_end=False)


def _parse_block_lang(code, none_end):
    """Для языков с отступом или end."""
    lines = _split_lines(code)
    prog = Program()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s in ("end", "}"):
            i += 1
            continue
        node = _parse_statement(lines, i, _indent(lines[i]), None)
        if node is None:
            i += 1
            continue
        n_stmt, next_i = node
        prog.body.append(n_stmt)
        i = next_i
    return prog


# ---------------------------------------------------------------------------
# Реестр
# ---------------------------------------------------------------------------

PARSERS = {
    "python": parse_python,
    "go": parse_go,
    "cpp": parse_cpp, "c": parse_cpp,
    "csharp": parse_csharp, "c#": parse_csharp,
    "java": parse_java,
    "kotlin": parse_kotlin,
    "scala": parse_scala,
    "swift": parse_swift,
    "php": parse_php,
    "js": parse_js, "javascript": parse_js,
    "dart": parse_dart,
    "typescript": parse_typescript, "ts": parse_typescript,
    "rust": parse_rust,
    "fsharp": parse_fsharp,
    "elixir": parse_elixir,
    "lua": parse_lua,
    "ruby": parse_ruby,
    "perl": parse_perl,
}


def parse_any(lang, code):
    fn = PARSERS.get(lang)
    if fn is None:
        raise UnsupportedConstruct(f"нет парсера для языка {lang!r}")
    return fn(code)
