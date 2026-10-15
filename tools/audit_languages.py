# tools/audit_languages.py
"""
Инвентаризация: что умеет каждый язык и что реально доступно.

Собирает по каждому языку:
  - имя, класс, модуль
  - какие методы переопределены (translate/generate_code/execute)
  - сколько шаблонов, разбивка по уровням L1..L5
  - есть ли реальные META_SNIPPETS
  - есть ли сниппеты в function_library.SNIPPETS
  - источник шаблона (generate_code vs meta vs fallback)

Запуск:
    python tools/audit_languages.py
    python tools/audit_languages.py --lang python
    python tools/audit_languages.py --json test_report/audit.json
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "test_report"
REPORT.mkdir(exist_ok=True)


def _force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Методы, которые интересуют
WANTED_METHODS = ("translate", "generate_code", "execute", "run", "eval")


def _own_methods(cls) -> dict[str, str]:
    """Какие методы определены именно в этом классе (не унаследованы)."""
    out: dict[str, str] = {}
    for name in WANTED_METHODS:
        fn = getattr(cls, name, None)
        if fn is None:
            continue
        qual = getattr(fn, "__qualname__", "")
        # own — если qualname начинается с имени класса
        if qual.startswith(cls.__name__ + "."):
            out[name] = "own"
        else:
            out[name] = "inherited"
    return out


def _template_source(lang, key: str) -> str:
    """Откуда шаблон: meta / generate_code / unknown."""
    try:
        from core.extended_templates import META_SNIPPETS
        if key in META_SNIPPETS.get(lang.name, {}):
            return "meta"
    except Exception:
        pass
    return "generated"


def audit_one(lang) -> dict:
    cls = type(lang)

    # уровни
    lv = Counter()
    for name in lang.templates:
        for L in ("L1", "L2", "L3", "L4", "L5"):
            if f"{L}-" in name:
                lv[L] += 1
                break
        else:
            lv["other"] += 1

    # META_SNIPPETS
    try:
        from core.extended_templates import META_SNIPPETS
        meta = META_SNIPPETS.get(lang.name, {})
    except Exception:
        meta = {}

    # function_library
    try:
        from core.function_library import SNIPPETS
        flibs = SNIPPETS.get(lang.name, {})
    except Exception:
        flibs = {}

    # методы
    methods = _own_methods(cls)

    # сколько шаблонов пришло из meta vs generated
    src_kinds = Counter()
    for k in lang.templates:
        src_kinds[_template_source(lang, k)] += 1

    return {
        "name": lang.name,
        "class": cls.__name__,
        "module": cls.__module__,
        "methods": methods,
        "templates_total": len(lang.templates),
        "templates_by_level": dict(lv),
        "templates_source": dict(src_kinds),
        "meta_snippets": len(meta),
        "function_library_snippets": len(flibs),
    }


def main() -> None:
    _force_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default=None, help="только один язык")
    ap.add_argument("--json", default=None, help="куда сохранить JSON")
    args = ap.parse_args()

    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()

    try:
        from core.extended_templates import replace_all
        replace_all(verbose=False)
    except Exception as e:
        print(f"# replace_all error: {e}", file=sys.stderr)

    langs = list(registry.all())
    if args.lang:
        langs = [l for l in langs if l.name == args.lang]

    rows = [audit_one(l) for l in langs]

    # --- печать ---
    print(f"\n{'='*100}")
    print(f"{'lang':<16} {'tpls':>5} {'L1':>3} {'L2':>3} "
          f"{'L3':>3} {'L4':>3} {'L5':>3}  {'meta':>4} {'fnlib':>5}  methods")
    print(f"{'='*100}")
    for r in rows:
        lv = r["templates_by_level"]
        methods = ",".join(f"{k}" for k, v in r["methods"].items()
                           if v == "own") or "-"
        print(f"{r['name']:<16} "
              f"{r['templates_total']:>5} "
              f"{lv.get('L1',0):>3} {lv.get('L2',0):>3} "
              f"{lv.get('L3',0):>3} {lv.get('L4',0):>3} "
              f"{lv.get('L5',0):>3}  "
              f"{r['meta_snippets']:>4} "
              f"{r['function_library_snippets']:>5}  "
              f"{methods}")

    # --- сводка ---
    print(f"\n{'='*100}")
    all_methods = Counter()
    for r in rows:
        for k, v in r["methods"].items():
            if v == "own":
                all_methods[k] += 1
    print("Методов 'own' по всем языкам:")
    for k, v in all_methods.most_common():
        print(f"  {k:<16} {v:>3} / {len(rows)} языков")

    no_exec = [r["name"] for r in rows if "execute" not in r["methods"]]
    if no_exec:
        print(f"\nЯзыки без собственного execute() ({len(no_exec)}): "
              f"{', '.join(no_exec)}")

    no_gc = [r["name"] for r in rows if "generate_code" not in r["methods"]]
    if no_gc:
        print(f"\nЯзыки без собственного generate_code() ({len(no_gc)}): "
              f"{', '.join(no_gc)}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"\nJSON: {args.json}")


if __name__ == "__main__":
    main()