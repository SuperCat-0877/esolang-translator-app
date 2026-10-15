# tools/probe_canvas_formats.py
"""
Сравнивает:
  - что ожидает Piet Canvas (по коду ui/piet_pack.py)
  - что ожидает Rivulet Canvas
  - что реально возвращает generate_code
  - что реально лежит в шаблонах языков

Показывает, где формат расходится.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def show_format(name: str, data: str, n: int = 4) -> None:
    print(f"  длина: {len(data)} байт, строк: {data.count(chr(10)) + 1}")
    print(f"  первые {n} строк (или весь текст если коротко):")
    for line in data.splitlines()[:n]:
        print(f"    |{line[:80]}")
    if data.count("\n") > n:
        print(f"    ... (+{data.count(chr(10)) - n} строк)")
    # есть ли base64-признаки?
    b64_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "abcdefghijklmnopqrstuvwxyz0123456789+/=")
    sample = data[:500].replace("\n", "")
    b64_ratio = sum(1 for c in sample if c in b64_chars) / max(len(sample), 1)
    print(f"  похоже на base64: {b64_ratio > 0.9}")


def main():
    _force_utf8()
    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()

    from core.extended_templates import replace_all
    replace_all(verbose=False)

    # --- 1. Что ждёт Piet Canvas ---
    print("=" * 72)
    print("  1. Что ожидает ui/piet_pack.py")
    print("=" * 72)
    p = ROOT / "ui" / "piet_pack.py"
    if not p.is_file():
        print("  [!] файла нет")
    else:
        text = p.read_text(encoding="utf-8")
        # ищем методы from_text / to_text
        for method in ("def from_text", "def to_text", "def _parse",
                       "def _serialize"):
            idx = text.find(method)
            if idx < 0:
                continue
            end = text.find("\ndef ", idx + 1)
            if end < 0:
                end = idx + 800
            print(f"\n  --- {method.strip()} ---")
            for line in text[idx:end].splitlines()[:20]:
                print(f"    {line}")

    # --- 2. Что ждёт Rivulet Canvas ---
    print()
    print("=" * 72)
    print("  2. Что ожидает ui/rivulet_canvas.py")
    print("=" * 72)
    p = ROOT / "ui" / "rivulet_canvas.py"
    if not p.is_file():
        print("  [!] файла нет")
    else:
        text = p.read_text(encoding="utf-8")
        for method in ("def from_text", "def to_text", "def _parse",
                       "def _serialize"):
            idx = text.find(method)
            if idx < 0:
                continue
            end = text.find("\ndef ", idx + 1)
            if end < 0:
                end = idx + 800
            print(f"\n  --- {method.strip()} ---")
            for line in text[idx:end].splitlines()[:20]:
                print(f"    {line}")

    # --- 3. Что реально возвращает generate_code ---
    print()
    print("=" * 72)
    print("  3. Что возвращает generate_code")
    print("=" * 72)

    for name in ("piet", "rivulet"):
        lang = registry.get(name)
        if not lang:
            continue
        code = lang.generate_code("Hi")
        print(f"\n  ### {name}.generate_code('Hi')")
        show_format(name, code)

    # --- 4. Что лежит в шаблонах ---
    print()
    print("=" * 72)
    print("  4. Что лежит в шаблонах языков")
    print("=" * 72)

    for name in ("piet", "rivulet"):
        lang = registry.get(name)
        if not lang:
            continue
        print(f"\n  ### {name}: первый шаблон")
        first_name = next(iter(lang.templates))
        code = lang.templates[first_name]
        print(f"  имя шаблона: {first_name}")
        show_format(name, code)


if __name__ == "__main__":
    main()