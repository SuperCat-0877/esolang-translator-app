# langs/brainpiet2d.py
"""
BrainPiet 2D — настоящий 2D-язык с DP/CC.

Команды (14):
    > < + - . , [ ]   — BF-операции
    v                 — DP + 90° (clockwise)
    ^                 — DP - 90°
    R                 — DP 180°
    L                 — CC flip
    #                 — halt
    пробел            — slide

Программа = сетка блоков. Движение через DP/CC, как в Piet.
Размер блока = сила команды (`+++++` = +5).

Serpentine layout:
    строка 0:  команды →  v
    (белая строка)
    строка 2:  v  ← команды  ^
    (белая строка)
    строка 4:  ^  → команды  v
    ...
"""

import base64
import struct
import zlib

from core.base import Language
from core.translate import TRANSPILERS


# ======================================================================
#  Палитра команд
# ======================================================================
CMD_TO_COLOR = {
    ">": (255, 192, 192),   # light red
    "<": (192, 255, 192),   # light green
    "+": (255, 0, 0),       # red
    "-": (0, 255, 0),       # green
    ".": (0, 0, 255),       # blue
    ",": (0, 255, 255),     # cyan
    "[": (255, 255, 0),     # yellow
    "]": (255, 0, 255),     # magenta
    "v": (192, 0, 0),       # dark red
    "^": (192, 192, 0),     # dark yellow
    "R": (0, 192, 192),     # dark cyan
    "L": (0, 192, 0),       # dark green
    "#": (0, 0, 0),         # black
    " ": (255, 255, 255),   # white
}
COLOR_TO_CMD = {v: k for k, v in CMD_TO_COLOR.items()}
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

DP_VECTORS = ((1, 0), (0, 1), (-1, 0), (0, -1))  # R D L U


# ======================================================================
#  PNG
# ======================================================================
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
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 3)
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


# ======================================================================
#  Блоки
# ======================================================================
def _build_blocks(px, W, H):
    block_id = [[-1] * W for _ in range(H)]
    cells = {}
    nid = 0
    for y in range(H):
        for x in range(W):
            if block_id[y][x] != -1:
                continue
            color = px[y][x][:3]
            stack = [(x, y)]
            group = []
            while stack:
                cx, cy = stack.pop()
                if block_id[cy][cx] != -1:
                    continue
                if px[cy][cx][:3] != color:
                    continue
                block_id[cy][cx] = nid
                group.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < W and 0 <= ny < H
                            and block_id[ny][nx] == -1):
                        stack.append((nx, ny))
            cells[nid] = group
            nid += 1
    return block_id, cells


def _pick_edge(cells, dp, cc):
    def key(c):
        x, y = c
        if dp == 0: return (x, -y) if cc == 0 else (x, y)
        if dp == 1: return (y, x) if cc == 0 else (y, -x)
        if dp == 2: return (-x, y) if cc == 0 else (-x, -y)
        return (-y, -x) if cc == 0 else (-y, x)
    return max(cells, key=key)


# ======================================================================
#  Интерпретатор с DP/CC
# ======================================================================
def run_2d(px, W, H, max_steps: int = 1_000_000) -> str:
    block_id, cells = _build_blocks(px, W, H)

    # старт — верхний левый не-white, не-black
    start = None
    for y in range(H):
        for x in range(W):
            c = px[y][x][:3]
            if c != WHITE and c != BLACK:
                start = (x, y)
                break
        if start:
            break
    if not start:
        return ""

    x, y = start
    dp = [0]
    cc = [0]
    tape = [0] * 30000
    ptr = 0
    out: list[str] = []
    prev_block = -1
    steps = 0

    while steps < max_steps:
        steps += 1
        cur = px[y][x][:3]

        # белый — slide
        if cur == WHITE:
            dx, dy = DP_VECTORS[dp[0]]
            nx, ny = x + dx, y + dy
            if (0 <= nx < W and 0 <= ny < H
                    and px[ny][nx][:3] != BLACK):
                x, y = nx, ny
                continue
            cc[0] = 1 - cc[0]
            dx, dy = DP_VECTORS[dp[0]]
            nx, ny = x + dx, y + dy
            if (0 <= nx < W and 0 <= ny < H
                    and px[ny][nx][:3] != BLACK):
                x, y = nx, ny
                continue
            break

        if cur == BLACK:
            break

        cmd = COLOR_TO_CMD.get(cur)
        if cmd is None:
            break

        cid = block_id[y][x]
        size = len(cells[cid]) if cmd not in "v^RL" else 1

        if cid != prev_block:
            if cmd == ">":
                ptr = (ptr + size) % 30000
            elif cmd == "<":
                ptr = (ptr - size) % 30000
            elif cmd == "+":
                for _ in range(size):
                    tape[ptr] = (tape[ptr] + 1) & 0xFF
            elif cmd == "-":
                for _ in range(size):
                    tape[ptr] = (tape[ptr] - 1) & 0xFF
            elif cmd == ".":
                for _ in range(size):
                    out.append(chr(tape[ptr] & 0xFF))
            elif cmd == ",":
                tape[ptr] = 0
            elif cmd == "v":
                dp[0] = (dp[0] + 1) % 4
            elif cmd == "^":
                dp[0] = (dp[0] + 3) % 4
            elif cmd == "R":
                dp[0] = (dp[0] + 2) % 4
            elif cmd == "L":
                cc[0] = 1 - cc[0]
            prev_block = cid

        cells_of = cells[cid]
        moved = False
        saved_cc = cc[0]
        for _ in range(2):
            edge = _pick_edge(cells_of, dp[0], cc[0])
            dx, dy = DP_VECTORS[dp[0]]
            nx, ny = edge[0] + dx, edge[1] + dy
            if (0 <= nx < W and 0 <= ny < H
                    and px[ny][nx][:3] != BLACK):
                x, y = nx, ny
                moved = True
                break
            cc[0] = 1 - cc[0]
        if not moved:
            cc[0] = saved_cc
            break

    return "".join(out)


# ======================================================================
#  Serpentine-укладка BF в 2D
# ======================================================================
def bf_to_2d_png(bf: str, W: int = 16) -> bytes:
    """
    BF-строка → 2D PNG.

    Data-rows на чётных Y, разделители на нечётных.
    Row 0: команды 0..W-2, v на W-1.
    Чётные data-rows: ^ на 0, команды 1..W-2, v на W-1.
    Нечётные data-rows: v на W-1, команды W-2..1, ^ на 0.
    """
    bf = bf or "#"
    row0_size = W - 1
    other_size = W - 2

    if len(bf) <= row0_size:
        chunks = [bf]
    else:
        chunks = [bf[:row0_size]]
        rest = bf[row0_size:]
        while rest:
            chunks.append(rest[:other_size])
            rest = rest[other_size:]

    H = 2 * len(chunks) - 1
    px = [[WHITE] * W for _ in range(H)]

    for r, chunk in enumerate(chunks):
        y = r * 2
        if r == 0:
            for i, ch in enumerate(chunk):
                if i < W - 1:
                    px[y][i] = CMD_TO_COLOR.get(ch, WHITE)
            px[y][W - 1] = CMD_TO_COLOR["v"]
        elif r % 2 == 1:
            px[y][W - 1] = CMD_TO_COLOR["v"]
            for i, ch in enumerate(chunk):
                col = W - 2 - i
                if col >= 1:
                    px[y][col] = CMD_TO_COLOR.get(ch, WHITE)
            px[y][0] = CMD_TO_COLOR["^"]
        else:
            px[y][0] = CMD_TO_COLOR["^"]
            for i, ch in enumerate(chunk):
                col = 1 + i
                if col < W - 1:
                    px[y][col] = CMD_TO_COLOR.get(ch, WHITE)
            px[y][W - 1] = CMD_TO_COLOR["v"]

    return _encode_png(px)


# ======================================================================
#  Language
# ======================================================================
class BrainPiet2DLang(Language):
    name = "brainpiet2d"
    title = "BrainPiet 2D"
    category = "Э"
    ext = ".bpng2d"
    keywords = []
    comment_regex = None

    def __init__(self):
        # Hello, World! без циклов — линейный BF
        # H(72) e(101) l(108) l(108) o(111) ,(44) ␣(32)
        # W(87) o(111) r(114) l(108) d(100) !(33)
        hw = "".join(
            ">" + "+" * ord(ch) + "."
            for ch in "Hello, World!"
        ) + "#"
        a = "+" * 65 + "."
        hi = ">" + "+" * 72 + ".>" + "+" * 105 + ".#"
        n42 = ">" + "+" * 52 + ".>" + "+" * 50 + ".#"
        n5 = ">" + "+" * 53 + ".#"

        self.templates = {
            "[1] Hello, World": base64.b64encode(
                bf_to_2d_png(hw)).decode("ascii"),
            "[2] A": base64.b64encode(
                bf_to_2d_png(a)).decode("ascii"),
            "[3] Hi": base64.b64encode(
                bf_to_2d_png(hi)).decode("ascii"),
            "[4] 42": base64.b64encode(
                bf_to_2d_png(n42)).decode("ascii"),
            "[5] 5": base64.b64encode(
                bf_to_2d_png(n5)).decode("ascii"),
        }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        try:
            raw = base64.b64decode(src.strip())
            if raw[:8] != b"\x89PNG\r\n\x1a\n":
                return "// BrainPiet2D: not PNG"
            w, h, px = _decode_png(raw)
            return run_2d(px, w, h)
        except Exception as e:
            return f"// BrainPiet2D: {type(e).__name__}: {e}"

    def generate_code(self, output):
        if not output:
            return base64.b64encode(bf_to_2d_png("#")).decode("ascii")
        bf = ""
        for ch in output:
            code = ord(ch) & 0xFF
            bf += ">" + "+" * code + "."
        bf += "#"
        return base64.b64encode(bf_to_2d_png(bf)).decode("ascii")


TRANSPILERS[("brainfuck", "brainpiet2d")] = lambda src: (
    base64.b64encode(bf_to_2d_png(src)).decode("ascii"))