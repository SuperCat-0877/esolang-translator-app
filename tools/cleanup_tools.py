# tools/cleanup_tools.py
"""
Уборка временных скриптов и бэкапов, накопившихся в проекте.

Что делает:
  - Одноразовые патч-скрипты и диагностику переносит в tools/_archive/.
  - *.bak*, *.bak_* файлы переносит в tools/_archive/_bak/.
  - __pycache__ удаляет (безопасно, кэш).
  - Core-тестеры (test_matrix, test_functions, summary, audit) НЕ трогает.

По умолчанию dry-run. Ничего не удаляет без --apply.

Запуск:
    python tools/cleanup_tools.py             # показать, что будет
    python tools/cleanup_tools.py --apply     # перенести
    python tools/cleanup_tools.py --restore   # вернуть всё из _archive/
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
ARCHIVE = TOOLS / "_archive"
ARCHIVE_BAK = ARCHIVE / "_bak"


def _force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ----------------------------------------------------------------------
#  СКРИПТЫ, КОТОРЫЕ НЕ НУЖНЫ ПОСЛЕ ПРОГОНА
# ----------------------------------------------------------------------
# Патч-скрипты (применились один раз, больше не нужны)
PATCH_SCRIPTS = [
    "apply_extra_templates.py",
    "apply_bf_fixes.py",
    "apply_empty_fix.py",
    "fix_ok_kinds_import.py",
    "fix_rivulet_spam.py",
    "fix_universal_minimal.py",
]

# Диагностические (одноразовые)
DIAG_SCRIPTS = [
    "diagnose_errors.py",
    "smoke_translate.py",
    "show_errors.py",
    "show_functions_errors.py",
    "bf_probe.py",
    "probe_go_execute.py",
    "probe_fallback.py",
    "diagnose_generate.py",
]

# Генераторы (одноразовые)
GEN_SCRIPTS = [
    "gen_extra_templates.py",
    "auto_fix_matrix.py",
]

# Core — НИКОГДА не трогаем (для напоминания)
KEEP_SCRIPTS = {
    "test_matrix.py",
    "test_functions.py",
    "_exec_daemon.py",
    "summary.py",
    "audit_languages.py",
    "cleanup_tools.py",   # сам себя
}


# ----------------------------------------------------------------------
def _collect_movable() -> list[Path]:
    """Скрипты, которые переносим в _archive."""
    names = PATCH_SCRIPTS + DIAG_SCRIPTS + GEN_SCRIPTS
    out = []
    for n in names:
        p = TOOLS / n
        if p.is_file() and n not in KEEP_SCRIPTS:
            out.append(p)
    return out


def _collect_backups() -> list[Path]:
    """*.bak* в tools/, langs/, core/."""
    out = []
    for sub in ("tools", "langs", "core"):
        d = ROOT / sub
        if not d.is_dir():
            continue
        for p in d.rglob("*.bak*"):
            if "_archive" in p.parts:
                continue
            if p.is_file():
                out.append(p)
    return out


def _collect_pycache() -> list[Path]:
    out = []
    for p in ROOT.rglob("__pycache__"):
        if "_archive" in p.parts:
            continue
        if p.is_dir():
            out.append(p)
    return out


# ----------------------------------------------------------------------
def cmd_show(movable, backups, pycaches) -> None:
    print(f"Корень: {ROOT}")
    print()
    if movable:
        print(f"Скриптов к переносу в tools/_archive/ ({len(movable)}):")
        for p in movable:
            print(f"  {p.relative_to(ROOT)}")
    else:
        print("Скриптов к переносу — нет.")
    print()

    if backups:
        print(f"Бэкапов к переносу в tools/_archive/_bak/ ({len(backups)}):")
        for p in backups[:30]:
            print(f"  {p.relative_to(ROOT)}")
        if len(backups) > 30:
            print(f"  ... и ещё {len(backups) - 30}")
    else:
        print("Бэкапов — нет.")
    print()

    if pycaches:
        print(f"__pycache__ к удалению ({len(pycaches)}):")
        for p in pycaches[:10]:
            print(f"  {p.relative_to(ROOT)}")
        if len(pycaches) > 10:
            print(f"  ... и ещё {len(pycaches) - 10}")
    else:
        print("__pycache__ — нет.")


def cmd_apply(movable, backups, pycaches) -> None:
    ARCHIVE.mkdir(exist_ok=True)
    moved = 0
    for p in movable:
        dst = ARCHIVE / p.name
        if dst.exists():
            dst.unlink()
        shutil.move(str(p), str(dst))
        moved += 1
    print(f"Скриптов в _archive/: {moved}")

    if backups:
        ARCHIVE_BAK.mkdir(parents=True, exist_ok=True)
        bmoved = 0
        for p in backups:
            # чтобы сохранить подпапку: tools_x.bak → tools/x.bak
            rel = p.relative_to(ROOT)
            flat = "_".join(rel.parts)
            dst = ARCHIVE_BAK / flat
            if dst.exists():
                dst.unlink()
            shutil.move(str(p), str(dst))
            bmoved += 1
        print(f"Бэкапов в _archive/_bak/: {bmoved}")

    if pycaches:
        for p in pycaches:
            try:
                shutil.rmtree(p)
            except Exception as e:
                print(f"  [!] {p}: {e}")
        print(f"__pycache__ удалено: {len(pycaches)}")


def cmd_restore() -> None:
    if not ARCHIVE.is_dir():
        print("Нет tools/_archive/ — восстанавливать нечего.")
        return
    n = 0
    for p in ARCHIVE.iterdir():
        if p.is_dir():
            continue
        dst = TOOLS / p.name
        if dst.exists():
            print(f"  [=] {p.name}: уже есть в tools/, пропуск")
            continue
        shutil.move(str(p), str(dst))
        n += 1
    print(f"Восстановлено скриптов: {n}")

    if ARCHIVE_BAK.is_dir():
        n = 0
        for p in ARCHIVE_BAK.iterdir():
            # tools_test_matrix.py.bak_empty → tools/test_matrix.py.bak_empty
            name = p.name
            parts = name.split("_", 1)
            if len(parts) != 2:
                continue
            sub, rest = parts
            target_dir = ROOT / sub
            if not target_dir.is_dir():
                continue
            dst = target_dir / rest
            if dst.exists():
                continue
            shutil.move(str(p), str(dst))
            n += 1
        print(f"Восстановлено бэкапов: {n}")


# ----------------------------------------------------------------------
def main() -> None:
    _force_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="перенести файлы (без флага — только показать)")
    ap.add_argument("--restore", action="store_true",
                    help="вернуть всё из tools/_archive/")
    args = ap.parse_args()

    if args.restore:
        cmd_restore()
        return

    movable = _collect_movable()
    backups = _collect_backups()
    pycaches = _collect_pycache()

    cmd_show(movable, backups, pycaches)
    print()

    if args.apply:
        cmd_apply(movable, backups, pycaches)
        print()
        print("Готово.")
        print("Вернуть обратно: python tools/cleanup_tools.py --restore")
    else:
        print("Это dry-run. Запусти с --apply, чтобы применить.")


if __name__ == "__main__":
    main()