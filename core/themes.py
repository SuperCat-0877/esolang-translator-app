# core/themes.py
"""Темы оформления. Базовые + регистрируемые пользователем."""


# ======================================================================
#  БАЗОВЫЕ ТЕМЫ
# ======================================================================
BASE_THEMES = {
    "dark":  {"bg": "#1e1e1e", "fg": "#e0e0e0", "field": "#1e1e1e",
              "border": "#3a3a3a", "term_bg": "#0d0d0d",
              "term_fg": "#d0d0d0", "accent": "#3a7bd5",
              "select": "#264f78", "sv": "dark"},
    "light": {"bg": "#f5f5f5", "fg": "#1a1a1a", "field": "#ffffff",
              "border": "#c8c8c8", "term_bg": "#ffffff",
              "term_fg": "#1a1a1a", "accent": "#3776AB",
              "select": "#cce5ff", "sv": "light"},
    "black": {"bg": "#000000", "fg": "#c8c8c8", "field": "#0a0a0a",
              "border": "#1f1f1f", "term_bg": "#000000",
              "term_fg": "#00ff41", "accent": "#00ff41",
              "select": "#003300", "sv": None},
}


# ======================================================================
#  ПОДСВЕТКА СИНТАКСИСА
# ======================================================================
SYNTAX_BASE = {
    "dark":  {"keyword": "#c586c0", "string": "#ce9178",
              "number": "#b5cea8", "comment": "#6a9955",
              "function": "#dcdcaa", "type": "#4ec9b0"},
    "light": {"keyword": "#0000ff", "string": "#a31515",
              "number": "#098658", "comment": "#008000",
              "function": "#795e26", "type": "#267f99"},
    "black": {"keyword": "#00ff41", "string": "#88ff88",
              "number": "#41ff88", "comment": "#008800",
              "function": "#a0ff41", "type": "#00ccff"},
}

# Дополнительные палитры для кастомных тем (если нет — берётся dark)
SYNTAX_BASE.update({
    "dracula":   {"keyword": "#ff79c6", "string": "#f1fa8c",
                  "number": "#bd93f9", "comment": "#6272a4",
                  "function": "#50fa7b", "type": "#8be9fd"},
    "nord":      {"keyword": "#81a1c1", "string": "#a3be8c",
                  "number": "#b48ead", "comment": "#616e88",
                  "function": "#88c0d0", "type": "#8fbcbb"},
    "gruvbox":   {"keyword": "#fb4934", "string": "#b8bb26",
                  "number": "#d3869b", "comment": "#928374",
                  "function": "#fabd2f", "type": "#83a598"},
    "solarized": {"keyword": "#859900", "string": "#2aa198",
                  "number": "#d33682", "comment": "#586e75",
                  "function": "#268bd2", "type": "#b58900"},
    "paper":     {"keyword": "#1a66cc", "string": "#b03030",
                  "number": "#0a8a5a", "comment": "#808080",
                  "function": "#6a3fb5", "type": "#0a6a8a"},
})


# ======================================================================
#  ХРАНИЛИЩА
# ======================================================================
THEMES: dict = {}
CUSTOM_THEMES: dict = {}


# ======================================================================
#  РЕГИСТРАЦИЯ НОВОЙ ТЕМЫ
# ======================================================================
_BASE_FALLBACK = {
    "bg": "#1e1e1e", "fg": "#d4d4d4", "field": "#252526",
    "select": "#264f78", "border": "#3c3c3c",
    "accent": "#4ea1ff",
    "term_bg": "#1a1a1a", "term_fg": "#d4d4d4",
    "sv": "dark",
}


def register_theme(name, palette, base="dark", override=False):
    """Добавить тему безопасно.

    name    — имя темы
    palette — dict с любыми из ключей: bg, fg, field, select, border,
              accent, term_bg, term_fg, sv
    base    — откуда брать недостающие ключи
    override — заменить, если уже есть
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Имя темы должно быть непустой строкой")
    name = name.strip()

    if name in BASE_THEMES:
        raise ValueError(f"{name!r} — базовая тема, перезаписать нельзя")
    if name in CUSTOM_THEMES and not override:
        raise ValueError(f"Тема {name!r} уже существует")

    # Fallback: base-тема → глобальный дефолт → то, что дал пользователь
    src = dict(BASE_THEMES.get(base) or {})
    src.update(_BASE_FALLBACK)
    src.update(palette or {})

    # sv-ttk понимает только dark / light / auto / None
    if src.get("sv") not in ("dark", "light", "auto", None):
        src["sv"] = "dark"

    CUSTOM_THEMES[name] = src
    rebuild()
    return name


def unregister_theme(name):
    """Удалить кастомную тему."""
    if name in BASE_THEMES:
        raise ValueError(f"{name!r} — базовая тема, удалить нельзя")
    CUSTOM_THEMES.pop(name, None)
    rebuild()


# ======================================================================
#  СБОРКА
# ======================================================================
def rebuild(*_args, **_kwargs):
    """Пересобрать THEMES из BASE + CUSTOM.

    Принимает (и игнорирует) любые аргументы — чтобы не падало,
    если кто-то вызывает rebuild(src) из старого кода.
    """
    THEMES.clear()
    THEMES.update(BASE_THEMES)
    THEMES.update(CUSTOM_THEMES)


def syntax_palette(name):
    return SYNTAX_BASE.get(name, SYNTAX_BASE["dark"])

# ======================================================================
#  ГЕНЕРАЦИЯ ПАЛИТР (для радуги и оттенков)
# ======================================================================
def _hex2rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb2hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(c))) for c in rgb))

def _mix(a: str, b: str, t: float) -> str:
    ra, ga, ba = _hex2rgb(a)
    rb, gb, bb = _hex2rgb(b)
    return _rgb2hex((ra + (rb-ra)*t, ga + (gb-ga)*t, ba + (bb-ba)*t))

def _darken(c, t):  return _mix(c, "#000000", t)
def _lighten(c, t): return _mix(c, "#ffffff", t)

def _saturate(c: str, factor: float = 1.6) -> str:
    """Увеличить насыщенность цвета (для accent у пастельных тем)."""
    r, g, b = _hex2rgb(c)
    avg = (r + g + b) / 3
    r = min(255, max(0, int(avg + (r - avg) * factor)))
    g = min(255, max(0, int(avg + (g - avg) * factor)))
    b = min(255, max(0, int(avg + (b - avg) * factor)))
    return _rgb2hex((r, g, b))

def _add_depth(p: dict, strength: float = 1.0) -> dict:
    """Глубина: поля чуть светлее фона (не сильно), границы — заметные.
    bg не трогаем — только field / border / select / term_bg.
    """
    p = dict(p)
    bg = p["bg"]
    is_light = _is_light(bg)

    if is_light:
        # Светлая тема: поля чуть светлее фона (было 0.55 → стало 0.28)
        p["field"]   = _lighten(bg, 0.28 * strength)
        p["border"]  = _darken(bg, 0.18 * strength)
        p["select"]  = _darken(bg, 0.25 * strength)
        p["term_bg"] = _lighten(bg, 0.18 * strength)   # тоже чуть темнее
        p["term_fg"] = _darken(p.get("term_fg", "#222"), 0.05 * strength)
        p["fg"]      = _darken(p.get("fg", "#222"), 0.05 * strength)
    else:
        # Тёмная тема: поля чуть светлее фона (было 0.10 → стало 0.05)
        p["field"]   = _lighten(bg, 0.05 * strength)
        p["border"]  = _lighten(bg, 0.22 * strength)
        p["select"]  = _lighten(bg, 0.18 * strength)
        p["term_bg"] = _darken(bg, 0.35 * strength)
        p["fg"]      = _lighten(p.get("fg", "#ddd"), 0.05 * strength)

    return p


def _is_light(c: str) -> bool:
    """Определить светлый ли цвет (по яркости)."""
    r, g, b = _hex2rgb(c)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 128

def _palette_dark(hue: str) -> dict:
    """Тёмная тема с живым цветом hue.
    Фон — умеренно тёмный (55% к чёрному), а не 90%, чтобы цвет был узнаваем.
    """
    return {
        "bg":      _darken(hue, 0.62),      # ← было 0.90
        "fg":      _lighten(hue, 0.88),
        "field":   _darken(hue, 0.45),      # ← было 0.80
        "select":  _darken(hue, 0.25),
        "border":  _darken(hue, 0.38),      # ← было 0.62
        "accent":  _saturate(_lighten(hue, 0.30), 1.5),  # ← жирный акцент
        "term_bg": _darken(hue, 0.78),      # терминал темнее — для глубины
        "term_fg": _lighten(hue, 0.80),
        "sv":      "dark",
    }

def _palette_light(hue: str) -> dict:
    """Светлая пастельная тема.
    hue — это и есть основной светлый цвет фона. Не осветляем его.
    Поля делаем чуть светлее, выделение — чуть темнее.
    """
    return {
        "bg":      hue,                    # ← пастель как есть
        "fg":      _darken(hue, 0.78),     # тёмный текст
        "field":   _lighten(hue, 0.45),    # поля — светлее фона
        "select":  _darken(hue, 0.18),     # выделение — темнее
        "border":  _darken(hue, 0.30),
        "accent":  _darken(_saturate(hue, 1.8), 0.55),  # цветной акцент
        "term_bg": _lighten(hue, 0.35),
        "term_fg": _darken(hue, 0.82),
        "sv":      "light",
    }

def _palette_mid(hue: str) -> dict:
    return {
        "bg":      _darken(hue, 0.55),
        "fg":      _lighten(hue, 0.92),
        "field":   _darken(hue, 0.42),
        "select":  _darken(hue, 0.22),
        "border":  _darken(hue, 0.32),
        "accent":  _lighten(hue, 0.45),
        "term_bg": _darken(hue, 0.78),
        "term_fg": _lighten(hue, 0.88),
        "sv":      "dark",
    }


# ======================================================================
#  ПОЛЬЗОВАТЕЛЬСКИЕ ТЕМЫ
# ======================================================================
register_theme("dracula", {
    "bg":      "#282a36",
    "fg":      "#f8f8f2",
    "field":   "#44475a",
    "select":  "#6272a4",
    "border":  "#44475a",
    "accent":  "#ff79c6",
    "term_bg": "#21222c",
    "term_fg": "#f8f8f2",
    "sv":      "dark",
}, override=True)

register_theme("nord", {
    "bg":      "#2e3440",
    "fg":      "#d8dee9",
    "field":   "#3b4252",
    "select":  "#434c5e",
    "border":  "#4c566a",
    "accent":  "#88c0d0",
    "term_bg": "#2e3440",
    "term_fg": "#d8dee9",
    "sv":      "dark",
}, override=True)

# ===== РАДУГА =====
register_theme("red",    _palette_dark("#d94141"), override=True)
register_theme("orange", _palette_dark("#dd8a33"), override=True)
register_theme("yellow", _palette_dark("#c7b53a"), override=True)
register_theme("green",  _palette_dark("#4ba554"), override=True)
register_theme("blue",   _palette_dark("#4a7fc9"), override=True)
register_theme("indigo", _palette_dark("#5450b3"), override=True)
register_theme("violet", _palette_dark("#8b54bd"), override=True)

register_theme("gruvbox", {
    "bg":      "#282828",
    "fg":      "#ebdbb2",
    "field":   "#3c3836",
    "select":  "#504945",
    "border":  "#504945",
    "accent":  "#fabd2f",
    "term_bg": "#1d2021",
    "term_fg": "#ebdbb2",
    "sv":      "dark",
}, override=True)

# ===== ГОЛУБЫЕ =====
register_theme("sky",       _palette_dark("#4fa8d8"), override=True)
register_theme("azure",     _palette_dark("#3d8ad8"), override=True)
register_theme("navy",      _palette_dark("#3a559c"), override=True)
register_theme("teal",      _palette_dark("#38a39c"), override=True)
register_theme("cyan",      _palette_dark("#37a6b8"), override=True)
register_theme("turquoise", _palette_dark("#40b0a4"), override=True)
register_theme("aqua",      _palette_mid ("#4fc3c3"), override=True)

register_theme("solarized", {
    "bg":      "#002b36",
    "fg":      "#839496",
    "field":   "#073642",
    "select":  "#586e75",
    "border":  "#586e75",
    "accent":  "#b58900",
    "term_bg": "#002b36",
    "term_fg": "#839496",
    "sv":      "dark",
}, override=True)

# ===== КРАСНЫЕ / ФИОЛЕТОВЫЕ =====
register_theme("crimson",   _palette_dark("#c23a58"), override=True)
register_theme("magenta",   _palette_dark("#b23ea0"), override=True)
register_theme("burgundy",  _palette_dark("#8a3648"), override=True)
register_theme("plum",      _palette_dark("#7c4488"), override=True)
register_theme("raspberry", _palette_dark("#c04a75"), override=True)
register_theme("orchid",    _palette_mid ("#a95abf"), override=True)

# ===== СВЕТЛЫЕ ПАСТЕЛЬНЫЕ =====
register_theme("cream",     _palette_light("#e8dcb8"), override=True)
register_theme("beige",     _palette_light("#e0d5c0"), override=True)
register_theme("ivory",     _palette_light("#ece5d0"), override=True)
register_theme("mint",      _palette_light("#c9e6d3"), override=True)
register_theme("lavender",  _palette_light("#d6c9e8"), override=True)
register_theme("peach",     _palette_light("#f0d1b8"), override=True)
register_theme("rose",      _palette_light("#efd0d6"), override=True)
register_theme("sky_light", _palette_light("#c9dcef"), override=True)
register_theme("sand",      _palette_light("#e0d0b0"), override=True)
register_theme("sage",      _palette_light("#c8d8c0"), override=True)

register_theme("paper", {
    "bg":      "#f5f5f0",
    "fg":      "#2b2b2b",
    "field":   "#ffffff",
    "select":  "#c9d6f2",
    "border":  "#d0d0c8",
    "accent":  "#1a66cc",
    "term_bg": "#f0f0ea",
    "term_fg": "#2b2b2b",
    "sv":      "light",
}, override=True)

# ======================================================================
#  ГЛУБИНА ДЛЯ ВСЕХ ТЕМ
# ======================================================================

def apply_depth_to_all(strength=1.0):
    for name, pal in list(BASE_THEMES.items()):
        s = strength * (0.9 if _is_light(pal["bg"]) else 1.1)
        BASE_THEMES[name] = _add_depth(pal, s)
    for name, pal in list(CUSTOM_THEMES.items()):
        s = strength * (0.9 if _is_light(pal["bg"]) else 1.1)
        CUSTOM_THEMES[name] = _add_depth(pal, s)


apply_depth_to_all(1.0)   # контрастнее
rebuild()

# Финальная сборка (на случай, если кто-то импортирует модуль и не вызывает rebuild)
rebuild()