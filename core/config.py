# core/config.py
import json
import shutil
import sys
from pathlib import Path
from .themes import CUSTOM_THEMES, rebuild, THEMES
from .registry import registry


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


APP_DIR = app_dir()
PLUGINS_DIR = APP_DIR / "plugins"
DISABLED_DIR = APP_DIR / "langs_disabled"     # ← удалённые .py хранятся тут
CONFIG_FILE = APP_DIR / "config.json"
PLUGINS_DIR.mkdir(exist_ok=True)
DISABLED_DIR.mkdir(exist_ok=True)


# ------------------------------------------------------------------
#  Настройки интерфейса
# ------------------------------------------------------------------
UI_SETTINGS = {
    "button_labels": {},   # {"translate": "Перевести!", ...}
    "listbox_theme": {},   # {"dark": {"bg":..., "fg":..., "select_bg":...}}
    "renamed_langs": {},   # {"ook": "Утиное", ...}
    "deleted_langs": [],   # ["ook", "malbolge_lite", ...]
    "language": "en",
}


def save():
    try:
        data = {
            "templates": {l.name: dict(l.templates)
                          for l in registry.all() if l._builtin},
            "custom_themes": CUSTOM_THEMES,
            "ui": UI_SETTINGS,
        }
        CONFIG_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")


def load():
    if not CONFIG_FILE.exists():
        return
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

        # Шаблоны: код имеет приоритет, из конфига берём только пользовательские
        saved = data.get("templates", {})
        for lang in registry.all():
            if lang.name in saved:
                for tn, code in saved[lang.name].items():
                    if tn not in lang.templates:
                        lang.templates[tn] = code

        CUSTOM_THEMES.clear()
        CUSTOM_THEMES.update(data.get("custom_themes", {}))

        ui = data.get("ui", {})
        UI_SETTINGS["button_labels"] = ui.get("button_labels", {})
        UI_SETTINGS["listbox_theme"] = ui.get("listbox_theme", {})
        UI_SETTINGS["renamed_langs"] = ui.get("renamed_langs", {})
        UI_SETTINGS["deleted_langs"] = ui.get("deleted_langs", [])
        UI_SETTINGS["language"] = ui.get("language", "en")

        rebuild()
    except Exception as e:
        print(f"Ошибка конфига: {e}")


# ------------------------------------------------------------------
#  Операции с языками
# ------------------------------------------------------------------
def disable_lang(name):
    """Переместить langs/{module}.py → langs_disabled/{module}.py."""
    lang = registry.get(name)
    if not lang or registry.is_system(name):
        return False
    mod = getattr(lang, "_module_name", None)
    if not mod:
        return False

    src = APP_DIR / "langs" / f"{mod}.py"
    dst = DISABLED_DIR / f"{mod}.py"
    try:
        if src.exists():
            shutil.move(str(src), str(dst))
        registry.unregister(name)
        if name not in UI_SETTINGS["deleted_langs"]:
            UI_SETTINGS["deleted_langs"].append(name)
        save()
        return True
    except Exception as e:
        print(f"disable_lang({name}): {e}")
        return False


def enable_lang(module_name):
    """Переместить langs_disabled/{module}.py → langs/{module}.py."""
    src = DISABLED_DIR / f"{module_name}.py"
    dst = APP_DIR / "langs" / f"{module_name}.py"
    try:
        if src.exists():
            shutil.move(str(src), str(dst))
            UI_SETTINGS["deleted_langs"] = [
                x for x in UI_SETTINGS["deleted_langs"]
                if x != module_name
            ]
            save()
            return True
    except Exception as e:
        print(f"enable_lang({module_name}): {e}")
    return False


def list_disabled():
    """Список .py-файлов в langs_disabled/ (без расширения)."""
    return sorted(p.stem for p in DISABLED_DIR.glob("*.py"))