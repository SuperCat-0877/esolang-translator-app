# core/pixel_tiles_lib.py
"""
Библиотека пользовательских плиток PixelCode.

Плитка = (category, value). 20×20 = 400 комбинаций.
Пользователь может:
  - создать новую плитку (имя → cat/val)
  - использовать в мозаике
  - сохранить в JSON
"""

from __future__ import annotations
import json
from pathlib import Path

from core.blockpiet_tiles import KEYWORDS, NAMES, OPERATORS, BRACKETS

LIB_FILE = Path(__file__).parent.parent / "data" / "pixel_tiles.json"


# ----------------------------------------------------------------------
#  Стандартные плитки (все 400)
# ----------------------------------------------------------------------
def default_tiles() -> dict[str, tuple[int, int]]:
    """Стандартная библиотека: все 20 категорий × 20 значений."""
    out: dict[str, tuple[int, int]] = {}

    # 0..12: байты (260 ASCII)
    for cat in range(13):
        for val in range(20):
            code = cat * 20 + val
            if 32 <= code <= 126:
                ch = chr(code)
                label = f"'{ch}'"
            else:
                label = f"#{code}"
            out[f"BYTE {label}"] = (cat, val)

    # 13: KEYWORDS
    for i, kw in enumerate(KEYWORDS):
        out[f"KEYWORD {kw}"] = (13, i)

    # 14: NAMES
    for i, name in enumerate(NAMES):
        out[f"NAME {name}"] = (14, i)

    # 15: OPERATORS
    for i, op in enumerate(OPERATORS):
        out[f"OP {op}"] = (15, i)

    # 16: BRACKETS
    for i, br in enumerate(BRACKETS[:20]):
        if br:
            out[f"BRACKET {br}"] = (16, i)

    # 18: STRUCT
    out["NEWLINE"] = (18, 0)
    out["INDENT"] = (18, 1)
    out["DEDENT"] = (18, 2)
    out["END"] = (18, 3)
    out["STR_START"] = (18, 4)
    out["STR_END"] = (18, 5)

    return out


# ----------------------------------------------------------------------
#  Хранилище пользовательских плиток
# ----------------------------------------------------------------------
class BlockPietTileLibrary:
    def __init__(self):
        self.tiles: dict[str, tuple[int, int]] = default_tiles()
        self._load_user()

    def _load_user(self):
        if not LIB_FILE.is_file():
            return
        try:
            data = json.loads(LIB_FILE.read_text(encoding="utf-8"))
            for name, pair in data.items():
                if isinstance(pair, list) and len(pair) == 2:
                    self.tiles[name] = (int(pair[0]), int(pair[1]))
        except Exception:
            pass

    def save_user(self):
        LIB_FILE.parent.mkdir(exist_ok=True)
        # сохраняем только пользовательские (те, что не в default)
        default = set(default_tiles().keys())
        user = {k: list(v) for k, v in self.tiles.items()
                if k not in default}
        LIB_FILE.write_text(
            json.dumps(user, ensure_ascii=False, indent=2),
            encoding="utf-8")

    def add(self, name: str, cat: int, val: int):
        self.tiles[name] = (cat, val)
        self.save_user()

    def remove(self, name: str):
        if name in self.tiles:
            del self.tiles[name]
            self.save_user()

    def get(self, name: str):
        return self.tiles.get(name)

    def list_by_category(self, cat: int) -> list[str]:
        return sorted(k for k, (c, v) in self.tiles.items()
                      if c == cat)

    def all_names(self) -> list[str]:
        return sorted(self.tiles.keys())