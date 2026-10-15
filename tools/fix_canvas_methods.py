# tools/fix_canvas_methods.py
"""Добавляет определения _render_brainpiet2d, _render_blockpiet2d, _rgb_to_cmd."""
from __future__ import annotations
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PC = ROOT / "ui" / "piet_canvas.py"


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


NEW_METHODS = '''    # ==============================================================
    #  BRAINPIET 2D
    # ==============================================================
    def _render_brainpiet2d(self):
        if not self._tiles:
            self._render_empty("🧠² BrainPiet 2D")
            return
        try:
            raw = base64.b64decode(self._tiles[self._tile_idx])
            w, h, px = _decode_png(raw)
        except Exception as e:
            self._render_error(f"BrainPiet 2D: {e}")
            return

        cell = max(8, self._zoom * 12)
        pad = 8

        brain_map = {
            (255,192,192): ">", (192,255,192): "<",
            (255,0,0): "+",     (0,255,0): "-",
            (0,0,255): ".",     (0,255,255): ",",
            (255,255,0): "[",   (255,0,255): "]",
            (192,0,0): "v",     (192,192,0): "^",
            (0,192,192): "R",   (0,192,0): "L",
            (0,0,0): "#",       (255,255,255): "",
        }
        for y in range(h):
            for x in range(w):
                rgb = px[y][x]
                hexc = "#%02X%02X%02X" % rgb
                x1, y1 = pad + x * cell, pad + y * cell
                x2, y2 = x1 + cell, y1 + cell
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=hexc, outline="#333")
                ch = brain_map.get(rgb, "")
                if ch and cell >= 10:
                    fg = "#FFF" if rgb == (0,0,0) else "#000"
                    self.canvas.create_text(
                        (x1+x2)//2, (y1+y2)//2,
                        text=ch, font=("Consolas", max(8, cell-4)),
                        fill=fg)

        total_w = pad * 2 + w * cell
        total_h = pad * 2 + h * cell
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.header_lbl.config(
            text=f"🧠² BrainPiet 2D · {w}×{h} · зум ×{self._zoom}")
        self._update_buttons()

    # ==============================================================
    #  BLOCKPIET 2D
    # ==============================================================
    def _render_blockpiet2d(self):
        if not self._tiles:
            self._render_empty("🟦² BlockPiet 2D")
            return
        try:
            raw = base64.b64decode(self._tiles[self._tile_idx])
            w, h, px = _decode_png(raw)
        except Exception as e:
            self._render_error(f"BlockPiet 2D: {e}")
            return

        rows_blocks = h // 2
        cols_blocks = w // 2
        cell = max(24, self._zoom * 24)
        pad = 12
        block_size = cell * 2

        for rb in range(rows_blocks):
            for cb in range(cols_blocks):
                x = cb * 2
                y = rb * 2
                tl = px[y][x]
                tr = px[y][x + 1]
                bl = px[y + 1][x]
                br = px[y + 1][x + 1]
                if (tl == (255,255,255) and tr == (255,255,255)
                        and bl == (255,255,255) and br == (255,255,255)):
                    continue

                x1 = pad + cb * block_size
                y1 = pad + rb * (block_size + 20)
                x2, y2 = x1 + block_size, y1 + block_size

                self.canvas.create_rectangle(
                    x1, y1, x1+cell, y1+cell,
                    fill="#%02X%02X%02X" % tl, outline="#888")
                self.canvas.create_rectangle(
                    x1+cell, y1, x2, y1+cell,
                    fill="#%02X%02X%02X" % tr, outline="#888")
                self.canvas.create_rectangle(
                    x1, y1+cell, x1+cell, y2,
                    fill="#%02X%02X%02X" % bl, outline="#888")
                self.canvas.create_rectangle(
                    x1+cell, y1+cell, x2, y2,
                    fill="#%02X%02X%02X" % br, outline="#888")

                if cell >= 20:
                    cmd = _rgb_to_cmd(tl)
                    self.canvas.create_text(
                        x1 + block_size // 2, y2 + 10,
                        text=cmd, font=("Consolas", 9),
                        fill="#DDD", anchor="n")

        total_w = pad * 2 + cols_blocks * block_size
        total_h = pad * 2 + rows_blocks * (block_size + 20)
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.header_lbl.config(
            text=f"🟦² BlockPiet 2D · "
                 f"{cols_blocks}×{rows_blocks} блоков · зум ×{self._zoom}")
        self._update_buttons()

'''

HELPERS = '''

# ======================================================================
#  Вспомогательные функции для BlockPiet 2D
# ======================================================================
_BLOCK_CMDS = [
    "PUSH", "POP", "ADD", "SUB", "MUL", "DIV", "MOD", "DUP",
    "SWAP", "LOAD", "STORE", "OUT_NUM", "OUT_CHAR",
    "IN_NUM", "IN_CHAR", "JMP", "JZ", "JNZ", "NOP", "HALT",
]
_PAL = [
    (255,192,192),(255,255,192),(192,255,192),(192,255,255),
    (192,192,255),(255,192,255),
    (255,0,0),(255,255,0),(0,255,0),(0,255,255),
    (0,0,255),(255,0,255),
    (192,0,0),(192,192,0),(0,192,0),(0,192,192),
    (0,0,192),(192,0,192),
    (255,255,255),(0,0,0),
]


def _rgb_to_idx(rgb):
    for i, c in enumerate(_PAL):
        if c == rgb:
            return i
    return 18


def _rgb_to_cmd(rgb):
    idx = _rgb_to_idx(rgb)
    if 0 <= idx < len(_BLOCK_CMDS):
        return _BLOCK_CMDS[idx]
    return "?"
'''


def main():
    _force_utf8()
    text = PC.read_text(encoding="utf-8")

    need_methods = "    def _render_brainpiet2d(self):" not in text
    need_helpers = "def _rgb_to_cmd(rgb):" not in text

    if not need_methods and not need_helpers:
        print("  [=] всё уже на месте")
        return

    bak = PC.with_suffix(PC.suffix + ".bak_methods")
    if not bak.exists():
        shutil.copy2(PC, bak)
        print(f"    бэкап: {bak.name}")

    # 1) вставить методы перед _render_piet
    anchor = "    def _render_piet(self):"
    if need_methods:
        if anchor in text:
            text = text.replace(anchor, NEW_METHODS + anchor, 1)
            print("  [+] методы _render_brainpiet2d, _render_blockpiet2d")
        else:
            print("  [!] не найден якорь _render_piet")

    # 2) добавить HELPERS в конец файла
    if need_helpers:
        text = text.rstrip() + "\n" + HELPERS + "\n"
        print("  [+] хелперы _rgb_to_cmd, _rgb_to_idx")

    PC.write_text(text, encoding="utf-8")
    print("  Готово.")


if __name__ == "__main__":
    main()