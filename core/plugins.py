# core/plugins.py
import importlib.util
from pathlib import Path
from .config import PLUGINS_DIR
from .registry import registry

def load_plugin(path):
    spec = importlib.util.spec_from_file_location("plugin_" + Path(path).stem, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    name = getattr(m, "NAME", None)
    if not name:
        raise ValueError("NAME не задан в плагине")
    cat = getattr(m, "CATEGORY", "О")
    tpls = dict(getattr(m, "TEMPLATES", {"[1] Пример": "..."}))
    execute = getattr(m, "execute", None)

    from .base import Language
    class CustomLang(Language):
        pass
    lang = CustomLang()
    lang.name = name
    lang.title = name
    lang.category = cat
    lang.templates = tpls
    lang.execute = execute or (lambda src: None)
    lang.generate_code = lambda out: f"// {name}\n// Вывод: {out!r}\n"
    registry.register(lang, builtin=False)
    return name

def discover():
    for f in sorted(PLUGINS_DIR.glob("*.py")):
        if f.name.startswith("_"): continue
        try:
            load_plugin(f)
        except Exception as e:
            print(f"Плагин {f.name}: {e}")