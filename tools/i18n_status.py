# tools/i18n_status.py
"""Показывает прогресс перевода по языкам.

Запуск:
    python tools/i18n_status.py
    python tools/i18n_status.py --missing en    # список непереведённых
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALES = ROOT / "locales"


def load(code: str) -> dict:
    p = LOCALES / f"{code}.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--missing", metavar="LANG",
                    help="Показать ключи, где не переведено (en, de, ...)")
    args = ap.parse_args()

    ru = load("ru")
    if not ru:
        print("✘ locales/ru.json не найден")
        return 1

    total = len(ru)

    if args.missing:
        lang = args.missing
        data = load(lang)
        print(f"Непереведённые строки в {lang}.json ({total} всего):\n")
        missing = 0
        for k, v in ru.items():
            cur = data.get(k, "")
            if not cur or cur == v:
                missing += 1
                print(f'  "{k}": "",  // {v}')
        print(f"\nОсталось перевести: {missing} из {total}")
        return 0

    # общий отчёт
    print(f"{'Язык':<8} {'Готово':>8} {'Всего':>8} {'%':>8}")
    print("─" * 36)
    for p in sorted(LOCALES.glob("*.json")):
        code = p.stem
        data = json.loads(p.read_text(encoding="utf-8"))
        if code == "ru":
            print(f"{code:<8} {total:>8} {total:>8} {100.0:>7.1f}%")
            continue
        done = sum(1 for k, v in ru.items()
                   if data.get(k) and data.get(k) != v)
        pct = done * 100 / total if total else 0
        print(f"{code:<8} {done:>8} {total:>8} {pct:>7.1f}%")

    print("\nПодсказка: python tools/i18n_status.py --missing en")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
