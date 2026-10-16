from core.i18n import t as tr
# ui/mosaic_tab.py
"""Вкладка «Мозаика».

  brainpiet — 1×1, BF-команды
  blockpiet — 2×2, токены Python
  piet++    — 1×1, цвета Piet
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

try:
    from PIL import Image, ImageTk  # noqa: F401
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from core.blockpiet_lib import BlockPietTileLibrary
from core.mosaic_palettes import get_palette, BRAINPIET_CHARS, _PIET_ITEMS
from core.mosaic_utils import (
    tiles_to_brainfuck,
    tiles_to_python,
    tiles_to_png_brainpiet,
    tiles_to_png_blockpiet,
    tiles_to_png_piet,
    run_brainpiet,
    run_blockpiet,
    run_piet,
)

LANGS = ["brainpiet", "blockpiet", "piet++"]
LANG_TITLES = {
    "brainpiet": "🧠 BrainPiet",
    "blockpiet": "🟦 BlockPiet",
    "piet++":    "🎨 Piet++",
}


# 20 базовых цветов проекта (для blockpiet 2×2 и для piet++ 1×1)
_BP_COLORS = [
    (255, 192, 192), (255, 255, 192), (192, 255, 192), (192, 255, 255),
    (192, 192, 255), (255, 192, 255),
    (255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255),
    (0, 0, 255), (255, 0, 255),
    (192, 0, 0), (192, 192, 0), (0, 192, 0), (0, 192, 192),
    (0, 0, 192), (192, 0, 192),
    (255, 255, 255), (0, 0, 0),
]
_BF_COLORS = [
    (255, 192, 192), (192, 255, 192), (255, 0, 0), (0, 255, 0),
    (0, 0, 255), (0, 255, 255), (255, 255, 0), (255, 0, 255),
    (0, 0, 0), (255, 255, 255),
]


def _piet_color(cat: int, val: int):
    """(cat, val) → RGB для отрисовки плитки Piet++."""
    if cat == 18:
        return (255, 255, 255)
    if cat == 19:
        return (0, 0, 0)
    idx = cat * 3 + val
    if 0 <= idx < 18:
        return _BP_COLORS[idx]
    return (128, 128, 128)


def _piet_symbol(name: str) -> str:
    """Короткая подпись на плитке."""
    shorts = {
        "nop": "·", "push": "p", "pop": "o", "add": "+",
        "sub": "−", "mul": "×", "div": "÷", "mod": "%",
        "not": "!", "gt": ">", "dp": "d", "cc": "c",
        "dup": "u", "roll": "r", "write": "w", "read": "R",
        "out_num": "n", "out_char": "C",
        "white": "·", "black": "#",
    }
    return shorts.get(name, name[:2])


class MosaicTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app

        self.current_lang = "brainpiet"
        self.mosaics: dict[str, list] = {
            "brainpiet": [],
            "blockpiet": [],
            "piet++":    [],
        }
        self.lib = BlockPietTileLibrary()

        self._build()
        self._refresh_palette()
        self._render_mosaic()
        self._update_code()

    # ------------------------------------------------------------------
    def _build(self):
        lang_bar = ttk.Frame(self.parent)
        lang_bar.pack(fill="x", padx=6, pady=(6, 0))
        ttk.Label(lang_bar, text=tr("mz_lang"),
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        self.lang_var = tk.StringVar(value=LANG_TITLES[self.current_lang])
        self.lang_cb = ttk.Combobox(
            lang_bar, textvariable=self.lang_var,
            values=[LANG_TITLES[l] for l in LANGS],
            state="readonly", width=18)
        self.lang_cb.pack(side="left")
        self.lang_cb.bind("<<ComboboxSelected>>",
                          lambda e: self._switch_lang())

        top = ttk.Frame(self.parent)
        top.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Button(top, text=tr("mz_run"), command=self.run_mosaic,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text=tr("mz_clear"), command=self.clear_mosaic,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text=tr("mz_undo"), command=self.pop_mosaic,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Separator(top, orient="vertical").pack(side="left",
                                                   fill="y", padx=6)
        ttk.Button(top, text=tr("mz_save_png"), command=self.save_png,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text=tr("mz_load_png"), command=self.load_png,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Separator(top, orient="vertical").pack(side="left",
                                                   fill="y", padx=6)
        ttk.Button(top, text=tr("mz_copy_code"), command=self.copy_code,
                   style="Smooth.TButton").pack(side="left")

        self.status = ttk.Label(top, text=tr("mz_done"))
        self.status.pack(side="right")

        main = ttk.Frame(self.parent)
        main.pack(fill="both", expand=True, padx=6, pady=6)
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.columnconfigure(2, weight=0)
        main.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(main, text=tr("mz_lib"), padding=4)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 4))

        cat_bar = ttk.Frame(left)
        cat_bar.pack(fill="x", pady=(0, 4))
        ttk.Label(cat_bar, text=tr("mz_category")).pack(side="left")
        self.cat_var = tk.StringVar(value="")
        self.cat_cb = ttk.Combobox(
            cat_bar, textvariable=self.cat_var,
            values=[], state="readonly", width=14)
        self.cat_cb.pack(side="left", padx=4)
        self.cat_cb.bind("<<ComboboxSelected>>",
                         lambda e: self._cat_combobox_changed())
        ttk.Button(cat_bar, text=tr("mz_custom"),
                   command=self._add_custom_tile,
                   style="Smooth.TButton").pack(side="right")

        lf = ttk.Frame(left)
        lf.pack(fill="both", expand=True)
        self.palette_list = tk.Listbox(lf, width=22, height=14,
                                       font=("Consolas", 9),
                                       activestyle="none",
                                       exportselection=False)
        self.palette_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lf, orient="vertical",
                           command=self.palette_list.yview)
        sb.pack(side="left", fill="y")
        self.palette_list.config(yscrollcommand=sb.set)
        self.palette_list.bind("<Double-Button-1>",
                               lambda e: self.add_selected_tile())

        ttk.Button(left, text=tr("mz_add"),
                   command=self.add_selected_tile,
                   style="Smooth.TButton").pack(fill="x", pady=(4, 0))

        tpl_frame = ttk.LabelFrame(left, text=tr("mz_templates"), padding=4)
        tpl_frame.pack(fill="x", pady=(6, 0))
        self.tpl_list = tk.Listbox(tpl_frame, width=22, height=8,
                                    font=("Consolas", 9),
                                    activestyle="none",
                                    exportselection=False)
        self.tpl_list.pack(side="left", fill="both", expand=True)
        tpl_sb = ttk.Scrollbar(tpl_frame, orient="vertical",
                                command=self.tpl_list.yview)
        tpl_sb.pack(side="left", fill="y")
        self.tpl_list.config(yscrollcommand=tpl_sb.set)
        self.tpl_list.bind("<Double-Button-1>",
                            lambda e: self.add_selected_template())

        ttk.Button(left, text=tr("mz_insert_tpl"),
                   command=self.add_selected_template,
                   style="Smooth.TButton").pack(fill="x", pady=(4, 0))

        center = ttk.LabelFrame(main, text=tr("mz_title"), padding=4)
        center.grid(row=0, column=1, sticky="nsew", padx=4)
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(center, bg="#1e1e1e",
                                bd=0, highlightthickness=1,
                                highlightbackground="#444",
                                height=400)
        vbar = ttk.Scrollbar(center, orient="vertical",
                             command=self.canvas.yview)
        hbar = ttk.Scrollbar(center, orient="horizontal",
                             command=self.canvas.xview)
        self.canvas.config(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

        right = ttk.LabelFrame(main, text=tr("mz_code"), padding=4)
        right.grid(row=0, column=2, sticky="nse", padx=(4, 0))

        self.py_out = tk.Text(right, width=40, height=12,
                              font=("Consolas", 10), wrap="word", bd=0)
        self.py_out.pack(fill="both", expand=True)
        self.py_out.config(state="disabled")

        ttk.Label(right, text=tr("mz_output")).pack(anchor="w", pady=(6, 0))
        self.exec_out = tk.Text(right, width=40, height=8,
                                font=("Consolas", 10), wrap="word", bd=0)
        self.exec_out.pack(fill="both", expand=True)
        self.exec_out.config(state="disabled")

    # ------------------------------------------------------------------
    def _switch_lang(self):
        title = self.lang_var.get()
        new = next((k for k, v in LANG_TITLES.items() if v == title), None)
        if new is None or new == self.current_lang:
            return
        self.current_lang = new
        self._refresh_palette()
        self._render_mosaic()
        self._update_code()
        self._set_exec("")
        if self.app:
            self.app.log(f"$ Мозаика: язык → {new}")

    def _palette(self):
        return get_palette(self.current_lang)

    def _current_mosaic(self):
        return self.mosaics.setdefault(self.current_lang, [])

    # ------------------------------------------------------------------
    def _refresh_palette(self):
        pal = self._palette()
        self.palette_list.delete(0, "end")
        self.tpl_list.delete(0, "end")
        if not pal:
            return
        cats = pal["categories"]
        self.cat_cb["values"] = [c[0] for c in cats]
        self.cat_var.set(cats[0][0] if cats else "")
        self._fill_palette_for_cat(cats[0] if cats else ("", []))
        for name in pal.get("templates", {}):
            self.tpl_list.insert("end", name)

    def _fill_palette_for_cat(self, cat_tuple):
        _, items = cat_tuple
        self.palette_list.delete(0, "end")
        for item in items:
            self.palette_list.insert("end", item[0])

    def _cat_combobox_changed(self):
        pal = self._palette()
        if not pal:
            return
        sel = self.cat_var.get()
        for cat_tuple in pal["categories"]:
            if cat_tuple[0] == sel:
                self._fill_palette_for_cat(cat_tuple)
                return

    def _add_custom_tile(self):
        from tkinter import simpledialog
        if self.current_lang == "piet++":
            return
        name = simpledialog.askstring(
            "Своя плитка", "Имя плитки:", parent=self.parent)
        if not name:
            return
        cat = simpledialog.askinteger(
            "Своя плитка", "Категория (0-19):",
            minvalue=0, maxvalue=19, parent=self.parent)
        if cat is None:
            return
        val = simpledialog.askinteger(
            "Своя плитка", "Значение (0-19):",
            minvalue=0, maxvalue=19, parent=self.parent)
        if val is None:
            return
        self.lib.add(name, cat, val)
        self._refresh_palette()
        if self.app:
            self.app.log(f"$ Мозаика: добавлена плитка «{name}»")

    # ------------------------------------------------------------------
    def add_selected_tile(self):
        sel = self.palette_list.curselection()
        if not sel:
            return
        name = self.palette_list.get(sel[0])
        pal = self._palette()
        if not pal:
            return
        cat_name = self.cat_var.get()
        for cat_tuple in pal["categories"]:
            if cat_tuple[0] != cat_name:
                continue
            for item in cat_tuple[1]:
                if item[0] == name:
                    self._current_mosaic().append((name, item[1]))
                    self._render_mosaic()
                    self._update_code()
                    return

    def add_selected_template(self):
        sel = self.tpl_list.curselection()
        if not sel:
            return
        pal = self._palette() or {}
        name = self.tpl_list.get(sel[0])
        tiles = pal.get("templates", {}).get(name)
        if not tiles:
            return
        for pair in tiles:
            self._current_mosaic().append((name, pair))
        self._render_mosaic()
        self._update_code()
        if self.app:
            self.app.log(
                f"$ Мозаика: вставлен шаблон «{name}» ({len(tiles)} плиток)")

    def pop_mosaic(self):
        m = self._current_mosaic()
        if m:
            m.pop()
            self._render_mosaic()
            self._update_code()

    def clear_mosaic(self):
        self.mosaics[self.current_lang] = []
        self._render_mosaic()
        self._update_code()
        self._set_exec("")

    # ------------------------------------------------------------------
    def _render_mosaic(self):
        self.canvas.delete("all")
        mosaic = self._current_mosaic()
        pal = self._palette() or {}
        tile_w, tile_h = pal.get("tile_size", (1, 1))
        cell = pal.get("cell_px", 32)

        if not mosaic:
            self.canvas.create_text(
                220, 80,
                text=tr("mz_empty_hint"),
                font=("Segoe UI", 11), fill="#888", justify="center")
            self.canvas.config(scrollregion=(0, 0, 440, 160))
            return

        pad = 8
        per_row = max(1, 20 // max(1, tile_w))

        for i, (name, pair) in enumerate(mosaic):
            r = i // per_row
            c = i % per_row
            x1 = pad + c * (cell * tile_w + 6)
            y1 = pad + r * (cell * tile_h + 22)

            if self.current_lang == "brainpiet":
                color = _BF_COLORS[pair[1] % len(_BF_COLORS)]
                self.canvas.create_rectangle(
                    x1, y1, x1 + cell, y1 + cell,
                    fill="#%02X%02X%02X" % color, outline="#666")
                ch = (BRAINPIET_CHARS[pair[1]]
                      if pair[1] < len(BRAINPIET_CHARS) else "?")
                fg = "#FFF" if color == (0, 0, 0) else "#000"
                self.canvas.create_text(
                    x1 + cell // 2, y1 + cell // 2, text=ch,
                    font=("Consolas", 14, "bold"), fill=fg)

            elif self.current_lang == "piet++":
                color = _piet_color(pair[0], pair[1])
                self.canvas.create_rectangle(
                    x1, y1, x1 + cell, y1 + cell,
                    fill="#%02X%02X%02X" % color, outline="#666")
                sym = _piet_symbol(name)
                fg = "#FFF" if sum(color) < 300 else "#000"
                self.canvas.create_text(
                    x1 + cell // 2, y1 + cell // 2, text=sym,
                    font=("Consolas", 14, "bold"), fill=fg)

            else:  # blockpiet — 2×2
                cat, val = pair
                col_tl = _BP_COLORS[cat % len(_BP_COLORS)]
                col_tr = _BP_COLORS[val % len(_BP_COLORS)]
                half = cell
                self.canvas.create_rectangle(
                    x1, y1, x1 + half, y1 + half,
                    fill="#%02X%02X%02X" % col_tl, outline="#888")
                self.canvas.create_rectangle(
                    x1 + half, y1, x1 + 2 * half, y1 + half,
                    fill="#%02X%02X%02X" % col_tr, outline="#888")
                self.canvas.create_rectangle(
                    x1, y1 + half, x1 + half, y1 + 2 * half,
                    fill="#C8C8C8", outline="#888")
                self.canvas.create_rectangle(
                    x1 + half, y1 + half, x1 + 2 * half, y1 + 2 * half,
                    fill="#DCDCDC", outline="#888")

            self.canvas.create_text(
                x1 + (cell * tile_w) // 2, y1 + cell * tile_h + 4,
                text=name[:16], font=("Consolas", 7),
                fill="#AAA", anchor="n")

        total_w = pad * 2 + per_row * (cell * tile_w + 6)
        rows = (len(mosaic) + per_row - 1) // per_row
        total_h = pad * 2 + rows * (cell * tile_h + 22)
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))

    # ------------------------------------------------------------------
    def _update_code(self):
        mosaic = self._current_mosaic()
        try:
            if self.current_lang == "brainpiet":
                code = tiles_to_brainfuck([p for _, p in mosaic])
            elif self.current_lang == "blockpiet":
                code = tiles_to_python([p for _, p in mosaic])
            else:  # piet++ — показываем команды, которые видит пользователь
                code = " ".join(name for name, _ in mosaic)
        except Exception as e:
            code = f"# ошибка: {e}"
        self.py_out.config(state="normal")
        self.py_out.delete("1.0", "end")
        self.py_out.insert("1.0", code)
        self.py_out.config(state="disabled")

    def _set_exec(self, text):
        self.exec_out.config(state="normal")
        self.exec_out.delete("1.0", "end")
        self.exec_out.insert("1.0", text)
        self.exec_out.config(state="disabled")

    def run_mosaic(self):
        tiles = [p for _, p in self._current_mosaic()]
        try:
            if self.current_lang == "brainpiet":
                result = run_brainpiet(tiles)
            elif self.current_lang == "blockpiet":
                result = run_blockpiet(tiles)
            else:
                result = run_piet(tiles)
        except Exception as e:
            result = f"// ошибка: {type(e).__name__}: {e}"
        self._set_exec(result)
        if self.app:
            self.app.log(f"$ Мозаика: вывод {result!r}")

    def copy_code(self):
        code = self.py_out.get("1.0", "end-1c")
        self.parent.clipboard_clear()
        self.parent.clipboard_append(code)
        if self.app:
            self.app.log(f"$ Мозаика: скопировано ({len(code)} симв.)")

    # ------------------------------------------------------------------
    def save_png(self):
        tiles = [p for _, p in self._current_mosaic()]
        if not tiles:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            if self.current_lang == "piet++":
                png = tiles_to_png_piet(tiles)
            elif self.current_lang == "brainpiet":
                png = tiles_to_png_brainpiet(tiles)
            else:
                png = tiles_to_png_blockpiet(tiles)
            Path(path).write_bytes(png)
            if self.app:
                self.app.log(f"$ Мозаика: PNG сохранён {path}")
        except Exception as e:
            if self.app:
                self.app.log(f"! Мозаика: {e}")

    def load_png(self):
        path = filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
        if not path:
            return
        if self.app:
            self.app.log("! Мозаика: загрузка PNG пока не поддержана")