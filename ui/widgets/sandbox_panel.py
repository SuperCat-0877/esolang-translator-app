# ui/widgets/sandbox_panel.py
"""
Панель запуска кода. Используется как самостоятельный экран
и как компонент урока.

Кнопки:
  ▶ Запустить     — выполнить код (в фоне)
  🔍 Разобрать    — показать структуру кода построчно
  Очистить        — очистить поля
  Копир. вывод    — скопировать в буфер
  Сохранить…      — сохранить вывод в файл

Для Piet: код показывается как картинка (PNG) + текстовый вывод.
Для Rivulet: код-диаграмма показывается текстом + текстовый вывод.
"""
from __future__ import annotations

import base64
import io
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from core.registry import registry
from core.themes import THEMES
from ui.editor import HighlightedText
from core.i18n import t as tr

CODE_FONT = ("Consolas", 11)


class SandboxPanel(ttk.Frame):
    def __init__(self, parent, app=None,
                 initial_lang: str = "python",
                 initial_code: str = "",
                 readonly: bool = False,
                 compact: bool = False):
        super().__init__(parent)
        self.app = app
        self.readonly = readonly
        self.compact = compact
        self._theme_name = getattr(app, "theme", "dark") if app else "dark"
        self._piet_image = None
        self._running = False
        self._lang_name = initial_lang
        self._templates_map: dict[str, list[str]] = {}   # lang → [tpl_name]

        self._build()
        self.set_lang(initial_lang)
        if initial_code:
            self.set_code(initial_code)

    # ==============================================================
    def _build(self):
        self.tpl_cb = None

        if not self.compact:
            bar = ttk.Frame(self)
            bar.pack(fill="x", pady=(0, 4))

            ttk.Label(bar, text=tr("sb_lang")).pack(side="left", padx=(0, 4))
            self.lang_cb = ttk.Combobox(
                bar, values=[l.name for l in registry.all()],
                state="readonly", width=14)
            self.lang_cb.pack(side="left", padx=(0, 6))
            self.lang_cb.bind("<<ComboboxSelected>>",
                              lambda e: self._on_lang_change())

            ttk.Label(bar, text=tr("sb_tpl")).pack(side="left", padx=(0, 4))
            self.tpl_cb = ttk.Combobox(bar, values=[], state="readonly",
                                        width=30)
            self.tpl_cb.pack(side="left", padx=(0, 10))
            self.tpl_cb.bind("<<ComboboxSelected>>",
                             lambda e: self._on_tpl_change())

            self.run_btn = ttk.Button(bar, text=tr("sb_run"),
                                      command=self.on_run,
                                      style="Smooth.TButton")
            self.run_btn.pack(side="left", padx=(0, 4))

            self.exp_btn = ttk.Button(bar, text=tr("sb_explain"),
                                      command=self.on_explain,
                                      style="Smooth.TButton")
            self.exp_btn.pack(side="left", padx=(0, 4))

            self.clear_btn = ttk.Button(bar, text=tr("sb_clear"),
                                        command=self.on_clear,
                                        style="Smooth.TButton")
            self.clear_btn.pack(side="left", padx=(0, 4))

            self.copy_btn = ttk.Button(bar, text=tr("sb_copy_out"),
                                       command=self.on_copy_output,
                                       style="Smooth.TButton")
            self.copy_btn.pack(side="left", padx=(0, 4))

            self.save_btn = ttk.Button(bar, text=tr("sb_save"),
                                       command=self.on_save_output,
                                       style="Smooth.TButton")
            self.save_btn.pack(side="left")

            self.status_lbl = ttk.Label(bar, text="")
            self.status_lbl.pack(side="right")
        else:
            self.lang_cb = None
            self.run_btn = None
            self.exp_btn = None
            self.clear_btn = None
            self.copy_btn = None
            self.save_btn = None
            self.status_lbl = None

        # -------------------- тело --------------------
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)

        ed_frame = ttk.LabelFrame(body, text=tr("sb_code"), padding=4)
        ed_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        ed_frame.rowconfigure(0, weight=1)
        ed_frame.columnconfigure(0, weight=1)

        self.editor = HighlightedText(
            ed_frame, self.app or self,
            font=CODE_FONT, wrap="none", bd=0, relief="flat",
            padx=6, pady=4, undo=not self.readonly)
        self.editor.grid(row=0, column=0, sticky="nsew")

        ed_sb = ttk.Scrollbar(ed_frame, orient="vertical",
                              command=self.editor.yview)
        ed_sb.grid(row=0, column=1, sticky="ns")
        self.editor.config(yscrollcommand=ed_sb.set)

        if self.readonly:
            self.editor.config(state="disabled")

        # нижняя часть — «Вывод» + «Разбор» в закладках
        bottom = ttk.Notebook(body)
        bottom.grid(row=1, column=0, sticky="nsew")
        self.bottom = bottom

        # --- вкладка Вывод ---
        out_tab = ttk.Frame(bottom)
        bottom.add(out_tab, text=tr("sb_output_tab"))
        out_tab.rowconfigure(0, weight=1)
        out_tab.columnconfigure(0, weight=1)

        self.output = tk.Text(out_tab, font=CODE_FONT, wrap="word",
                              bd=0, relief="flat", padx=6, pady=4,
                              state="disabled", height=8)
        self.output.grid(row=0, column=0, sticky="nsew")

        out_sb = ttk.Scrollbar(out_tab, orient="vertical",
                               command=self.output.yview)
        out_sb.grid(row=0, column=1, sticky="ns")
        self.output.config(yscrollcommand=out_sb.set)

        # для piet — картинка
        self.piet_frame = ttk.Frame(out_tab)
        self.piet_label = None

        # --- вкладка Разбор ---
        exp_tab = ttk.Frame(bottom)
        bottom.add(exp_tab, text=tr("sb_explain_tab"))
        exp_tab.rowconfigure(0, weight=1)
        exp_tab.columnconfigure(0, weight=1)

        self.explain_txt = tk.Text(exp_tab, font=CODE_FONT, wrap="word",
                                    bd=0, relief="flat", padx=6, pady=4,
                                    state="disabled", height=8)
        self.explain_txt.grid(row=0, column=0, sticky="nsew")
        exp_sb = ttk.Scrollbar(exp_tab, orient="vertical",
                                command=self.explain_txt.yview)
        exp_sb.grid(row=0, column=1, sticky="ns")
        self.explain_txt.config(yscrollcommand=exp_sb.set)

    # ==============================================================
    #  публичный API
    # ==============================================================
    def set_lang(self, name: str) -> None:
        self._lang_name = name
        if self.lang_cb is not None:
            self.lang_cb.set(name)
        if isinstance(self.editor, HighlightedText):
            try:
                self.editor.set_language(name)
            except Exception:
                pass
        self._refresh_template_list()

    def get_lang(self) -> str:
        return self._lang_name

    def set_code(self, code: str) -> None:
        state = self.editor.cget("state")
        self.editor.config(state="normal")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", code)
        if isinstance(self.editor, HighlightedText):
            try:
                self.editor.highlight()
            except Exception:
                pass
        if state == "disabled":
            self.editor.config(state="disabled")

    def get_code(self) -> str:
        return self.editor.get("1.0", "end-1c")

    def set_output(self, text: str, kind: str = "") -> None:
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.config(state="disabled")
        if self.status_lbl is not None:
            self.status_lbl.config(text=kind)

    def set_explain(self, text: str) -> None:
        self.explain_txt.config(state="normal")
        self.explain_txt.delete("1.0", "end")
        self.explain_txt.insert("1.0", text)
        self.explain_txt.config(state="disabled")

    def clear_output(self) -> None:
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")
        if self.status_lbl is not None:
            self.status_lbl.config(text="")
        if self.piet_label is not None:
            self.piet_label.config(image="")
            self._piet_image = None

    # ==============================================================
    #  шаблоны
    # ==============================================================
    def _refresh_template_list(self) -> None:
        if self.tpl_cb is None:
            return
        lang = registry.get(self._lang_name)
        if not lang:
            self.tpl_cb["values"] = []
            self.tpl_cb.set("")
            return
        names = list(lang.templates.keys())
        self.tpl_cb["values"] = names
        if names:
            self.tpl_cb.current(0)
            self._load_template(names[0])
        else:
            self.tpl_cb.set("")

    def _on_tpl_change(self) -> None:
        if self.tpl_cb is None:
            return
        self._load_template(self.tpl_cb.get())

    def _load_template(self, name: str) -> None:
        lang = registry.get(self._lang_name)
        if not lang or name not in lang.templates:
            return
        self.set_code(lang.templates[name])
        if self.status_lbl is not None:
            self.status_lbl.config(text=name)

    # ==============================================================
    #  действия
    # ==============================================================
    def on_run(self) -> None:
        if self._running:
            return
        code = self.get_code()
        lang_name = self._lang_name
        self._running = True
        if self.run_btn is not None:
            self.run_btn.config(state="disabled")
        if self.status_lbl is not None:
            self.status_lbl.config(text=tr("sb_running"))

        threading.Thread(target=self._run_thread,
                         args=(lang_name, code),
                         daemon=True).start()

    def _run_thread(self, lang_name: str, code: str) -> None:
        try:
            from services import get_execute_service
            svc = get_execute_service()
            res = svc.run(lang_name, code, timeout=5.0)
            err_text = ""
        except Exception as e:
            res = None
            err_text = f"Сервис упал: {type(e).__name__}: {e}"

        self.after(0, lambda: self._on_run_done(lang_name, res, err_text))

    def _on_run_done(self, lang_name: str, res, err_text: str) -> None:
        self._running = False
        if self.run_btn is not None:
            self.run_btn.config(state="normal")

        if res is None:
            self.set_output(f"! {err_text}\n", kind=tr("sb_error"))
            if self.app is not None:
                self.app.log(f"! {err_text}")
            return

        if not res.ok:
            self.set_output(f"! {res.error}\n", kind=tr("sb_error"))
            if self.app is not None:
                self.app.log(f"! {lang_name}: {res.error}")
            return

        output = res.output

        # === PIET-FIX ===
        # Для piet «код» — это base64 PNG. Показываем код как картинку,
        # а output (текст) — под ней в поле вывода.
        if lang_name == "piet":
            code_b64 = self.get_code().strip()
            self._show_piet_image(code_b64)
            self.set_output(output, kind=f"вывод · {res.elapsed:.2f}с")
        else:
            self.clear_piet_image()
            self.set_output(output, kind=f"{res.elapsed:.2f}с")

        if self.app is not None:
            self.app.log(f"$ {lang_name}: {res.elapsed:.2f}с, "
                         f"{len(output)} симв.")

    def clear_piet_image(self) -> None:
        if self.piet_label is not None:
            self.piet_label.config(image="")
            self._piet_image = None

    def _show_piet_image(self, code_b64: str) -> None:
        if not HAS_PIL:
            self.set_output(
                "[Piet] PIL не установлен. pip install Pillow\n\n"
                + code_b64[:300], kind="Piet")
            return
        try:
            raw = base64.b64decode(code_b64)
            im = Image.open(io.BytesIO(raw))
            scale = max(1, min(16, 512 // max(im.width, im.height)))
            if scale > 1:
                im = im.resize((im.width * scale, im.height * scale),
                               Image.NEAREST)
            self._piet_image = ImageTk.PhotoImage(im)
            if self.piet_label is None:
                self.piet_label = ttk.Label(self.piet_frame)
                self.piet_label.pack()
                self.piet_frame.pack(fill="x", pady=(4, 0))
            self.piet_label.config(image=self._piet_image)
        except Exception as e:
            if self.app is not None:
                self.app.log(f"! Piet: не удалось показать: {e}")

    def on_explain(self) -> None:
        """Разобрать текущий код по строкам."""
        try:
            from core.code_explainer import explain_text
            text = explain_text(self._lang_name, self.get_code())
            self.set_explain(text)
            if self.bottom is not None:
                self.bottom.select(1)   # переключиться на «Разбор»
            if self.app is not None:
                self.app.log(f"$ разбор кода ({self._lang_name})")
        except Exception as e:
            self.set_explain(f"Ошибка разбора: {e}")
            if self.app is not None:
                self.app.log(f"! разбор: {e}")

    def on_clear(self) -> None:
        if not self.readonly:
            self.editor.delete("1.0", "end")
        self.clear_output()
        self.set_explain("")

    def on_copy_output(self) -> None:
        text = self.output.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        if self.app is not None:
            self.app.log(f"$ вывод скопирован ({len(text)} симв.)")

    def on_save_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return
        try:
            Path(path).write_text(self.output.get("1.0", "end-1c"),
                                  encoding="utf-8")
            if self.app is not None:
                self.app.log(f"$ сохранено: {path}")
        except Exception as e:
            if self.app is not None:
                self.app.log(f"! {e}")

    def _on_lang_change(self) -> None:
        if self.lang_cb is None:
            return
        self.set_lang(self.lang_cb.get())

    # ==============================================================
    #  тема
    # ==============================================================
    def apply_theme(self, theme_name: str) -> None:
        if theme_name not in THEMES:
            theme_name = "dark"
        self._theme_name = theme_name
        t = THEMES[theme_name]

        for w in (self.editor, self.output, self.explain_txt):
            w.configure(
                bg=t["field"], fg=t["fg"],
                insertbackground=t["fg"],
                selectbackground=t["select"],
                selectforeground=t["fg"])
        if isinstance(self.editor, HighlightedText):
            try:
                self.editor.update_colors(theme_name)
            except Exception:
                pass