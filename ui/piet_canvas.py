# ui/piet_canvas.py
"""Piet Canvas — просмотрщик Piet-программ с тремя режимами.

  BRAINPIET — 1 клетка = 1 BF-команда
  BLOCKPIET — 2×2 = 1 слово Python
  PIET++    — настоящая Piet-мозаика
"""

import base64
import io
import tkinter as tk
from tkinter import ttk, filedialog
from core.i18n import t as tr

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

GRID = 16
CELL = 22

MODES = ["BRAINPIET2D", "BLOCKPIET2D", "PIET++"]
MODE_TITLES = {
    "BRAINPIET2D": "🧠² BrainPiet 2D",
    "BLOCKPIET2D": "🟦² BlockPiet 2D",
    "PIET++":      "🎨 Piet++",
}

BRAINPIET_CHARS = {
    "#FFC0C0": ">", "#C0FFC0": "<", "#FF0000": "+", "#00FF00": "-",
    "#0000FF": ".", "#00FFFF": ",", "#FFFF00": "[", "#FF00FF": "]",
    "#000000": "#", "#FFFFFF": " ",
}

PIET_HEX = [
    "#FFC0C0", "#FFFFC0", "#C0FFC0", "#C0FFFF",
    "#C0C0FF", "#FFC0FF",
    "#FF0000", "#FFFF00", "#00FF00", "#00FFFF",
    "#0000FF", "#FF00FF",
    "#C00000", "#C0C000", "#00C000", "#00C0C0",
    "#0000C0", "#C000C0",
    "#FFFFFF", "#000000",
]
PIET_HEX_TO_IDX = {c: i for i, c in enumerate(PIET_HEX)}

BLOCKPIET_TYPES = [
    "KEYWORD", "NAME", "NUMBER", "STRING",
    "OP", "LPAREN", "RPAREN", "LBRACK", "RBRACK",
    "LBRACE", "RBRACE", "COMMA", "COLON", "DOT",
    "NEWLINE", "INDENT", "DEDENT", "END",
    "STRING_END", "ERROR",
]

PIET_COLORS = [
    "#FFC0C0", "#FFFFC0", "#C0FFC0", "#C0FFFF", "#C0C0FF", "#FFC0FF",
    "#FF0000", "#FFFF00", "#00FF00", "#00FFFF", "#0000FF", "#FF00FF",
    "#C00000", "#C0C000", "#00C000", "#00C0C0", "#0000C0", "#C000C0",
    "#FFFFFF", "#000000",
]
CHARS = "0123456789abcdefghij"
CHARS_BY_SYM = {c: i for i, c in enumerate(CHARS)}
NAMES = [
    "Light Red", "Light Yellow", "Light Green", "Light Cyan",
    "Light Blue", "Light Magenta",
    "Red", "Yellow", "Green", "Cyan", "Blue", "Magenta",
    "Dark Red", "Dark Yellow", "Dark Green", "Dark Cyan",
    "Dark Blue", "Dark Magenta",
    "White", "Black",
]


class PietCanvasTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.active_color = 18
        self.grid = [[18] * GRID for _ in range(GRID)]
        self._palette_btns = []
        self._painting = False

        # состояние
        self._mode = "PIET++"
        self._mode_btns: dict = {}
        self._zoom = 2
        self._png_mode = False
        self._png_image = None
        self._png_pil = None
        self._png_base64 = None
        self._png_dims = (0, 0)
        self._tiles: list[str] = []
        self._tile_idx = 0

        self._build()
        self._render()

    # ==================================================================
    #  UI
    # ==================================================================
    def _build(self):
        # ---------- верхняя панель с режимами ----------
        modes_bar = ttk.Frame(self.parent)
        modes_bar.pack(fill="x", padx=6, pady=(6, 0))
        ttk.Label(modes_bar, text=tr("rezhim_2"),
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        for mode in MODES:
            btn = ttk.Button(
                modes_bar, text=MODE_TITLES[mode],
                command=lambda m=mode: self.set_mode(m),
                style="Smooth.TButton")
            btn.pack(side="left", padx=2)
            self._mode_btns[mode] = btn

        # ---------- main area: left + right ----------
        main = ttk.Frame(self.parent)
        main.pack(fill="both", expand=True)

        right = ttk.Frame(main)
        right.pack(side="right", fill="y", padx=(4, 6), pady=6)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True, padx=(6, 4), pady=6)

        # ---------- заголовок left ----------
        top = ttk.Frame(left)
        top.pack(fill="x")
        self.header_lbl = ttk.Label(
            top, text=f"Piet {GRID}×{GRID}",
            font=("Segoe UI", 10, "bold"))
        self.header_lbl.pack(side="left")

        ttk.Button(top, text=tr("ochistit_3"), command=self.clear,
                   style="Smooth.TButton").pack(side="right")
        ttk.Button(top, text=tr("pereklyuchit_vid"), command=self._toggle_mode,
                   style="Smooth.TButton").pack(side="right", padx=(0, 4))

        # ---------- панель навигации ----------
        pbar = ttk.Frame(left)
        pbar.pack(fill="x", pady=(6, 2))
        ttk.Button(pbar, text="◀", width=3, command=self._tile_prev,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        self.tile_lbl = ttk.Label(pbar, text="—/—",
                                   font=("Segoe UI", 10, "bold"))
        self.tile_lbl.pack(side="left", padx=(0, 4))
        ttk.Button(pbar, text="▶", width=3, command=self._tile_next,
                   style="Smooth.TButton").pack(side="left", padx=(0, 12))

        ttk.Label(pbar, text=tr("zum_2")).pack(side="left", padx=(0, 4))
        for z in (1, 2, 4, 8):
            ttk.Button(pbar, text=f"×{z}", width=3,
                       command=lambda zz=z: self._set_zoom(zz),
                       style="Smooth.TButton").pack(side="left", padx=1)
        ttk.Button(pbar, text="Fit", command=lambda: self._set_zoom(0),
                   style="Smooth.TButton").pack(side="left", padx=(4, 0))

        # ---------- canvas со скроллами ----------
        wrap = ttk.Frame(left)
        wrap.pack(fill="both", expand=True, pady=6)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        size = GRID * CELL
        self.canvas = tk.Canvas(wrap, width=size, height=size, bd=0,
                                 highlightthickness=1,
                                 highlightbackground="#666")
        vbar = ttk.Scrollbar(wrap, orient="vertical",
                              command=self.canvas.yview)
        hbar = ttk.Scrollbar(wrap, orient="horizontal",
                              command=self.canvas.xview)
        self.canvas.config(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # ---------- правая панель: палитра ----------
        ttk.Label(right, text=tr("palitra"),
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        pal = ttk.Frame(right)
        pal.pack(fill="x", pady=(0, 8))
        for i in range(20):
            r, c = i // 10, i % 10
            b = tk.Canvas(pal, width=26, height=26, bd=1,
                          highlightthickness=2,
                          highlightbackground="#666", highlightcolor="#666")
            b.grid(row=r, column=c, padx=1, pady=1)
            b.create_rectangle(0, 0, 26, 26, fill=PIET_COLORS[i], outline="")
            b.bind("<Button-1>", lambda e, idx=i: self._pick(idx))
            self._palette_btns.append(b)

        act = ttk.Frame(right)
        act.pack(fill="x", pady=(0, 8))
        ttk.Label(act, text=tr("aktivnyy")).pack(side="left")
        self.active_preview = tk.Canvas(act, width=32, height=24, bd=1,
                                         highlightthickness=0)
        self.active_preview.pack(side="left", padx=6)
        self.active_rect = self.active_preview.create_rectangle(
            0, 0, 32, 24, fill=PIET_COLORS[18], outline="")
        self.active_label = ttk.Label(act, text="White (18)")
        self.active_label.pack(side="left")

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=8)

        ttk.Button(right, text=tr("iz_is_1"), command=self.from_editor,
                   style="Smooth.TButton").pack(fill="x", pady=2)
        ttk.Button(right, text=tr("iz_is_2"), command=self.from_editor2,
                   style="Smooth.TButton").pack(fill="x", pady=2)
        ttk.Button(right, text=tr("v_is_1"), command=self.to_editor,
                   style="Smooth.TButton").pack(fill="x", pady=2)
        ttk.Button(right, text=tr("zagruzit"),
                   command=self.load_file,
                   style="Smooth.TButton").pack(fill="x", pady=2)
        ttk.Button(right, text=tr("sohranit_png_2"),
                   command=self.save_file,
                   style="Smooth.TButton").pack(fill="x", pady=2)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=8)

        info = ("◀ ▶ — листать плитки\n"
                "Зум ×1/×2/×4/×8 — размер\n"
                "Fit — вписать в окно\n\n"
                "Три режима:\n"
                "🧠 BrainPiet — 1 клетка = 1 символ BF\n"
                "🟦 BlockPiet — 2×2 = 1 слово Python\n"
                "🎨 Piet++ — codel-мозаика")
        ttk.Label(right, text=info, justify="left",
                  font=("Segoe UI", 8)).pack(anchor="w")

        self._pick(18)
        self.set_mode("PIET++")

    # ==================================================================
    #  РЕЖИМЫ
    # ==================================================================
    def set_mode(self, mode: str):
        if mode not in MODES:
            return
        self._mode = mode
        for m, btn in self._mode_btns.items():
            if m == mode:
                btn.state(["pressed"])
            else:
                btn.state(["!pressed"])
        self._render()

    # ==================================================================
    #  РЕНДЕР
    # ==================================================================
    def _render(self):
        """Диспетчер: вызывает отрисовщик по текущему режиму."""
        self.canvas.delete("all")
        if self._mode == "BRAINPIET2D":
            self._render_brainpiet2d()
        elif self._mode == "BLOCKPIET2D":
            self._render_blockpiet2d()
        else:
            self._render_piet()


    def _update_buttons(self):
        n = len(self._tiles)
        if n:
            self.tile_lbl.config(text=f"{self._tile_idx + 1}/{n}")
        else:
            self.tile_lbl.config(text="—/—")

    # ---------- BRAINPIET ----------
    def _render_brainpiet(self):
        if not self._tiles:
            self._render_empty("🧠 BrainPiet")
            return
        tile_b64 = self._tiles[self._tile_idx]
        try:
            raw = base64.b64decode(tile_b64)
            w, h, px = _decode_png(raw)
        except Exception as e:
            self._render_error(f"BrainPiet: {e}")
            return

        cell = max(6, self._zoom * 8)
        pad = 8
        for y in range(h):
            for x in range(w):
                rgb = px[y][x]
                hexc = "#%02X%02X%02X" % rgb
                x1, y1 = pad + x * cell, pad + y * cell
                self.canvas.create_rectangle(
                    x1, y1, x1 + cell, y1 + cell,
                    fill=hexc, outline="#333")
                ch = BRAINPIET_CHARS.get(hexc)
                if ch and ch != " " and cell >= 8:
                    self.canvas.create_text(
                        x1 + cell // 2, y1 + cell // 2,
                        text=ch, font=("Consolas", max(8, cell - 4)),
                        fill="#FFF" if hexc == "#000000" else "#000")

        total_w = pad * 2 + w * cell
        total_h = pad * 2 + h * cell
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.header_lbl.config(text=f"🧠 BrainPiet · {w}×{h} · зум ×{self._zoom}")
        self._update_buttons()

    # ---------- BLOCKPIET ----------
    def _render_blockpiet(self):
        if not self._tiles:
            self._render_empty("🟦 BlockPiet")
            return
        tile_b64 = self._tiles[self._tile_idx]
        try:
            raw = base64.b64decode(tile_b64)
            w, h, px = _decode_png(raw)
        except Exception as e:
            self._render_error(f"BlockPiet: {e}")
            return

        rows_blocks = h // 2
        cols_blocks = w // 2
        cell = max(32, self._zoom * 24)
        pad = 12
        half = cell // 2

        for rb in range(rows_blocks):
            for cb in range(cols_blocks):
                x, y = cb * 2, rb * 2
                c_tl = px[y][x]
                c_tr = px[y][x + 1]
                c_bl = px[y + 1][x]
                c_br = px[y + 1][x + 1]
                if (c_tl == (255, 255, 255) and c_tr == (255, 255, 255)
                        and c_bl == (255, 255, 255)
                        and c_br == (255, 255, 255)):
                    continue

                x1 = pad + cb * cell
                y1 = pad + rb * cell
                x2, y2 = x1 + cell, y1 + cell

                self.canvas.create_rectangle(
                    x1, y1, x1 + half, y1 + half,
                    fill="#%02X%02X%02X" % c_tl, outline="#888")
                self.canvas.create_rectangle(
                    x1 + half, y1, x2, y1 + half,
                    fill="#%02X%02X%02X" % c_tr, outline="#888")
                self.canvas.create_rectangle(
                    x1, y1 + half, x1 + half, y2,
                    fill="#%02X%02X%02X" % c_bl, outline="#888")
                self.canvas.create_rectangle(
                    x1 + half, y1 + half, x2, y2,
                    fill="#%02X%02X%02X" % c_br, outline="#888")

                type_idx = PIET_HEX_TO_IDX.get("#%02X%02X%02X" % c_tl, -1)
                if 0 <= type_idx < len(BLOCKPIET_TYPES) and cell >= 32:
                    label = BLOCKPIET_TYPES[type_idx]
                    self.canvas.create_text(
                        x1 + cell // 2, y2 + 8,
                        text=label, font=("Consolas", 8),
                        fill="#DDD", anchor="n")

        total_w = pad * 2 + cols_blocks * cell
        total_h = pad * 2 + rows_blocks * (cell + 18)
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.header_lbl.config(
            text=f"🟦 BlockPiet · {cols_blocks}×{rows_blocks} блоков · "
                 f"зум ×{self._zoom}")
        self._update_buttons()

    # ---------- PIET++ ----------
    # ==============================================================
    #  BRAINPIET 2D
    # ==============================================================
    def _render_brainpiet2d(self):
        if not self._tiles:
            self._render_empty("🧠² BrainPiet 2D")
            return
        try:
            raw = base64.b64decode(self._tiles[self._tile_idx])
            w, h, px = _decode_png(raw)
        except Exception as e:
            self._render_error(f"BrainPiet 2D: {e}")
            return

        cell = max(8, self._zoom * 12)
        pad = 8

        brain_map = {
            (255,192,192): ">", (192,255,192): "<",
            (255,0,0): "+",     (0,255,0): "-",
            (0,0,255): ".",     (0,255,255): ",",
            (255,255,0): "[",   (255,0,255): "]",
            (192,0,0): "v",     (192,192,0): "^",
            (0,192,192): "R",   (0,192,0): "L",
            (0,0,0): "#",       (255,255,255): "",
        }
        for y in range(h):
            for x in range(w):
                rgb = px[y][x]
                hexc = "#%02X%02X%02X" % rgb
                x1, y1 = pad + x * cell, pad + y * cell
                x2, y2 = x1 + cell, y1 + cell
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=hexc, outline="#333")
                ch = brain_map.get(rgb, "")
                if ch and cell >= 10:
                    fg = "#FFF" if rgb == (0,0,0) else "#000"
                    self.canvas.create_text(
                        (x1+x2)//2, (y1+y2)//2,
                        text=ch, font=("Consolas", max(8, cell-4)),
                        fill=fg)

        total_w = pad * 2 + w * cell
        total_h = pad * 2 + h * cell
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.header_lbl.config(
            text=f"🧠² BrainPiet 2D · {w}×{h} · зум ×{self._zoom}")
        self._update_buttons()

    # ==============================================================
    #  BLOCKPIET 2D
    # ==============================================================
    def _render_blockpiet2d(self):
        if not self._tiles:
            self._render_empty("🟦² BlockPiet 2D")
            return
        try:
            raw = base64.b64decode(self._tiles[self._tile_idx])
            w, h, px = _decode_png(raw)
        except Exception as e:
            self._render_error(f"BlockPiet 2D: {e}")
            return

        rows_blocks = h // 2
        cols_blocks = w // 2
        cell = max(24, self._zoom * 24)
        pad = 12
        block_size = cell * 2

        for rb in range(rows_blocks):
            for cb in range(cols_blocks):
                x = cb * 2
                y = rb * 2
                tl = px[y][x]
                tr = px[y][x + 1]
                bl = px[y + 1][x]
                br = px[y + 1][x + 1]
                if (tl == (255,255,255) and tr == (255,255,255)
                        and bl == (255,255,255) and br == (255,255,255)):
                    continue

                x1 = pad + cb * block_size
                y1 = pad + rb * (block_size + 20)
                x2, y2 = x1 + block_size, y1 + block_size

                self.canvas.create_rectangle(
                    x1, y1, x1+cell, y1+cell,
                    fill="#%02X%02X%02X" % tl, outline="#888")
                self.canvas.create_rectangle(
                    x1+cell, y1, x2, y1+cell,
                    fill="#%02X%02X%02X" % tr, outline="#888")
                self.canvas.create_rectangle(
                    x1, y1+cell, x1+cell, y2,
                    fill="#%02X%02X%02X" % bl, outline="#888")
                self.canvas.create_rectangle(
                    x1+cell, y1+cell, x2, y2,
                    fill="#%02X%02X%02X" % br, outline="#888")

                if cell >= 20:
                    cmd = _rgb_to_cmd(tl)
                    self.canvas.create_text(
                        x1 + block_size // 2, y2 + 10,
                        text=cmd, font=("Consolas", 9),
                        fill="#DDD", anchor="n")

        total_w = pad * 2 + cols_blocks * block_size
        total_h = pad * 2 + rows_blocks * (block_size + 20)
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.header_lbl.config(
            text=f"🟦² BlockPiet 2D · "
                 f"{cols_blocks}×{rows_blocks} блоков · зум ×{self._zoom}")
        self._update_buttons()

    def _render_piet(self):
        if self._png_pil is None:
            return
        w, h = self._png_dims if self._png_dims != (0, 0) else (1, 1)
        z = self._zoom
        if z == 0:
            cw = max(self.canvas.winfo_width() or 500, 200)
            ch = max(self.canvas.winfo_height() or 500, 200)
            sx = cw / max(self._png_pil.width, 1)
            sy = ch / max(self._png_pil.height, 1)
            z = max(1, int(min(sx, sy)))

        self.header_lbl.config(text=f"🎨 Piet++ · {w}×{h} · зум ×{z}")

        im = self._png_pil
        if z > 1:
            im = im.resize((im.width * z, im.height * z), Image.NEAREST)
        self._png_image = ImageTk.PhotoImage(im)
        self.canvas.create_image(0, 0, image=self._png_image, anchor="nw")
        self.canvas.config(scrollregion=(0, 0, im.width, im.height))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self._update_buttons()

    # ---------- пусто / ошибка ----------
    def _render_empty(self, mode_name):
        self.canvas.create_text(
            250, 100,
            text=f"{mode_name}\n\nПлиток нет.\n"
                 f"Открой вкладку «Перевод»,\n"
                 f"выбери язык, нажми F5,\n"
                 f"потом «⬅ Из ИС 2».",
            font=("Segoe UI", 11), fill="#888", justify="center")
        self.header_lbl.config(text=f"{mode_name} · пусто")
        self._update_buttons()

    def _render_error(self, msg):
        self.canvas.create_text(
            250, 100, text=msg, font=("Segoe UI", 11),
            fill="#f66", width=400)
        self.header_lbl.config(text=tr("oshibka_2"))

    # ---------- grid (редактор) ----------
    def _render_grid(self):
        self.canvas.delete("all")
        for y in range(GRID):
            for x in range(GRID):
                x1, y1 = x * CELL, y * CELL
                self.canvas.create_rectangle(
                    x1, y1, x1 + CELL, y1 + CELL,
                    fill=PIET_COLORS[self.grid[y][x]],
                    outline="", tags=(f"cell_{x}_{y}",))
        for i in range(GRID + 1):
            self.canvas.create_line(i * CELL, 0, i * CELL, GRID * CELL,
                                     fill="#555")
            self.canvas.create_line(0, i * CELL, GRID * CELL, i * CELL,
                                     fill="#555")
        self.header_lbl.config(text=f"Piet {GRID}×{GRID}")
        self._update_buttons()

    # ==================================================================
    #  РИСОВАНИЕ GRID
    # ==================================================================
    def _cell(self, e):
        return e.x // CELL, e.y // CELL

    def _paint(self, x, y):
        if 0 <= x < GRID and 0 <= y < GRID:
            if self.grid[y][x] != self.active_color:
                self.grid[y][x] = self.active_color
                self.canvas.itemconfig(f"cell_{x}_{y}",
                                        fill=PIET_COLORS[self.active_color])

    def _on_click(self, e):
        if self._png_mode:
            return
        self._painting = True
        x, y = self._cell(e)
        self._paint(x, y)

    def _on_drag(self, e):
        if self._png_mode:
            return
        if self._painting:
            x, y = self._cell(e)
            self._paint(x, y)

    def _on_release(self, e):
        self._painting = False

    def _pick(self, idx):
        self.active_color = idx
        self.active_preview.itemconfig(self.active_rect,
                                        fill=PIET_COLORS[idx])
        self.active_label.config(text=f"{NAMES[idx]} ({idx})")
        for i, btn in enumerate(self._palette_btns):
            hl = "#ff00ff" if i == idx else "#666"
            btn.config(highlightbackground=hl, highlightcolor=hl)

    # ==================================================================
    #  ЗУМ / НАВИГАЦИЯ
    # ==================================================================
    def _tile_prev(self):
        if not self._tiles:
            return
        self._load_tile(self._tile_idx - 1)
        self._render()

    def _tile_next(self):
        if not self._tiles:
            return
        self._load_tile(self._tile_idx + 1)
        self._render()

    def _set_zoom(self, z):
        self._zoom = 2 if z == 0 else z
        self._render()

    def _load_tile(self, idx):
        if not self._tiles:
            return False
        idx = max(0, min(idx, len(self._tiles) - 1))
        self._tile_idx = idx
        try:
            raw = base64.b64decode(self._tiles[idx])
            im = Image.open(io.BytesIO(raw))
        except Exception:
            return False
        self._png_dims = (im.width, im.height)
        self._png_pil = im.convert("RGB") if im.mode != "RGB" else im
        self._png_image = ImageTk.PhotoImage(self._png_pil)
        self._png_base64 = "|".join(self._tiles)
        self._png_mode = True
        return True

    # ==================================================================
    #  ЗАГРУЗКА / ВЫГРУЗКА
    # ==================================================================
    def _toggle_mode(self):
        if self._png_pil is None:
            self.app.log("$ Piet: PNG нет")
            return
        self._png_mode = not self._png_mode
        self._render()

    def _enter_png(self, b64):
        if not HAS_PIL:
            self.app.log("! Piet: pip install Pillow")
            return False
        parts = [p.strip() for p in b64.split("|") if p.strip()]
        valid = []
        for p in parts:
            try:
                raw = base64.b64decode(p)
                if raw[:8] == b"\x89PNG\r\n\x1a\n":
                    valid.append(p)
            except Exception:
                continue
        if not valid:
            return False
        self._tiles = valid
        self._tile_idx = 0
        return self._load_tile(0)

    def to_text(self):
        if self._png_mode and self._png_base64:
            return self._png_base64
        return "\n".join(
            "".join(CHARS[self.grid[y][x]] for x in range(GRID))
            for y in range(GRID))

    def from_text(self, text):
        text = text or ""
        stripped = text.strip()
        parts = [p.strip() for p in stripped.split("|") if p.strip()]
        is_b64 = (len(parts) >= 1
                  and all(len(p) > 50
                          and all(c.isalnum() or c in "+/=" for c in p[:200])
                          for p in parts)
                  and not any(c in text for c in "│─╮╭╰╯"))
        if is_b64 and self._enter_png(stripped):
            self._auto_detect_mode()
            self._render()
            return

        # обычный grid-режим
        self._png_mode = False
        self._png_image = None
        self._png_pil = None
        self._png_base64 = None
        self._tiles = []
        self._tile_idx = 0
        self.grid = [[18] * GRID for _ in range(GRID)]
        lines = [ln for ln in text.splitlines() if ln.strip()]
        for y in range(GRID):
            if y >= len(lines):
                break
            ln = lines[y]
            for x in range(GRID):
                if x >= len(ln):
                    break
                idx = CHARS_BY_SYM.get(ln[x])
                if idx is not None:
                    self.grid[y][x] = idx
        self._render()

    def clear(self):
        self._png_mode = False
        self._png_image = None
        self._png_pil = None
        self._png_base64 = None
        self._png_dims = (0, 0)
        self._tiles = []
        self._tile_idx = 0
        self.grid = [[18] * GRID for _ in range(GRID)]
        self._render()

    # ==================================================================
    #  ИНТЕГРАЦИЯ
    # ==================================================================
    def _auto_detect_mode(self):
        """Автодетект по форме PNG."""
        if not self._tiles:
            return
        try:
            import struct
            raw = base64.b64decode(self._tiles[0])
            if raw[:8] != b"\x89PNG\r\n\x1a\n":
                return
            w, h = struct.unpack(">II", raw[16:24])
        except Exception:
            return

        # BrainPiet 2D — serpentine, H всегда НЕЧЁТНОЕ (2N-1)
        # BlockPiet 2D — блоки 2×2, H чётное и маленькое (2, 4, 6...)
        # Piet++ — H = 16 (стандартная высота)
        if h % 2 == 1:
            detected = "BRAINPIET2D"
        elif h <= 8:
            detected = "BLOCKPIET2D"
        else:
            detected = "PIET++"

        if detected != self._mode:
            self._mode = detected
            for m, btn in self._mode_btns.items():
                btn.state(["pressed"] if m == detected else ["!pressed"])
            if self.app:
                self.app.log(
                    f"$ Piet Canvas: автодетект → {detected} ({w}×{h})")

        # BrainPiet 2D — ширина 8 или 16, но с рамкой ROT (визуально
        # широкие ряды от 8×N до 32×N). Пока не различаем точно,
        # используем эвристику по цвету: BrainPiet 2D использует
        # только BF-цвета (10 штук).
        bf_colors = {
            (255, 192, 192), (192, 255, 192), (255, 0, 0), (0, 255, 0),
            (0, 0, 255), (0, 255, 255), (255, 255, 0), (255, 0, 255),
            (192, 0, 0), (192, 192, 0), (0, 192, 192), (0, 192, 0),
            (0, 0, 0), (255, 255, 255),
        }
        try:
            _, _, px = _decode_png(raw)
            seen = set()
            for y in range(min(h, 8)):
                for x in range(w):
                    seen.add(px[y][x])
            if seen <= bf_colors:
                detected = "BRAINPIET2D"
            else:
                detected = "BLOCKPIET2D"
        except Exception:
            detected = "PIET++"

        # Если ширина большая — Piet++ (мозаика)
        if w > 32:
            detected = "PIET++"

        if detected != self._mode:
            self._mode = detected
            for m, btn in self._mode_btns.items():
                btn.state(["pressed"] if m == detected else ["!pressed"])
            if self.app:
                self.app.log(
                    f"$ Piet Canvas: автодетект → {detected} ({w}×{h})")


    def from_editor2(self):
        try:
            text = self.app.output.get("1.0", "end-1c")
            self.from_text(text)
            n = len(self._tiles)
            self.app.log(f"$ Piet: из ИС 2 ({n} плиток, режим {self._mode})")
        except Exception as e:
            self.app.log(f"! Piet: {e}")

    def from_editor(self):
        try:
            text = self.app.editor.get("1.0", "end-1c")
            self.from_text(text)
            n = len(self._tiles)
            self.app.log(f"$ Piet: из ИС 1 ({n} плиток)")
        except Exception as e:
            self.app.log(f"! Piet: {e}")

    def to_editor(self):
        try:
            text = self.to_text()
            self.app.editor.delete("1.0", "end")
            self.app.editor.insert("1.0", text)
            self.app.log("$ Piet → ИС 1")
        except Exception as e:
            self.app.log(f"! Piet: {e}")

    def load_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Piet / PNG", "*.piet *.png"), ("Все", "*.*")])
        if not path:
            return
        try:
            if path.lower().endswith(".png"):
                with open(path, "rb") as f:
                    raw = f.read()
                self.from_text(base64.b64encode(raw).decode("ascii"))
                self.app.log(f"$ Piet: загружен {path}")
            else:
                with open(path, encoding="utf-8") as f:
                    self.from_text(f.read())
                self.app.log(f"$ Piet: загружено {path}")
        except Exception as e:
            self.app.log(f"! Piet: {e}")

    def save_file(self):
        if not self._tiles:
            self.app.log("$ Piet: нет плиток")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                             filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            raw = base64.b64decode(self._tiles[self._tile_idx])
            with open(path, "wb") as f:
                f.write(raw)
            self.app.log(f"$ Piet: плитка {self._tile_idx + 1} → {path}")
        except Exception as e:
            self.app.log(f"! Piet: {e}")


# ======================================================================
#  PNG decoder
# ======================================================================
def _decode_png(raw):
    import struct
    import zlib
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not PNG")
    pos, idat = 8, b""
    W = H = color_type = None
    while pos < len(raw):
        ln = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        cdata = raw[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if ctype == b"IHDR":
            W, H, _bd, color_type, _, _, _ = struct.unpack(
                ">IIBBBBB", cdata)
        elif ctype == b"IDAT":
            idat += cdata
        elif ctype == b"IEND":
            break
    if W is None:
        raise ValueError("no IHDR")
    raw_data = zlib.decompress(idat)
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 3)
    stride = W * ch
    prev = bytearray(stride)
    pixels = []
    offset = 0
    for _y in range(H):
        ft = raw_data[offset]; offset += 1
        line = bytearray(raw_data[offset:offset + stride]); offset += stride
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if ft == 1: line[i] = (line[i] + a) & 0xFF
            elif ft == 2: line[i] = (line[i] + b) & 0xFF
            elif ft == 3: line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        row = []
        for x in range(W):
            base = x * ch
            row.append((line[base], line[base + 1], line[base + 2]))
        pixels.append(row)
        prev = line
    return W, H, pixels


# ======================================================================
#  Вспомогательные функции для BlockPiet 2D
# ======================================================================
_BLOCK_CMDS = [
    "PUSH", "POP", "ADD", "SUB", "MUL", "DIV", "MOD", "DUP",
    "SWAP", "LOAD", "STORE", "OUT_NUM", "OUT_CHAR",
    "IN_NUM", "IN_CHAR", "JMP", "JZ", "JNZ", "NOP", "HALT",
]


def _rgb_to_idx(rgb):
    """Преобразует RGB → индекс палитры 0..19."""
    pal = [
        (255,192,192),(255,255,192),(192,255,192),(192,255,255),
        (192,192,255),(255,192,255),
        (255,0,0),(255,255,0),(0,255,0),(0,255,255),
        (0,0,255),(255,0,255),
        (192,0,0),(192,192,0),(0,192,0),(0,192,192),
        (0,0,192),(192,0,192),
        (255,255,255),(0,0,0),
    ]
    for i, c in enumerate(pal):
        if c == rgb:
            return i
    return 18


def _rgb_to_cmd(rgb):
    """Преобразует RGB в имя команды BlockPiet 2D."""
    idx = _rgb_to_idx(rgb)
    if 0 <= idx < len(_BLOCK_CMDS):
        return _BLOCK_CMDS[idx]
    return "?"

