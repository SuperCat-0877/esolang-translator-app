# core/registry.py
import importlib
import pkgutil
from .base import Language

# Языки, которые НЕЛЬЗЯ удалить/переименовать в UI
SYSTEM_LANGS = {"python", "javascript", "cpp", "brainfuck",
                "whitespace", "rivulet"}


class Registry:
    def __init__(self):
        self.languages = {}

    def register(self, lang: Language, builtin=True, module_name=None):
        lang._builtin = builtin
        lang._module_name = module_name or getattr(lang, "_module_name", None)
        self.languages[lang.name] = lang

    def get(self, name):
        return self.languages.get(name)

    def all(self):
        return list(self.languages.values())

    def by_category(self, cat):
        return [l for l in self.languages.values() if l.category == cat]

    def is_system(self, name):
        return name in SYSTEM_LANGS

    def discover_builtin(self):
        pkg = importlib.import_module("langs")
        for _, mod_name, _ in pkgutil.iter_modules(pkg.__path__):
            if mod_name.startswith("_"):
                continue
            try:
                mod = importlib.import_module(f"langs.{mod_name}")
            except Exception as e:
                print(f"Пропускаю langs.{mod_name}: {e}")
                continue
            for obj in vars(mod).values():
                if (isinstance(obj, type)
                        and issubclass(obj, Language)
                        and obj is not Language):
                    self.register(obj(), builtin=True,
                                   module_name=mod_name)

    def unregister(self, name):
        lang = self.languages.get(name)
        if not lang or self.is_system(name):
            return False
        del self.languages[name]
        return True


registry = Registry()