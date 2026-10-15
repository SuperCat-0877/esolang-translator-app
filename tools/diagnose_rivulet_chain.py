# tools/diagnose_rivulet_chain.py
"""
Разбирает цепочку X → rivulet по шагам: что попадает в generate_code,
что он выдаёт, что исполняется. Показывает, где теряется смысл.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def section(t):
    print(f"\n{'='*75}\n  {t}\n{'='*75}")


def preview(s: str, n: int = 120) -> str:
    if s is None:
        return "<None>"
    if not isinstance(s, str):
        return f"<{type(s).__name__}>"
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
    from core.universal_fallback import install, direct_pairs
    install()

    from core.translate import TRANSPILERS

    # === 1. Какие транспайлеры зарегистрированы ===
    section("1. Транспайлеры с rivulet")
    for key in sorted(TRANSPILERS):
        if "rivulet" in key:
            fn = TRANSPILERS[key]
            name = getattr(fn, "__name__", "?")
            print(f"  {key} → {name}")

    print("\n  _direct_pairs с rivulet:")
    for p in sorted(direct_pairs()):
        if "rivulet" in p:
            print(f"    {p}")

    # === 2. Разбор цепочки для двух кейсов ===
    riv = registry.get("rivulet")

    cases = [
        ("javascript", 'console.log("Hello, World!");'),
        ("cpp", '''#include <iostream>
using namespace std;
int square(int x) { return x * x; }
int main() { cout << square(7) << endl; return 0; }'''),
        ("python", 'print("Hi")'),
    ]

    for src_name, src_code in cases:
        section(f"2. Цепочка {src_name} → rivulet")
        src = registry.get(src_name)
        print(f"  {src_name}.execute():")
        try:
            out = src.execute(src_code)
            print(f"    → {preview(out)}")
        except Exception as e:
            print(f"    → ERR {type(e).__name__}: {e}")
            out = ""

        # Что делает chain: X → python
        print(f"\n  {src_name} → python:")
        if (src_name, "python") in TRANSPILERS:
            try:
                py = TRANSPILERS[(src_name, "python")](src_code)
                print(f"    → {preview(py)}")
            except Exception as e:
                print(f"    → ERR {type(e).__name__}: {e}")
                py = ""
        else:
            print(f"    нет прямого транспайлера")
            py = ""

        # python → rivulet
        print(f"\n  python → rivulet (через generate_code):")
        text_for_riv = py if py else out
        print(f"    text для rivulet: {preview(text_for_riv)}")
        try:
            riv_code = riv.generate_code(text_for_riv)
            print(f"    rivulet-код: {preview(riv_code)}")
            print(f"    строк в диаграмме: {riv_code.count(chr(10)) + 1}")
        except Exception as e:
            print(f"    ERR {type(e).__name__}: {e}")
            continue

        # что исполняет rivulet
        print(f"\n  rivulet.execute(riv_code):")
        try:
            final = riv.execute(riv_code)
            print(f"    → {preview(final)}")
        except Exception as e:
            print(f"    ERR {type(e).__name__}: {e}")

    # === 3. Что вызывается в translate(X, rivulet) ===
    section("3. translate(X, rivulet) — что реально происходит")
    from core.translate import translate

    for src_name, src_code in cases:
        print(f"\n  --- {src_name} → rivulet ---")
        # Проверяем, есть ли universal_X__rivulet
        key = (src_name, "rivulet")
        fn = TRANSPILERS.get(key)
        if fn:
            print(f"    TRANSPILERS[{key}] = {fn.__name__}")
            try:
                r = fn(src_code)
                print(f"    результат: {preview(r)}")
            except Exception as e:
                print(f"    ERR {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()