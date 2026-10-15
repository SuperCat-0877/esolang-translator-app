# tools/test_functions.py
"""
Тест библиотеки атомарных функций БЕЗ AST.
Гоняет реальные сниппеты через translate() и (опц.) execute().

Запуск:
    python tools/test_functions.py
    python tools/test_functions.py --exec
    python tools/test_functions.py --src python --exec
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# --- PATCH: module-level OK_KINDS ---
from tools.test_matrix import (        # noqa: E402
    Executor,
    LIMITED_DST,
    OK_KINDS,
)
# --- /PATCH ---

REPORT = ROOT / "test_report"
REPORT.mkdir(exist_ok=True)


def _force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> None:
    _force_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--exec", action="store_true",
                    help="дополнительно запускать execute()")
    ap.add_argument("--src", default=None, help="только один источник")
    args = ap.parse_args()

    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()

    from core.extended_templates import replace_all
    replace_all(verbose=False)

    from core.universal_fallback import install
    install()

    from core.function_library import SNIPPETS, get_entry
    from core.translate import translate

    # Executor из test_matrix — переиспользуем
    from tools.test_matrix import Executor

    langs = list(registry.all())
    if args.src:
        langs = [l for l in langs if l.name == args.src]

    executor = Executor() if args.exec else None
    results: list[dict] = []
    t_start = time.monotonic()

    try:
        for src in langs:
            if src.name not in SNIPPETS:
                continue
            for dst in registry.all():
                if dst.name == src.name:
                    continue
                for fid in SNIPPETS[src.name]:
                    entry = get_entry(src.name, fid)
                    if not entry:
                        continue
                    code = entry["code"]
                    try:
                        r = translate(src.name, dst.name, code, None)
                        if isinstance(r, tuple):
                            r = r[0]
                        if r is None or not isinstance(r, str):
                            kind, msg = "EMPTY", repr(r)[:120]
                        elif r == "":
                            if dst.name in LIMITED_DST:
                                kind, msg = "SKIP_LIMITED", \
                                    f"{dst.name}: не умеет рендерить вывод"
                            else:
                                kind, msg = "EMPTY", "translate -> ''"
                        else:
                            kind, msg = "OK", ""
                            if executor is not None:
                                err = executor.run(dst.name, r)
                                if err:
                                    kind, msg = "EXEC_ERR", err
                    except BaseException as e:
                        kind, msg = "ERR", f"{type(e).__name__}: {e}"
                    results.append({
                        "src": src.name, "dst": dst.name, "fn": fid,
                        "kind": kind, "msg": msg[:300],
                    })
    finally:
        if executor is not None:
            executor.close()

    _report(results, time.monotonic() - t_start)


def _report(rows: list[dict], elapsed: float) -> None:
    kinds = Counter(r["kind"] for r in rows)
    print(f"\n{'='*60}")
    print(f"Всего: {len(rows)}   за {elapsed:.1f}s")
    print(f"{'='*60}")
    for k, v in kinds.most_common():
        print(f"  {k:<12} {v:>6}")

    by_fn = Counter(r["fn"] for r in rows if r["kind"] not in OK_KINDS)
    if by_fn:
        print("\nТоп-20 проблемных функций:")
        for fn, n in by_fn.most_common(20):
            print(f"  {fn:<12} {n:>6}")

    by_pair = Counter((r["src"], r["dst"])
                      for r in rows if r["kind"] not in OK_KINDS)
    if by_pair:
        print("\nТоп-20 проблемных пар:")
        for (s, d), n in by_pair.most_common(20):
            print(f"  {s:<14} -> {d:<14} bad={n}")

    (REPORT / "functions.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8")
    errs = [r for r in rows if r["kind"] not in OK_KINDS]
    (REPORT / "functions_errors.json").write_text(
        json.dumps(errs, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\nОтчёт: {REPORT/'functions.json'}")
    print(f"Ошибки: {REPORT/'functions_errors.json'} ({len(errs)})")


if __name__ == "__main__":
    main()