# tools/add_is2_buttons.py
"""
Добавляет в Piet Canvas и Rivulet Canvas кнопку «Из ИС 2»
(результат перевода в правой панели), рядом с существующей «Из ИС 1».

Проблема: результат перевода лежит в self.app.output (ИС 2),
а кнопка «Из ИС 1» читает self.app.editor (ИС 1 — исходник).

Запуск:
    python tools/add_is2_buttons.py --check
    python tools/add_is2_buttons.py
    python tools/add_is2_buttons.py --revert
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PC = ROOT / "ui" / "piet_pack.py"
RC = ROOT / "ui" / "rivulet_canvas.py"

MARKER = "# === IS2-BUTTON ==="


# ==================================================================
#  PIET
# ==================================================================
PIET_BTN_OLD = '''        ttk.Button(right, text="⬅  Из ИС 1 (парсить текст)",
                   command=self.from_editor,
                   style="Smooth.TButton").pack(fill="x", pady=2)'''

PIET_BTN_NEW = '''        ttk.Button(right, text="⬅  Из ИС 1 (исходник)",
                   command=self.from_editor,
                   style="Smooth.TButton").pack(fill="x", pady=2)
        # === IS2-BUTTON ===
        ttk.Button(right, text="⬅  Из ИС 2 (результат перевода)",
                   command=self.from_editor2,
                   style="Smooth.TButton").pack(fill="x", pady=2)
        # === /IS2-BUTTON ==='''

PIET_METHOD_ANCHOR = "    def from_editor(self):"

PIET_METHOD_NEW = '''    def from_editor2(self):
        """Загрузить в canvas содержимое ИС 2 (правая панель — результат)."""
        try:
            # === IS2-BUTTON ===
            text = self.app.output.get("1.0", "end-1c")
            # === /IS2-BUTTON ===
            self.from_text(text)
            mode = "PNG" if self._png_mode else "GRID"
            self.app.log(f"$ Piet: загружено из ИС 2 ({mode})")
        except Exception as e:
            self.app.log(f"! Piet: {e}")

    def from_editor(self):'''


def patch_piet(dry, check):
    if not PC.is_file():
        print(f"  [!] нет файла: {PC}")
        return 0

    text = PC.read_text(encoding="utf-8")

    if "IS2-BUTTON" in text:
        print(f"  [=] piet_pack.py: уже пропатчен")
        return 0

    changes = 0

    if PIET_BTN_OLD in text:
        text = text.replace(PIET_BTN_OLD, PIET_BTN_NEW, 1)
        print(f"  [+] piet: кнопка «Из ИС 2»")
        changes += 1
    else:
        print(f"  [!] piet: блок кнопок не найден")

    if PIET_METHOD_ANCHOR in text:
        text = text.replace(PIET_METHOD_ANCHOR, PIET_METHOD_NEW, 1)
        print(f"  [+] piet: метод from_editor2")
        changes += 1
    else:
        print(f"  [!] piet: метод from_editor не найден")

    if check:
        return changes
    if dry:
        return changes
    if changes == 0:
        return 0

    bak = PC.with_suffix(PC.suffix + ".bak_is2")
    if not bak.exists():
        shutil.copy2(PC, bak)
        print(f"    бэкап: {bak.name}")
    PC.write_text(text, encoding="utf-8")
    return changes


# ==================================================================
#  RIVULET
# ==================================================================
RC_BTN_OLD = '''        ttk.Button(btns, text="В редактор",
                   command=self.send_to_editor).pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="Запустить",
                   command=self.run_program).pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="Очистить всё",
                   command=self.clear_all).pack(side="left", padx=(0, 5))'''

RC_BTN_NEW = '''        # === IS2-BUTTON ===
        ttk.Button(btns, text="Из ИС 1",
                   command=self.from_editor).pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="Из ИС 2",
                   command=self.from_editor2).pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="В редактор",
                   command=self.send_to_editor).pack(side="left", padx=(0, 5))
        # === /IS2-BUTTON ===
        ttk.Button(btns, text="Запустить",
                   command=self.run_program).pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="Очистить всё",
                   command=self.clear_all).pack(side="left", padx=(0, 5))'''

RC_METHOD_ANCHOR = "    def send_to_editor(self):"

RC_METHOD_NEW = '''    # === IS2-BUTTON ===
    def from_editor(self):
        """Загрузить в canvas содержимое ИС 1 (левая панель — исходник)."""
        try:
            text = self.app.editor.get("1.0", "end-1c")
            self.from_text(text)
            self.app.log("$ Rivulet: загружено из ИС 1")
        except Exception as e:
            self.app.log(f"! Rivulet: {e}")

    def from_editor2(self):
        """Загрузить в canvas содержимое ИС 2 (правая панель — результат)."""
        try:
            text = self.app.output.get("1.0", "end-1c")
            self.from_text(text)
            self.app.log("$ Rivulet: загружено из ИС 2")
        except Exception as e:
            self.app.log(f"! Rivulet: {e}")
    # === /IS2-BUTTON ===

    def send_to_editor(self):'''


def patch_rivulet(dry, check):
    if not RC.is_file():
        print(f"  [!] нет файла: {RC}")
        return 0

    text = RC.read_text(encoding="utf-8")

    if "IS2-BUTTON" in text:
        print(f"  [=] rivulet_canvas.py: уже пропатчен")
        return 0

    changes = 0

    if RC_BTN_OLD in text:
        text = text.replace(RC_BTN_OLD, RC_BTN_NEW, 1)
        print(f"  [+] rivulet: кнопки «Из ИС 1» и «Из ИС 2»")
        changes += 1
    else:
        print(f"  [!] rivulet: блок кнопок не найден дословно")

    if RC_METHOD_ANCHOR in text:
        text = text.replace(RC_METHOD_ANCHOR, RC_METHOD_NEW, 1)
        print(f"  [+] rivulet: методы from_editor / from_editor2")
        changes += 1
    else:
        print(f"  [!] rivulet: метод send_to_editor не найден")

    if check:
        return changes
    if dry:
        return changes
    if changes == 0:
        return 0

    bak = RC.with_suffix(RC.suffix + ".bak_is2")
    if not bak.exists():
        shutil.copy2(RC, bak)
        print(f"    бэкап: {bak.name}")
    RC.write_text(text, encoding="utf-8")
    return changes


# ==================================================================
def revert():
    for p in (PC, RC):
        bak = p.with_suffix(p.suffix + ".bak_is2")
        if bak.is_file():
            shutil.copy2(bak, p)
            print(f"  [<] {p.name}: восстановлен")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    if args.revert:
        revert()
        return

    print(f"Piet:    {PC}")
    print(f"Rivulet: {RC}\n")

    if args.check:
        print("PIET:")
        n1 = patch_piet(dry=False, check=True)
        print("\nRIVULET:")
        n2 = patch_rivulet(dry=False, check=True)
        print(f"\nНайдено изменений: {n1 + n2}")
        return

    n1 = patch_piet(dry=args.dry, check=False)
    n2 = patch_rivulet(dry=args.dry, check=False)
    print(f"\nИзменений: {n1 + n2}")
    if not args.dry and (n1 or n2):
        print(f"\nОткат: python tools/add_is2_buttons.py --revert")


if __name__ == "__main__":
    main()