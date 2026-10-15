# core/str_utils.py
"""String-aware утилиты: split/find вне строковых литералов."""
from __future__ import annotations


def find_outside_strings(s: str, target: str, start: int = 0) -> int:
    """Индекс первого target вне строк, или -1."""
    i, n = start, len(s)
    in_str = None
    while i < n:
        c = s[i]
        if in_str:
            if c == "\\" and i + 1 < n:
                i += 2; continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in '"\'':
            in_str = c; i += 1; continue
        if s.startswith(target, i):
            return i
        i += 1
    return -1


def split_outside_strings(s: str, sep: str) -> list[str]:
    """Разбивает по sep вне строк."""
    parts = []
    rest = s
    while True:
        idx = find_outside_strings(rest, sep)
        if idx < 0:
            parts.append(rest)
            break
        parts.append(rest[:idx])
        rest = rest[idx + len(sep):]
    return parts


def cut_line_comment(line: str, marker: str = "//") -> str:
    """Срезает маркер и всё после, если он вне строк."""
    i, n = 0, len(line)
    in_str = None
    while i < n:
        c = line[i]
        if in_str:
            if c == "\\" and i + 1 < n:
                i += 2; continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in '"\'':
            in_str = c; i += 1; continue
        if line.startswith(marker, i):
            return line[:i]
        i += 1
    return line


def find_statement_end(s: str, start: int = 0) -> int:
    """Индекс первой ; вне строк и вне (){}[], или len(s)."""
    i, n = start, len(s)
    depth = 0
    in_str = None
    while i < n:
        c = s[i]
        if in_str:
            if c == "\\" and i + 1 < n:
                i += 2; continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in '"\'':
            in_str = c; i += 1; continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            return i
        i += 1
    return n


def split_statements(src: str) -> list[str]:
    """Разбивает по ; вне строк и вне скобок."""
    parts = []
    rest = src
    while True:
        idx = find_statement_end(rest, 0)
        if idx >= len(rest):
            parts.append(rest)
            break
        parts.append(rest[:idx])
        rest = rest[idx + 1:]
    return [p for p in parts if p.strip()]
