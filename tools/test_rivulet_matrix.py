# tools/test_rivulet_matrix.py
"""
Матрица: rivulet (25 шаблонов) → все 39 языков = 975 пар.

Проверяет:
  1. translate(rivulet, X) возвращает непустую строку
  2. X.execute(результат) совпадает с ожидаемым выводом rivulet
  3. Где не совпадает — показывает что получилось

Использует persistent Executor из test_matrix для скорости.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "test_report"
REPORT.mkdir(exist_ok=True)


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def preview(s, n=50):
    if s is None:
        return "<None>"
    if not isinstance(s, str):
        return f"<{type(s).__name__}>"
    s = s.replace("\n", "\\n")
    if len(s) <= n:
        return repr(s)
    return repr(s[:n]) + f"...[{len(s)}]"


def main():
    _force_utf8()

    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()

    from core.extended_templates import replace_all
    replace_all(verbose=False)
    from core.universal_fallback import install
    install()

    from core.translate import translate
    from tools.test_matrix import Executor

    riv = registry.get("rivulet")
    all_langs = [l for l in registry.all() if l.name != "rivulet"]
    templates = list(riv.templates.items())

    n_tpl = len(templates)
    n_dst = len(all_langs)
    total = n_tpl * n_dst
    print(f"Rivulet: {n_tpl} шаблонов × {n_dst} языков = {total} пар\n")

    ex = Executor()
    results = []
    t0 = time.monotonic()

    try:
        for i, (tpl_name, riv_code) in enumerate(templates, 1):
            # 1) что rivulet выдаёт для своего шаблона
            try:
                expected = riv.execute(riv_code)
            except Exception as e:
                expected = f"<ERR {type(e).__name__}: {e}>"
            expected = expected.strip()

            ok_n, fail_n, empty_n, err_n = 0, 0, 0, 0
            detail = []

            for dst in all_langs:
                # 2) translate(rivulet → dst)
                try:
                    r = translate("rivulet", dst.name, riv_code, None)
                    if isinstance(r, tuple):
                        r = r[0]
                except Exception as e:
                    err_n += 1
                    detail.append((dst.name, "ERR_translate",
                                   f"{type(e).__name__}: {e}"))
                    continue

                if not isinstance(r, str) or len(r) == 0:
                    empty_n += 1
                    detail.append((dst.name, "EMPTY_TRANSLATE", ""))
                    continue

                # 3) dst.execute(r)
                try:
                    err, out = ex.run_full(dst.name, r, timeout=5.0)
                except Exception as e:
                    err_n += 1
                    detail.append((dst.name, "ERR_EXEC",
                                   f"{type(e).__name__}: {e}"))
                    continue

                if err:
                    err_n += 1
                    detail.append((dst.name, "EXEC_ERR", err[:80]))
                    continue

                got = out.strip() if isinstance(out, str) else ""
                if got == expected:
                    ok_n += 1
                else:
                    fail_n += 1
                    detail.append((dst.name, "MISMATCH",
                                   f"got={preview(got, 30)} "
                                   f"exp={preview(expected, 30)}"))

            dt = time.monotonic() - t0
            status = "✓" if fail_n == 0 and err_n == 0 else "✗"
            print(f"  [{i:>2}/{n_tpl}] {status} {tpl_name[:44]:<44} "
                  f"ok={ok_n:>2} fail={fail_n:>2} empty={empty_n:>2} "
                  f"err={err_n:>2}  ({dt:>5.1f}s)")

            for name, kind, msg in detail[:5]:
                print(f"           · {name:<12} {kind:<18} {msg}")

            results.append({
                "tpl": tpl_name,
                "expected": expected[:100],
                "ok": ok_n, "fail": fail_n,
                "empty": empty_n, "err": err_n,
                "detail": detail,
            })
    finally:
        ex.close()

    dt = time.monotonic() - t0

    # Сводка
    print(f"\n{'='*75}")
    total_ok = sum(r["ok"] for r in results)
    total_fail = sum(r["fail"] for r in results)
    total_empty = sum(r["empty"] for r in results)
    total_err = sum(r["err"] for r in results)

    print(f"ИТОГО за {dt:.1f}s")
    print(f"  ✓ OK:      {total_ok:>5} / {total}")
    print(f"  ✗ MISMATCH:{total_fail:>5}")
    print(f"  · EMPTY:   {total_empty:>5}")
    print(f"  ! ERR:     {total_err:>5}")

    # Топ проблемных dst
    from collections import Counter
    by_dst_ok = Counter()
    by_dst_bad = Counter()
    for r in results:
        for name, kind, _ in r["detail"]:
            if kind == "MISMATCH":
                by_dst_bad[name] += 1
            else:
                by_dst_bad[name] += 1

    if by_dst_bad:
        print(f"\nТоп-15 проблемных dst:")
        for dst, n in by_dst_bad.most_common(15):
            print(f"  {dst:<16} bad={n}")

    # Сохранить отчёт
    import json
    out_file = REPORT / "rivulet_matrix.json"
    out_file.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\nОтчёт: {out_file}")


if __name__ == "__main__":
    main()