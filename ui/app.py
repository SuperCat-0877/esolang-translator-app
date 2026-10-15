# ui/app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
from io import BytesIO
from pathlib import Path
import os, sys
import re
import importlib

from core.registry import registry
from core.template_types import (
    TEMPLATE_TYPES, TYPE_BY_LABEL, ALL_LABELS,
    classify as _tpl_classify,
    reclassify as _tpl_reclassify,
)
from core.translate import translate
from core.themes import THEMES, BASE_THEMES, CUSTOM_THEMES, rebuild, syntax_palette
from core.config import (
    save as save_config, load as load_config,
    PLUGINS_DIR, DISABLED_DIR, UI_SETTINGS,
    disable_lang, enable_lang, list_disabled,
)
from core.plugins import load_plugin, discover as discover_plugins
from ui.editor import HighlightedText

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

CODE_FONT = ("Consolas", 11)
MODES = [("О = О", "О", "О"), ("О = Э", "О", "Э"),
         ("Э = О", "Э", "О"), ("Э = Э", "Э", "Э")]
NO_MARK = " (нет)"


class App:
    def __init__(self, root):
        self.root = root
        root.title("Esolang Translator")
        root.geometry("1300x950")
        root.minsize(1000, 750)

        self.theme = "dark"
        self._prev_dst = None
        self._last_result = None
        self._term_expanded = False
        self.rivulet_canvas = None
        self.piet_canvas = None
        self._buttons = {}

        registry.discover_builtin()
        discover_plugins()
        load_config()

        # ---- Универсальный fallback: TRANSPILERS[(src, dst)] для
        #      всех 1560 пар. Гарантирует, что translate() никогда
        #      не падает с KeyError. Медленный путь, но рабочий. ----
        from core.universal_fallback import install as _install_uf
        _uf_added = _install_uf()

        # Применить пользовательские имена языков
        for lang in registry.all():
            custom = UI_SETTINGS["renamed_langs"].get(lang.name)
            if custom:
                lang.title = custom

        # Переклассификация шаблонов: [1]→[E1], [Test]→[T1].
        # Старые ключи удаляются, остаются только [E/M/H/W/T][N].
        self._templates_stats = {}
        for lang in registry.all():
            old_keys = set(lang.templates.keys())
            lang.templates = _tpl_reclassify(lang.templates)
            new_keys = set(lang.templates.keys())
            removed = len(old_keys - new_keys)
            added = len(new_keys - old_keys)
            self._templates_stats[lang.name] = (
                len(old_keys), len(new_keys), removed, added)

        # === SANDBOX-INIT ===

        self._sandbox_panels = []

        self.sandbox = None

        # === /SANDBOX-INIT ===

        self._build()
        self._sandbox_panels = []  # ← добавить
        self._apply_theme(self.theme)
        self._bind_hotkeys()
        # закрытие — корректно гасим Executor
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)  # ← добавить
        self.on_mode()
        self.log("> готово. F1 — справка")
        # Сводка переклассификации шаблонов
        renamed_langs = [
            name for name, (o, n, r, a)
            in getattr(self, "_templates_stats", {}).items()
            if r or a
        ]
        if renamed_langs:
            self.log(f"[templates] переклассифицировано: "
                     f"{len(renamed_langs)} языков")
            if _uf_added:
                self.log(f"[translate] универсальных пар: {_uf_added}")

    # ==========================================================
    #  ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ==========================================================
    def _build(self):
        # ---------- МЕНЮ ----------
        menubar = tk.Menu(self.root)
        fm = tk.Menu(menubar, tearoff=0)
        fm.add_command(label="Открыть...", accelerator="Ctrl+O", command=self.do_open)
        fm.add_command(label="Сохранить...", accelerator="Ctrl+S", command=self.do_save)
        fm.add_separator()
        fm.add_command(label="Выход", command=self.root.destroy)
        menubar.add_cascade(label="Файл", menu=fm)

        vm = tk.Menu(menubar, tearoff=0)
        vm.add_command(label="Тёмная тема (F2)",
                       command=lambda: self._apply_theme("dark"))
        vm.add_command(label="Светлая тема (F3)",
                       command=lambda: self._apply_theme("light"))
        vm.add_command(label="Чёрная тема (F4)",
                       command=lambda: self._apply_theme("black"))
        menubar.add_cascade(label="Вид", menu=vm)

        lm = tk.Menu(menubar, tearoff=0)
        lm.add_command(label="Загрузить язык...", accelerator="Ctrl+L",
                       command=self.load_custom_lang)
        lm.add_command(label="Открыть папку плагинов", command=self.open_plugins_dir)
        menubar.add_cascade(label="Языки", menu=lm)

        rm = tk.Menu(menubar, tearoff=0)
        rm.add_command(label="Перевести", accelerator="F5", command=self.do_translate)
        rm.add_command(label="Запустить", accelerator="F6", command=self.do_run)
        menubar.add_cascade(label="Запуск", menu=rm)

        hm = tk.Menu(menubar, tearoff=0)
        hm.add_command(label="Справка", accelerator="F1", command=self.show_help)
        menubar.add_cascade(label="Справка", menu=hm)
        self.root.config(menu=menubar)

        # ---------- ТУЛБАР ----------
        tb = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        tb.pack(fill="x")

        ttk.Label(tb, text="Режим:").grid(row=0, column=0, padx=(0, 5))
        self.mode = ttk.Combobox(tb, values=[m[0] for m in MODES],
                                 state="readonly", width=10)
        self.mode.current(0)
        self.mode.grid(row=0, column=1, padx=(0, 15))
        self.mode.bind("<<ComboboxSelected>>", self.on_mode)

        ttk.Label(tb, text="Из:").grid(row=0, column=2, padx=(0, 3))
        self.src = ttk.Combobox(tb, values=[], state="readonly", width=14)
        self.src.grid(row=0, column=3, padx=(0, 10))
        self.src.bind("<<ComboboxSelected>>", self.on_src)

        ttk.Label(tb, text="В:").grid(row=0, column=4, padx=(0, 3))
        self.dst = ttk.Combobox(tb, values=[], state="readonly", width=16)
        self.dst.grid(row=0, column=5, padx=(0, 10))
        self.dst.bind("<<ComboboxSelected>>", self.on_dst)

        ttk.Label(tb, text="Тип:").grid(row=0, column=6, padx=(0, 3))
        self.tpl_type = ttk.Combobox(tb, values=ALL_LABELS,
                                     state="readonly", width=10)
        self.tpl_type.grid(row=0, column=7, padx=(0, 10))
        self.tpl_type.current(0)
        self.tpl_type.bind("<<ComboboxSelected>>", self.on_tpl_type)

        ttk.Label(tb, text="Шаблон:").grid(row=0, column=8, padx=(0, 3))
        self.tpl = ttk.Combobox(tb, values=[], state="readonly", width=32)
        self.tpl.grid(row=0, column=9, padx=(0, 10))
        self.tpl.bind("<<ComboboxSelected>>", self.on_tpl)

        # ---------- КНОПКИ ----------
        bt = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        bt.pack(fill="x")

        def mkbtn(key, default_text, cmd):
            text = UI_SETTINGS["button_labels"].get(key, default_text)
            b = ttk.Button(bt, text=text, command=cmd, style="Smooth.TButton")
            b.pack(side="left", padx=(0, 6))
            self._buttons[key] = (b, default_text)
            return b

        mkbtn("translate", "Перевести  F5", self.do_translate)
        mkbtn("run",       "Запустить  F6", self.do_run)
        ttk.Separator(bt, orient="vertical").pack(side="left", fill="y", padx=6)
        mkbtn("open",      "Открыть", self.do_open)
        mkbtn("save",      "Сохранить", self.do_save)
        mkbtn("clear",     "Очистить", self.do_clear)
        ttk.Separator(bt, orient="vertical").pack(side="left", fill="y", padx=6)
        mkbtn("copy_src",  "Копир. ИС 1", self.copy_src)
        mkbtn("paste_src", "Встав. ИС 1", self.paste_src)
        mkbtn("copy_dst",  "Копир. ИС 2", self.copy_dst)
        ttk.Separator(bt, orient="vertical").pack(side="left", fill="y", padx=6)
        mkbtn("load_lang", "Язык из файла", self.load_custom_lang)
        mkbtn("theme",     "Тема", self.cycle_theme)

        # ---------- ТЕРМИНАЛ СНИЗУ ----------
        self.status = ttk.Label(self.root, text="", padding=(10, 0, 10, 4))
        self.status.pack(fill="x", side="bottom")

        tf = ttk.Frame(self.root)
        tf.pack(fill="x", side="bottom")

        head = ttk.Frame(tf, padding=(10, 2, 10, 0))
        head.pack(fill="x")
        ttk.Label(head, text="Терминал",
                  font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(head, text="Очистить", command=self.clear_term,
                   style="Smooth.TButton").pack(side="right")
        ttk.Button(head, text="Развернуть", command=self.toggle_terminal,
                   style="Smooth.TButton").pack(side="right", padx=(0, 4))

        self.term = tk.Text(tf, height=6, font=("Consolas", 10),
                            wrap="word", bd=0, padx=8, pady=6)
        self.term.pack(fill="x", padx=10, pady=(2, 8))
        self.term.config(state="disabled")

        # ---------- ВКЛАДКИ ----------
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self._build_tab_translate()
        self._build_tab_rivulet()
        self._build_tab_other()
        self._build_tab_examples()
        self._build_tab_about()
        self._build_tab_sandbox()
        self._build_tab_mosaic()
        self._build_tab_piet_asm() # Piet-ASM   # === SANDBOX ===

    # ==========================================================
    #  ОБЩЕЕ ПОЛЕ
    # ==========================================================
    def _make_field(self, parent, highlight=True):
        t = THEMES[self.theme]
        cls = HighlightedText if highlight else tk.Text
        kw = dict(font=CODE_FONT, wrap="word", bd=0, relief="flat",
                  padx=8, pady=6, height=20, undo=True,
                  insertbackground=t["fg"], selectbackground=t["select"],
                  selectforeground=t["fg"], highlightthickness=1,
                  highlightbackground=t["border"], highlightcolor=t["accent"],
                  bg=t["field"], fg=t["fg"])
        return cls(parent, self, **kw) if highlight else cls(parent, **kw)

    # ==========================================================
    #  ВКЛАДКА «ПЕРЕВОД»
    # ==========================================================
    def _build_tab_translate(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="Перевод")

        mid = ttk.Frame(tab)
        mid.pack(fill="both", expand=True)
        mid.columnconfigure(0, weight=1, uniform="half")
        mid.columnconfigure(1, weight=1, uniform="half")
        mid.rowconfigure(0, weight=1)

        left = ttk.Frame(mid)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        self.src_label = ttk.Label(left, text="Язык №1:")
        self.src_label.grid(row=0, column=0, sticky="w", pady=(0, 3))
        self.editor = self._make_field(left, highlight=True)
        self.editor.grid(row=1, column=0, sticky="nsew")

        right = ttk.Frame(mid)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        self.dst_label = ttk.Label(right, text="Язык №2:")
        self.dst_label.grid(row=0, column=0, sticky="w", pady=(0, 3))
        self.output = self._make_field(right, highlight=True)
        self.output.grid(row=1, column=0, sticky="nsew")

        self.output.bind("<Key>", lambda e: "break")
        self.output.bind("<<Paste>>", lambda e: "break")
        self.output.bind("<<Cut>>", lambda e: "break")

    # ==========================================================
    #  ВКЛАДКА «RIVULET CANVAS»
    # ==========================================================
    def _build_tab_rivulet(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="Rivulet Canvas")

        try:
            from ui.rivulet_canvas import RivuletCanvasTab
        except Exception as e:
            ttk.Label(tab,
                text=f"Не удалось загрузить Rivulet Canvas:\n{e}",
                foreground="red", wraplength=800).pack(pady=20, padx=20)
            return

        try:
            self.rivulet_canvas = RivuletCanvasTab(tab, self)
        except Exception as e:
            ttk.Label(tab,
                text=f"Ошибка при создании холста:\n{e}",
                foreground="red", wraplength=800).pack(pady=20, padx=20)

    # ==========================================================
    #  ВКЛАДКА «PIET CANVAS»
    # ==========================================================
    def _build_tab_piet(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="Piet Canvas")

        try:
            from ui.piet_canvas import PietCanvasTab
        except Exception as e:
            ttk.Label(
                tab,
                text=f"Не удалось загрузить Piet Canvas:\n{e}",
                foreground="red", wraplength=800,
            ).pack(pady=20, padx=20)
            return

        try:
            self.piet_canvas = PietCanvasTab(tab, self)
        except Exception as e:
            ttk.Label(
                tab,
                text=f"Ошибка при создании холста:\n{e}",
                foreground="red", wraplength=800,
            ).pack(pady=20, padx=20)

    # ==========================================================
    #  ВКЛАДКА «ДРУГОЕ»
    # ==========================================================
    def _build_tab_other(self):
        outer = ttk.Frame(self.tabs, padding=(8, 8, 8, 8))
        self.tabs.add(outer, text="Другое")

        sub = ttk.Notebook(outer)
        sub.pack(fill="both", expand=True)

        self._build_theme_tab(sub)
        self._build_templates_tab(sub)
        self._build_languages_tab(sub)
        self._build_ui_tab(sub)

        self._refresh_theme_list()
        self._refresh_template_languages()
        self._refresh_language_list()
        self._refresh_button_list()
        self._refresh_disabled_list()
        self._refresh_listbox_editor()

    # ---------- ПОД-ВКЛАДКА «ТЕМЫ» ----------
    def _build_theme_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        parent.add(tab, text="🎨 Темы")

        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        ttk.Label(left, text="Встроенные темы",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        lf = ttk.Frame(left)
        lf.pack(fill="both", expand=True, pady=(4, 0))
        self.theme_list = tk.Listbox(lf, width=22, height=18,
                                      font=("Segoe UI", 10),
                                      activestyle="none",
                                      exportselection=False)
        self.theme_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.theme_list.yview)
        sb.pack(side="left", fill="y")
        self.theme_list.config(yscrollcommand=sb.set)
        self.theme_list.bind("<<ListboxSelect>>", self._on_theme_select)
        self.theme_list.bind("<Double-Button-1>",
                              lambda e: self._apply_selected_theme())

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right, text="Превью",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        pv = ttk.Frame(right, relief="solid", borderwidth=1)
        pv.pack(fill="both", expand=True, pady=(4, 8))
        self.theme_preview = tk.Text(pv, height=6, font=("Consolas", 10),
                                      wrap="word", bd=0, padx=10, pady=8,
                                      state="disabled")
        self.theme_preview.pack(fill="both", expand=True)

        actions = ttk.LabelFrame(right, text="Действия", padding=8)
        actions.pack(fill="x")
        ttk.Button(actions, text="Применить тему",
                   command=self._apply_selected_theme,
                   style="Smooth.TButton").pack(fill="x")

    # ---------- ПОД-ВКЛАДКА «ШАБЛОНЫ» ----------
    def _build_templates_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        parent.add(tab, text="📝 Шаблоны")

        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Язык:").pack(side="left", padx=(0, 6))
        self.cfg_lang = ttk.Combobox(top, values=[], state="readonly", width=24)
        self.cfg_lang.pack(side="left", padx=(0, 10))
        self.cfg_lang.bind("<<ComboboxSelected>>",
                            lambda e: self._refresh_template_list())
        ttk.Button(top, text="Сбросить к встроенным",
                   command=self._reset_templates_for_lang,
                   style="Smooth.TButton").pack(side="right")

        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        ttk.Label(left, text="Шаблоны",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        lf = ttk.Frame(left)
        lf.pack(fill="both", expand=True, pady=(4, 4))
        self.tpl_list = tk.Listbox(lf, width=30, height=16,
                                    font=("Segoe UI", 10),
                                    activestyle="none",
                                    exportselection=False)
        self.tpl_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.tpl_list.yview)
        sb.pack(side="left", fill="y")
        self.tpl_list.config(yscrollcommand=sb.set)
        self.tpl_list.bind("<<ListboxSelect>>", self._on_template_select)

        tb = ttk.Frame(left); tb.pack(fill="x")
        ttk.Button(tb, text="+ Добавить",
                   command=self._add_new_template,
                   style="Smooth.TButton").pack(side="left", fill="x",
                                                 expand=True, padx=(0, 2))
        ttk.Button(tb, text="− Удалить",
                   command=self._delete_selected_template,
                   style="Smooth.TButton").pack(side="left", fill="x",
                                                 expand=True, padx=(2, 0))

        tb2 = ttk.Frame(left); tb2.pack(fill="x", pady=(4, 0))
        ttk.Button(tb2, text="Переименовать…",
                   command=self._rename_selected_template,
                   style="Smooth.TButton").pack(fill="x")

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right, text="Название:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tpl_name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.tpl_name_var,
                  font=("Consolas", 11)).pack(fill="x", pady=(4, 8))
        ttk.Label(right, text="Код:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        txt_frame = ttk.Frame(right)
        txt_frame.pack(fill="both", expand=True, pady=(4, 8))
        self.cfg_txt = tk.Text(txt_frame, font=("Consolas", 10),
                                wrap="none", bd=0, padx=8, pady=6)
        self.cfg_txt.pack(side="left", fill="both", expand=True)
        sb2 = ttk.Scrollbar(txt_frame, orient="vertical",
                             command=self.cfg_txt.yview)
        sb2.pack(side="right", fill="y")
        self.cfg_txt.config(yscrollcommand=sb2.set)

        btns = ttk.Frame(right); btns.pack(fill="x")
        ttk.Button(btns, text="💾 Сохранить",
                   command=self._save_template_edit,
                   style="Smooth.TButton").pack(side="left", fill="x",
                                                 expand=True, padx=(0, 3))
        ttk.Button(btns, text="Отменить",
                   command=self._on_template_select,
                   style="Smooth.TButton").pack(side="left", fill="x",
                                                 expand=True, padx=(3, 0))

    # ---------- ПОД-ВКЛАДКА «ЯЗЫКИ» ----------
    def _build_languages_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        parent.add(tab, text="🧩 Языки")

        ttk.Label(tab,
            text="Системные языки (Python, JavaScript, C++, Brainfuck, "
                 "Whitespace, Rivulet) удалить нельзя.\n"
                 "Остальные при отключении сохраняются в папку "
                 "langs_disabled/ и могут быть восстановлены.",
            justify="left").pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Активные", padding=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        lf1 = ttk.Frame(left); lf1.pack(fill="both", expand=True)
        self.lang_list = tk.Listbox(lf1, font=("Segoe UI", 10),
                                     activestyle="none",
                                     exportselection=False)
        self.lang_list.pack(side="left", fill="both", expand=True)
        sb1 = ttk.Scrollbar(lf1, orient="vertical", command=self.lang_list.yview)
        sb1.pack(side="left", fill="y")
        self.lang_list.config(yscrollcommand=sb1.set)

        right = ttk.LabelFrame(body, text="Отключённые (langs_disabled/)",
                                padding=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        lf2 = ttk.Frame(right); lf2.pack(fill="both", expand=True)
        self.disabled_list = tk.Listbox(lf2, font=("Segoe UI", 10),
                                         activestyle="none",
                                         exportselection=False)
        self.disabled_list.pack(side="left", fill="both", expand=True)
        sb2 = ttk.Scrollbar(lf2, orient="vertical",
                             command=self.disabled_list.yview)
        sb2.pack(side="left", fill="y")
        self.disabled_list.config(yscrollcommand=sb2.set)

        btns = ttk.Frame(tab)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Переименовать язык…",
                   command=self._rename_language,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(btns, text="Отключить →",
                   command=self._disable_selected_lang,
                   style="Smooth.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text="← Восстановить",
                   command=self._enable_selected_lang,
                   style="Smooth.TButton").pack(side="left", padx=4)
        ttk.Separator(btns, orient="vertical").pack(side="left", fill="y",
                                                      padx=8)
        ttk.Button(btns, text="Загрузить плагин…",
                   command=self.load_custom_lang,
                   style="Smooth.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text="Открыть папки",
                   command=self.open_plugins_dir,
                   style="Smooth.TButton").pack(side="left", padx=4)

    # ---------- ПОД-ВКЛАДКА «ИНТЕРФЕЙС» ----------
    def _build_ui_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        parent.add(tab, text="⚙️ Интерфейс")

        # --- Подписи кнопок ---
        btn_frame = ttk.LabelFrame(tab, text="Подписи кнопок", padding=8)
        btn_frame.pack(fill="x", pady=(0, 10))

        self.btn_list = tk.Listbox(btn_frame, height=8,
                                    font=("Consolas", 10),
                                    activestyle="none",
                                    exportselection=False)
        self.btn_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(btn_frame, orient="vertical",
                            command=self.btn_list.yview)
        sb.pack(side="left", fill="y")
        self.btn_list.config(yscrollcommand=sb.set)
        self.btn_list.bind("<<ListboxSelect>>", self._on_btn_select)

        ctrl = ttk.Frame(btn_frame)
        ctrl.pack(side="left", padx=(10, 0))
        ttk.Label(ctrl, text="Новый текст:").pack(anchor="w")
        self.btn_text_var = tk.StringVar()
        ttk.Entry(ctrl, textvariable=self.btn_text_var,
                  width=28).pack(pady=4)
        ttk.Button(ctrl, text="Применить",
                   command=self._apply_btn_rename,
                   style="Smooth.TButton").pack(fill="x", pady=2)
        ttk.Button(ctrl, text="Сбросить всё",
                   command=self._reset_button_labels,
                   style="Smooth.TButton").pack(fill="x", pady=2)

        # --- Цвета списков для темы ---
        lb_frame = ttk.LabelFrame(tab,
                                   text="Цвета списков (для темы)",
                                   padding=8)
        lb_frame.pack(fill="x", pady=(0, 10))

        top = ttk.Frame(lb_frame)
        top.pack(fill="x")
        ttk.Label(top, text="Тема:").pack(side="left", padx=(0, 6))
        self.lb_theme_var = tk.StringVar(value="dark")
        self.lb_theme_cb = ttk.Combobox(top,
                                         textvariable=self.lb_theme_var,
                                         values=list(THEMES.keys()),
                                         state="readonly", width=16)
        self.lb_theme_cb.pack(side="left", padx=(0, 10))
        self.lb_theme_cb.bind("<<ComboboxSelected>>",
                                lambda e: self._refresh_listbox_editor())

        colors_frame = ttk.Frame(lb_frame)
        colors_frame.pack(fill="x", pady=6)
        self.lb_colors = {}
        for key, label in (("bg", "Фон"),
                            ("fg", "Текст"),
                            ("select_bg", "Выделение (фон)"),
                            ("select_fg", "Выделение (текст)")):
            col = ttk.Frame(colors_frame)
            col.pack(side="left", padx=4)
            ttk.Label(col, text=label,
                      font=("Segoe UI", 9)).pack()
            b = ttk.Button(col, text="#------", width=12)
            b.pack()
            self.lb_colors[key] = b

            def make_cmd(k, btn):
                def cmd():
                    theme_name = self.lb_theme_var.get()
                    current = (UI_SETTINGS["listbox_theme"]
                               .get(theme_name, {})
                               .get(k, "#ffffff"))
                    new = colorchooser.askcolor(color=current,
                                                 title=f"Цвет: {k}")[1]
                    if new:
                        (UI_SETTINGS["listbox_theme"]
                         .setdefault(theme_name, {}))[k] = new
                        btn.config(text=new)
                        save_config()
                        self._apply_theme(self.theme)
                return cmd
            b.config(command=make_cmd(key, b))

        reset_row = ttk.Frame(lb_frame)
        reset_row.pack(fill="x", pady=4)
        ttk.Button(reset_row, text="Сбросить цвета для этой темы",
                   command=self._reset_listbox_colors,
                   style="Smooth.TButton").pack(side="left")

    # ==========================================================
    #  ВКЛАДКА «ПРИМЕРЫ (TXT)»
    # ==========================================================
    def _build_tab_examples(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="Примеры (TXT)")

        self.ex_txt = self._make_field(tab, highlight=False)
        self.ex_txt.pack(fill="both", expand=True, pady=(4, 8))
        self._fill_examples()

        btns = ttk.Frame(tab)
        btns.pack(fill="x")
        ttk.Button(btns, text="Сохранить в TXT",
                   command=self._export_examples,
                   style="Smooth.TButton").pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="Загрузить из TXT",
                   command=self._import_examples,
                   style="Smooth.TButton").pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="Обновить",
                   command=self._fill_examples,
                   style="Smooth.TButton").pack(side="left")

    # ==========================================================
    #  ВКЛАДКА «О ПРОГРАММЕ»
    # ==========================================================
    def _build_tab_about(self):
        tab = ttk.Frame(self.tabs, padding=0)
        self.tabs.add(tab, text="О программе")  # ← было "Справка"

        wrapper = ttk.Frame(tab)
        wrapper.pack(fill="both", expand=True)

        self.about_txt = tk.Text(  # ← было help_txt
            wrapper,
            wrap="word",
            font=("Consolas", 10),
            bd=0,
            padx=20,
            pady=15,
            cursor="arrow",
        )
        sb = ttk.Scrollbar(wrapper, orient="vertical",
                           command=self.about_txt.yview)
        self.about_txt.config(yscrollcommand=sb.set)
        self.about_txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # --- Заголовки ---
        self.about_txt.tag_configure("h1", font=("Segoe UI", 18, "bold"))
        self.about_txt.tag_configure("h2", font=("Segoe UI", 12, "bold"))
        self.about_txt.tag_configure("h3", font=("Segoe UI", 10, "bold"))
        self.about_txt.tag_configure("mono", font=("Consolas", 10))
        self.about_txt.tag_configure("accent", font=("Consolas", 10, "bold"))

        # --- Семантические теги (цвета задаст _apply_theme,
        #     здесь — только шрифты) ---
        self.about_txt.tag_configure("key",   font=("Segoe UI", 10, "bold"))
        self.about_txt.tag_configure("num",   font=("Consolas", 10, "bold"))
        self.about_txt.tag_configure("os",    font=("Consolas", 10, "bold"))
        self.about_txt.tag_configure("pyver", font=("Consolas", 10, "bold"))
        self.about_txt.tag_configure("ext",   font=("Consolas", 10))
        self.about_txt.tag_configure("path",  font=("Consolas", 10))
        self.about_txt.tag_configure("cmd",   font=("Consolas", 10))
        self.about_txt.tag_configure("ok",    font=("Consolas", 10, "bold"))
        self.about_txt.tag_configure("bad",   font=("Consolas", 10, "bold"))
        self.about_txt.tag_configure("warn",  font=("Consolas", 10, "bold"))
        self.about_txt.tag_configure("dim",   font=("Consolas", 9))
        self._fill_about()  # ← было _fill_help
        self.about_txt.config(state="disabled")
    # ----------------------------------------------------------

    def _insert_line(self, base_tag: str, text: str) -> None:
        """Вставляет одну строку. Поддерживает маркеры {tag|текст}.
        base_tag — тег для всего текста вне маркеров ('' — без тега).
        """
        t = self.about_txt
        pattern = re.compile(r"\{(\w+)\|([^}]*)\}")
        pos = 0
        for m in pattern.finditer(text):
            # обычный текст до маркера
            if m.start() > pos:
                chunk = text[pos:m.start()]
                if base_tag:
                    t.insert("end", chunk, base_tag)
                else:
                    t.insert("end", chunk)
            # маркер → цветной кусок
            tag, content = m.group(1), m.group(2)
            t.insert("end", content, tag)
            pos = m.end()
        # хвост строки
        if pos < len(text):
            chunk = text[pos:]
            if base_tag:
                t.insert("end", chunk, base_tag)
            else:
                t.insert("end", chunk)
        t.insert("end", "\n")

    def _fill_about(self):
        t = self.about_txt
        t.config(state="normal")
        t.delete("1.0", "end")

        ordinary = sorted(l.title for l in registry.all()
                          if l.category == "О")
        esoteric = sorted(l.title for l in registry.all()
                          if l.category == "Э")
        total = len(ordinary) + len(esoteric)

        try:
            import platform
            os_name = f"{platform.system()} {platform.release()}"
        except Exception:
            os_name = "?"
        py_ver = sys.version.split()[0]

        def has(mod):
            try:
                __import__(mod)
                return "✔"
            except Exception:
                return "✘"

        pil   = has("PIL")
        cairo = has("cairosvg")
        svttk = has("sv_ttk")

        sections = [
            ("h1", "Esolang Translator"),
            ("mono", "Версия {ver|2.5}  ·  сборка {ver|2026}  ·  MIT License"),
            ("mono", "© 2026  Esolang Translator"),
            ("", ""),

            ("h2", "О программе"),
            ("", "Esolang Translator — многоязычная среда разработки для "
                 "эзотерических и обычных языков программирования."),
            ("", "Программа позволяет писать код на одном языке, переводить "
                 "его в другой ({key|F5}), запускать прямо в окне "
                 "({key|F6}) и визуализировать 2D-языки "
                 "({key|Rivulet}, {key|Piet}) на встроенных холстах."),
            ("", "Поддерживается {num|1560} направлений перевода между всеми "
                 "языками: «обычный → эзотерический», «эзотерический → "
                 "обычный» и «эзотерический → эзотерический»."),
            ("", ""),

            ("h2", "Ключевые возможности"),
            ("", "• {num|1560} направлений перевода между всеми языками."),
            ("", "• Подсветка синтаксиса для каждого языка."),
            ("", "• {num|38} встроенных тем: 3 базовые, 5 классических, "
                 "радуга, оттенки голубого / красного / фиолетового, "
                 "10 светлых пастельных."),
            ("", "• 2D-редакторы {key|Rivulet} и {key|Piet} с превью."),
            ("", "• Вкладка «{key|Мозаика}» — плиточная визуализация."),
            ("", "• Вкладка «{key|Песочница}» — изолированный запуск кода."),
            ("", "• {key|Piet-ASM} — ассемблер Piet с плитками {num|16×16}."),
            ("", "• Плагины {ext|.py} в папке {path|plugins/} без перезапуска."),
            ("", "• Переименование языков, кнопок и языков-плагинов."),
            ("", "• Пользовательские темы с настройкой цветов списков."),
            ("", "• Отключение ненужных языков в {path|langs_disabled/}."),
            ("", ""),

            ("h2", "Системные требования"),
            ("h3", "Операционная система"),
            ("mono", "  {os|Windows 10 / 11}         → Python {pyver|3.10} – {pyver|3.14}"),
            ("mono", "  {os|Linux}  (любой с Tk)      → Python {pyver|3.10} – {pyver|3.14}"),
            ("mono", "  {os|macOS}  10.13+           → Python {pyver|3.10} – {pyver|3.14}"),
            ("", ""),
            ("h3", "Python"),
            ("warn", "  Требуется:   Python {pyver|3.10} или новее"),
            ("dim",  "  Причина:     pattern matching (match / case)"),
            ("dim",  "               и type hints нового синтаксиса"),
            ("mono", "  Проверено:   Python {pyver|3.10} – {pyver|3.14}"),
            ("", ""),
            ("h3", "Обязательные библиотеки"),
            ("mono", "  {key|tkinter}       — входит в стандартный Python"),
            ("mono", "  {key|sv-ttk}        — нативные темы dark / light"),
            ("cmd",  "                  pip install sv-ttk"),
            ("", ""),
            ("h3", "Опциональные библиотеки"),
            ("mono", "  {key|Pillow}        — превью PNG, плитки Piet-ASM"),
            ("cmd",  "                  pip install Pillow"),
            ("mono", "  {key|cairosvg}      — превью SVG-схем Rivulet"),
            ("cmd",  "                  pip install cairosvg"),
            ("", ""),
            ("h3", "Обнаружено в этой системе"),
            ("mono", f"  ОС:            {os_name}"),
            ("mono", f"  Python:        {py_ver}"),
            ("", ""),

            ("h2", "Горячие клавиши"),
            ("", "  {key|F1}        — эта вкладка («О программе»)"),
            ("", "  {key|F2}        — тёмная тема"),
            ("", "  {key|F3}        — светлая тема"),
            ("", "  {key|F4}        — чёрная тема"),
            ("", "  {key|F5}        — Перевести (Из: → В:)"),
            ("", "  {key|F6}        — Запустить текущий код"),
            ("", "  {key|Ctrl+O}    — открыть файл"),
            ("", "  {key|Ctrl+S}    — сохранить результат"),
            ("", "  {key|Ctrl+L}    — загрузить язык из .py-файла"),
            ("", "  {key|Ctrl+`}    — развернуть / свернуть терминал"),
            ("", ""),

            ("h2", "Вкладки"),
            ("h3", "Перевод"),
            ("", "Основная вкладка. Слева ИС 1 (исходник), справа ИС 2 "
                 "(результат). Выбор режима, языка-источника и языка-"
                 "приёмника, фильтра шаблонов и самого шаблона."),
            ("h3", "Rivulet Canvas"),
            ("", "Визуальный редактор 2D-языка {key|Rivulet}. Сетка "
                 "глифов, палитра команд, экспорт в {ext|.riv}-файл."),
            ("h3", "Piet-ASM"),
            ("", "Текстовый ассемблер Piet: {key|push}, {key|add}, "
                 "{key|sub}, {key|mul}, {key|div}, {key|mod}, "
                 "{key|not}, {key|gt}, {key|dp}, {key|cc}, {key|dup}, "
                 "{key|roll}, {key|write}, {key|read}, {key|out_num}, "
                 "{key|out_char}, {key|nop}."),
            ("", "Кнопки «▶ Запустить», «🔍 Разобрать», «📦 Плитки»."),
            ("", "Плитки {num|16×16} рендерятся через Pillow."),
            ("h3", "Мозаика"),
            ("", "Плиточное представление кода (экспериментально)."),
            ("h3", "Песочница"),
            ("", "Изолированный запуск кода с таймаутом {num|5} сек. "
                 "Язык и шаблон выбираются независимо от вкладки "
                 "«Перевод». Есть вкладки «Вывод» и «Разбор»."),
            ("h3", "Примеры (TXT)"),
            ("", "Все шаблоны всех языков одним текстом. "
                 "Экспорт и импорт в {ext|.txt}-файл."),
            ("h3", "Другое"),
            ("", "4 под-вкладки: Темы · Шаблоны · Языки · Интерфейс."),
            ("", ""),

            ("h2", f"Языки ({total})"),
            ("h3", f"Обычные ({len(ordinary)})"),
            ("mono", "  " + ", ".join(ordinary)),
            ("", ""),
            ("h3", f"Эзотерические ({len(esoteric)})"),
            ("mono", "  " + ", ".join(esoteric)),
            ("", ""),

            ("h2", "Режимы перевода"),
            ("mono", "{key|О = О}   обычный       → обычный"),
            ("mono", "{key|О = Э}   обычный       → эзотерический"),
            ("mono", "{key|Э = О}   эзотерический → обычный"),
            ("mono", "{key|Э = Э}   эзотерический → эзотерический"),
            ("", "«Из:» и «В:» — всегда разные языки."),
            ("", ""),

            ("h2", "Как работает перевод"),
            ("h3", "Обычный → Обычный"),
            ("", "Цепочка {key|X} → {key|Python} → {key|Y} через "
                 "выполнение и генерацию."),
            ("h3", "Обычный → Эзотерический"),
            ("", "Выполнение исходного кода, получение вывода, генерация "
                 "эквивалента на целевом языке."),
            ("h3", "Эзотерический → Обычный"),
            ("", "Линейный транспайлер по правилам конкретного языка."),
            ("h3", "Rivulet / Piet"),
            ("", "2D-холсты + линейный транспайлер."),
            ("", ""),

            ("h2", "Piet — 20 цветов"),
            ("mono", "Light:  0 1 2 3 4 5   (red yellow green cyan blue magenta)"),
            ("mono", "Normal: 6 7 8 9 a b   (red yellow green cyan blue magenta)"),
            ("mono", "Dark:   c d e f g h   (red yellow green cyan blue magenta)"),
            ("mono", "i — white (пустое),  j — black (стена)"),
            ("", ""),

            ("h2", "Шаблоны"),
            ("", "У каждого языка ровно {num|13} шаблонов: [1]–[11] + 2 Test."),
            ("", "У Rivulet {num|12} — настоящие {ext|.riv}-файлы."),
            ("", "Переклассификация: [1]→[E1], [Test]→[T1] и т. п."),
            ("", "Шаблоны можно редактировать в под-вкладке "
                 "«Другое → 📝 Шаблоны»."),
            ("", ""),

            ("h2", "Плагины"),
            ("", "Создайте {ext|.py}-файл в {path|plugins/} со структурой:"),
            ("mono", ""),
            ("mono", "    {key|NAME} = \"mylang\""),
            ("mono", "    {key|CATEGORY} = \"О\"  # или \"Э\""),
            ("mono", "    {key|TEMPLATES} = {"),
            ("mono", "        \"[1] Пример\": \"код...\","),
            ("mono", "        \"[2] Привет\":  \"код...\","),
            ("mono", "    }"),
            ("mono", "    {key|def execute}(src):"),
            ("mono", "        return \"вывод\""),
            ("mono", ""),
            ("", "Затем: меню «Языки → Загрузить язык…» или {key|Ctrl+L}."),
            ("dim", "Плагин появится в списке без перезапуска приложения."),
            ("", ""),

            ("h2", "Файлы проекта"),
            ("path", "  config.json          — настройки и темы"),
            ("path", "  rivulet_library.json — кэш Rivulet-программ"),
            ("path", "  plugins/             — пользовательские плагины"),
            ("path", "  langs_disabled/      — отключённые языки"),
            ("path", "  Rivulet_examples/    — .riv-файлы"),
            ("path", "  core/                — ядро"),
            ("path", "  langs/               — языки"),
            ("path", "  ui/                  — интерфейс"),
            ("path", "  tools/               — скрипты и Executor"),
            ("path", "  services/            — сервисный слой"),
            ("path", "  rivulet/             — интерпретатор Rivulet"),
            ("", ""),

            ("h2", "Лицензия"),
            ("", "MIT License — свободное использование, изменение и"),
            ("", "распространение с сохранением копирайта."),
            ("", ""),
            ("mono", "© 2026  Esolang Translator"),
        ]

        for tag, text in sections:
            self._insert_line(tag, text)

        # Цветные галочки «Обнаружено в этой системе»
        t.insert("end", "  Pillow (PIL):  ")
        t.insert("end", pil + "\n", "ok" if pil == "✔" else "bad")
        t.insert("end", "  cairosvg:      ")
        t.insert("end", cairo + "\n", "ok" if cairo == "✔" else "bad")
        t.insert("end", "  sv-ttk:        ")
        t.insert("end", svttk + "\n", "ok" if svttk == "✔" else "bad")

        t.config(state="disabled")

    def _refresh_theme_list(self):
        if not hasattr(self, "theme_list"):
            return
        self.theme_list.delete(0, "end")
        for name in THEMES.keys():
            marker = " ★" if name == self.theme else ""
            self.theme_list.insert("end", f" {name}{marker}")
        keys = list(THEMES.keys())
        if self.theme in keys:
            idx = keys.index(self.theme)
            self.theme_list.selection_clear(0, "end")
            self.theme_list.selection_set(idx)
            self.theme_list.see(idx)
            self._on_theme_select()

    def _on_theme_select(self, event=None):
        sel = self.theme_list.curselection()
        if not sel or not hasattr(self, "theme_preview"):
            return
        name = list(THEMES.keys())[sel[0]]
        t = THEMES[name]
        pal = syntax_palette(name)

        self.theme_preview.config(state="normal")
        self.theme_preview.delete("1.0", "end")
        self.theme_preview.config(
            bg=t["field"], fg=t["fg"],
            insertbackground=t["fg"],
            selectbackground=t["select"],
            selectforeground=t["fg"])
        for tag, color in pal.items():
            self.theme_preview.tag_configure(tag, foreground=color)

        self.theme_preview.insert("end", "def hello(name):\n")
        self.theme_preview.insert("end", "    # комментарий\n")
        self.theme_preview.insert("end", "    print(f'Привет, {name}!')\n")
        self.theme_preview.insert("end", "    return 42\n")

        txt = self.theme_preview.get("1.0", "end-1c")
        for m in re.finditer(r"#.*", txt):
            self.theme_preview.tag_add("comment",
                f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in re.finditer(r"\b(def|return|print)\b", txt):
            self.theme_preview.tag_add("keyword",
                f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in re.finditer(r"'[^']*'", txt):
            self.theme_preview.tag_add("string",
                f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in re.finditer(r"\b\d+\b", txt):
            self.theme_preview.tag_add("number",
                f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        self.theme_preview.config(state="disabled")

    def _apply_selected_theme(self):
        sel = self.theme_list.curselection()
        if not sel:
            return
        self._apply_theme(list(THEMES.keys())[sel[0]])

        def _style_ttk(self, t):
            """Применяет цвета темы ко всем ttk-виджетам через ttk.Style()."""
            s = ttk.Style()
            bg = t.get("bg", "#1e1e1e")
            fg = t.get("fg", "#d4d4d4")
            field = t.get("field", bg)
            select = t.get("select", "#264f78")
            border = t.get("border", "#3c3c3c")
            accent = t.get("accent", "#4ea1ff")

            # --- контейнеры ---
            for cls in ("TFrame", "TLabelframe", "TNotebook",
                        "TPanedwindow", "TLabelframe.Label"):
                s.configure(cls, background=bg, bordercolor=border,
                            lightcolor=bg, darkcolor=bg)
            s.configure("TLabelframe.Label", foreground=fg)

            # --- текст и переключатели ---
            for cls in ("TLabel", "TCheckbutton", "TRadiobutton"):
                s.configure(cls, background=bg, foreground=fg)
                s.map(cls,
                      background=[("active", bg)],
                      foreground=[("disabled", border)])

            # --- кнопки (включая Smooth.TButton) ---
            for cls in ("TButton", "Smooth.TButton", "Toolbutton"):
                s.configure(cls,
                            background=field, foreground=fg,
                            bordercolor=border,
                            focuscolor=accent,
                            lightcolor=field, darkcolor=field,
                            relief="flat", borderwidth=0)
                s.map(cls,
                      background=[("active", select), ("pressed", select),
                                  ("disabled", bg)],
                      foreground=[("disabled", border)])

            # --- поля ввода ---
            s.configure("TEntry",
                        fieldbackground=field, foreground=fg,
                        bordercolor=border,
                        lightcolor=border, darkcolor=border)
            s.map("TEntry",
                  fieldbackground=[("readonly", bg)],
                  foreground=[("disabled", border)])

            # --- выпадающие списки ---
            s.configure("TCombobox",
                        fieldbackground=field, background=field,
                        foreground=fg, arrowcolor=fg,
                        bordercolor=border)
            s.map("TCombobox",
                  fieldbackground=[("readonly", field)],
                  selectbackground=[("readonly", field)],
                  selectforeground=[("readonly", fg)],
                  foreground=[("disabled", border)])
            # выпадающий list у Combobox — это обычный tk.Listbox,
            # ему цвет задаётся через option_add
            try:
                self.root.option_add("*TCombobox*Listbox.background", field)
                self.root.option_add("*TCombobox*Listbox.foreground", fg)
                self.root.option_add("*TCombobox*Listbox.selectBackground", select)
                self.root.option_add("*TCombobox*Listbox.selectForeground", fg)
            except Exception:
                pass

            # --- вкладки ---
            s.configure("TNotebook", background=bg, bordercolor=border)
            s.configure("TNotebook.Tab",
                        background=bg, foreground=fg,
                        padding=(12, 6), bordercolor=border)
            s.map("TNotebook.Tab",
                  background=[("selected", field), ("active", select)],
                  foreground=[("selected", accent)])

            # --- полосы прокрутки ---
            s.configure("TScrollbar",
                        background=field, troughcolor=bg,
                        bordercolor=border, arrowcolor=fg)
            s.map("TScrollbar",
                  background=[("active", select)])

            # --- разделители ---
            s.configure("TSeparator", background=border)

    def _style_ttk(self, t):
        """Красит ttk-виджеты под палитру темы. Работает только с clam."""
        s = ttk.Style()

        bg     = t.get("bg",      "#1e1e1e")
        fg     = t.get("fg",      "#d4d4d4")
        field  = t.get("field",   bg)
        select = t.get("select",  "#264f78")
        border = t.get("border",  "#3c3c3c")
        accent = t.get("accent",  "#4ea1ff")

        # --- контейнеры ---
        for cls in ("TFrame", "TLabelframe", "TNotebook",
                    "TPanedwindow"):
            s.configure(cls, background=bg, bordercolor=border,
                        lightcolor=bg, darkcolor=bg)
        s.configure("TLabelframe.Label", background=bg, foreground=fg)

        # --- тексты ---
        for cls in ("TLabel", "TCheckbutton", "TRadiobutton"):
            s.configure(cls, background=bg, foreground=fg)
            s.map(cls,
                  background=[("active", bg)],
                  foreground=[("disabled", border)])

        # --- кнопки ---
        for cls in ("TButton", "Smooth.TButton", "Toolbutton"):
            s.configure(cls,
                        background=field, foreground=fg,
                        bordercolor=border,
                        focuscolor=accent,
                        lightcolor=field, darkcolor=field,
                        relief="flat", borderwidth=0)
            s.map(cls,
                  background=[("active", select), ("pressed", select),
                              ("disabled", bg)],
                  foreground=[("disabled", border)])

        # --- поля ввода ---
        s.configure("TEntry",
                    fieldbackground=field, foreground=fg,
                    bordercolor=border,
                    lightcolor=border, darkcolor=border)
        s.map("TEntry",
              fieldbackground=[("readonly", bg)],
              foreground=[("disabled", border)])

        # --- комбобоксы ---
        s.configure("TCombobox",
                    fieldbackground=field, background=field,
                    foreground=fg, arrowcolor=fg,
                    bordercolor=border,
                    lightcolor=border, darkcolor=border)
        s.map("TCombobox",
              fieldbackground=[("readonly", field)],
              selectbackground=[("readonly", field)],
              selectforeground=[("readonly", fg)],
              foreground=[("disabled", border)])
        # выпадающий список комбобокса — обычный tk.Listbox
        self.root.option_add("*TCombobox*Listbox.background", field)
        self.root.option_add("*TCombobox*Listbox.foreground", fg)
        self.root.option_add("*TCombobox*Listbox.selectBackground", select)
        self.root.option_add("*TCombobox*Listbox.selectForeground", fg)

        # --- вкладки ---
        s.configure("TNotebook", background=bg, bordercolor=border,
                    lightcolor=bg, darkcolor=bg)
        s.configure("TNotebook.Tab",
                    background=bg, foreground=fg,
                    padding=(12, 6), bordercolor=border,
                    lightcolor=bg, darkcolor=bg)
        s.map("TNotebook.Tab",
              background=[("selected", field), ("active", select)],
              foreground=[("selected", accent)])

        # --- скроллбары ---
        s.configure("TScrollbar",
                    background=field, troughcolor=bg,
                    bordercolor=border, arrowcolor=fg,
                    lightcolor=field, darkcolor=field)
        s.map("TScrollbar",
              background=[("active", select)])

        # --- разделители ---
        s.configure("TSeparator", background=border)

    def _apply_theme(self, name):
        if name not in THEMES:
            name = "dark"
        self.theme = name
        t = THEMES[name]

        # --- выбор базового ttk-движка ---
        is_base = name in BASE_THEMES  # dark / light / black

        if is_base:
            # для базовых — родной sv-ttk (нативный вид)
            sv = t.get("sv") or "dark"
            if sv not in ("dark", "light", "auto"):
                sv = "dark"
            try:
                import sv_ttk
                sv_ttk.set_theme(sv)
            except Exception:
                try:
                    ttk.Style().theme_use("clam")
                except Exception:
                    pass
        else:
            # для кастомных — clam, т.к. sv-ttk игнорирует наши цвета
            try:
                ttk.Style().theme_use("clam")
            except Exception:
                pass

        # --- свои стили поверх (для всех тем) ---
        try:
            self._style_ttk(t)
        except Exception as e:
            print(f"[theme] _style_ttk: {e}")

        ttk.Style().configure("Smooth.TButton",
                              padding=(12, 6),
                              font=("Segoe UI", 9),
                              borderwidth=0,
                              relief="flat")

        self.root.configure(bg=t["bg"])

        # ИС 1 и ИС 2
        for w in (self.editor, self.output):
            w.configure(
                bg=t["field"], fg=t["fg"],
                insertbackground=t["fg"],
                selectbackground=t["select"],
                selectforeground=t["fg"],
                highlightbackground=t["border"],
                highlightcolor=t["accent"])
            if isinstance(w, HighlightedText):
                w.update_colors(name)

        # Примеры и шаблоны
        for w in (self.ex_txt, self.cfg_txt):
            w.configure(
                bg=t["field"], fg=t["fg"],
                insertbackground=t["fg"],
                selectbackground=t["select"],
                selectforeground=t["fg"])

        # Терминал
        self.term.configure(
            bg=t["term_bg"], fg=t["term_fg"],
            insertbackground=t["term_fg"],
            selectbackground=t["select"],
            selectforeground=t["fg"])

        # --- О программе ---
        if hasattr(self, "about_txt"):
            self.about_txt.configure(
                bg=t["bg"], fg=t["fg"],
                insertbackground=t["fg"],
                selectbackground=t["select"],
                selectforeground=t["fg"])

            # определить, светлая ли тема
            def _is_light(hex_color: str) -> bool:
                h = hex_color.lstrip("#")
                r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
                return (0.299 * r + 0.587 * g + 0.114 * b) > 128
            light = _is_light(t["bg"])

            if light:
                C = {
                    "ok":    "#1f7a2e",
                    "bad":   "#a51e35",
                    "warn":  "#b86a10",
                    "path":  "#155a7a",
                    "cmd":   "#7a6200",
                    "num":   "#8a4a10",
                    "os":    "#5a3a8a",
                    "pyver": "#1a5c8a",
                    "ext":   "#155a7a",
                }
            else:
                C = {
                    "ok":    "#4ba554",
                    "bad":   "#c23a58",
                    "warn":  "#dd8a33",
                    "path":  "#37a6b8",
                    "cmd":   "#c7b53a",
                    "num":   "#dd8a33",
                    "os":    "#a95abf",
                    "pyver": "#4fa8d8",
                    "ext":   "#37a6b8",
                }

            self.about_txt.tag_configure("h1", foreground=t["accent"])
            self.about_txt.tag_configure("h2", foreground=t["accent"])
            self.about_txt.tag_configure("h3", foreground=t["accent"])
            self.about_txt.tag_configure("accent", foreground=t["accent"])
            self.about_txt.tag_configure("key", foreground=t["accent"])
            self.about_txt.tag_configure("ver", foreground=t["accent"])

            self.about_txt.tag_configure("ok",    foreground=C["ok"])
            self.about_txt.tag_configure("bad",   foreground=C["bad"])
            self.about_txt.tag_configure("warn",  foreground=C["warn"])
            self.about_txt.tag_configure("path",  foreground=C["path"])
            self.about_txt.tag_configure("cmd",   foreground=C["cmd"])
            self.about_txt.tag_configure("num",   foreground=C["num"])
            self.about_txt.tag_configure("os",    foreground=C["os"])
            self.about_txt.tag_configure("pyver", foreground=C["pyver"])
            self.about_txt.tag_configure("ext",   foreground=C["ext"])
            self.about_txt.tag_configure("dim",   foreground=t["border"])
        # Списки — с учётом UI_SETTINGS["listbox_theme"]
        lb = UI_SETTINGS["listbox_theme"].get(name, {})
        lb_bg     = lb.get("bg", t["field"])
        lb_fg     = lb.get("fg", t["fg"])
        lb_sel_bg = lb.get("select_bg", t["select"])
        lb_sel_fg = lb.get("select_fg", t["fg"])

        for attr in ("theme_list", "tpl_list", "lang_list",
                     "btn_list", "disabled_list"):
            if hasattr(self, attr):
                getattr(self, attr).configure(
                    bg=lb_bg, fg=lb_fg,
                    selectbackground=lb_sel_bg,
                    selectforeground=lb_sel_fg)

        # Холст Rivulet
        if (self.rivulet_canvas is not None
                and hasattr(self.rivulet_canvas, "canvas")):
            try:
                self.rivulet_canvas.canvas.configure(bg=t["field"])
                self.rivulet_canvas._redraw_grid()
            except Exception:
                pass

        # Холст Piet
        if (self.piet_canvas is not None
                and hasattr(self.piet_canvas, "canvas")):
            try:
                self.piet_canvas.canvas.configure(bg=t["field"])
                self.piet_canvas._render()
            except Exception:
                pass

        # Превью темы
        if hasattr(self, "theme_list"):
            self._on_theme_select()

        # Звёздочка текущей темы
        if hasattr(self, "theme_list"):
            keys = list(THEMES.keys())
            if name in keys:
                idx = keys.index(name)
                self.theme_list.selection_clear(0, "end")
                self.theme_list.selection_set(idx)
                self.theme_list.see(idx)

        # === SANDBOX: покрасить все песочницы ===
        for panel in getattr(self, "_sandbox_panels", []):
            try:
                panel.apply_theme(name)
            except Exception:
                pass

        self.set_status(f"Тема: {name}")

    def cycle_theme(self, event=None):
        """Переключить тему на следующую в списке THEMES."""
        keys = list(THEMES.keys())
        idx = keys.index(self.theme) if self.theme in keys else 0
        self._apply_theme(keys[(idx + 1) % len(keys)])

        t = THEMES[self.theme]

        # --- sv-ttk: только dark / light / auto ---
        sv = t.get("sv") or "dark"
        if sv not in ("dark", "light", "auto"):
            sv = "dark"
        try:
            import sv_ttk
            sv_ttk.set_theme(sv)
        except Exception:
            try:
                ttk.Style().theme_use("clam")
            except Exception:
                pass

        # ★ НОВОЕ: перекрасить все ttk-виджеты под палитру темы
        try:
            self._style_ttk(t)
        except Exception:
            pass

        # ... дальше как было: root.configure, editor, output и т.д.

    # ==========================================================
    #  ИНТЕРФЕЙС
    # ==========================================================
    def _refresh_button_list(self):
        if not hasattr(self, "btn_list"):
            return
        self.btn_list.delete(0, "end")
        for key, (btn, default) in self._buttons.items():
            current = btn.cget("text")
            self.btn_list.insert("end", f" {key:12} = {current}")

    def _on_btn_select(self, event=None):
        sel = self.btn_list.curselection()
        if not sel:
            return
        key = list(self._buttons.keys())[sel[0]]
        self.btn_text_var.set(self._buttons[key][0].cget("text"))

    def _apply_btn_rename(self):
        sel = self.btn_list.curselection()
        if not sel:
            return
        key = list(self._buttons.keys())[sel[0]]
        new = self.btn_text_var.get().strip()
        if not new:
            return
        self._buttons[key][0].config(text=new)
        UI_SETTINGS["button_labels"][key] = new
        save_config()
        self._refresh_button_list()
        self.log(f"$ кнопка «{key}» → «{new}»")

    def _reset_button_labels(self):
        if not messagebox.askyesno("Сброс",
                                    "Вернуть все подписи по умолчанию?"):
            return
        for key, (btn, default) in self._buttons.items():
            btn.config(text=default)
        UI_SETTINGS["button_labels"].clear()
        save_config()
        self._refresh_button_list()
        self.log("$ все подписи сброшены")

    def _refresh_listbox_editor(self):
        if not hasattr(self, "lb_colors"):
            return
        theme_name = self.lb_theme_var.get()
        if theme_name not in THEMES:
            theme_name = "dark"
            self.lb_theme_var.set("dark")
        t = THEMES[theme_name]
        custom = UI_SETTINGS["listbox_theme"].get(theme_name, {})
        defaults = {"bg": t["field"], "fg": t["fg"],
                    "select_bg": t["select"], "select_fg": t["fg"]}
        for key, btn in self.lb_colors.items():
            btn.config(text=custom.get(key, defaults[key]))

    def _reset_listbox_colors(self):
        name = self.lb_theme_var.get()
        UI_SETTINGS["listbox_theme"].pop(name, None)
        save_config()
        self._refresh_listbox_editor()
        self._apply_theme(self.theme)
        self.log(f"$ цвета списков для «{name}» сброшены")

    # ==========================================================
    #  ШАБЛОНЫ
    # ==========================================================
    def _refresh_template_languages(self):
        if not hasattr(self, "cfg_lang"):
            return
        names = [l.name for l in registry.all()]
        self.cfg_lang["values"] = names
        if names and self.cfg_lang.get() not in names:
            self.cfg_lang.current(0)
        self._refresh_template_list()

    def _refresh_template_list(self, event=None):
        if not hasattr(self, "tpl_list"):
            return
        self.tpl_list.delete(0, "end")
        lang = registry.get(self.cfg_lang.get())
        if not lang:
            return
        for tn in lang.templates.keys():
            self.tpl_list.insert("end", tn)
        if self.tpl_list.size():
            self.tpl_list.selection_set(0)
            self._on_template_select()

    def _on_template_select(self, event=None):
        sel = self.tpl_list.curselection()
        if not sel:
            return
        lang = registry.get(self.cfg_lang.get())
        if not lang:
            return
        name = self.tpl_list.get(sel[0])
        self.tpl_name_var.set(name)
        self.cfg_txt.delete("1.0", "end")
        self.cfg_txt.insert("1.0", lang.templates.get(name, ""))

    def _save_template_edit(self):
        lang = registry.get(self.cfg_lang.get())
        if not lang:
            return
        sel = self.tpl_list.curselection()
        if not sel:
            return
        old = self.tpl_list.get(sel[0])
        new = self.tpl_name_var.get().strip()
        if not new:
            messagebox.showerror("Ошибка", "Имя пустое")
            return
        code = self.cfg_txt.get("1.0", "end-1c")
        items = list(lang.templates.items())
        lang.templates.clear()
        for k, v in items:
            if k == old:
                lang.templates[new] = code
            else:
                lang.templates[k] = v
        save_config()
        self._refresh_template_list()
        self.on_src()
        self.log(f"$ шаблон «{new}» сохранён")

    def _add_new_template(self):
        lang = registry.get(self.cfg_lang.get())
        if not lang:
            return
        name = simpledialog.askstring(
            "Новый шаблон", "Название:",
            initialvalue="[User] Новый", parent=self.root)
        if not name or name in lang.templates:
            return
        lang.templates[name] = ""
        save_config()
        self._refresh_template_list()
        idx = list(lang.templates.keys()).index(name)
        self.tpl_list.selection_clear(0, "end")
        self.tpl_list.selection_set(idx)
        self.tpl_list.see(idx)
        self._on_template_select()
        self.on_src()

    def _delete_selected_template(self):
        lang = registry.get(self.cfg_lang.get())
        if not lang:
            return
        sel = self.tpl_list.curselection()
        if not sel:
            return
        name = self.tpl_list.get(sel[0])
        if not messagebox.askyesno("Удаление", f"Удалить «{name}»?"):
            return
        lang.templates.pop(name, None)
        save_config()
        self._refresh_template_list()
        self.on_src()

    def _rename_selected_template(self):
        lang = registry.get(self.cfg_lang.get())
        if not lang:
            return
        sel = self.tpl_list.curselection()
        if not sel:
            return
        old = self.tpl_list.get(sel[0])
        new = simpledialog.askstring(
            "Переименовать", "Новое имя:",
            initialvalue=old, parent=self.root)
        if not new or new == old or new in lang.templates:
            return
        items = list(lang.templates.items())
        lang.templates.clear()
        for k, v in items:
            lang.templates[new if k == old else k] = v
        save_config()
        self._refresh_template_list()
        self.on_src()

    def _reset_templates_for_lang(self):
        lang = registry.get(self.cfg_lang.get())
        if not lang:
            return
        if not messagebox.askyesno(
            "Сброс",
            f"Сбросить шаблоны «{lang.title}» к встроенным?\n"
            f"Пользовательские изменения будут потеряны."):
            return
        try:
            mod_name = getattr(lang, "_module_name", None) or lang.name
            mod = importlib.import_module(f"langs.{mod_name}")
            importlib.reload(mod)
            from core.base import Language
            for obj in vars(mod).values():
                if (isinstance(obj, type)
                        and issubclass(obj, Language)
                        and obj is not Language):
                    lang.templates = dict(obj().templates)
                    break
            save_config()
            self._refresh_template_list()
            self.on_src()
            self.log(f"$ шаблоны «{lang.title}» сброшены")
        except Exception as e:
            self.log(f"! {e}")

    # ==========================================================
    #  ЯЗЫКИ
    # ==========================================================
    def _refresh_language_list(self):
        if not hasattr(self, "lang_list"):
            return
        self.lang_list.delete(0, "end")
        for l in registry.all():
            star = "★" if registry.is_system(l.name) else " "
            self.lang_list.insert("end", f" {star} {l.title} ({l.name})")

    def _refresh_disabled_list(self):
        if not hasattr(self, "disabled_list"):
            return
        self.disabled_list.delete(0, "end")
        try:
            for name in list_disabled():
                self.disabled_list.insert("end", f" {name}")
        except Exception as e:
            self.log(f"! не удалось прочитать langs_disabled: {e}")

    def _disable_selected_lang(self):
        sel = self.lang_list.curselection()
        if not sel:
            return
        entry = self.lang_list.get(sel[0])
        name = entry[entry.rfind("(") + 1:-1]
        if registry.is_system(name):
            messagebox.showerror(
                "Ошибка",
                f"«{name}» — системный язык, удалить нельзя")
            return
        if not messagebox.askyesno(
            "Отключить",
            f"Отключить язык «{name}»?\n"
            f"Файл переместится в langs_disabled/."):
            return
        if disable_lang(name):
            self._refresh_language_list()
            self._refresh_disabled_list()
            self._refresh_template_languages()
            self.on_mode()
            self.log(f"$ язык «{name}» отключён (перезапустите приложение)")

    def _enable_selected_lang(self):
        sel = self.disabled_list.curselection()
        if not sel:
            return
        mod_name = self.disabled_list.get(sel[0]).strip()
        if not messagebox.askyesno(
            "Восстановить",
            f"Вернуть язык из «{mod_name}.py»?"):
            return
        if enable_lang(mod_name):
            self.log(f"$ «{mod_name}.py» возвращён "
                     f"(перезапустите приложение)")

    def _rename_language(self):
        sel = self.lang_list.curselection()
        if not sel:
            return
        entry = self.lang_list.get(sel[0])
        name = entry[entry.rfind("(") + 1:-1]
        lang = registry.get(name)
        if not lang:
            return
        new_title = simpledialog.askstring(
            "Переименовать язык",
            f"Новое отображаемое имя для «{lang.title}»:",
            initialvalue=lang.title, parent=self.root)
        if not new_title or new_title == lang.title:
            return
        lang.title = new_title
        UI_SETTINGS["renamed_langs"][name] = new_title
        save_config()
        self._refresh_language_list()
        self.on_src()
        self.log(f"$ язык «{name}» → «{new_title}»")

    def load_custom_lang(self):
        path = filedialog.askopenfilename(
            filetypes=[("Python", "*.py"), ("All", "*.*")])
        if not path:
            return
        try:
            name = load_plugin(path)
            self.on_mode()
            self._refresh_language_list()
            self._refresh_template_languages()
            self.log(f"$ плагин: {name}")
        except Exception as e:
            self.log(f"! {e}")

    def open_plugins_dir(self):
        try:
            if sys.platform == "win32":
                os.startfile(PLUGINS_DIR)
            else:
                os.system(f"xdg-open '{PLUGINS_DIR}'")
        except Exception as e:
            self.log(f"! {e}")

    # ==========================================================
    #  СОБЫТИЯ
    # ==========================================================
    def on_mode(self, event=None):
        label = self.mode.get()
        _, s_cat, _ = next(m for m in MODES if m[0] == label)
        # Сбросить фильтр типа при смене режима
        if hasattr(self, "tpl_type"):
            self.tpl_type.current(0)

        src_list = [l.name for l in registry.by_category(s_cat)]
        self.src["values"] = src_list
        if src_list and self.src.get() not in src_list:
            self.src.current(0)
        self._apply_src_lang()

        self._refresh_dst_list()

        if hasattr(self, "cfg_lang"):
            self.cfg_lang["values"] = [l.name for l in registry.all()]
            if not self.cfg_lang.get() and self.cfg_lang["values"]:
                self.cfg_lang.current(0)

        self._refresh_language_list()
        self._refresh_template_list()
        self.set_status(f"Режим: {label}")

    def on_tpl_type(self, event=None):
        """Изменение фильтра типа → перестроить список шаблонов."""
        self._refresh_tpl_list()

    def _refresh_tpl_list(self):
        """Заполняет Combobox «Шаблон» с учётом фильтра типа."""
        name = self.src.get()
        lang = registry.get(name)
        if not lang:
            self.tpl["values"] = []
            return
        sel = self.tpl_type.get() if hasattr(self, "tpl_type") else "Все"
        if sel == "Все" or not sel:
            filtered = list(lang.templates.keys())
        else:
            code = TYPE_BY_LABEL.get(sel)
            filtered = [n for n in lang.templates
                        if _tpl_classify(n) == code]
        self.tpl["values"] = filtered
        if filtered:
            self.tpl.current(0)
            self.on_tpl()
        else:
            self.tpl.set("")

    def _apply_src_lang(self):
        name = self.src.get()
        lang = registry.get(name)
        if not lang:
            self.src_label.config(text="Язык №1:")
            return
        self.src_label.config(text=f"Язык №1: {lang.title} ({lang.category})")
        if isinstance(self.editor, HighlightedText):
            self.editor.set_language(name)
        self._refresh_tpl_list()

    def _apply_dst_lang(self):
        name = self.dst.get()
        lang = registry.get(name)
        if not lang:
            self.dst_label.config(text="Язык №2:")
            return
        self.dst_label.config(text=f"Язык №2: {lang.title} ({lang.category})")
        if isinstance(self.output, HighlightedText):
            self.output.set_language(name)

    def _refresh_dst_list(self):
        label = self.mode.get()
        _, _, d_cat = next(m for m in MODES if m[0] == label)
        src_name = self.src.get()
        vals = [l.name for l in registry.by_category(d_cat)
                if l.name != src_name]
        self.dst["values"] = vals
        if vals:
            if self.dst.get() not in vals:
                self.dst.current(0)
                self._apply_dst_lang()
        else:
            self.dst.set("")

    def _refresh_src_list(self):
        label = self.mode.get()
        _, s_cat, _ = next(m for m in MODES if m[0] == label)
        dst_name = self.dst.get()
        vals = [l.name for l in registry.by_category(s_cat)
                if l.name != dst_name]
        self.src["values"] = vals
        if vals:
            if self.src.get() not in vals:
                self.src.current(0)
                self._apply_src_lang()
        else:
            self.src.set("")

    def on_src(self, event=None):
        self._apply_src_lang()
        self._refresh_dst_list()

    def on_dst(self, event=None):
        self._apply_dst_lang()
        self._refresh_src_list()

    def on_tpl(self, event=None):
        name = self.src.get()
        tn = self.tpl.get()
        lang = registry.get(name)
        if not lang:
            return
        if tn in lang.templates:
            code = lang.templates[tn]
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", code)
            if isinstance(self.editor, HighlightedText):
                self.editor.highlight()
            self.set_status(f"Шаблон: {tn}")

            # Синхронизация с 2D-холстами
            if name == "rivulet" and self.rivulet_canvas is not None:
                try:
                    self.rivulet_canvas.from_text(code)
                except Exception:
                    pass
            if name == "piet" and self.piet_canvas is not None:
                try:
                    self.piet_canvas.from_text(code)
                except Exception:
                    pass

    # ==========================================================
    #  ДЕЙСТВИЯ
    # ==========================================================
    def do_translate(self):
        src = self.src.get()
        dst = self.dst.get()
        if not src or not dst:
            return
        code = self.editor.get("1.0", "end-1c")
        try:
            result = translate(src, dst, code, None)
            if isinstance(result, tuple):
                result = result[0]
            if not result.endswith("\n"):
                result += "\n"
            self.output.config(state="normal")
            self.output.delete("1.0", "end")
            self.output.insert("1.0", result)
            if isinstance(self.output, HighlightedText):
                self.output.highlight()
            self.output.config(state="disabled")

            # === CANVAS-SYNC + AUTOSWITCH ===
            # Показать результат в 2D-холстах И переключиться на них.
            if dst == "piet" and getattr(self, "piet_canvas", None) is not None:
                try:
                    self.piet_canvas.from_text(result)
                    self.log("$ Piet Canvas: результат перевода загружен")
                    self._switch_to_tab("Piet Canvas")
                except Exception as e:
                    self.log(f"! Piet Canvas: {e}")

            if dst == "rivulet" and getattr(self, "rivulet_canvas", None) is not None:
                try:
                    self.rivulet_canvas.from_text(result)
                    self.log("$ Rivulet Canvas: результат перевода загружен")
                    self._switch_to_tab("Rivulet Canvas")
                except Exception as e:
                    self.log(f"! Rivulet Canvas: {e}")
            # === /CANVAS-SYNC + AUTOSWITCH ===

            self.log(f"$ переведено {src} → {dst}")
            self.set_status("Готово")
        except Exception as e:
            self.log(f"! ошибка: {e}")

    def do_run(self):
        name = self.src.get()
        code = self.editor.get("1.0", "end-1c")
        lang = registry.get(name)
        if not lang:
            return
        try:
            out = lang.execute(code)
            if out is None:
                self.log(f"! {name}: не выполнилось")
                return
            self.log(f"$ вывод: {out!r}")
        except Exception as e:
            self.log(f"! {e}")

    def do_open(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        try:
            with open(path, "rb") as f:
                raw = f.read()
            text = raw.decode("utf-8", errors="replace")
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", text)
            if isinstance(self.editor, HighlightedText):
                self.editor.highlight()
            self.log(f"$ загружено: {path}")
        except Exception as e:
            self.log(f"! {e}")

    def do_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return
        try:
            content = self.output.get("1.0", "end-1c")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log(f"$ сохранено: {path}")
        except Exception as e:
            self.log(f"! {e}")

    def do_clear(self):
        self.editor.delete("1.0", "end")
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")
        self._last_result = None

    # ==========================================================
    #  ТЕРМИНАЛ
    # ==========================================================
    def log(self, text):
        self.term.config(state="normal")
        self.term.insert("end", text + "\n")
        self.term.see("end")
        self.term.config(state="disabled")

    def clear_term(self):
        self.term.config(state="normal")
        self.term.delete("1.0", "end")
        self.term.config(state="disabled")

    def toggle_terminal(self):
        self._term_expanded = not self._term_expanded
        self.term.configure(height=16 if self._term_expanded else 6)

    def set_status(self, text):
        self.status.config(text=text)

    # ==========================================================
    #  КОПИРОВАНИЕ
    # ==========================================================
    def copy_src(self):
        t = self.editor.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(t)
        self.root.update()
        self.log(f"$ ИС 1 → буфер ({len(t)})")

    def paste_src(self):
        try:
            t = self.root.clipboard_get()
            self.editor.insert("insert", t)
            if isinstance(self.editor, HighlightedText):
                self.editor.highlight()
        except Exception:
            pass

    def copy_dst(self):
        t = self.output.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(t)
        self.root.update()
        self.log(f"$ ИС 2 → буфер ({len(t)})")

    # ==========================================================
    #  ПРИМЕРЫ (TXT)
    # ==========================================================
    def _fill_examples(self):
        self.ex_txt.delete("1.0", "end")
        for lang in registry.all():
            self.ex_txt.insert("end", f"## {lang.title}\n")
            for name, code in lang.templates.items():
                self.ex_txt.insert("end", f"### {name}\n{code}\n\n")
            self.ex_txt.insert("end", "\n")

    def _export_examples(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.ex_txt.get("1.0", "end-1c"))
            self.log(f"$ сохранено: {path}")
        except Exception as e:
            self.log(f"! {e}")

    def _import_examples(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt")])
        if not path:
            return
        try:
            content = open(path, encoding="utf-8").read()
        except Exception as e:
            self.log(f"! {e}")
            return

        cur_title, cur_name, buf = None, None, []
        for line in content.splitlines():
            if line.startswith("## "):
                if cur_title and cur_name:
                    for l in registry.all():
                        if l.title == cur_title:
                            l.templates[cur_name] = "\n".join(buf).rstrip()
                cur_title = line[3:].strip()
                cur_name = None
                buf = []
            elif line.startswith("### "):
                if cur_title and cur_name:
                    for l in registry.all():
                        if l.title == cur_title:
                            l.templates[cur_name] = "\n".join(buf).rstrip()
                cur_name = line[4:].strip()
                buf = []
            else:
                buf.append(line)
        if cur_title and cur_name:
            for l in registry.all():
                if l.title == cur_title:
                    l.templates[cur_name] = "\n".join(buf).rstrip()

        self._fill_examples()
        self.on_src()

    # ==========================================================
    #  ГОРЯЧИЕ КЛАВИШИ
    # ==========================================================
    def show_template_stats(self):
        """Debug: печатает статистику типов шаблонов в терминал."""
        from core.template_types import stats
        self.log("--- шаблоны ---")
        for lang in registry.all():
            s = stats(lang.templates)
            self.log(
                f"  {lang.name:<14} "
                f"E={s['E']} M={s['M']} H={s['H']} "
                f"W={s['W']} T={s['T']} ?={s['?']}"
            )

    # ==========================================================
    #  ВКЛАДКА «ПЕСОЧНИЦА»  (=== SANDBOX ===)
    # ==========================================================
    def _build_tab_mosaic(self):
        try:
            from ui.mosaic_tab import MosaicTab
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text="Мозаика")
            ttk.Label(tab,
                      text=f"Не удалось загрузить Мозаику:\n{e}",
                      foreground="red", wraplength=800).pack(pady=20)
            return
        tab = ttk.Frame(self.tabs, padding=6)
        self.tabs.add(tab, text="Мозаика")
        try:
            self.mosaic_tab = MosaicTab(tab, self)
        except Exception as e:
            ttk.Label(tab,
                      text=f"Ошибка при создании Мозаики:\n{e}",
                      foreground="red", wraplength=800).pack(pady=20)

    def _build_tab_sandbox(self):
        try:
            from ui.widgets.sandbox_panel import SandboxPanel
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text="Песочница")
            ttk.Label(
                tab,
                text=f"Не удалось загрузить песочницу:\n{e}",
                foreground="red", wraplength=800,
            ).pack(pady=20, padx=20)
            return

        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="Песочница")
        try:
            self.sandbox = SandboxPanel(
                tab, self,
                initial_lang="python",
                # код подгрузится автоматически из шаблонов языка
            )
            self.sandbox.pack(fill="both", expand=True)
            self._sandbox_panels.append(self.sandbox)
        except Exception as e:
            ttk.Label(
                tab,
                text=f"Ошибка при создании песочницы:\n{e}",
                foreground="red", wraplength=800,
            ).pack(pady=20, padx=20)

    def _switch_to_tab(self, tab_text: str):
        """Переключить Notebook на вкладку с данным текстом."""
        try:
            for i in range(self.tabs.index("end")):
                if self.tabs.tab(i, "text") == tab_text:
                    self.tabs.select(i)
                    return
        except Exception:
            pass

    def _on_close(self):
        """Корректно закрыть Executor и окно."""
        try:
            from services import get_execute_service
            get_execute_service().close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # ==========================================================
    #  ВКЛАДКА «PIET-ASM»
    # ==========================================================
    def _build_tab_piet_asm(self):
        try:
            from langs.piet import EXAMPLES, COMMANDS
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

        # --- тело: палитра слева + редактор + результат ---
        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0)  # палитра
        body.columnconfigure(1, weight=2)  # редактор
        body.columnconfigure(2, weight=2)  # результат
        body.rowconfigure(0, weight=1)

        # ---- палитра команд ----
        pal = ttk.LabelFrame(body, text="Команды", padding=4)
        pal.grid(row=0, column=0, sticky="nsw", padx=(0, 4))

        ttk.Label(pal, text="Клик — вставить",
                  font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 2))

        self.asm_cmd_list = tk.Listbox(
            pal, width=12, height=20,
            font=("Consolas", 10),
            activestyle="none",
            exportselection=False)
        self.asm_cmd_list.pack(side="left", fill="both", expand=True)
        sb_cmd = ttk.Scrollbar(pal, orient="vertical",
                               command=self.asm_cmd_list.yview)
        sb_cmd.pack(side="left", fill="y")
        self.asm_cmd_list.config(yscrollcommand=sb_cmd.set)
        self.asm_cmd_list.bind("<Double-Button-1>",
                               self._asm_insert_cmd)
        self.asm_cmd_list.bind("<Return>", self._asm_insert_cmd)

        # порядок — как в COMMANDS
        _ORDER = ["push", "pop", "add", "sub", "mul", "div", "mod",
                  "not", "gt", "dp", "cc", "dup", "roll", "write",
                  "read", "out_num", "out_char", "nop"]
        for c in _ORDER:
            if c in COMMANDS:
                self.asm_cmd_list.insert("end", c)

        ttk.Button(pal, text="+ push N…",
                   command=self._asm_insert_push,
                   style="Smooth.TButton").pack(fill="x", pady=(4, 0))

        # ---- редактор ----
        left = ttk.LabelFrame(body, text="Piet-ASM код", padding=4)
        left.grid(row=0, column=1, sticky="nsew", padx=4)

        self.asm_editor = tk.Text(
            left, font=("Consolas", 11), wrap="none",
            bd=0, padx=6, pady=4, undo=True)
        self.asm_editor.pack(fill="both", expand=True)

        # ---- результат ----
        right = ttk.LabelFrame(body, text="Результат", padding=4)
        right.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

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
    #  Новые методы для палитры команд
    # ----------------------------------------------------------
    def _asm_insert_cmd(self, event=None):
        sel = self.asm_cmd_list.curselection()
        if not sel:
            return
        cmd = self.asm_cmd_list.get(sel[0])
        self.asm_editor.insert("insert", cmd + "\n")
        self.asm_editor.focus_set()

    def _asm_insert_push(self):
        arg = simpledialog.askinteger(
            "push", "Аргумент push (число):",
            initialvalue=42, minvalue=0, maxvalue=10000,
            parent=self.root)
        if arg is None:
            return
        self.asm_editor.insert("insert", f"push {arg}\n")
        self.asm_editor.focus_set()

    # ----------------------------------------------------------
    def _asm_load_example(self, event=None):
        try:
            from langs.piet import EXAMPLES
        except Exception:
            return
        name = self.asm_example_cb.get()
        code = EXAMPLES.get(name, "")
        self.asm_editor.delete("1.0", "end")
        self.asm_editor.insert("1.0", code)

    def _asm_run(self):
        try:
            from langs.piet import execute_asm
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
            from langs.piet import parse_asm, COMMANDS
            code = self.asm_editor.get("1.0", "end-1c")
            cmds = parse_asm(code)
            lines = []
            for i, (cmd, arg) in enumerate(cmds, 1):
                dh, dl = COMMANDS[cmd]
                arg_s = f" {arg}" if arg is not None else ""
                lines.append(
                    f"  {i:>3}. {cmd}{arg_s:<8} → delta ({dh},{dl})")
            text = "\n".join(lines) if lines else "(пусто)"
            self.asm_output.config(state="normal")
            self.asm_output.delete("1.0", "end")
            self.asm_output.insert("1.0",
                f"Команд: {len(cmds)}\n\n{text}")
            self.asm_output.config(state="disabled")
        except Exception as e:
            self.log(f"! Piet-ASM разбор: {e}")

    def _asm_show_tiles(self):
        try:
            from langs.piet import asm_to_tiles
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

    def _show_explain_window(self, title: str, text: str):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("700x500")
        frame = ttk.Frame(win, padding=8)
        frame.pack(fill="both", expand=True)
        header = ttk.Frame(frame)
        header.pack(fill="x", pady=(0, 6))
        ttk.Label(header, text=title,
                  font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(header, text="Копировать",
                   command=lambda: self._copy_text(text),
                   style="Smooth.TButton").pack(side="right", padx=(4, 0))
        ttk.Button(header, text="Закрыть",
                   command=win.destroy,
                   style="Smooth.TButton").pack(side="right")
        body = ttk.Frame(frame)
        body.pack(fill="both", expand=True)
        txt = tk.Text(body, font=("Consolas", 10), wrap="word",
                      bd=0, padx=8, pady=6)
        txt.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(body, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.config(yscrollcommand=sb.set)
        txt.insert("1.0", text)
        txt.config(state="disabled")

    def _copy_text(self, text: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"$ скопировано ({len(text)} симв.)")

    def _bind_hotkeys(self):

        r = self.root
        r.bind("<F1>", lambda e: self.show_help())
        r.bind("<F2>", lambda e: self._apply_theme("dark"))
        r.bind("<F3>", lambda e: self._apply_theme("light"))
        r.bind("<F4>", lambda e: self._apply_theme("black"))
        r.bind("<F5>", lambda e: self.do_translate())
        r.bind("<F6>", lambda e: self.do_run())
        r.bind("<Control-o>", lambda e: self.do_open())
        r.bind("<Control-s>", lambda e: self.do_save())
        r.bind("<Control-l>", lambda e: self.load_custom_lang())
        r.bind("<Control-grave>", lambda e: self.toggle_terminal())

    def show_help(self):
        try:
            for idx in range(self.tabs.index("end")):
                if self.tabs.tab(idx, "text") == "О программе":  # ← было "Справка"
                    self.tabs.select(idx)
                    return
        except Exception:
            pass

        messagebox.showinfo(
            "О программе",
            "Esolang Translator 2.5\n"
            "MIT License · © 2026\n\n"
            "F1 — эта вкладка\n"
            "F2 / F3 / F4 — тёмная / светлая / чёрная темы\n"
            "F5 — Перевести\n"
            "F6 — Запустить\n"
            "Ctrl+O — Открыть файл\n"
            "Ctrl+S — Сохранить результат\n"
            "Ctrl+L — Загрузить свой язык из файла\n"
            "Ctrl+` — Развернуть / свернуть терминал"
        )