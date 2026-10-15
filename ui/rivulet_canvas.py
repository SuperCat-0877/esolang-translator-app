# ui/rivulet_canvas.py
import tkinter as tk
from tkinter import ttk
from core.registry import registry

EMPTY = " "


# Какие стороны клетки соединяет каждый глиф.
GLYPH_SIDES = {
    "─": ("L", "R"),
    "│": ("U", "D"),
    "╮": ("L", "D"),
    "╭": ("R", "D"),
    "╰": ("R", "U"),
    "╯": ("L", "U"),
    "╵": ("D",),
    "╷": ("U",),
    "╶": ("R",),
    "╴": ("L",),
}

# Палитра (Solarized)
PALETTE = [
    "#dc322f",  # красный
    "#268bd2",  # синий
    "#859900",  # зелёный
    "#b58900",  # жёлтый
    "#d33682",  # фиолетовый
    "#2aa198",  # бирюзовый
    "#cb4b16",  # оранжевый
    "#6c71c4",  # индиго
]

# Фиксированные цвета для типа глифа
COLOR_START = "#28a745"   # ╵
COLOR_END   = "#dc3545"   # ╷
COLOR_MARK  = "#3a7bd5"   # ╶ ╴
COLOR_LINE  = "#e8e8e8"   # всё остальное


class RivuletCanvasTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.cols = 120
        self.rows = 120
        self.cell_w = 16
        self.cell_h = 16

        self.grid = [[EMPTY] * self.cols for _ in range(self.rows)]
        self._last_drag_cell = None

        self._build_ui()
        self._redraw_grid()

    # ------------------------------------------------------------
    def _build_ui(self):
        # ---------- ТУЛБАР 1: инструменты ----------
        tb1 = ttk.Frame(self.parent, padding=(0, 0, 0, 4))
        tb1.pack(fill="x")

        ttk.Label(tb1, text="Инструмент:").pack(side="left", padx=(0, 5))

        self.tool = tk.StringVar(value="auto")
        tools = [
            ("Авто-линия", "auto"),
            ("Карандаш ─", "line_h"),
            ("Карандаш │", "line_v"),
            ("Угол ╮", "c_ld"),
            ("Угол ╭", "c_rd"),
            ("Угол ╰", "c_ru"),
            ("Угол ╯", "c_lu"),
            ("Начало ╵", "start"),
            ("Конец ╷", "end"),
            ("Маркер ╶/╴", "loc"),
            ("Стереть", "erase"),
        ]
        for label, val in tools:
            ttk.Radiobutton(tb1, text=label, value=val,
                            variable=self.tool).pack(side="left", padx=2)

        ttk.Button(tb1, text="Очистить всё",
                   command=self.clear_all).pack(side="right")

        # ---------- ТУЛБАР 2: примеры + режим цвета ----------
        tb2 = ttk.Frame(self.parent, padding=(0, 0, 0, 6))
        tb2.pack(fill="x")

        ttk.Label(tb2, text="Пример:").pack(side="left", padx=(0, 5))

        self.tpl_var = tk.StringVar(value="")
        self.tpl_cb = ttk.Combobox(tb2, textvariable=self.tpl_var,
                                    values=[], state="readonly", width=40)
        self.tpl_cb.pack(side="left", padx=(0, 5))
        self.tpl_cb.bind("<<ComboboxSelected>>", self._on_template_selected)

        ttk.Button(tb2, text="Обновить список",
                   command=self._refresh_templates).pack(side="left", padx=(0, 15))

        ttk.Label(tb2, text="Цвет:").pack(side="left", padx=(0, 5))
        self.color_mode = tk.StringVar(value="by_component")
        modes = [
            ("по компоненту", "by_component"),
            ("по длине",      "by_length"),
            ("по координатам","by_coords"),
            ("по старту",     "by_start"),
            ("по типу",       "by_type"),
            ("однотонный",    "mono"),
        ]
        self.color_cb = ttk.Combobox(tb2, textvariable=self.color_mode,
                                      values=[m[0] for m in modes],
                                      state="readonly", width=16)
        self.color_cb.current(0)
        self.color_cb.pack(side="left", padx=(0, 5))
        self.color_cb.bind("<<ComboboxSelected>>",
                            lambda e: self._redraw_grid())
        self._modes = dict(modes)

        # ---------- ХОЛСТ ----------
        wrapper = ttk.Frame(self.parent)
        wrapper.pack(fill="both", expand=True)
        wrapper.grid_rowconfigure(0, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(wrapper, bg="#1e1e1e",
                                 highlightthickness=1,
                                 highlightbackground="#333")
        vbar = ttk.Scrollbar(wrapper, orient="vertical",
                             command=self.canvas.yview)
        hbar = ttk.Scrollbar(wrapper, orient="horizontal",
                             command=self.canvas.xview)
        self.canvas.config(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<MouseWheel>", self._on_wheel)

        # ---------- КНОПКИ ВНИЗУ ----------
        btns = ttk.Frame(self.parent, padding=(0, 6, 0, 0))
        btns.pack(fill="x")
        # === IS2-BUTTON ===
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
                   command=self.clear_all).pack(side="left", padx=(0, 5))

        self._refresh_templates()

    # ------------------------------------------------------------
    #  ПРИМЕРЫ
    # ------------------------------------------------------------
    def _refresh_templates(self):
        lang = registry.get("rivulet")
        if not lang:
            self.tpl_cb["values"] = []
            return
        names = list(lang.templates.keys())
        self.tpl_cb["values"] = names
        if names:
            self.tpl_var.set(names[0])
            self._on_template_selected()

    def _on_template_selected(self, event=None):
        name = self.tpl_var.get()
        if not name:
            return
        lang = registry.get("rivulet")
        if not lang:
            return
        code = lang.templates.get(name)
        if code is None:
            return
        self.from_text(code)
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    # ------------------------------------------------------------
    #  Работа с холстом
    # ------------------------------------------------------------
    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _cell_at(self, x, y):
        cx = int(x // self.cell_w)
        cy = int(y // self.cell_h)
        if 0 <= cx < self.cols and 0 <= cy < self.rows:
            return cx, cy
        return None

    def _on_left_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        cell = self._cell_at(x, y)
        if not cell:
            return
        self._place(cell[0], cell[1])
        self._redraw_grid()
        self._last_drag_cell = cell

    def _on_right_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        cell = self._cell_at(x, y)
        if not cell:
            return
        self.grid[cell[1]][cell[0]] = EMPTY
        self._redraw_grid()

    def _on_drag(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        cell = self._cell_at(x, y)
        if not cell or cell == self._last_drag_cell:
            return
        self._place(cell[0], cell[1])
        self._redraw_grid()
        self._last_drag_cell = cell

    def _place(self, x, y):
        tool = self.tool.get()
        if tool == "erase":
            self.grid[y][x] = EMPTY
            return
        if tool == "auto":
            ch = self._auto_char(x, y)
        elif tool == "line_h":
            ch = "─"
        elif tool == "line_v":
            ch = "│"
        elif tool == "c_ld":
            ch = "╮"
        elif tool == "c_rd":
            ch = "╭"
        elif tool == "c_ru":
            ch = "╰"
        elif tool == "c_lu":
            ch = "╯"
        elif tool == "start":
            ch = "╵"
        elif tool == "end":
            ch = "╷"
        elif tool == "loc":
            ch = "╶"
        else:
            ch = "─"
        self.grid[y][x] = ch

    def _auto_char(self, x, y):
        def has(cx, cy):
            if 0 <= cx < self.cols and 0 <= cy < self.rows:
                return self.grid[cy][cx].strip() != ""
            return False

        left = has(x - 1, y)
        right = has(x + 1, y)
        up = has(x, y - 1)
        down = has(x, y + 1)

        connections = []
        if left:  connections.append("left")
        if right: connections.append("right")
        if up:    connections.append("up")
        if down:  connections.append("down")

        key = tuple(sorted(connections))
        lookup = {
            ("left", "right"): "─",
            ("down", "up"):    "│",
            ("down", "left"):  "╮",
            ("down", "right"): "╭",
            ("right", "up"):   "╰",
            ("left", "up"):    "╯",
        }
        if key in lookup:
            return lookup[key]
        if len(connections) == 1:
            d = connections[0]
            if d in ("left", "right"): return "─"
            if d in ("up", "down"):    "│"
            return "│"
        return "─"

    # ------------------------------------------------------------
    #  СВЯЗНЫЕ КОМПОНЕНТЫ (нити)
    # ------------------------------------------------------------
    def _compute_components(self):
        """Возвращает:
            comp       — dict[(x,y)] = component_id
            comp_info  — dict[component_id] = {
                            'size': N, 'start': (x0,y0), 'glyphs': set()
                         }
        """
        comp = {}
        comp_info = {}
        next_id = 0

        def sides(ch):
            return GLYPH_SIDES.get(ch[0], ())

        for sy in range(self.rows):
            for sx in range(self.cols):
                if self.grid[sy][sx] == EMPTY:
                    continue
                if (sx, sy) in comp:
                    continue

                # Обходим одну нить через BFS/DFS
                stack = [(sx, sy)]
                member = []
                glyphs = set()
                while stack:
                    x, y = stack.pop()
                    if (x, y) in comp:
                        continue
                    comp[(x, y)] = next_id
                    member.append((x, y))
                    glyphs.add(self.grid[y][x][0])
                    cur = sides(self.grid[y][x])

                    for nx, ny, need_cur, need_nb in (
                        (x + 1, y, "R", "L"),
                        (x - 1, y, "L", "R"),
                        (x, y + 1, "D", "U"),
                        (x, y - 1, "U", "D"),
                    ):
                        if not (0 <= nx < self.cols and 0 <= ny < self.rows):
                            continue
                        if self.grid[ny][nx] == EMPTY:
                            continue
                        if (nx, ny) in comp:
                            continue
                        nb = sides(self.grid[ny][nx])
                        if need_cur in cur and need_nb in nb:
                            stack.append((nx, ny))

                # Метрики нити
                min_x = min(p[0] for p in member)
                min_y = min(p[1] for p in member)
                comp_info[next_id] = {
                    "size": len(member),
                    "start": (min_x, min_y),
                    "glyphs": glyphs,
                }
                next_id += 1

        return comp, comp_info

    # ------------------------------------------------------------
    #  РАСКРАСКА
    # ------------------------------------------------------------
    def _color_for(self, x, y, ch, cid, info):
        """Возвращает цвет для клетки (x, y)."""
        mode = self._modes.get(self.color_mode.get(), "by_component")

        # 1. Однотонный
        if mode == "mono":
            first = ch[0]
            if first == "╵": return COLOR_START
            if first == "╷": return COLOR_END
            if first in "╶╴": return COLOR_MARK
            return COLOR_LINE

        # 2. По типу глифа (старт/конец/маркер/линия)
        if mode == "by_type":
            first = ch[0]
            if first == "╵": return COLOR_START
            if first == "╷": return COLOR_END
            if first in "╶╴": return COLOR_MARK
            return COLOR_LINE

        # 3. По компоненту (разные нити — разные цвета)
        if mode == "by_component":
            return PALETTE[cid % len(PALETTE)]

        # 4. По длине нити: чем длиннее — тем дальше по палитре
        if mode == "by_length":
            size = info.get("size", 1)
            return PALETTE[size % len(PALETTE)]

        # 5. По координатам стартовой клетки нити
        if mode == "by_start":
            sx, sy = info.get("start", (0, 0))
            return PALETTE[(sx + sy) % len(PALETTE)]

        # 6. По координатам самой клетки
        if mode == "by_coords":
            return PALETTE[(x + y) % len(PALETTE)]

        return COLOR_LINE

    # ------------------------------------------------------------
    def _redraw_grid(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        w, h = self.cell_w, self.cell_h

        # 1. Сетка
        for i in range(self.cols + 1):
            self.canvas.create_line(i * w, 0, i * w, self.rows * h,
                                    fill="#2a2a2a")
        for j in range(self.rows + 1):
            self.canvas.create_line(0, j * h, self.cols * w, j * h,
                                    fill="#2a2a2a")

        # 2. Компоненты (для раскраски)
        comp, comp_info = self._compute_components()

        # 3. Рисуем глифы
        for y in range(self.rows):
            for x in range(self.cols):
                ch = self.grid[y][x]
                if ch == EMPTY:
                    continue

                cid = comp.get((x, y), 0)
                info = comp_info.get(cid, {"size": 1, "start": (0, 0)})
                color = self._color_for(x, y, ch, cid, info)

                # Края и центр клетки
                x0 = x * w
                y0 = y * h
                x1 = x0 + w
                y1 = y0 + h
                cx = x0 + w // 2
                cy = y0 + h // 2

                # Многоуровневые (╵╵, ╵╵╵) — текстом
                if len(ch) > 1:
                    self.canvas.create_text(cx, cy, text=ch,
                                            font=("Consolas", 10),
                                            fill=color)
                    continue

                # Параметры линии: круглые концы и стыки —
                # линии сливаются без «швов» и «изломов».
                lk = {
                    "fill": color,
                    "width": 3,
                    "capstyle": tk.ROUND,
                    "joinstyle": tk.ROUND,
                }

                if ch == "─":
                    self.canvas.create_line(x0, cy, x1, cy, **lk)
                elif ch == "│":
                    self.canvas.create_line(cx, y0, cx, y1, **lk)
                elif ch == "╮":
                    # L + D: влево → центр → вниз
                    self.canvas.create_line(x0, cy, cx, cy, cx, y1, **lk)
                elif ch == "╭":
                    # R + D: вправо → центр → вниз
                    self.canvas.create_line(x1, cy, cx, cy, cx, y1, **lk)
                elif ch == "╰":
                    # R + U: вправо → центр → вверх
                    self.canvas.create_line(x1, cy, cx, cy, cx, y0, **lk)
                elif ch == "╯":
                    # L + U: влево → центр → вверх
                    self.canvas.create_line(x0, cy, cx, cy, cx, y0, **lk)
                elif ch == "╵":
                    # D: центр → вниз
                    self.canvas.create_line(cx, cy, cx, y1, **lk)
                elif ch == "╷":
                    # U: центр → вверх
                    self.canvas.create_line(cx, cy, cx, y0, **lk)
                elif ch == "╶":
                    # R: центр → вправо
                    self.canvas.create_line(cx, cy, x1, cy, **lk)
                elif ch == "╴":
                    # L: влево → центр
                    self.canvas.create_line(x0, cy, cx, cy, **lk)

        self.canvas.config(scrollregion=(0, 0, self.cols * w, self.rows * h))

    # ------------------------------------------------------------
    def to_text(self):
        lines = []
        for y in range(self.rows):
            line = "".join(self.grid[y]).rstrip()
            lines.append(line)
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)

    def from_text(self, text):
        """Загружает текст в сетку. Оставляет только глифы,
        цифры и пробелы — всё остальное превращает в пробел."""
        allowed = set("─│╮╭╰╯╵╷╶╴0123456789 ")
        lines = text.splitlines()[:self.rows]
        self.grid = [[EMPTY] * self.cols for _ in range(self.rows)]
        for y, ln in enumerate(lines):
            for x, ch in enumerate(ln[:self.cols]):
                self.grid[y][x] = ch if ch in allowed else EMPTY
        self._redraw_grid()

    def clear_all(self):
        self.grid = [[EMPTY] * self.cols for _ in range(self.rows)]
        self._redraw_grid()
        self.tpl_var.set("")

    # ------------------------------------------------------------
    # === IS2-BUTTON ===
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

    def send_to_editor(self):
        text = self.to_text()
        self.app.editor.delete("1.0", "end")
        self.app.editor.insert("1.0", text)
        self.app.tabs.select(0)
        self.app.log("$ Rivulet-код перенесён в редактор")

    def run_program(self):
        lang = registry.get("rivulet")
        if not lang:
            self.app.log("! Rivulet не зарегистрирован")
            return
        try:
            out = lang.execute(self.to_text())
            self.app.log(f"$ Rivulet вывод: {out!r}")
        except Exception as e:
            self.app.log(f"! Rivulet: {e}")