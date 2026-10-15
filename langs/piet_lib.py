# langs/piet_lib.py
"""
Библиотека готовых Piet-плиток 16×16.

Каждая запись — готовая программа на ассемблере, которую можно
вставить в Piet-ASM одной строкой. Используется как справочник.

Пользователь может расширить словарь своими программами.
"""

from __future__ import annotations

from langs.piet import asm_to_tiles


# ----------------------------------------------------------------------
#  Готовые «макросы» — короткие программы на ассемблере
# ----------------------------------------------------------------------
MACROS: dict[str, str] = {
    # Арифметика
    "add 5 + 3":         "push 5\npush 3\nadd\nout_num\n",
    "sub 10 - 4":        "push 10\npush 4\nsub\nout_num\n",
    "mul 6 * 7":         "push 6\npush 7\nmul\nout_num\n",
    "div 20 / 4":        "push 20\npush 4\ndiv\nout_num\n",
    "mod 17 % 5":        "push 17\npush 5\nmod\nout_num\n",
    "pow 2^8":           "push 2\npush 8\nmul\nout_num\n",   # упрощённо
    # Вывод
    "print 42":          "push 42\nout_num\n",
    "print 'A'":         "push 65\nout_char\n",
    "print 'Hi'":        "push 72\nout_char\npush 105\nout_char\n",
    "print 'Hello'":     ("push 72\nout_char\npush 101\nout_char\n"
                          "push 108\nout_char\npush 108\nout_char\n"
                          "push 111\nout_char\n"),
    # Пустая программа
    "no-op":             "nop\n",
}


# ----------------------------------------------------------------------
#  Публичный API
# ----------------------------------------------------------------------
def list_macros() -> list[str]:
    """Имена всех готовых программ."""
    return list(MACROS.keys())


def get_asm(name: str) -> str:
    """Получить asm-код макроса по имени."""
    return MACROS.get(name, "")


def get_tiles(name: str) -> list[str]:
    """Получить список плиток для макроса."""
    asm = MACROS.get(name)
    if not asm:
        return []
    return asm_to_tiles(asm)


def add_macro(name: str, asm: str) -> None:
    """Добавить макрос в библиотеку во время работы."""
    MACROS[name] = asm


def save_macro(name: str, asm: str, path: str) -> None:
    """Сохранить макрос в файл (для пользовательской библиотеки)."""
    import json
    from pathlib import Path
    p = Path(path)
    data = {}
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[name] = asm
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                 encoding="utf-8")


def load_macros(path: str) -> None:
    """Загрузить пользовательские макросы из файла."""
    import json
    from pathlib import Path
    p = Path(path)
    if not p.is_file():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        for k, v in data.items():
            if isinstance(v, str):
                MACROS[k] = v
    except Exception:
        pass