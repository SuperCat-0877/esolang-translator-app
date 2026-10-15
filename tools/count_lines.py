# tools/count_lines.py
"""Считает строки в активных .py файлах проекта.

Исключает: __pycache__, .venv, venv, env, build, dist, .git, node_modules,
а также скомпилированные .pyc и всё, что не .py.

Метрики:
  total   - все строки, включая пустые и комментарии
  blank   - пустые строки
  comment - строки, начинающиеся с #
  code    - реальный код (total - blank - comment - docstring)
  docstr  - строки внутри тройных кавычек

Запуск:
    python tools/count_lines.py
    python tools/count_lines.py --by-file
    python tools/count_lines.py --by-dir
"""
import argparse
import io
import tokenize
from pathlib import Path

EXCLUDE_DIRS = {
    "__pycache__", ".venv", "venv", "env",
    "build", "dist", ".git", "node_modules",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".idea", ".vscode", "out",
}

ROOT = Path(__file__).parent.parent


def is_excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return any(part in EXCLUDE_DIRS for part in rel.parts)


def analyze_file(path: Path):
    """Возвращает (total, blank, comment, docstr, code)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    lines = text.splitlines()
    total = len(lines)
    blank = sum(1 for l in lines if not l.strip())
    comment = sum(1 for l in lines if l.strip().startswith("#"))

    # docstring — через tokenize (единственный надёжный способ)
    docstr_lines = set()
    try:
        with io.StringIO(text) as f:
            for tok in tokenize.generate_tokens(f.readline):
                if tok.type == tokenize.STRING:
                    # это docstring, если стоит отдельным выражением
                    # грубая, но рабочая эвристика: строка начинается
                    # с ''' или """
                    s = tok.string
                    if s.startswith(('"""', "'''", 'r"""', "r'''")):
                        start_line = tok.start[0] - 1
                        end_line = tok.end[0] - 1
                        for i in range(start_line, end_line + 1):
                            docstr_lines.add(i)
    except (tokenize.TokenError, IndentationError):
        pass

    docstr = len(docstr_lines - {i for i, l in enumerate(lines)
                                 if not l.strip()})

    # комментарии внутри docstring не считаем
    comment -= sum(1 for i in docstr_lines
                   if i < len(lines) and lines[i].strip().startswith("#"))

    code = total - blank - comment - docstr
    return {
        "total": total,
        "blank": blank,
        "comment": comment,
        "docstr": docstr,
        "code": max(code, 0),
    }


def collect_files():
    files = []
    for p in ROOT.rglob("*.py"):
        if p.suffix != ".py":
            continue  # отсекаем .pyc/.pyo
        if is_excluded(p, ROOT):
            continue
        files.append(p)
    return sorted(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--by-file", action="store_true",
                    help="показать статистику по каждому файлу")
    ap.add_argument("--by-dir", action="store_true",
                    help="сгруппировать по верхнеуровневым папкам")
    args = ap.parse_args()

    files = collect_files()

    rows = []
    for p in files:
        r = analyze_file(p)
        if r is None:
            continue
        r["path"] = p.relative_to(ROOT)
        rows.append(r)

    if args.by_file:
        print(f"{'file':<55} {'total':>7} {'code':>7} "
              f"{'comment':>8} {'doc':>6} {'blank':>6}")
        print("-" * 95)
        for r in sorted(rows, key=lambda x: -x["code"]):
            print(f"{str(r['path']):<55} {r['total']:>7} "
                  f"{r['code']:>7} {r['comment']:>8} "
                  f"{r['docstr']:>6} {r['blank']:>6}")
        print("-" * 95)

    if args.by_dir:
        from collections import defaultdict
        agg = defaultdict(lambda: {"total": 0, "code": 0,
                                    "comment": 0, "docstr": 0,
                                    "blank": 0, "files": 0})
        for r in rows:
            key = r["path"].parts[0] if len(r["path"].parts) > 1 else "(root)"
            agg[key]["total"] += r["total"]
            agg[key]["code"] += r["code"]
            agg[key]["comment"] += r["comment"]
            agg[key]["docstr"] += r["docstr"]
            agg[key]["blank"] += r["blank"]
            agg[key]["files"] += 1
        print(f"{'dir':<25} {'files':>6} {'total':>8} {'code':>8} "
              f"{'comment':>8} {'doc':>7} {'blank':>7}")
        print("-" * 78)
        for k, v in sorted(agg.items(), key=lambda x: -x[1]["code"]):
            print(f"{k:<25} {v['files']:>6} {v['total']:>8} "
                  f"{v['code']:>8} {v['comment']:>8} "
                  f"{v['docstr']:>7} {v['blank']:>7}")
        print("-" * 78)

    # итог
    tot = sum(r["total"] for r in rows)
    code = sum(r["code"] for r in rows)
    comment = sum(r["comment"] for r in rows)
    docstr = sum(r["docstr"] for r in rows)
    blank = sum(r["blank"] for r in rows)

    print()
    print("=" * 60)
    print(f"  файлов .py:      {len(rows)}")
    print(f"  всего строк:     {tot}")
    print(f"  код:             {code}")
    print(f"  комментарии:     {comment}")
    print(f"  docstring:       {docstr}")
    print(f"  пустые:          {blank}")
    print("=" * 60)


if __name__ == "__main__":
    main()