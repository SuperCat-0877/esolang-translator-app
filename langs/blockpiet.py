# langs/pixelcode.py
"""
PixelCode — 2×1 плитки = Python-токены.

Python → токены → плитки → PNG-мозаика.
PNG → плитки → Python → вывод / перевод куда угодно через chain.
"""

import base64
import io
import struct
import sys
import tokenize
import zlib

from core.base import Language
from core.translate import TRANSPILERS
from core.blockpiet_tiles import (
    KEYWORDS, NAMES, OPERATORS, BRACKETS, SEPARATORS, STRUCT,
    tile_to_token, token_to_tile,
)


# Палитра 20 цветов (как везде в проекте)
PALETTE = [
    (255,192,192), (255,255,192), (192,255,192), (192,255,255),
    (192,192,255), (255,192,255),
    (255,0,0), (255,255,0), (0,255,0), (0,255,255),
    (0,0,255), (255,0,255),
    (192,0,0), (192,192,0), (0,192,0), (0,192,192),
    (0,0,192), (192,0,192),
    (255,255,255), (0,0,0),
]
PAL_IDX = {c: i for i, c in enumerate(PALETTE)}
WHITE = (255,255,255)

TILES_PER_ROW = 16


# ======================================================================
#  Python → плитки → Python
# ======================================================================
def python_to_tiles(src: str):
    tiles = []
    local_names = list(NAMES)  # копия, расширяем при новых именах
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except Exception:
        return [(18, 3)]  # END

    for tok in toks:
        ttype, tstr = tok.type, tok.string
        if ttype == tokenize.ENDMARKER:
            tiles.append((18, 3))
            break
        if ttype == tokenize.NAME:
            if tstr in KEYWORDS:
                tiles.append((13, KEYWORDS.index(tstr)))
            else:
                if tstr not in local_names:
                    local_names.append(tstr)
                idx = local_names.index(tstr)
                tiles.append((14, idx % 20))
        elif ttype == tokenize.NUMBER:
            try:
                n = int(tstr) % 260
            except ValueError:
                n = 0
            tiles.append((n // 20, n % 20))
        elif ttype == tokenize.STRING:
            tiles.append((18, 4))  # STR_START
            s = tstr
            for q in ('"""', "'''", '"', "'"):
                if s.startswith(q) and s.endswith(q):
                    s = s[len(q):-len(q)]
                    break
            for ch in s:
                n = ord(ch) & 0xFF
                tiles.append((n // 20, n % 20))
            tiles.append((18, 5))  # STR_END
        elif ttype == tokenize.OP:
            t = token_to_tile("OP", tstr)
            tiles.append(t if t else (16, 0))
        elif ttype == tokenize.NEWLINE:
            tiles.append((18, 0))
        elif ttype == tokenize.INDENT:
            tiles.append((18, 1))
        elif ttype == tokenize.DEDENT:
            tiles.append((18, 2))
    return tiles


def tiles_to_python(tiles) -> str:
    out = []
    string_mode = False
    prev_kind = None

    def add(kind, text):
        nonlocal prev_kind
        if prev_kind in ("ID", "NUM") and kind in ("ID", "NUM"):
            out.append(" ")
        out.append(text)
        prev_kind = kind

    for cat, val in tiles:
        if cat == 18 and val == 3:
            break
        if cat == 18 and val == 4:
            out.append("'")
            string_mode = True
            prev_kind = "STR"
            continue
        if cat == 18 and val == 5:
            out.append("'")
            string_mode = False
            prev_kind = "STR"
            continue
        if cat == 18 and val == 0:
            out.append("\n")
            prev_kind = "NL"
            continue
        if cat == 18 and val == 1:
            out.append("    ")
            prev_kind = "NL"
            continue
        if cat == 18 and val == 2:
            continue
        kind, val_s = tile_to_token(cat, val, string_mode)
        if kind == "CHAR":
            c = val_s
            if c == "'":
                c = "\\'"
            out.append(c)
            continue
        if kind == "NUMBER":
            add("NUM", val_s)
        elif kind == "ID":
            add("ID", val_s)
        elif kind == "OP":
            out.append(val_s)
            prev_kind = "OP"
        elif kind == "STRUCT":
            pass
    return "".join(out)


# ======================================================================
#  Плитки → PNG
# ======================================================================
def _encode_png(px):
    H, W = len(px), len(px[0])
    rows = []
    for y in range(H):
        row = bytearray([0])
        for x in range(W):
            r, g, b = px[y][x]
            row += bytes([r, g, b])
        rows.append(bytes(row))
    raw = b"".join(rows)
    comp = zlib.compress(raw, 9)

    def chunk(t, d):
        c = t + d
        return (struct.pack(">I", len(d)) + c +
                struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp)
            + chunk(b"IEND", b""))


def tiles_to_png(tiles, tiles_per_row: int = TILES_PER_ROW) -> bytes:
    """
    Каждая плитка = 2 пикселя (1×2 ширина).
    Раскладываем слева-направо, сверху-вниз.
    """
    n = len(tiles)
    rows = max(1, (n + tiles_per_row - 1) // tiles_per_row)
    W = tiles_per_row * 2
    H = rows
    px = [[WHITE] * W for _ in range(H)]

    for i, (cat, val) in enumerate(tiles):
        r = i // tiles_per_row
        c = i % tiles_per_row
        x = c * 2
        px[r][x]     = PALETTE[cat % 20]
        px[r][x + 1] = PALETTE[val % 20]
    return _encode_png(px)


def _decode_png(raw):
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not PNG")
    pos, idat = 8, b""
    W = H = color_type = None
    while pos < len(raw):
        ln = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        cdata = raw[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if ctype == b"IHDR":
            W, H, _bd, color_type, _, _, _ = struct.unpack(
                ">IIBBBBB", cdata)
        elif ctype == b"IDAT":
            idat += cdata
        elif ctype == b"IEND":
            break
    if W is None:
        raise ValueError("no IHDR")
    raw_data = zlib.decompress(idat)
    ch = {0:1, 2:3, 3:1, 4:2, 6:4}.get(color_type, 3)
    stride = W * ch
    prev = bytearray(stride)
    pixels = []
    offset = 0
    for _y in range(H):
        ft = raw_data[offset]; offset += 1
        line = bytearray(raw_data[offset:offset + stride]); offset += stride
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if ft == 1: line[i] = (line[i] + a) & 0xFF
            elif ft == 2: line[i] = (line[i] + b) & 0xFF
            elif ft == 3: line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        row = []
        for x in range(W):
            base = x * ch
            row.append((line[base], line[base + 1], line[base + 2]))
        pixels.append(row)
        prev = line
    return W, H, pixels


def png_to_tiles(px, W: int, H: int):
    """PNG → плитки. Каждая плитка = 2 пикселя в ряд."""
    tiles = []
    for y in range(H):
        x = 0
        while x + 1 < W:
            c1 = px[y][x]
            c2 = px[y][x + 1]
            if c1 == WHITE and c2 == WHITE:
                x += 2
                continue
            cat = PAL_IDX.get(c1, 19)
            val = PAL_IDX.get(c2, 0)
            tiles.append((cat, val))
            x += 2
    return tiles


# ======================================================================
#  Language
# ======================================================================
class BlockPiet21Lang(Language):
    name = "blockpiet21"
    title = "BlockPiet 2×1"
    category = "Э"
    ext = ".pxc"
    keywords = []
    comment_regex = None

    def __init__(self):
        examples = {
            "[1] print 42":        "print(42)",
            "[2] print 'Hi'":      "print('Hi')",
            "[3] x = 5":           "x = 5\nprint(x)",
            "[4] 5 + 3":           "x = 5 + 3\nprint(x)",
            "[5] Hello":           "print('Hello')",
            "[6] for 3":           "for i in range(3):\n    print(i)",
        }
        self.templates = {}
        for name, src in examples.items():
            tiles = python_to_tiles(src)
            png = tiles_to_png(tiles)
            self.templates[name] = base64.b64encode(png).decode("ascii")

    def generate_code(self, output):
        if not output:
            return ""
        src = f"print({output!r})"
        tiles = python_to_tiles(src)
        png = tiles_to_png(tiles)
        return base64.b64encode(png).decode("ascii")

    def execute(self, src):
        if not src or not src.strip():
            return ""
        try:
            raw = base64.b64decode(src.strip())
            if raw[:8] != b"\x89PNG\r\n\x1a\n":
                return "// PixelCode: not PNG"
            w, h, px = _decode_png(raw)
            tiles = png_to_tiles(px, w, h)
            py_code = tiles_to_python(tiles)
        except Exception as e:
            return f"// PixelCode decode: {type(e).__name__}: {e}"

        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            exec(compile(py_code, "<pixelcode>", "exec"), {})
        except BaseException as e:
            sys.stdout = old
            return f"// PixelCode exec: {type(e).__name__}: {e}\n# code: {py_code!r}"
        finally:
            sys.stdout = old
        return buf.getvalue()


# ======================================================================
#  Транспайлеры — universal через Python
# ======================================================================
def _py_to_pixelcode(src):
    try:
        tiles = python_to_tiles(src)
        png = tiles_to_png(tiles)
        return base64.b64encode(png).decode("ascii")
    except Exception as e:
        return f"# PixelCode: {type(e).__name__}: {e}"


def _pixelcode_to_py(src):
    try:
        raw = base64.b64decode(src.strip())
        w, h, px = _decode_png(raw)
        tiles = png_to_tiles(px, w, h)
        return tiles_to_python(tiles)
    except Exception as e:
        return f"# PixelCode: {type(e).__name__}: {e}"


TRANSPILERS[("python", "pixelcode")] = _py_to_pixelcode
TRANSPILERS[("pixelcode", "python")] = _pixelcode_to_py