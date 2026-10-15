# tools/add_piet_asm_ui.py
"""
Добавляет в Main.py новую вкладку «Piet-ASM».

Внутри:
  - слева: текстовый редактор для asm-команд
  - справа: результат (текст) + панель плиток (◀ ▶)
  - кнопки: ▶ Запустить, Показать плитки, Копировать

Запуск:
    python tools/add_piet_asm_ui.py --check
    python tools/add_piet_asm_ui.py
    python tools/add_piet_asm_ui.py --revert
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "ui" / "app.py"


METHOD = '''
    # ==========================================================
    #  ВКЛАДКА «PIET-ASM»
    # ==========================================================
    def _build_tab_piet_asm(self):
        try:
            from langs.piet_asm import EXAMPLES
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text="Piet-ASM")
            ttk.Label(tab, text=f"Ошибка: {e}",
                      foreground="red").pack()
            return

        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="Piet-ASM")

        # --- верхняя панель ---
        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 6))

        ttk.Label(top, text="Пример:").pack(side="left", padx=(0, 4))
        self.asm_example_cb = ttk.Combobox(
            top, values=list(EXAMPLES.keys()),
            state="readonly", width=22)
        self.asm_example_cb.pack(side="left", padx=(0, 10))
        self.asm_example_cb.bind(
            "<<ComboboxSelected>>", self._asm_load_example)
        if EXAMPLES:
            self.asm_example_cb.current(0)

        ttk.Button(top, text="▶ Запустить",
                   command=self._asm_run,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text="🔍 Разобрать",
                   command=self._asm_explain,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text="📦 Плитки",
                   command=self._asm_show_tiles,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text="Копир. результат",
                   command=self._asm_copy,
                   style="Smooth.TButton").pack(side="left")

        self.asm_status = ttk.Label(top, text="")
        self.asm_status.pack(side="right")

        # --- тело: редактор и результат ---
        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Piet-ASM код", padding=4)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.asm_editor = tk.Text(
            left, font=("Consolas", 11), wrap="none",
            bd=0, padx=6, pady=4, undo=True)
        self.asm_editor.pack(fill="both", expand=True)

        right = ttk.LabelFrame(body, text="Результат", padding=4)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.asm_output = tk.Text(
            right, font=("Consolas", 11), wrap="word",
            bd=0, padx=6, pady=4, state="disabled", height=8)
        self.asm_output.pack(fill="both", expand=True)

        # --- нижняя панель: плитки ---
        bottom = ttk.LabelFrame(tab, text="Плитки 16×16", padding=4)
        bottom.pack(fill="both", expand=False, pady=(6, 0))

        pbar = ttk.Frame(bottom)
        pbar.pack(fill="x", pady=(0, 4))

        ttk.Button(pbar, text="◀", width=3,
                   command=self._asm_tile_prev,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        self.asm_tile_lbl = ttk.Label(pbar, text="—/—",
                                       font=("Segoe UI", 10, "bold"))
        self.asm_tile_lbl.pack(side="left", padx=(0, 4))
        ttk.Button(pbar, text="▶", width=3,
                   command=self._asm_tile_next,
                   style="Smooth.TButton").pack(side="left", padx=(0, 12))

        ttk.Label(pbar, text="Зум:").pack(side="left", padx=(0, 4))
        for z in (1, 2, 4, 8):
            ttk.Button(pbar, text=f"×{z}", width=3,
                       command=lambda zz=z: self._asm_set_zoom(zz),
                       style="Smooth.TButton").pack(side="left", padx=1)

        # canvas для плиток
        cframe = ttk.Frame(bottom)
        cframe.pack(fill="both", expand=True)
        self.asm_canvas = tk.Canvas(cframe, width=256, height=256,
                                     bd=0, highlightthickness=1,
                                     highlightbackground="#666")
        self.asm_canvas.pack(side="left")

        # --- состояние ---
        self._asm_tiles = []
        self._asm_tile_idx = 0
        self._asm_zoom = 4
        self._asm_img = None

        self._asm_load_example()

    # ----------------------------------------------------------
    def _asm_load_example(self, event=None):
        try:
            from langs.piet_asm import EXAMPLES
        except Exception:
            return
        name = self.asm_example_cb.get()
        code = EXAMPLES.get(name, "")
        self.asm_editor.delete("1.0", "end")
        self.asm_editor.insert("1.0", code)

    def _asm_run(self):
        try:
            from langs.piet_asm import execute_asm
            code = self.asm_editor.get("1.0", "end-1c")
            result = execute_asm(code)
            self.asm_output.config(state="normal")
            self.asm_output.delete("1.0", "end")
            self.asm_output.insert("1.0", result)
            self.asm_output.config(state="disabled")
            self.asm_status.config(text="OK")
            self.log(f"$ Piet-ASM: вывод {result!r}")
        except Exception as e:
            self.asm_output.config(state="normal")
            self.asm_output.delete("1.0", "end")
            self.asm_output.insert("1.0", f"Ошибка: {e}")
            self.asm_output.config(state="disabled")
            self.asm_status.config(text="ошибка")
            self.log(f"! Piet-ASM: {e}")

    def _asm_explain(self):
        try:
            from langs.piet_asm import parse_asm, COMMANDS
            code = self.asm_editor.get("1.0", "end-1c")
            cmds = parse_asm(code)
            lines = []
            for i, (cmd, arg) in enumerate(cmds, 1):
                dh, dl = COMMANDS[cmd]
                arg_s = f" {arg}" if arg is not None else ""
                lines.append(
                    f"  {i:>3}. {cmd}{arg_s:<8} → delta ({dh},{dl})")
            text = "\\n".join(lines) if lines else "(пусто)"
            self.asm_output.config(state="normal")
            self.asm_output.delete("1.0", "end")
            self.asm_output.insert("1.0",
                f"Команд: {len(cmds)}\\n\\n{text}")
            self.asm_output.config(state="disabled")
        except Exception as e:
            self.log(f"! Piet-ASM разбор: {e}")

    def _asm_show_tiles(self):
        try:
            from langs.piet_asm import asm_to_tiles
            code = self.asm_editor.get("1.0", "end-1c")
            tiles = asm_to_tiles(code)
            self._asm_tiles = tiles
            self._asm_tile_idx = 0
            self._asm_render_tile()
            self.log(f"$ Piet-ASM: {len(tiles)} плиток")
        except Exception as e:
            self.log(f"! Piet-ASM плитки: {e}")

    def _asm_tile_prev(self):
        if not self._asm_tiles:
            return
        self._asm_tile_idx = max(0, self._asm_tile_idx - 1)
        self._asm_render_tile()

    def _asm_tile_next(self):
        if not self._asm_tiles:
            return
        self._asm_tile_idx = min(len(self._asm_tiles) - 1,
                                   self._asm_tile_idx + 1)
        self._asm_render_tile()

    def _asm_set_zoom(self, z):
        self._asm_zoom = z
        self._asm_render_tile()

    def _asm_render_tile(self):
        try:
            import base64, io
            from PIL import Image, ImageTk
        except ImportError:
            return
        if not self._asm_tiles:
            self.asm_tile_lbl.config(text="—/—")
            self.asm_canvas.delete("all")
            return

        n = len(self._asm_tiles)
        self.asm_tile_lbl.config(
            text=f"{self._asm_tile_idx + 1}/{n}")

        try:
            raw = base64.b64decode(self._asm_tiles[self._asm_tile_idx])
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            z = self._asm_zoom
            if z > 1:
                im = im.resize((im.width * z, im.height * z),
                               Image.NEAREST)
            self._asm_img = ImageTk.PhotoImage(im)
            self.asm_canvas.delete("all")
            self.asm_canvas.create_image(0, 0, image=self._asm_img,
                                          anchor="nw")
            self.asm_canvas.config(
                scrollregion=(0, 0, im.width, im.height))
        except Exception as e:
            self.log(f"! отрисовка плитки: {e}")

    def _asm_copy(self):
        text = self.asm_output.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"$ результат в буфере ({len(text)})")

    def _bind_hotkeys(self):
'''

OLD_BIND = "    def _bind_hotkeys(self):\n"

# куда добавить вызов _build_tab_piet_asm
OLD_TABS = '''        self._build_tab_examples()
        self._build_tab_help()
        self._build_tab_sandbox()'''

NEW_TABS = '''        self._build_tab_examples()
        self._build_tab_help()
        self._build_tab_sandbox()
        self._build_tab_piet_asm()   # Piet-ASM'''


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _force_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    if args.revert:
        bak = APP.with_suffix(APP.suffix + ".bak_asmui")
        if bak.is_file():
            shutil.copy2(bak, APP)
            print("  [<] app.py восстановлен")
        return

    text = APP.read_text(encoding="utf-8")

    if "_build_tab_piet_asm" in text:
        print("  [=] уже пропатчен")
        return

    if OLD_BIND not in text:
        print("  [!] не найден _bind_hotkeys — структура другая")
        return
    if OLD_TABS not in text:
        print("  [!] не найден блок вкладок")
        return

    if args.check:
        print("  ✓ _bind_hotkeys найден")
        print("  ✓ блок вкладок найден")
        return

    bak = APP.with_suffix(APP.suffix + ".bak_asmui")
    if not bak.exists():
        shutil.copy2(APP, bak)
        print(f"    бэкап: {bak.name}")

    text = text.replace(OLD_TABS, NEW_TABS, 1)
    text = text.replace(OLD_BIND, METHOD + "\n", 1)
    APP.write_text(text, encoding="utf-8")
    print("  [+] app.py: вкладка Piet-ASM")


if __name__ == "__main__":
    main()