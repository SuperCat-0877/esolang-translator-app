# ui/editor.py
import tkinter as tk
import re

from core.themes import syntax_palette
from core.registry import registry


class HighlightedText(tk.Text):
    def __init__(self, parent, app, **kw):
        super().__init__(parent, **kw)
        self.app = app
        self._lang = None
        self._setup_tags()
        self.bind("<KeyRelease>", self._on_change)

    def _setup_tags(self):
        for name, color in syntax_palette(self.app.theme).items():
            self.tag_configure(name, foreground=color)

    def update_colors(self, theme):
        for name, color in syntax_palette(theme).items():
            self.tag_configure(name, foreground=color)
        self.highlight()

    def set_language(self, name):
        self._lang = name
        self.highlight()

    def _on_change(self, event=None):
        if event and event.keysym in (
            "Up", "Down", "Left", "Right",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Escape",
            "Tab", "Home", "End", "Prior", "Next",
        ):
            return
        self.highlight()

    def highlight(self):
        lang = registry.get(self._lang)
        if not lang:
            return

        text = self.get("1.0", "end-1c")

        # Чистим все теги
        for name in ("keyword", "string", "number",
                     "comment", "function", "type"):
            self.tag_remove(name, "1.0", "end")

        # ------------------------------------------------------------------
        #  1. Строковые литералы — запоминаем их диапазоны
        #     (это нужно, чтобы не путать # и // внутри строк с комментариями)
        # ------------------------------------------------------------------
        string_ranges = []
        for m in re.finditer(r'"[^"\n]*"|\'[^\'\n]*\'', text):
            string_ranges.append((m.start(), m.end()))
            self.tag_add("string",
                         f"1.0 + {m.start()}c",
                         f"1.0 + {m.end()}c")

        def in_string(pos):
            """True, если позиция pos внутри строкового литерала."""
            return any(s <= pos < e for s, e in string_ranges)

        # ------------------------------------------------------------------
        #  2. Комментарии — только ВНЕ строк
        # ------------------------------------------------------------------
        if lang.comment_regex:
            for m in re.finditer(lang.comment_regex, text):
                if not in_string(m.start()):
                    self.tag_add("comment",
                                 f"1.0 + {m.start()}c",
                                 f"1.0 + {m.end()}c")

        # ------------------------------------------------------------------
        #  3. Числа — только вне строк
        # ------------------------------------------------------------------
        for m in re.finditer(r'\b\d+(\.\d+)?\b', text):
            if not in_string(m.start()):
                self.tag_add("number",
                             f"1.0 + {m.start()}c",
                             f"1.0 + {m.end()}c")

        # ------------------------------------------------------------------
        #  4. Ключевые слова — только вне строк
        # ------------------------------------------------------------------
        for kw in lang.keywords:
            for m in re.finditer(r'\b' + re.escape(kw) + r'\b', text):
                if not in_string(m.start()):
                    self.tag_add("keyword",
                                 f"1.0 + {m.start()}c",
                                 f"1.0 + {m.end()}c")

        # ------------------------------------------------------------------
        #  5. Типы — только вне строк
        # ------------------------------------------------------------------
        for tp in lang.types:
            for m in re.finditer(r'\b' + re.escape(tp) + r'\b', text):
                if not in_string(m.start()):
                    self.tag_add("type",
                                 f"1.0 + {m.start()}c",
                                 f"1.0 + {m.end()}c")

        # ------------------------------------------------------------------
        #  6. Функции: имя перед '('
        # ------------------------------------------------------------------
        for m in re.finditer(r'\b(\w+)\s*\(', text):
            if not in_string(m.start(1)):
                self.tag_add("function",
                             f"1.0 + {m.start(1)}c",
                             f"1.0 + {m.end(1)}c")