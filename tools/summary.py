# tools/summary.py
"""
Сводный отчёт: читает test_report/*.json и печатает единую картину.

Запуск:
    python tools/summary.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "test_report"


def _force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _load(name: str) -> list | None:
    p = REPORT / name
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _section(title: str) -> None:
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def main() -> None:
    _force_utf8()

    # --- аудит ---
    audit = _load("audit.json")
    if audit:
        _section("Аудит языков")
        n = len(audit)
        print(f"Всего языков: {n}")
        no_exec = [r["name"] for r in audit
                   if "execute" not in r["methods"]]
        no_gc = [r["name"] for r in audit
                 if "generate_code" not in r["methods"]]
        no_meta = [r["name"] for r in audit
                   if r["meta_snippets"] == 0]
        no_fnlib = [r["name"] for r in audit
                    if r["function_library_snippets"] == 0]
        print(f"Без своего execute():       {len(no_exec)}")
        print(f"Без своего generate_code(): {len(no_gc)}")
        print(f"Без META_SNIPPETS:          {len(no_meta)}")
        print(f"Без function_library:       {len(no_fnlib)}")
        if no_meta:
            print(f"  META нет у: {', '.join(no_meta[:20])}")

    # --- matrix errors ---
    mx = _load("matrix_errors.json")
    if mx is not None:
        _section(f"Матрица: ошибок {len(mx)}")
        if mx:
            kinds = Counter(r["kind"] for r in mx)
            for k, v in kinds.most_common():
                print(f"  {k:<12} {v:>5}")
            by_dst = Counter(r.get("dst") for r in mx)
            print("\nПо dst:")
            for k, v in by_dst.most_common(10):
                print(f"  {str(k):<20} {v:>5}")
        else:
            print("Ошибок нет — матрица чистая.")

    # --- functions errors ---
    fx = _load("functions_errors.json")
    if fx is not None:
        _section(f"Функции без AST: ошибок {len(fx)}")
        if fx:
            kinds = Counter(r["kind"] for r in fx)
            for k, v in kinds.most_common():
                print(f"  {k:<12} {v:>5}")
            by_fn = Counter(r["fn"] for r in fx)
            print("\nТоп проблемных функций:")
            for k, v in by_fn.most_common(15):
                print(f"  {k:<12} {v:>5}")
        else:
            print("Ошибок нет — все функции проходят.")


if __name__ == "__main__":
    main()