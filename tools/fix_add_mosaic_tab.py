# tools/fix_add_mosaic_tab.py
"""Добавляет метод _build_tab_mosaic в App, если его нет."""
from __future__ import annotations
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


METHOD = '''    def _build_tab_mosaic(self):
        try:
            from ui.mosaic_tab import MosaicTab
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=6)
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


def main():
    _force_utf8()
    if not APP.is_file():
        print(f"  [!] нет файла: {APP}")
        return

    text = APP.read_text(encoding="utf-8")

    if "def _build_tab_mosaic" in text:
        print("  [=] метод уже есть")
        return

    # якорь — перед _build_tab_piet_asm
    anchor = "    def _build_tab_piet_asm(self):"

    if anchor in text:
        text = text.replace(anchor, METHOD + anchor, 1)
        print("  [+] вставлен _build_tab_mosaic перед _build_tab_piet_asm")
    else:
        # альтернативный якорь — перед _bind_hotkeys
        anchor2 = "    def _bind_hotkeys(self):"
        if anchor2 in text:
            text = text.replace(anchor2, METHOD + anchor2, 1)
            print("  [+] вставлен _build_tab_mosaic перед _bind_hotkeys")
        else:
            print("  [!] не найден якорь для вставки")
            return

    bak = APP.with_suffix(APP.suffix + ".bak_mosaic")
    if not bak.exists():
        shutil.copy2(APP, bak)
        print(f"    бэкап: {bak.name}")

    APP.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()