# tools/diagnose_strings.py
"""Точные причины для 5 приёмников с проблемами строк."""
from __future__ import annotations
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_str_unsafe_regexes(path, marker_patterns):
    """Ищет в файле строки с regex, которые ломают строки."""
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    print(f"\n--- {path.relative_to(ROOT)} ---")
    for i, line in enumerate(text.splitlines(), 1):
        for pat in marker_patterns:
            if pat in line:
                print(f"  {i:>4}: {line.strip()[:100]}")


def main():
    _force_utf8()
    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()

    # ==========================================================
    print("=" * 72)
    print("  1. JS: что делает _js_to_python с // внутри строки")
    print("=" * 72)
    try:
        mod = __import__("langs.javascript_lang", fromlist=["x"])
        # найти функции *to_python или *to_js
        fn = None
        for name in dir(mod):
            if "to_python" in name.lower():
                fn = getattr(mod, name)
                break
        if fn is None:
            print("  [!] не найдена to_python функция")
            print("      функции:", [n for n in dir(mod)
                                    if callable(getattr(mod, n, None))
                                    and not n.startswith("_")])
        else:
            print(f"  функция: {fn.__name__}")
            tests = [
                "console.log('Hi');",
                "console.log('17 // 5 = 3');",
                "console.log('// comm');",
                "console.log('a; b');",
            ]
            for t in tests:
                try:
                    r = fn(t)
                    print(f"  {t!r}")
                    print(f"    → {r!r}")
                except Exception as e:
                    print(f"  {t!r} ERR {type(e).__name__}: {e}")
    except Exception as e:
        print(f"  ERR import: {e}")

    # ==========================================================
    print()
    print("=" * 72)
    print("  2. CPP: _rewrite_cout с << внутри строки")
    print("=" * 72)
    try:
        from langs.cpp_lang import _rewrite_cout
        tests = [
            'cout << "Hello";',
            'std::cout << "Hello" << " " << "World!" << endl;',
            'std::cout << "a << b";',
            'std::cout << "a; b";',
        ]
        for t in tests:
            try:
                r = _rewrite_cout(t)
                print(f"  {t!r}")
                print(f"    → {r!r}")
            except Exception as e:
                print(f"  {t!r} ERR {type(e).__name__}: {e}")
    except Exception as e:
        print(f"  ERR import: {e}")

    # ==========================================================
    print()
    print("=" * 72)
    print("  3. LOLCODE / PHP / ELIXIR")
    print("=" * 72)
    for lang_name, mod_name, pat in (
        ("lolcode", "langs.lolcode_lang", "lolcode"),
        ("php",     "langs.php_lang",     "php"),
        ("elixir",  "langs.elixir_lang",  "elixir"),
    ):
        print(f"\n--- {lang_name} ---")
        try:
            mod = __import__(mod_name, fromlist=["x"])
            # ищем *to_python
            fn = None
            for name in dir(mod):
                if "to_python" in name.lower() and callable(getattr(mod, name)):
                    fn = getattr(mod, name)
                    break
            if fn is None:
                print(f"  функции: "
                      f"{[n for n in dir(mod) if 'python' in n.lower()]}")
                continue
            print(f"  функция: {fn.__name__}")

            # пробуем найти какой-то шаблон для источника
            from core.registry import registry
            lang = registry.get(lang_name)
            if lang and lang.templates:
                first = next(iter(lang.templates))
                code = lang.templates[first]
                print(f"  пример {first}:")
                print(f"    in:  {code[:80]!r}")
                try:
                    r = fn(code)
                    print(f"    out: {r[:120]!r}")
                except Exception as e:
                    print(f"    ERR {type(e).__name__}: {e}")
        except Exception as e:
            print(f"  ERR import: {e}")

    # ==========================================================
    print()
    print("=" * 72)
    print("  4. Где в файлах регексы, которые могут резать внутри строк")
    print("=" * 72)
    unsafe_patterns = [
        r"//[^\n]",           # // комментарий
        r"# [^\n]",           # # комментарий
        r";",                 # ;
        r"split",             # split
    ]
    candidates = [
        ("js", "langs/javascript_lang.py"),
        ("ts", "langs/typescript_lang.py"),
        ("php", "langs/php_lang.py"),
        ("elixir", "langs/elixir_lang.py"),
        ("lolcode", "langs/lolcode_lang.py"),
    ]
    for name, rel in candidates:
        p = ROOT / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        found = []
        for i, line in enumerate(text.splitlines(), 1):
            if "re.sub" in line and any(pat in line for pat in unsafe_patterns):
                found.append((i, line.strip()))
        if found:
            print(f"\n--- {name} ---")
            for i, line in found[:8]:
                print(f"  {i:>4}: {line[:110]}")


if __name__ == "__main__":
    main()