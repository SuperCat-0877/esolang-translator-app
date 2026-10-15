# tools/rename_to_blockpiet.py
"""
Переименование pixelcode → blockpiet.

Что делает:
  1. langs/pixelcode.py → langs/blockpiet.py
     (старый blockpiet.py 2×2 → langs/blockpiet_legacy.py)
  2. core/pixel_tiles.py → core/blockpiet_tiles.py
  3. core/pixel_tiles_lib.py → core/blockpiet_lib.py
  4. Обновляет внутренние импорты в новых файлах
  5. Обновляет ui/mosaic_tab.py
  6. Обновляет упоминания в других файлах

Запуск:
    python tools/rename_to_blockpiet.py --check
    python tools/rename_to_blockpiet.py
    python tools/rename_to_blockpiet.py --revert
"""
from __future__ import annotations
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


RENAMES = [
    ("langs/pixelcode.py",          "langs/blockpiet.py"),
    ("langs/blockpiet.py",          "langs/blockpiet_legacy.py"),  # старый 2×2
    ("core/pixel_tiles.py",         "core/blockpiet_tiles.py"),
    ("core/pixel_tiles_lib.py",     "core/blockpiet_lib.py"),
]


# Замены импортов и имён по всему проекту
REPLACEMENTS = [
    # imports
    ("from core.blockpiet_tiles import", "from core.blockpiet_tiles import"),
    ("from core.blockpiet_lib import", "from core.blockpiet_lib import"),
    ("import core.blockpiet_tiles", "import core.blockpiet_tiles"),
    ("from langs.blockpiet import", "from langs.blockpiet import"),
    ("import langs.blockpiet", "import langs.blockpiet"),
    # имена классов
    ("BlockPiet21Lang", "BlockPiet21Lang"),
    ("BlockPietTileLibrary", "BlockPietBlockPietTileLibrary"),  # чтобы не путать
    # имя языка в реестре
    ('name = "blockpiet21"', 'name = "blockpiet21"'),  # новая система = blockpiet21
    ('title = "BlockPiet 2×1"', 'title = "BlockPiet 2×1"'),
]


def _iter_py_files():
    for p in ROOT.rglob("*.py"):
        if "_archive" in p.parts or "__pycache__" in p.parts:
            continue
        if "tools/rename_to_blockpiet" in str(p):
            continue
        yield p


def _replace_in_file(p: Path, replacements, dry=False) -> int:
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return 0
    original = text
    n = 0
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new)
            n += 1
    if text != original:
        if dry:
            print(f"    [dry] {p.relative_to(ROOT)}: {n} замен")
        else:
            p.write_text(text, encoding="utf-8")
            print(f"    [+] {p.relative_to(ROOT)}: {n} замен")
        return 1
    return 0


def do_rename(dry=False, check=False) -> int:
    print("Шаг 1: переименование файлов")

    # порядок важен: сначала pixelcode → blockpiet,
    # потом blockpiet → blockpiet_legacy
    # (иначе перезапишем новый старым)
    src1 = ROOT / "langs" / "pixelcode.py"
    dst1 = ROOT / "langs" / "blockpiet.py"
    src2 = ROOT / "langs" / "blockpiet.py"  # уже после первой операции
    dst2 = ROOT / "langs" / "blockpiet_legacy.py"

    # Проверки
    if src1.is_file() and not dst1.is_file():
        if check:
            print(f"  ✓ {src1.name} → {dst1.name}")
        elif dry:
            print(f"  [dry] {src1.name} → {dst1.name}")
        else:
            # сначала переместим старый blockpiet (если он есть)
            # во временное место
            tmp = None
            if dst1.is_file():
                tmp = ROOT / "langs" / "_old_blockpiet_tmp.py"
                shutil.move(str(dst1), str(tmp))
            shutil.move(str(src1), str(dst1))
            print(f"  [+] {src1.name} → {dst1.name}")
            if tmp and tmp.is_file():
                shutil.move(str(tmp), str(dst2))
                print(f"  [+] старый blockpiet → {dst2.name}")

    src3 = ROOT / "core" / "pixel_tiles.py"
    dst3 = ROOT / "core" / "blockpiet_tiles.py"
    if src3.is_file() and not dst3.is_file():
        if check:
            print(f"  ✓ {src3.name} → {dst3.name}")
        elif dry:
            print(f"  [dry] {src3.name} → {dst3.name}")
        else:
            shutil.move(str(src3), str(dst3))
            print(f"  [+] {src3.name} → {dst3.name}")

    src4 = ROOT / "core" / "pixel_tiles_lib.py"
    dst4 = ROOT / "core" / "blockpiet_lib.py"
    if src4.is_file() and not dst4.is_file():
        if check:
            print(f"  ✓ {src4.name} → {dst4.name}")
        elif dry:
            print(f"  [dry] {src4.name} → {dst4.name}")
        else:
            shutil.move(str(src4), str(dst4))
            print(f"  [+] {src4.name} → {dst4.name}")

    if check or dry:
        return 0

    print()
    print("Шаг 2: замена импортов и имён во всех .py")
    n = 0
    for p in _iter_py_files():
        n += _replace_in_file(p, REPLACEMENTS, dry=dry)
    print(f"  изменено файлов: {n}")
    return n


def revert():
    """Откат — вернуть файлы как было."""
    pairs = [
        ("langs/blockpiet.py", "langs/pixelcode.py"),
        ("langs/blockpiet_legacy.py", "langs/blockpiet.py"),
        ("core/blockpiet_tiles.py", "core/pixel_tiles.py"),
        ("core/blockpiet_lib.py", "core/pixel_tiles_lib.py"),
    ]
    # откат имён
    reverse_repl = [(new, old) for old, new in REPLACEMENTS]
    for p in _iter_py_files():
        _replace_in_file(p, reverse_repl)

    for src, dst in pairs:
        s = ROOT / src
        d = ROOT / dst
        if s.is_file():
            if d.is_file():
                # сохраним старый под суффиксом
                d2 = d.with_suffix(".py.old")
                shutil.move(str(d), str(d2))
            shutil.move(str(s), str(d))
            print(f"  [<] {src} → {dst}")


def main():
    _force_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    if args.revert:
        print("Откат:")
        revert()
        return

    if args.check:
        do_rename(check=True)
        return

    do_rename(dry=args.dry)


if __name__ == "__main__":
    main()