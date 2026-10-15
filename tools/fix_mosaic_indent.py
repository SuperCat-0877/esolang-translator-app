# tools/fix_mosaic_indent.py
"""
Баг: _build_tab_mosaic вложен внутрь _asm_copy.
Фикс: вырезать его оттуда и добавить как метод класса.
"""
from __future__ import annotations
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "ui" / "app.py"


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


BROKEN = '''    def _asm_copy(self):
        text = self.asm_output.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"$ результат в буфере ({len(text)})")

        def _build_tab_mosaic(self):
            from ui.mosaic_tab import MosaicTab
            tab = ttk.Frame(self.tabs, padding=6)
            self.tabs.add(tab, text="Мозаика")
            self.mosaic_tab = MosaicTab(tab, self)

'''

FIXED = '''    def _asm_copy(self):
        text = self.asm_output.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"$ результат в буфере ({len(text)})")

'''


def main():
    _force_utf8()
    if not APP.is_file():
        print(f"  [!] нет файла {APP}")
        return

    text = APP.read_text(encoding="utf-8")

    # проверка что баг есть
    if BROKEN not in text:
        print("  [=] баг не найден в этом виде — проверь вручную")
        # всё равно пробуем добавить метод
    else:
        bak = APP.with_suffix(APP.suffix + ".bak_indent")
        if not bak.exists():
            shutil.copy2(APP, bak)
            print(f"    бэкап: {bak.name}")

        text = text.replace(BROKEN, FIXED, 1)
        print("  [+] убран вложенный _build_tab_mosaic")

    # теперь добавим правильный метод, если его нет
    if "    def _build_tab_mosaic(self):" not in text:
        anchor = "    def _build_tab_sandbox(self):"
        method = '''    def _build_tab_mosaic(self):
        try:
            from ui.mosaic_tab import MosaicTab
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text="Мозаика")
            ttk.Label(tab,
                      text=f"Не удалось загрузить Мозаику:\\n{e}",
                      foreground="red", wraplength=800).pack(pady=20)
            return
        tab = ttk.Frame(self.tabs, padding=6)
        self.tabs.add(tab, text="Мозаика")
        try:
            self.mosaic_tab = MosaicTab(tab, self)
        except Exception as e:
            ttk.Label(tab,
                      text=f"Ошибка при создании Мозаики:\\n{e}",
                      foreground="red", wraplength=800).pack(pady=20)

'''
        if anchor in text:
            text = text.replace(anchor, method + anchor, 1)
            print("  [+] добавлен метод _build_tab_mosaic")
        else:
            print("  [!] не найден якорь _build_tab_sandbox")

    APP.write_text(text, encoding="utf-8")
    print("  Готово.")


if __name__ == "__main__":
    main()