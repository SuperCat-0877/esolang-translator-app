# ui/app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
import os
import sys
import re
import importlib
import json
from pathlib import Path

from core.template_types import (
    classify as _tpl_classify,
    reclassify as _tpl_reclassify,
)
from core.registry import registry
from core.translate import translate
from core.themes import THEMES, BASE_THEMES, syntax_palette
from core.i18n import t as tr, tf, set_lang, get_lang, available_langs
from core.config import (
    save as save_config, load as load_config,
    PLUGINS_DIR, UI_SETTINGS,
    disable_lang, enable_lang, list_disabled,
)
from core.plugins import load_plugin, discover as discover_plugins
from ui.editor import HighlightedText

CODE_FONT = ("Consolas", 11)


def _modes() -> list[tuple[str, str, str]]:
    """Отображаемые метки + внутренние коды категорий (О/Э)."""
    r = tr("cat_regular")
    e = tr("cat_esoteric")
    return [
        (f"{r} = {r}", "О", "О"),
        (f"{r} = {e}", "О", "Э"),
        (f"{e} = {r}", "Э", "О"),
        (f"{e} = {e}", "Э", "Э"),
    ]


class App:
    # ==========================================================
    #  ИНИЦИАЛИЗАЦИЯ
    # ==========================================================
    def __init__(self, root):
        self.root = root
        root.title("Esolang Translator")
        root.geometry("1300x950")
        root.minsize(1000, 750)

        self.theme = "dark"
        self._term_expanded = False
        self.rivulet_canvas = None
        self.piet_canvas = None
        self._buttons = {}
        self._sandbox_panels = []
        self.sandbox = None

        registry.discover_builtin()
        discover_plugins()
        load_config()
        set_lang(UI_SETTINGS.get('language', 'en'))

        # Универсальный fallback: TRANSPILERS[(src, dst)] для всех пар.
        from core.universal_fallback import install as _install_uf
        _uf_added = _install_uf()

        # Пользовательские имена языков
        for lang in registry.all():
            custom = UI_SETTINGS["renamed_langs"].get(lang.name)
            if custom:
                lang.title = custom

        # Переклассификация шаблонов
        self._templates_stats = {}
        for lang in registry.all():
            old_keys = set(lang.templates.keys())
            lang.templates = _tpl_reclassify(lang.templates)
            new_keys = set(lang.templates.keys())
            removed = len(old_keys - new_keys)
            added = len(new_keys - old_keys)
            self._templates_stats[lang.name] = (
                len(old_keys), len(new_keys), removed, added)

        self._build()
        self._apply_theme(self.theme)
        self._bind_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.on_mode()
        self.log("> " + tr("msg_ready"))

        renamed_langs = [
            name for name, (o, n, r, a)
            in self._templates_stats.items()
            if r or a
        ]
        if renamed_langs:
            self.log("[templates] " + tf("msg_tpl_reclassified",
                                          n=len(renamed_langs)))
            if _uf_added:
                self.log("[translate] " + tf("msg_universal_pairs",
                                              n=_uf_added))

    # ==========================================================
    #  ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ==========================================================
    def _build(self):
        self._build_menu()
        self._build_toolbar()
        self._build_terminal()
        self._build_tabs()

    # ---------- МЕНЮ ----------
    def _build_menu(self):
        menubar = tk.Menu(self.root)

        fm = tk.Menu(menubar, tearoff=0)
        fm.add_command(label=tr("otkryt"), accelerator="Ctrl+O",
                       command=self.do_open)
        fm.add_command(label=tr("sohranit"), accelerator="Ctrl+S",
                       command=self.do_save)
        fm.add_separator()
        fm.add_command(label=tr("vyhod"), command=self.root.destroy)
        menubar.add_cascade(label=tr("fayl"), menu=fm)

        vm = tk.Menu(menubar, tearoff=0)
        vm.add_command(label=tr("temnaya_tema_f2"),
                       command=lambda: self._apply_theme("dark"))
        vm.add_command(label=tr("svetlaya_tema_f3"),
                       command=lambda: self._apply_theme("light"))
        vm.add_command(label=tr("chernaya_tema_f4"),
                       command=lambda: self._apply_theme("black"))
        menubar.add_cascade(label=tr("vid"), menu=vm)

        lm = tk.Menu(menubar, tearoff=0)
        lm.add_command(label=tr("zagruzit_yazyk"), accelerator="Ctrl+L",
                       command=self.load_custom_lang)
        lm.add_command(label=tr("otkryt_papku_plaginov"),
                       command=self.open_plugins_dir)
        menubar.add_cascade(label=tr("yazyki"), menu=lm)

        rm = tk.Menu(menubar, tearoff=0)
        rm.add_command(label=tr("perevesti"), accelerator="F5",
                       command=self.do_translate)
        rm.add_command(label=tr("zapustit"), accelerator="F6",
                       command=self.do_run)
        menubar.add_cascade(label=tr("zapusk"), menu=rm)

        hm = tk.Menu(menubar, tearoff=0)
        hm.add_command(label=tr("spravka"), accelerator="F1",
                       command=self.show_help)
        menubar.add_cascade(label=tr("spravka"), menu=hm)

        self.root.config(menu=menubar)

    # ---------- ТУЛБАР ----------
    def _build_toolbar(self):
        tb = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        tb.pack(fill="x")

        ttk.Label(tb, text=tr("rezhim")).grid(row=0, column=0, padx=(0, 5))
        self.mode = ttk.Combobox(tb, values=[m[0] for m in _modes()],
                                 state="readonly", width=10)
        self.mode.current(0)
        self.mode.grid(row=0, column=1, padx=(0, 15))
        self.mode.bind("<<ComboboxSelected>>", self.on_mode)

        ttk.Label(tb, text=tr("iz")).grid(row=0, column=2, padx=(0, 3))
        self.src = ttk.Combobox(tb, values=[], state="readonly", width=14)
        self.src.grid(row=0, column=3, padx=(0, 10))
        self.src.bind("<<ComboboxSelected>>", self.on_src)

        ttk.Label(tb, text=tr("v")).grid(row=0, column=4, padx=(0, 3))
        self.dst = ttk.Combobox(tb, values=[], state="readonly", width=16)
        self.dst.grid(row=0, column=5, padx=(0, 10))
        self.dst.bind("<<ComboboxSelected>>", self.on_dst)

        ttk.Label(tb, text=tr("tip")).grid(row=0, column=6, padx=(0, 3))
        self._tpl_type_pairs = self._tpl_type_labels()
        self.tpl_type = ttk.Combobox(
            tb,
            values=[lbl for lbl, _ in self._tpl_type_pairs],
            state="readonly", width=10,
        )
        self.tpl_type.grid(row=0, column=7, padx=(0, 10))
        self.tpl_type.current(0)
        self.tpl_type.bind("<<ComboboxSelected>>", self.on_tpl_type)

        ttk.Label(tb, text=tr("shablon")).grid(row=0, column=8, padx=(0, 3))
        self.tpl = ttk.Combobox(tb, values=[], state="readonly", width=32)
        self.tpl.grid(row=0, column=9, padx=(0, 10))
        self.tpl.bind("<<ComboboxSelected>>", self.on_tpl)

        # ---------- КНОПКИ ----------
        bt = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        bt.pack(fill="x")

        def mkbtn(key, default_key, cmd):
            default_text = tr(default_key)
            text = UI_SETTINGS["button_labels"].get(key, default_text)
            b = ttk.Button(bt, text=text, command=cmd,
                           style="Smooth.TButton")
            b.pack(side="left", padx=(0, 6))
            self._buttons[key] = (b, default_text)
            return b

        mkbtn("translate", "btn_translate", self.do_translate)
        mkbtn("run", "btn_run", self.do_run)
        ttk.Separator(bt, orient="vertical").pack(side="left", fill="y", padx=6)
        mkbtn("open", "btn_open", self.do_open)
        mkbtn("save", "btn_save", self.do_save)
        mkbtn("clear", "btn_clear", self.do_clear)
        ttk.Separator(bt, orient="vertical").pack(side="left", fill="y", padx=6)
        mkbtn("copy_src", "btn_copy_src", self.copy_src)
        mkbtn("paste_src", "btn_paste_src", self.paste_src)
        mkbtn("copy_dst", "btn_copy_dst", self.copy_dst)
        ttk.Separator(bt, orient="vertical").pack(side="left", fill="y", padx=6)
        mkbtn("load_lang", "btn_load_lang", self.load_custom_lang)
        mkbtn("theme", "btn_theme", self.cycle_theme)

    # ---------- ТЕРМИНАЛ ----------
    def _build_terminal(self):
        self.status = ttk.Label(self.root, text="", padding=(10, 0, 10, 4))
        self.status.pack(fill="x", side="bottom")

        term_frame = ttk.Frame(self.root)
        term_frame.pack(fill="x", side="bottom")

        head = ttk.Frame(term_frame, padding=(10, 2, 10, 0))
        head.pack(fill="x")
        ttk.Label(head, text=tr("terminal"),
                  font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(head, text=tr("ochistit"), command=self.clear_term,
                   style="Smooth.TButton").pack(side="right")
        ttk.Button(head, text=tr("razvernut"), command=self.toggle_terminal,
                   style="Smooth.TButton").pack(side="right", padx=(0, 4))

        self.term = tk.Text(term_frame, height=6, font=("Consolas", 10),
                            wrap="word", bd=0, padx=8, pady=6)
        self.term.pack(fill="x", padx=10, pady=(2, 8))
        self.term.config(state="disabled")

    # ---------- ВКЛАДКИ ----------
    def _build_tabs(self):
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self._build_tab_translate()
        self._build_tab_rivulet()
        self._build_tab_piet()
        self._build_tab_other()
        self._build_tab_examples()
        self._build_tab_about()
        self._build_tab_sandbox()
        self._build_tab_mosaic()
        self._build_tab_piet_asm()

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

    def _tpl_type_labels(self):
        """[(локализованная метка, код типа)] — первым идёт «Все» (code=None)."""
        return [
            (tr("filter_all"), None),
            (tr("tpl_type_E"), "E"),
            (tr("tpl_type_M"), "M"),
            (tr("tpl_type_H"), "H"),
            (tr("tpl_type_W"), "W"),
            (tr("tpl_type_T"), "T"),
        ]

    # ==========================================================
    #  ВКЛАДКА «ПЕРЕВОД»
    # ==========================================================
    def _build_tab_translate(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text=tr("perevod"))

        mid = ttk.Frame(tab)
        mid.pack(fill="both", expand=True)
        mid.columnconfigure(0, weight=1, uniform="half")
        mid.columnconfigure(1, weight=1, uniform="half")
        mid.rowconfigure(0, weight=1)

        left = ttk.Frame(mid)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        self.src_label = ttk.Label(left, text=tr("yazyk_1"))
        self.src_label.grid(row=0, column=0, sticky="w", pady=(0, 3))
        self.editor = self._make_field(left, highlight=True)
        self.editor.grid(row=1, column=0, sticky="nsew")

        right = ttk.Frame(mid)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        self.dst_label = ttk.Label(right, text=tr("yazyk_2"))
        self.dst_label.grid(row=0, column=0, sticky="w", pady=(0, 3))
        self.output = self._make_field(right, highlight=True)
        self.output.grid(row=1, column=0, sticky="nsew")

        self.output.bind("<Key>", lambda e: "break")
        self.output.bind("<<Paste>>", lambda e: "break")
        self.output.bind("<<Cut>>", lambda e: "break")

    def _load_tab_widget(self, tab_key: str, name: str, factory,
                         pack: bool = True):
        """Единая обёртка для загрузки вкладок.

        factory может вернуть:
          • ttk.Frame / tk.Canvas / любой widget → пакуем его самого;
          • объект-контроллер (RivuletCanvasTab, PietCanvasTab, ...),
            который уже сам встроился в переданный parent → ничего
            не пакуем, только возвращаем объект;
          • объект-контроллер с .frame / .widget / .container
            → пакуем этот вложенный виджет.
        """
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text=tr(tab_key))

        try:
            widget = factory(tab)
        except Exception as e:
            ttk.Label(
                tab,
                text=tf("err_canvas_load", name=name) + f"\n{e}",
                foreground="red", wraplength=800,
            ).pack(pady=20, padx=20)
            return None

        if pack:
            target = None

            # 1) сам объект — виджет?
            if hasattr(widget, "pack"):
                target = widget
            else:
                # 2) у контроллера есть типовой атрибут-виджет?
                for attr in ("frame", "widget", "container", "root_widget"):
                    cand = getattr(widget, attr, None)
                    if cand is not None and hasattr(cand, "pack"):
                        target = cand
                        break

            # 3) если нашли — пакуем; иначе считаем, что контроллер
            #    уже сам всё упаковал в parent (типичный случай для
            #    RivuletCanvasTab / PietCanvasTab).
            if target is not None:
                target.pack(fill="both", expand=True)

        return widget

    # ==========================================================
    #  ВКЛАДКА «RIVULET CANVAS»
    # ==========================================================
    def _build_tab_rivulet(self):
        try:
            from ui.rivulet_canvas import RivuletCanvasTab
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text=tr("rivulet_canvas"))
            ttk.Label(tab,
                      text=tf("err_canvas_load",
                              name=tr("rivulet_canvas")) + f"\n{e}",
                      foreground="red", wraplength=800).pack(pady=20, padx=20)
            return

        self.rivulet_canvas = self._load_tab_widget(
            "rivulet_canvas", tr("rivulet_canvas"),
            lambda parent: RivuletCanvasTab(parent, self),
        )

    # ==========================================================
    #  ВКЛАДКА «PIET CANVAS»
    # ==========================================================
    def _build_tab_piet(self):
        try:
            from ui.piet_canvas import PietCanvasTab
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text=tr("piet_canvas"))
            ttk.Label(tab,
                      text=tf("err_canvas_load",
                              name=tr("piet_canvas")) + f"\n{e}",
                      foreground="red", wraplength=800).pack(pady=20, padx=20)
            return

        self.piet_canvas = self._load_tab_widget(
            "piet_canvas", tr("piet_canvas"),
            lambda parent: PietCanvasTab(parent, self),
        )

    # ==========================================================
    #  ВКЛАДКА «ДРУГОЕ»
    # ==========================================================
    def _build_tab_other(self):
        outer = ttk.Frame(self.tabs, padding=(8, 8, 8, 8))
        self.tabs.add(outer, text=tr("drugoe"))

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
        parent.add(tab, text=tr("temy_palette"))

        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        ttk.Label(left, text=tr("vstroennye_temy"),
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
        ttk.Label(right, text=tr("prevyu"),
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        pv = ttk.Frame(right, relief="solid", borderwidth=1)
        pv.pack(fill="both", expand=True, pady=(4, 8))
        self.theme_preview = tk.Text(pv, height=6, font=("Consolas", 10),
                                      wrap="word", bd=0, padx=10, pady=8,
                                      state="disabled")
        self.theme_preview.pack(fill="both", expand=True)

        actions = ttk.LabelFrame(right, text=tr("deystviya"), padding=8)
        actions.pack(fill="x")
        ttk.Button(actions, text=tr("primenit_temu"),
                   command=self._apply_selected_theme,
                   style="Smooth.TButton").pack(fill="x")

    # ---------- ПОД-ВКЛАДКА «ШАБЛОНЫ» ----------
    def _build_templates_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        parent.add(tab, text=tr("shablony_list"))

        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text=tr("yazyk")).pack(side="left", padx=(0, 6))
        self.cfg_lang = ttk.Combobox(top, values=[], state="readonly", width=24)
        self.cfg_lang.pack(side="left", padx=(0, 10))
        self.cfg_lang.bind("<<ComboboxSelected>>",
                            lambda e: self._refresh_template_list())
        ttk.Button(top, text=tr("sbrosit_k_vstroennym"),
                   command=self._reset_templates_for_lang,
                   style="Smooth.TButton").pack(side="right")

        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        ttk.Label(left, text=tr("shablony"),
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

        tb = ttk.Frame(left)
        tb.pack(fill="x")
        ttk.Button(tb, text=tr("dobavit"),
                   command=self._add_new_template,
                   style="Smooth.TButton").pack(side="left", fill="x",
                                                 expand=True, padx=(0, 2))
        ttk.Button(tb, text=tr("udalit"),
                   command=self._delete_selected_template,
                   style="Smooth.TButton").pack(side="left", fill="x",
                                                 expand=True, padx=(2, 0))

        tb2 = ttk.Frame(left)
        tb2.pack(fill="x", pady=(4, 0))
        ttk.Button(tb2, text=tr("pereimenovat"),
                   command=self._rename_selected_template,
                   style="Smooth.TButton").pack(fill="x")

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right, text=tr("nazvanie"),
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tpl_name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.tpl_name_var,
                  font=("Consolas", 11)).pack(fill="x", pady=(4, 8))
        ttk.Label(right, text=tr("kod"),
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

        btns = ttk.Frame(right)
        btns.pack(fill="x")
        ttk.Button(btns, text=tr("sohranit_disk"),
                   command=self._save_template_edit,
                   style="Smooth.TButton").pack(side="left", fill="x",
                                                 expand=True, padx=(0, 3))
        ttk.Button(btns, text=tr("otmenit"),
                   command=self._on_template_select,
                   style="Smooth.TButton").pack(side="left", fill="x",
                                                 expand=True, padx=(3, 0))

    # ---------- ПОД-ВКЛАДКА «ЯЗЫКИ» ----------
    def _build_languages_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        parent.add(tab, text=tr("yazyki_puzzle"))

        ttk.Label(tab, text=tr("langs_hint"),
                  justify="left").pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text=tr("aktivnye"), padding=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        lf1 = ttk.Frame(left)
        lf1.pack(fill="both", expand=True)
        self.lang_list = tk.Listbox(lf1, font=("Segoe UI", 10),
                                     activestyle="none",
                                     exportselection=False)
        self.lang_list.pack(side="left", fill="both", expand=True)
        sb1 = ttk.Scrollbar(lf1, orient="vertical", command=self.lang_list.yview)
        sb1.pack(side="left", fill="y")
        self.lang_list.config(yscrollcommand=sb1.set)

        right = ttk.LabelFrame(body, text=tr("otklyuchennye_langs_disabled"),
                                padding=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        lf2 = ttk.Frame(right)
        lf2.pack(fill="both", expand=True)
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
        ttk.Button(btns, text=tr("pereimenovat_yazyk"),
                   command=self._rename_language,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(btns, text=tr("otklyuchit"),
                   command=self._disable_selected_lang,
                   style="Smooth.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text=tr("vosstanovit_arrow"),
                   command=self._enable_selected_lang,
                   style="Smooth.TButton").pack(side="left", padx=4)
        ttk.Separator(btns, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(btns, text=tr("zagruzit_plagin"),
                   command=self.load_custom_lang,
                   style="Smooth.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text=tr("otkryt_papki"),
                   command=self.open_plugins_dir,
                   style="Smooth.TButton").pack(side="left", padx=4)

    # ---------- ПОД-ВКЛАДКА «ИНТЕРФЕЙС» ----------
    def _build_ui_tab(self, parent):
        tab = ttk.Frame(parent, padding=10)
        parent.add(tab, text=tr("interfeys_gear"))

        # --- Подписи кнопок ---
        btn_frame = ttk.LabelFrame(tab, text=tr("podpisi_knopok"), padding=8)
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
        ttk.Label(ctrl, text=tr("novyy_tekst")).pack(anchor="w")
        self.btn_text_var = tk.StringVar()
        ttk.Entry(ctrl, textvariable=self.btn_text_var, width=28).pack(pady=4)
        ttk.Button(ctrl, text=tr("primenit"),
                   command=self._apply_btn_rename,
                   style="Smooth.TButton").pack(fill="x", pady=2)
        ttk.Button(ctrl, text=tr("sbrosit_vse"),
                   command=self._reset_button_labels,
                   style="Smooth.TButton").pack(fill="x", pady=2)

        # --- Язык / Language ---
        lang_frame = ttk.LabelFrame(tab, text=tr("lang_section"), padding=8)
        lang_frame.pack(fill="x", pady=(0, 10))

        self.lang_var = tk.StringVar(value=get_lang())
        for _code in available_langs():
            ttk.Radiobutton(
                lang_frame,
                text=_code.upper(),
                variable=self.lang_var,
                value=_code,
                command=self._change_language,
            ).pack(side="left", padx=4)

        ttk.Label(
            lang_frame,
            text=tr("restart_hint"),
            font=("Segoe UI", 8),
        ).pack(side="left", padx=(12, 0))

        # --- Цвета списков для темы ---
        lb_frame = ttk.LabelFrame(tab, text=tr("cveta_spiskov_dlya"),
                                   padding=8)
        lb_frame.pack(fill="x", pady=(0, 10))

        top = ttk.Frame(lb_frame)
        top.pack(fill="x")
        ttk.Label(top, text=tr("tema")).pack(side="left", padx=(0, 6))
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
        for key, label_key in (
                ("bg", "lb_color_bg"),
                ("fg", "lb_color_fg"),
                ("select_bg", "lb_color_select_bg"),
                ("select_fg", "lb_color_select_fg"),
        ):
            col = ttk.Frame(colors_frame)
            col.pack(side="left", padx=4)
            ttk.Label(col, text=tr(label_key),
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
                    new = colorchooser.askcolor(
                        color=current,
                        title=tf("dlg_color_pick", key=k),
                    )[1]
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
        ttk.Button(reset_row, text=tr("sbrosit_cveta_dlya"),
                   command=self._reset_listbox_colors,
                   style="Smooth.TButton").pack(side="left")

    # ==========================================================
    #  ВКЛАДКА «ПРИМЕРЫ (TXT)»
    # ==========================================================
    def _build_tab_examples(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text=tr("primery_txt"))

        self.ex_txt = self._make_field(tab, highlight=False)
        self.ex_txt.pack(fill="both", expand=True, pady=(4, 8))
        self._fill_examples()

        btns = ttk.Frame(tab)
        btns.pack(fill="x")
        ttk.Button(btns, text=tr("sohranit_v_txt"),
                   command=self._export_examples,
                   style="Smooth.TButton").pack(side="left", padx=(0, 5))
        ttk.Button(btns, text=tr("zagruzit_iz_txt"),
                   command=self._import_examples,
                   style="Smooth.TButton").pack(side="left", padx=(0, 5))
        ttk.Button(btns, text=tr("obnovit"),
                   command=self._fill_examples,
                   style="Smooth.TButton").pack(side="left")

    # ==========================================================
    #  ВКЛАДКА «О ПРОГРАММЕ»
    # ==========================================================
    def _build_tab_about(self):
        tab = ttk.Frame(self.tabs, padding=0)
        self.tabs.add(tab, text=tr("o_programme"))

        wrapper = ttk.Frame(tab)
        wrapper.pack(fill="both", expand=True)

        self.about_txt = tk.Text(
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

        # Заголовки
        self.about_txt.tag_configure("h1", font=("Segoe UI", 18, "bold"))
        self.about_txt.tag_configure("h2", font=("Segoe UI", 12, "bold"))
        self.about_txt.tag_configure("h3", font=("Segoe UI", 10, "bold"))
        self.about_txt.tag_configure("mono", font=("Consolas", 10))
        self.about_txt.tag_configure("accent", font=("Consolas", 10, "bold"))

        # Семантические теги (цвета задаст _apply_theme)
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
        self._fill_about()
        self.about_txt.config(state="disabled")

    def _insert_line(self, base_tag: str, text: str) -> None:
        """Вставляет одну строку. Поддерживает маркеры {tag|текст}."""
        t = self.about_txt
        pattern = re.compile(r"\{(\w+)\|([^}]*)\}")
        pos = 0
        for m in pattern.finditer(text):
            if m.start() > pos:
                chunk = text[pos:m.start()]
                if base_tag:
                    t.insert("end", chunk, base_tag)
                else:
                    t.insert("end", chunk)
            tag, content = m.group(1), m.group(2)
            t.insert("end", content, tag)
            pos = m.end()
        if pos < len(text):
            chunk = text[pos:]
            if base_tag:
                t.insert("end", chunk, base_tag)
            else:
                t.insert("end", chunk)
        t.insert("end", "\n")

    def _fill_about(self):
        """Строит текст About из locales/about.json с fallback на встроенный."""
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

        # Загрузка контента
        sections = None
        try:
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
            about_path = base / "locales" / "about.json"
            if about_path.exists():
                data = json.loads(about_path.read_text(encoding="utf-8"))
                sections = (data.get(get_lang())
                            or data.get("en")
                            or data.get("ru"))
        except Exception as e:
            print(f"[about] load: {e}")

        if not sections:
            sections = [
                ("h1", tr("esolang_translator")),
                ("mono", "© 2026"),
            ]

        def sub(text: str) -> str:
            text = text.replace("<os_name>", os_name)
            text = text.replace("<py_ver>",  py_ver)
            text = text.replace("<pil>",     pil)
            text = text.replace("<cairo>",   cairo)
            text = text.replace("<svttk>",   svttk)
            text = text.replace("<total>",          str(total))
            text = text.replace("<ordinary_count>", str(len(ordinary)))
            text = text.replace("<esoteric_count>", str(len(esoteric)))
            text = text.replace("<ordinary_list>",  ", ".join(ordinary))
            text = text.replace("<esoteric_list>",  ", ".join(esoteric))
            return text

        for tag, text in sections:
            self._insert_line(tag, sub(text))

        t.insert("end", "  Pillow (PIL):  ")
        t.insert("end", pil + "\n", "ok" if pil == "✔" else "bad")
        t.insert("end", "  cairosvg:      ")
        t.insert("end", cairo + "\n", "ok" if cairo == "✔" else "bad")
        t.insert("end", "  sv-ttk:        ")
        t.insert("end", svttk + "\n", "ok" if svttk == "✔" else "bad")

        t.config(state="disabled")

    # ==========================================================
    #  ЯЗЫК ИНТЕРФЕЙСА
    # ==========================================================
    def _change_language(self):
        code = self.lang_var.get()
        UI_SETTINGS["language"] = code
        save_config()
        set_lang(code)
        self._retranslate_ui()

    def _retranslate_ui(self):
        """Пересоздаёт интерфейс с новым языком, сохраняя состояние."""
        try:
            state = {
                "editor": self.editor.get("1.0", "end-1c"),
                "output": self.output.get("1.0", "end-1c"),
                "src": self.src.get(),
                "dst": self.dst.get(),
                "mode_idx": self.mode.current(),
                "theme": self.theme,
            }
        except Exception:
            state = {}

        for w in list(self.root.winfo_children()):
            if isinstance(w, tk.Menu):
                continue
            w.destroy()

        self._buttons = {}
        self.rivulet_canvas = None
        self.piet_canvas = None
        self._sandbox_panels = []

        self._build()
        self._apply_theme(state.get("theme", "dark"))
        self._bind_hotkeys()

        if state.get("editor"):
            self.editor.insert("1.0", state["editor"])
            if isinstance(self.editor, HighlightedText):
                self.editor.highlight()
        if state.get("output"):
            self.output.config(state="normal")
            self.output.insert("1.0", state["output"])
            self.output.config(state="disabled")
        if state.get("src"):
            try:
                self.src.set(state["src"])
                self.on_src()
            except Exception:
                pass
        if state.get("dst"):
            try:
                self.dst.set(state["dst"])
                self.on_dst()
            except Exception:
                pass
        if state.get("mode_idx") is not None:
            try:
                self.mode.current(state["mode_idx"])
                self.on_mode()
            except Exception:
                pass

        self.log("$ " + tf("msg_lang_switched", code=get_lang()))

    # ==========================================================
    #  ТЕМЫ
    # ==========================================================
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
        self.theme_preview.insert("end", "    # comment\n")
        self.theme_preview.insert("end", "    print(f'Hello, {name}!')\n")
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
        """Красит ttk-виджеты под палитру темы (стиль clam)."""
        s = ttk.Style()

        bg     = t.get("bg",      "#1e1e1e")
        fg     = t.get("fg",      "#d4d4d4")
        field  = t.get("field",   bg)
        select = t.get("select",  "#264f78")
        border = t.get("border",  "#3c3c3c")
        accent = t.get("accent",  "#4ea1ff")

        for cls in ("TFrame", "TLabelframe", "TNotebook", "TPanedwindow"):
            s.configure(cls, background=bg, bordercolor=border,
                        lightcolor=bg, darkcolor=bg)
        s.configure("TLabelframe.Label", background=bg, foreground=fg)

        for cls in ("TLabel", "TCheckbutton", "TRadiobutton"):
            s.configure(cls, background=bg, foreground=fg)
            s.map(cls,
                  background=[("active", bg)],
                  foreground=[("disabled", border)])

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

        s.configure("TEntry",
                    fieldbackground=field, foreground=fg,
                    bordercolor=border,
                    lightcolor=border, darkcolor=border)
        s.map("TEntry",
              fieldbackground=[("readonly", bg)],
              foreground=[("disabled", border)])

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

        self.root.option_add("*TCombobox*Listbox.background", field)
        self.root.option_add("*TCombobox*Listbox.foreground", fg)
        self.root.option_add("*TCombobox*Listbox.selectBackground", select)
        self.root.option_add("*TCombobox*Listbox.selectForeground", fg)

        s.configure("TNotebook", background=bg, bordercolor=border,
                    lightcolor=bg, darkcolor=bg)
        s.configure("TNotebook.Tab",
                    background=bg, foreground=fg,
                    padding=(12, 6), bordercolor=border,
                    lightcolor=bg, darkcolor=bg)
        s.map("TNotebook.Tab",
              background=[("selected", field), ("active", select)],
              foreground=[("selected", accent)])

        s.configure("TScrollbar",
                    background=field, troughcolor=bg,
                    bordercolor=border, arrowcolor=fg,
                    lightcolor=field, darkcolor=field)
        s.map("TScrollbar",
              background=[("active", select)])

        s.configure("TSeparator", background=border)

    def _apply_theme(self, name):
        if name not in THEMES:
            name = "dark"
        self.theme = name
        t = THEMES[name]

        is_base = name in BASE_THEMES
        if is_base:
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
            try:
                ttk.Style().theme_use("clam")
            except Exception:
                pass

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

        for w in (self.ex_txt, self.cfg_txt):
            w.configure(
                bg=t["field"], fg=t["fg"],
                insertbackground=t["fg"],
                selectbackground=t["select"],
                selectforeground=t["fg"])

        self.term.configure(
            bg=t["term_bg"], fg=t["term_fg"],
            insertbackground=t["term_fg"],
            selectbackground=t["select"],
            selectforeground=t["fg"])

        if hasattr(self, "about_txt"):
            self._apply_theme_about(t)

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

        if (self.rivulet_canvas is not None
                and hasattr(self.rivulet_canvas, "canvas")):
            try:
                self.rivulet_canvas.canvas.configure(bg=t["field"])
                self.rivulet_canvas._redraw_grid()
            except Exception:
                pass

        if (self.piet_canvas is not None
                and hasattr(self.piet_canvas, "canvas")):
            try:
                self.piet_canvas.canvas.configure(bg=t["field"])
                self.piet_canvas._render()
            except Exception:
                pass

        if hasattr(self, "theme_list"):
            self._on_theme_select()

        if hasattr(self, "theme_list"):
            keys = list(THEMES.keys())
            if name in keys:
                idx = keys.index(name)
                self.theme_list.selection_clear(0, "end")
                self.theme_list.selection_set(idx)
                self.theme_list.see(idx)

        for panel in getattr(self, "_sandbox_panels", []):
            try:
                panel.apply_theme(name)
            except Exception:
                pass

        self.set_status(f"{tr('status_theme')} {name}")

    def _apply_theme_about(self, t):
        """Красит текст About под палитру темы."""
        self.about_txt.configure(
            bg=t["bg"], fg=t["fg"],
            insertbackground=t["fg"],
            selectbackground=t["select"],
            selectforeground=t["fg"])

        def _is_light(hex_color: str) -> bool:
            h = hex_color.lstrip("#")
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
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

    def cycle_theme(self, event=None):
        """Переключить тему на следующую в списке THEMES."""
        keys = list(THEMES.keys())
        idx = keys.index(self.theme) if self.theme in keys else 0
        self._apply_theme(keys[(idx + 1) % len(keys)])

    # ==========================================================
    #  ИНТЕРФЕЙС — КНОПКИ / СПИСКИ
    # ==========================================================
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
        self.log("$ " + tf("msg_btn_renamed", key=key, new=new))

    def _reset_button_labels(self):
        if not messagebox.askyesno(
                tr("dlg_reset"),
                tr("dlg_confirm_reset_labels")):
            return
        for key, (btn, default) in self._buttons.items():
            btn.config(text=default)
        UI_SETTINGS["button_labels"].clear()
        save_config()
        self._refresh_button_list()
        self.log("$ " + tr("msg_labels_reset"))

    def _refresh_button_list(self):
        if not hasattr(self, "btn_list"):
            return
        self.btn_list.delete(0, "end")
        for key, (btn, default) in self._buttons.items():
            self.btn_list.insert("end", f" {key:<12} = {btn.cget('text')}")

    def _on_btn_select(self, event=None):
        sel = self.btn_list.curselection()
        if not sel:
            return
        key = list(self._buttons.keys())[sel[0]]
        self.btn_text_var.set(self._buttons[key][0].cget("text"))

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
        self.log("$ " + tf("msg_lb_colors_reset", name=name))

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
            messagebox.showerror(tr("dlg_reset"),
                                 tr("err_template_empty_name"))
            return
        code = self.cfg_txt.get("1.0", "end-1c")
        items = list(lang.templates.items())
        lang.templates.clear()
        for k, v in items:
            lang.templates[new if k == old else k] = code if k == old else v
        save_config()
        self._refresh_template_list()
        self.on_src()
        self.log("$ " + tf("msg_tpl_saved", name=new))

    def _add_new_template(self):
        lang = registry.get(self.cfg_lang.get())
        if not lang:
            return
        name = simpledialog.askstring(
            tr("dlg_new_template"), tr("dlg_name"),
            initialvalue=tr("dlg_new_template_default"),
            parent=self.root,
        )
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
        if not messagebox.askyesno(
                tr("dlg_delete"),
                tf("dlg_confirm_delete", name=name)):
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
            tr("dlg_rename"), tr("dlg_rename_prompt"),
            initialvalue=old, parent=self.root,
        )
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
                tr("dlg_reset"),
                tf("dlg_reset_templates", title=lang.title)):
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
            self.log("$ " + tf("msg_tpl_reset", title=lang.title))
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))

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
            self.log("! " + tf("err_read_disabled", e=e))

    def _disable_selected_lang(self):
        sel = self.lang_list.curselection()
        if not sel:
            return
        entry = self.lang_list.get(sel[0])
        name = entry[entry.rfind("(") + 1:-1]
        if registry.is_system(name):
            messagebox.showerror(
                tr("dlg_disable"),
                tf("err_system_lang", name=name),
            )
            return
        if not messagebox.askyesno(
                tr("dlg_disable"),
                tf("dlg_confirm_disable", name=name)):
            return
        if disable_lang(name):
            self._refresh_language_list()
            self._refresh_disabled_list()
            self._refresh_template_languages()
            self.on_mode()
            self.log("$ " + tf("msg_lang_disabled", name=name))

    def _enable_selected_lang(self):
        sel = self.disabled_list.curselection()
        if not sel:
            return
        mod_name = self.disabled_list.get(sel[0]).strip()
        if not messagebox.askyesno(
                tr("dlg_restore"),
                tf("dlg_confirm_restore", mod=mod_name)):
            return
        if enable_lang(mod_name):
            self.log("$ " + tf("msg_lang_enabled", mod=mod_name))

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
            tr("dlg_rename_lang"),
            tf("dlg_rename_lang_prompt", title=lang.title),
            initialvalue=lang.title, parent=self.root,
        )
        if not new_title or new_title == lang.title:
            return
        lang.title = new_title
        UI_SETTINGS["renamed_langs"][name] = new_title
        save_config()
        self._refresh_language_list()
        self.on_src()
        self.log("$ " + tf("msg_lang_renamed",
                           name=name, title=new_title))

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
            self.log("$ " + tf("msg_plugin_loaded", name=name))
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))

    def open_plugins_dir(self):
        try:
            if sys.platform == "win32":
                os.startfile(PLUGINS_DIR)
            else:
                os.system(f"xdg-open '{PLUGINS_DIR}'")
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))

    # ==========================================================
    #  СОБЫТИЯ
    # ==========================================================
    def on_mode(self, event=None):
        label = self.mode.get()
        _, s_cat, _ = next(m for m in _modes() if m[0] == label)
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
        self.set_status(f"{tr('status_mode')} {label}")

    def on_tpl_type(self, event=None):
        self._refresh_tpl_list()

    def _refresh_tpl_list(self):
        """Заполняет Combobox «Шаблон» с учётом фильтра типа."""
        name = self.src.get()
        lang = registry.get(name)
        if not lang:
            self.tpl["values"] = []
            return

        sel_label = (self.tpl_type.get()
                     if hasattr(self, "tpl_type") else "")
        code = next(
            (c for lbl, c in getattr(self, "_tpl_type_pairs", [])
             if lbl == sel_label),
            None,
        )

        if code is None:
            filtered = list(lang.templates.keys())
        else:
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
            self.src_label.config(text=tr("yazyk_1"))
            return
        self.src_label.config(
            text=f"{tr('yazyk_1')} {lang.title} ({lang.category})")
        if isinstance(self.editor, HighlightedText):
            self.editor.set_language(name)
        self._refresh_tpl_list()

    def _apply_dst_lang(self):
        name = self.dst.get()
        lang = registry.get(name)
        if not lang:
            self.dst_label.config(text=tr("yazyk_2"))
            return
        self.dst_label.config(
            text=f"{tr('yazyk_2')} {lang.title} ({lang.category})")
        if isinstance(self.output, HighlightedText):
            self.output.set_language(name)

    def _refresh_dst_list(self):
        label = self.mode.get()
        _, _, d_cat = next(m for m in _modes() if m[0] == label)
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
        _, s_cat, _ = next(m for m in _modes() if m[0] == label)
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
            self.set_status(f"{tr('status_template')} {tn}")

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

            if dst == "piet" and getattr(self, "piet_canvas", None) is not None:
                try:
                    self.piet_canvas.from_text(result)
                    self.log("$ " + tf("msg_canvas_loaded",
                                       name=tr("piet_canvas")))
                    self._switch_to_tab(tr("piet_canvas"))
                except Exception as e:
                    self.log("! " + tf("err_generic", e=e))

            if (dst == "rivulet"
                    and getattr(self, "rivulet_canvas", None) is not None):
                try:
                    self.rivulet_canvas.from_text(result)
                    self.log("$ " + tf("msg_canvas_loaded",
                                       name=tr("rivulet_canvas")))
                    self._switch_to_tab(tr("rivulet_canvas"))
                except Exception as e:
                    self.log("! " + tf("err_generic", e=e))

            self.log("$ " + tf("msg_translated", src=src, dst=dst))
            self.set_status(tr("status_ready"))
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))

    def do_run(self):
        name = self.src.get()
        code = self.editor.get("1.0", "end-1c")
        lang = registry.get(name)
        if not lang:
            return
        try:
            out = lang.execute(code)
            if out is None:
                self.log("! " + tf("err_run_failed", name=name))
                return
            self.log("$ " + tf("err_output", out=repr(out)))
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))

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
            self.log("$ " + tf("msg_loaded", path=path))
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))

    def do_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return
        try:
            content = self.output.get("1.0", "end-1c")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log("$ " + tf("msg_saved", path=path))
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))

    def do_clear(self):
        self.editor.delete("1.0", "end")
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")

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
        self.log("$ " + tf("msg_clip_src", n=len(t)))

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
        self.log("$ " + tf("msg_clip_dst", n=len(t)))

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
            self.log("$ " + tf("msg_saved", path=path))
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))

    def _import_examples(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt")])
        if not path:
            return
        try:
            content = open(path, encoding="utf-8").read()
        except Exception as e:
            self.log("! " + tf("err_generic", e=e))
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
        self.log("--- " + tr("shablony_list") + " ---")
        for lang in registry.all():
            s = stats(lang.templates)
            self.log(
                f"  {lang.name:<14} "
                f"E={s['E']} M={s['M']} H={s['H']} "
                f"W={s['W']} T={s['T']} ?={s['?']}"
            )

    # ==========================================================
    #  ВКЛАДКА «МОЗАИКА»
    # ==========================================================
    def _build_tab_mosaic(self):
        try:
            from ui.mosaic_tab import MosaicTab
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text=tr("mozaika"))
            ttk.Label(tab,
                      text=tf("err_canvas_load", name=tr("mozaika")) + f"\n{e}",
                      foreground="red", wraplength=800).pack(pady=20)
            return
        tab = ttk.Frame(self.tabs, padding=6)
        self.tabs.add(tab, text=tr("mozaika"))
        try:
            self.mosaic_tab = MosaicTab(tab, self)
        except Exception as e:
            ttk.Label(tab,
                      text=tf("err_canvas_create",
                              name=tr("mozaika")) + f"\n{e}",
                      foreground="red", wraplength=800).pack(pady=20)

    # ==========================================================
    #  ВКЛАДКА «ПЕСОЧНИЦА»
    # ==========================================================
    def _build_tab_sandbox(self):
        try:
            from ui.widgets.sandbox_panel import SandboxPanel
        except Exception as e:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text=tr("pesochnica"))
            ttk.Label(tab,
                      text=tf("err_canvas_load",
                              name=tr("pesochnica")) + f"\n{e}",
                      foreground="red", wraplength=800).pack(pady=20, padx=20)
            return

        self.sandbox = self._load_tab_widget(
            "pesochnica", tr("pesochnica"),
            lambda parent: SandboxPanel(parent, self, initial_lang="python"),
        )
        if self.sandbox is not None:
            self._sandbox_panels.append(self.sandbox)

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
            self.tabs.add(tab, text=tr("piet_asm"))
            ttk.Label(tab, text=tf("err_generic", e=e),
                      foreground="red").pack()
            return

        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text=tr("piet_asm"))

        # --- верхняя панель ---
        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 6))

        ttk.Label(top, text=tr("primer")).pack(side="left", padx=(0, 4))
        self.asm_example_cb = ttk.Combobox(
            top, values=list(EXAMPLES.keys()),
            state="readonly", width=22)
        self.asm_example_cb.pack(side="left", padx=(0, 10))
        self.asm_example_cb.bind("<<ComboboxSelected>>",
                                  self._asm_load_example)
        if EXAMPLES:
            self.asm_example_cb.current(0)

        ttk.Button(top, text=tr("zapustit_play"),
                   command=self._asm_run,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text=tr("razobrat_search"),
                   command=self._asm_explain,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text=tr("plitki_box"),
                   command=self._asm_show_tiles,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(top, text=tr("kopir_rezultat"),
                   command=self._asm_copy,
                   style="Smooth.TButton").pack(side="left")

        self.asm_status = ttk.Label(top, text="")
        self.asm_status.pack(side="right")

        # --- тело ---
        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=2)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        # палитра команд
        pal = ttk.LabelFrame(body, text=tr("komandy"), padding=4)
        pal.grid(row=0, column=0, sticky="nsw", padx=(0, 4))

        ttk.Label(pal, text=tr("klik_vstavit"),
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
        self.asm_cmd_list.bind("<Double-Button-1>", self._asm_insert_cmd)
        self.asm_cmd_list.bind("<Return>", self._asm_insert_cmd)

        _ORDER = ["push", "pop", "add", "sub", "mul", "div", "mod",
                  "not", "gt", "dp", "cc", "dup", "roll", "write",
                  "read", "out_num", "out_char", "nop"]
        for c in _ORDER:
            if c in COMMANDS:
                self.asm_cmd_list.insert("end", c)

        ttk.Button(pal, text=tr("push_n"),
                   command=self._asm_insert_push,
                   style="Smooth.TButton").pack(fill="x", pady=(4, 0))

        # редактор
        left = ttk.LabelFrame(body, text=tr("piet_asm_kod"), padding=4)
        left.grid(row=0, column=1, sticky="nsew", padx=4)

        self.asm_editor = tk.Text(
            left, font=("Consolas", 11), wrap="none",
            bd=0, padx=6, pady=4, undo=True)
        self.asm_editor.pack(fill="both", expand=True)

        # результат
        right = ttk.LabelFrame(body, text=tr("rezultat"), padding=4)
        right.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        self.asm_output = tk.Text(
            right, font=("Consolas", 11), wrap="word",
            bd=0, padx=6, pady=4, state="disabled", height=8)
        self.asm_output.pack(fill="both", expand=True)

        # нижняя панель: плитки
        bottom = ttk.LabelFrame(tab, text=tr("plitki_16_16"), padding=4)
        bottom.pack(fill="both", expand=False, pady=(6, 0))

        pbar = ttk.Frame(bottom)
        pbar.pack(fill="x", pady=(0, 4))

        ttk.Button(pbar, text="◀", width=3,
                   command=self._asm_tile_prev,
                   style="Smooth.TButton").pack(side="left", padx=(0, 4))
        self.asm_tile_lbl = ttk.Label(pbar, text=tr("str_81"),
                                      font=("Segoe UI", 10, "bold"))
        self.asm_tile_lbl.pack(side="left", padx=(0, 4))
        ttk.Button(pbar, text="▶", width=3,
                   command=self._asm_tile_next,
                   style="Smooth.TButton").pack(side="left", padx=(0, 12))

        ttk.Label(pbar, text=tr("zum")).pack(side="left", padx=(0, 4))
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

        # состояние
        self._asm_tiles = []
        self._asm_tile_idx = 0
        self._asm_zoom = 4
        self._asm_img = None

        self._asm_load_example()

    # ---------- Piet-ASM: палитра команд ----------
    def _asm_insert_cmd(self, event=None):
        sel = self.asm_cmd_list.curselection()
        if not sel:
            return
        cmd = self.asm_cmd_list.get(sel[0])
        self.asm_editor.insert("insert", cmd + "\n")
        self.asm_editor.focus_set()

    def _asm_insert_push(self):
        arg = simpledialog.askinteger(
            tr("dlg_push"), tr("dlg_push_arg"),
            initialvalue=42, minvalue=0, maxvalue=10000,
            parent=self.root,
        )
        if arg is None:
            return
        self.asm_editor.insert("insert", f"push {arg}\n")
        self.asm_editor.focus_set()

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
            self.log("$ " + tf("msg_piet_asm_out", result=repr(result)))
        except Exception as e:
            self.asm_output.config(state="normal")
            self.asm_output.delete("1.0", "end")
            self.asm_output.insert("1.0", tf("err_generic", e=e))
            self.asm_output.config(state="disabled")
            self.asm_status.config(text=tr("oshibka"))
            self.log("! " + tf("msg_piet_asm_err", e=e))

    def _asm_explain(self):
        try:
            from langs.piet import parse_asm, COMMANDS
            code = self.asm_editor.get("1.0", "end-1c")
            cmds = parse_asm(code)
            lines = [
                tf("asm_explain_line",
                   i=i, cmd=cmd,
                   arg=(f" {arg}" if arg is not None else ""),
                   dh=COMMANDS[cmd][0], dl=COMMANDS[cmd][1])
                for i, (cmd, arg) in enumerate(cmds, 1)
            ]
            body = "\n".join(lines) if lines else tr("empty")
            header = tf("asm_explain_header", n=len(cmds))
            self.asm_output.config(state="normal")
            self.asm_output.delete("1.0", "end")
            self.asm_output.insert("1.0", f"{header}\n\n{body}")
            self.asm_output.config(state="disabled")
        except Exception as e:
            self.log("! " + tf("msg_piet_asm_parse_err", e=e))

    def _asm_show_tiles(self):
        try:
            from langs.piet import asm_to_tiles
            code = self.asm_editor.get("1.0", "end-1c")
            tiles = asm_to_tiles(code)
            self._asm_tiles = tiles
            self._asm_tile_idx = 0
            self._asm_render_tile()
            self.log("$ " + tf("msg_piet_asm_tiles", n=len(tiles)))
        except Exception as e:
            self.log("! " + tf("msg_piet_asm_tiles_err", e=e))

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
            import base64
            import io
            from PIL import Image, ImageTk
        except ImportError:
            return
        if not self._asm_tiles:
            self.asm_tile_lbl.config(text=tr("str_81"))
            self.asm_canvas.delete("all")
            return

        n = len(self._asm_tiles)
        self.asm_tile_lbl.config(text=f"{self._asm_tile_idx + 1}/{n}")

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
            self.asm_canvas.config(scrollregion=(0, 0, im.width, im.height))
        except Exception as e:
            self.log("! " + tf("msg_drawing_tile_err", e=e))

    def _asm_copy(self):
        text = self.asm_output.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log("$ " + tf("msg_clip_result", n=len(text)))

    # ==========================================================
    #  ОКНО «ОБЪЯСНЕНИЕ»
    # ==========================================================
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
        ttk.Button(header, text=tr("kopirovat"),
                   command=lambda: self._copy_text(text),
                   style="Smooth.TButton").pack(side="right", padx=(4, 0))
        ttk.Button(header, text=tr("zakryt"),
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
        self.log("$ " + tf("msg_copied", n=len(text)))

    # ==========================================================
    #  ГОРЯЧИЕ КЛАВИШИ
    # ==========================================================
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
                if self.tabs.tab(idx, "text") == tr("o_programme"):
                    self.tabs.select(idx)
                    return
        except Exception:
            pass

        messagebox.showinfo(
            tr("o_programme"),
            "Esolang Translator 2.6\n"
            "MIT License · © 2026\n\n"
            "F1 — help\n"
            "F2 / F3 / F4 — dark / light / black themes\n"
            "F5 — Translate\n"
            "F6 — Run\n"
            "Ctrl+O — Open file\n"
            "Ctrl+S — Save result\n"
            "Ctrl+L — Load custom language\n"
            "Ctrl+` — Toggle terminal"
        )