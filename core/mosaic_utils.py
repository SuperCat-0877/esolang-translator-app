# core/mosaic_utils.py
"""Конвертация мозаик ↔ код/PNG/исполнение.

Каждая мозаика — список пар (name, (cat, val)).
Здесь — единственное место, где эти пары превращаются в BF/Python
и упаковываются в 2D-PNG через brainpiet2d / blockpiet2d.
"""

from __future__ import annotations

from core.mosaic_palettes import BRAINPIET_CHARS
from core.blockpiet_tiles import tile_to_token


# ----------------------------------------------------------------------
#  BrainPiet (BF → 2D PNG)
# ----------------------------------------------------------------------
def tiles_to_brainfuck(tiles: list[tuple[int, int]]) -> str:
    """[(cat, val)] → BF-строка. Для brainpiet cat всегда 0."""
    chars: list[str] = []
    for cat, val in tiles:
        if cat == 0 and 0 <= val < len(BRAINPIET_CHARS):
            chars.append(BRAINPIET_CHARS[val])
    return "".join(chars)


def tiles_to_png_brainpiet(tiles: list[tuple[int, int]]) -> bytes:
    from langs.brainpiet2d import bf_to_2d_png
    bf = tiles_to_brainfuck(tiles) or "#"
    return bf_to_2d_png(bf)


def run_brainpiet(tiles: list[tuple[int, int]]) -> str:
    from langs.brainpiet2d import bf_to_2d_png, _decode_png, run_2d
    bf = tiles_to_brainfuck(tiles) or "#"
    png = bf_to_2d_png(bf)
    w, h, px = _decode_png(png)
    return run_2d(px, w, h)


# ----------------------------------------------------------------------
#  BlockPiet: плитки → Python
# ----------------------------------------------------------------------
_OPEN  = {"(", "[", "{"}
_CLOSE = {")", "]", "}", ",", ":", ".", ";"}
_OPS   = {
    "+", "-", "*", "/", "//", "%", "**",
    "=", "==", "!=", "<", ">", "<=", ">=",
    "+=", "-=", "*=", "/=", "->", "=>",
}
_WORDS = {"ID", "NUMBER"}


def _need_space(prev_kind: str, prev_text: str,
                kind: str, text: str) -> bool:
    if not prev_text:
        return False
    if text in _CLOSE:                      # ) ] } , : . ;
        return False
    if prev_text in _OPEN or prev_text == ".":
        return False
    if text in _OPEN and prev_kind in _WORDS:
        return False                        # print(   a(
    if text in _OPS or prev_text in _OPS:   # a = 5, x + 1
        return True
    if kind in _WORDS and prev_kind in _WORDS:
        return True                         # for i in range
    return False


def tiles_to_python(tiles: list[tuple[int, int]]) -> str:
    """[(cat,val)] → Python-подобный код. Учитывает STR_START/STR_END."""
    lines: list[str] = []
    cur = ""
    indent = 0
    prev_kind, prev_text = "", ""
    string_mode = False

    for cat, val in tiles:
        # --- структурные плитки (cat=18) ---
        if cat == 18:
            if val == 0:                       # NEWLINE
                if cur:
                    lines.append(cur)
                cur = ""
                prev_kind = prev_text = ""
                continue
            if val == 1:                       # INDENT
                indent += 1
                continue
            if val == 2:                       # DEDENT
                indent = max(0, indent - 1)
                continue
            if val == 3:                       # END
                break
            if val == 4:                       # STR_START
                cur += "'"
                string_mode = True
                prev_kind, prev_text = "STR", "'"
                continue
            if val == 5:                       # STR_END
                cur += "'"
                string_mode = False
                prev_kind, prev_text = "STR", "'"
                continue

        kind, text = tile_to_token(cat, val, string_mode)
        if not text:
            continue
        if kind == "CHAR":                     # внутри строки
            cur += text
            continue

        if not cur:
            cur = "    " * indent + text
        elif _need_space(prev_kind, prev_text, kind, text):
            cur += " " + text
        else:
            cur += text
        prev_kind, prev_text = kind, text

    if cur:
        lines.append(cur)
    return "\n".join(lines)


def tiles_to_png_blockpiet(tiles: list[tuple[int, int]]) -> bytes:
    from langs.blockpiet2d import commands_to_png, python_to_commands
    src = tiles_to_python(tiles)
    return commands_to_png(python_to_commands(src))


def run_blockpiet(tiles: list[tuple[int, int]]) -> str:
    from langs.blockpiet2d import (
        commands_to_png, python_to_commands, _decode_png, run_2d,
    )
    src = tiles_to_python(tiles)
    cmds = python_to_commands(src)
    png = commands_to_png(cmds)
    w, h, px = _decode_png(png)
    return run_2d(px, w, h)

## ----------------------------------------------------------------------
#  Piet++ : лента цветов → Piet-PNG → run
# ----------------------------------------------------------------------
def tiles_to_png_piet(tiles: list) -> bytes:
    """[(cat, val)] → Piet PNG (одна строка цветов + рамка).

    cat 0..5, val 0..2 — цвета Piet
    cat 18 — white, cat 19 — black
    """
    from langs.piet import _PALETTE_LIST, _px_to_png
    W = len(tiles)
    H = 3
    WHITE = (255, 255, 255)
    px = [[WHITE] * (W + 2) for _ in range(H)]
    for i, (cat, val) in enumerate(tiles):
        if cat == 18:
            c = WHITE
        elif cat == 19:
            c = (0, 0, 0)
        else:
            idx = cat * 3 + val
            if 0 <= idx < len(_PALETTE_LIST):
                c = _PALETTE_LIST[idx]
            else:
                c = WHITE
        px[1][i + 1] = c
    return _px_to_png(px)


def run_piet(tiles: list) -> str:
    from langs.piet import _decode_png, _run_2d
    if not tiles:
        return ""
    png = tiles_to_png_piet(tiles)
    w, h, px = _decode_png(png)
    # initial_prev=(0,0) — чтобы первый блок исполнялся (nop при (0,0))
    result, _, _ = _run_2d(px, w, h, initial_prev=(0, 0))
    return result