# langs/piet.py
"""
Piet — 2D-эзотерический язык.

В одном файле:
  * PNG-декодер и энкодер
  * палитра Piet (18 цветов + white + black)
  * интерпретатор 2D (блоки, DP, CC, все 18 команд)
  * текст-энкодер: текст → PNG-пазл
  * плиточная система: 16×16 плитки с общим стеком
  * Piet-ассемблер: текстовые команды → плитки
"""

import base64
import struct
import zlib

from core.base import Language
from core.translate import TRANSPILERS


TILE = 16          # размер плитки
MAX_TEXT_LEN = 500


# ======================================================================
#  1. PNG
# ======================================================================
def _decode_png(raw):
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat = 8, b""
    W = H = color_type = None
    while pos < len(raw):
        ln = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        cdata = raw[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if ctype == b"IHDR":
            W, H, _bd, color_type, _, _, _ = struct.unpack(">IIBBBBB", cdata)
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
            if ch >= 3:
                row.append((line[base], line[base + 1], line[base + 2]))
            else:
                v = line[base]; row.append((v, v, v))
        pixels.append(row)
        prev = line
    return W, H, pixels


def _px_to_png(px):
    H = len(px); W = len(px[0])
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
#  2. Палитра
# ======================================================================
_PIET_PALETTE = {
    (255, 192, 192): (0, 0), (255, 0, 0): (0, 1), (192, 0, 0): (0, 2),
    (255, 255, 192): (1, 0), (255, 255, 0): (1, 1), (192, 192, 0): (1, 2),
    (192, 255, 192): (2, 0), (0, 255, 0): (2, 1), (0, 192, 0): (2, 2),
    (192, 255, 255): (3, 0), (0, 255, 255): (3, 1), (0, 192, 192): (3, 2),
    (192, 192, 255): (4, 0), (0, 0, 255): (4, 1), (0, 0, 192): (4, 2),
    (255, 192, 255): (5, 0), (255, 0, 255): (5, 1), (192, 0, 192): (5, 2),
}
_PALETTE_LIST = [
    (255, 192, 192), (255, 0, 0), (192, 0, 0),
    (255, 255, 192), (255, 255, 0), (192, 192, 0),
    (192, 255, 192), (0, 255, 0), (0, 192, 0),
    (192, 255, 255), (0, 255, 255), (0, 192, 192),
    (192, 192, 255), (0, 0, 255), (0, 0, 192),
    (255, 192, 255), (255, 0, 255), (192, 0, 192),
]
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def _rgb(h, l):
    return _PALETTE_LIST[h * 3 + l]


# ======================================================================
#  3. Команды Piet (delta-таблица)
# ======================================================================
COMMANDS = {
    "nop":      (0, 0),
    "push":     (0, 1),
    "pop":      (0, 2),
    "add":      (1, 0),
    "sub":      (1, 1),
    "mul":      (1, 2),
    "div":      (2, 0),
    "mod":      (2, 1),
    "not":      (2, 2),
    "gt":       (3, 0),
    "dp":       (3, 1),
    "cc":       (3, 2),
    "dup":      (4, 0),
    "roll":     (4, 1),
    "write":    (4, 2),
    "read":     (5, 0),
    "out_num":  (5, 1),
    "out_char": (5, 2),
}


# ======================================================================
#  4. Интерпретатор 2D
# ======================================================================
def _do(dh, dl, stack, out, dp_ref, cc_ref, block_size, ctx=None):
    h, l = dh, dl
    if h == 0 and l == 0: pass
    elif h == 0 and l == 1: stack.append(block_size)
    elif h == 0 and l == 2:
        if stack: stack.pop()
    elif h == 1 and l == 0:
        if len(stack) >= 2:
            a, b = stack.pop(), stack.pop(); stack.append(b + a)
    elif h == 1 and l == 1:
        if len(stack) >= 2:
            a, b = stack.pop(), stack.pop(); stack.append(b - a)
    elif h == 1 and l == 2:
        if len(stack) >= 2:
            a, b = stack.pop(), stack.pop(); stack.append(b * a)
    elif h == 2 and l == 0:
        if len(stack) >= 2:
            a, b = stack.pop(), stack.pop()
            stack.append(0 if a == 0 else b // a)
    elif h == 2 and l == 1:
        if len(stack) >= 2:
            a, b = stack.pop(), stack.pop()
            stack.append(0 if a == 0 else b % a)
    elif h == 2 and l == 2:
        if stack: stack.append(1 if stack.pop() == 0 else 0)
    elif h == 3 and l == 0:
        if len(stack) >= 2:
            a, b = stack.pop(), stack.pop()
            stack.append(1 if b > a else 0)
    elif h == 3 and l == 1:
        if stack: dp_ref[0] = (dp_ref[0] + stack.pop()) % 4
    elif h == 3 and l == 2:
        if stack: cc_ref[0] = (cc_ref[0] + stack.pop()) % 2
    elif h == 4 and l == 0:
        if stack: stack.append(stack[-1])
    elif h == 4 and l == 1:
        if len(stack) >= 2:
            depth = stack.pop(); rolls = stack.pop()
            if 0 < depth <= len(stack):
                n = rolls % depth
                if n:
                    top = stack[-depth:]
                    stack[-depth:] = top[-n:] + top[:-n]
    elif h == 4 and l == 2:
        if ctx is not None and len(stack) >= 4:
            y = stack.pop() & 0xFF
            x = stack.pop() & 0xFF
            ch = stack.pop() % 6
            cl = stack.pop() % 3
            if 0 <= x < ctx["W"] and 0 <= y < ctx["H"]:
                ctx["px"][y][x] = _PALETTE_LIST[ch * 3 + cl]
                ctx["dirty"] = True
    elif h == 5 and l == 0:
        if ctx is not None and len(stack) >= 2:
            y = stack.pop() & 0xFF
            x = stack.pop() & 0xFF
            if 0 <= x < ctx["W"] and 0 <= y < ctx["H"]:
                rgb = ctx["px"][y][x][:3]
                if rgb in _PIET_PALETTE:
                    hh, ll = _PIET_PALETTE[rgb]
                    stack.append(hh); stack.append(ll)
                else:
                    stack.append(0); stack.append(0)
    elif h == 5 and l == 1:
        if stack: out.append(str(stack.pop()).encode("ascii"))
    elif h == 5 and l == 2:
        if stack: out.append(bytes([stack.pop() & 0xFF]))


def _build_blocks(px, W, H):
    block_id = [[-1] * W for _ in range(H)]
    cells_of = {}
    next_id = 0
    for y in range(H):
        for x in range(W):
            if block_id[y][x] != -1:
                continue
            color = px[y][x][:3]
            stack = [(x, y)]
            cells = []
            while stack:
                cx, cy = stack.pop()
                if block_id[cy][cx] != -1: continue
                if px[cy][cx][:3] != color: continue
                block_id[cy][cx] = next_id
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and block_id[ny][nx] == -1:
                        stack.append((nx, ny))
            cells_of[next_id] = cells
            next_id += 1
    return block_id, cells_of


def _pick_edge(cells, dp, cc):
    def key(c):
        x, y = c
        if dp == 0: return (x, -y) if cc == 0 else (x, y)
        if dp == 1: return (y, x) if cc == 0 else (y, -x)
        if dp == 2: return (-x, y) if cc == 0 else (-x, -y)
        return (-y, -x) if cc == 0 else (-y, x)
    return max(cells, key=key)


DP_VECTORS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def _run_2d(px, W, H, initial_stack=None, initial_prev=None):
    """Полный интерпретатор. Возвращает (output, final_stack, final_prev)."""
    block_id, cells_of = _build_blocks(px, W, H)

    start = None
    for y in range(H):
        for x in range(W):
            c = px[y][x][:3]
            if c != BLACK and c != WHITE:
                start = (x, y); break
        if start: break
    if not start:
        return "", initial_stack or [], initial_prev

    x, y = start
    dp = [0]; cc = [0]
    stack = initial_stack if initial_stack is not None else []
    out = []
    prev_hl = initial_prev
    steps = 0
    max_steps = W * H * 30

    ctx = {"px": px, "W": W, "H": H, "dirty": False}

    while steps < max_steps:
        steps += 1
        cur_rgb = px[y][x][:3]

        if cur_rgb == WHITE:
            dx, dy = DP_VECTORS[dp[0]]
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and px[ny][nx][:3] != BLACK:
                x, y = nx, ny; continue
            cc[0] = 1 - cc[0]
            edge = _pick_edge(cells_of[block_id[y][x]], dp[0], cc[0])
            nx, ny = edge[0] + dx, edge[1] + dy
            if 0 <= nx < W and 0 <= ny < H and px[ny][nx][:3] != BLACK:
                x, y = nx, ny; continue
            break

        if cur_rgb == BLACK:
            break

        hl = _PIET_PALETTE.get(cur_rgb)
        if hl is None:
            break

        if prev_hl is not None:
            dh = (hl[0] - prev_hl[0]) % 6
            dl = (hl[1] - prev_hl[1]) % 3
            cid = block_id[y][x]
            size = len(cells_of[cid])
            _do(dh, dl, stack, out, dp, cc, size, ctx)
            if ctx["dirty"]:
                block_id, cells_of = _build_blocks(px, W, H)
                ctx["dirty"] = False
        prev_hl = hl

        cid = block_id[y][x]
        cells = cells_of[cid]
        moved = False
        saved_cc = cc[0]
        for _ in range(2):
            edge = _pick_edge(cells, dp[0], cc[0])
            dx, dy = DP_VECTORS[dp[0]]
            nx, ny = edge[0] + dx, edge[1] + dy
            if 0 <= nx < W and 0 <= ny < H and px[ny][nx][:3] != BLACK:
                x, y = nx, ny; moved = True; break
            cc[0] = 1 - cc[0]
        if not moved:
            cc[0] = saved_cc
            break

    return (b"".join(out).decode("utf-8", errors="replace"),
            stack, prev_hl)


# ======================================================================
#  5. Текст-энкодер: текст → PNG-пазл
# ======================================================================
def _make_tile_png(codels):
    """PNG 16×16: codels в первой строке (до 16), остальное чёрное."""
    px = [[BLACK] * TILE for _ in range(TILE)]
    for i, c in enumerate(codels[:TILE]):
        px[0][i] = c
    return _px_to_png(px)


def _build_text_codels(text):
    """Цепочка кодлов для текста."""
    if not text:
        return [WHITE]
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN]
    data = text.encode("utf-8", errors="replace")
    codels = []
    h, l = 0, 0
    codels.append(_rgb(h, l))
    for byte in data:
        if byte == 0: continue
        l = (l + 1) % 3
        push_color = _rgb(h, l)
        codels.extend([push_color] * byte)
        h = (h + 5) % 6
        l = (l + 2) % 3
        codels.append(_rgb(h, l))
    return codels


def _make_strip_png(codels):
    """PNG высотой TILE: данные в первой строке (любой ширины)."""
    w = max(1, len(codels))
    px = [[BLACK] * w for _ in range(TILE)]
    for i, c in enumerate(codels[:w]):
        px[0][i] = c
    return _px_to_png(px)


def _gen_text_puzzle(text):
    """
    Текст → ОДИН широкий PNG (не пазл).

    ВАЖНО: не разбиваем на плитки. Блок push может быть длиной
    до 250+ клеток, его нельзя резать. Один длинный ряд —
    единственный корректный формат для текст-энкодера.
    """
    codels = _build_text_codels(text)
    return base64.b64encode(_make_strip_png(codels)).decode("ascii")


# ======================================================================
#  6. Плиточная система
# ======================================================================
def _merge_puzzles(puzzle):
    """Склейка плиток в один массив пикселей (для старого execute)."""
    parts = [p.strip() for p in puzzle.strip().split("|") if p.strip()]
    decoded = []
    for part in parts:
        try:
            raw = base64.b64decode(part)
            w, h, px = _decode_png(raw)
            decoded.append((w, h, px))
        except Exception:
            continue
    if not decoded:
        return None
    total_w = sum(d[0] for d in decoded)
    max_h = max(d[1] for d in decoded)
    merged = []
    for y in range(max_h):
        row = []
        for w, h, px in decoded:
            row.extend(px[y] if y < h else [BLACK] * w)
        merged.append(row)
    return merged, total_w, max_h


def run_tiles(tiles, initial_stack=None):
    """Последовательное исполнение плиток с общим стеком."""
    stack = initial_stack if initial_stack is not None else []
    out_parts = []
    prev_hl = None
    for t_b64 in tiles:
        try:
            raw = base64.b64decode(t_b64)
            w, h, px = _decode_png(raw)
        except Exception:
            continue
        text, stack, prev_hl = _run_2d(px, w, h, stack, prev_hl)
        if text:
            out_parts.append(text)
    return "".join(out_parts)


# ======================================================================
#  7. Ассемблер
# ======================================================================
def parse_asm(text):
    result = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line: continue
        parts = line.split()
        cmd = parts[0].lower()
        if cmd not in COMMANDS:
            raise ValueError(f"строка {i}: неизвестная команда {cmd!r}")
        arg = None
        if len(parts) > 1:
            try: arg = int(parts[1])
            except ValueError:
                raise ValueError(f"строка {i}: аргумент не число")
        if cmd == "push" and arg is None:
            raise ValueError(f"строка {i}: push требует аргумент")
        result.append((cmd, arg))
    return result


def _tile_for_command(cmd, arg, prev_h, prev_l):
    """Строит плитку для одной команды. Возвращает (b64, new_h, new_l)."""
    dh, dl = COMMANDS[cmd]
    h_cmd = (prev_h + dh) % 6
    l_cmd = (prev_l + dl) % 3

    px = [[BLACK] * TILE for _ in range(TILE)]
    px[0][0] = _rgb(prev_h, prev_l)   # стартовый = prev (NOP при первом входе)
    if cmd == "push":
        size = max(1, min(TILE - 1, arg or 1))
        for i in range(1, size + 1):
            px[0][i] = _rgb(h_cmd, l_cmd)
    else:
        px[0][1] = _rgb(h_cmd, l_cmd)

    return base64.b64encode(_px_to_png(px)).decode("ascii"), h_cmd, l_cmd


def asm_to_tiles(text):
    """Ассемблер → список 16×16 плиток."""
    commands = parse_asm(text)
    tiles = []
    h, l = 0, 0
    for cmd, arg in commands:
        if cmd == "push":
            n = max(1, arg or 1)
            chunks = []
            while n > 0:
                c = min(15, n); chunks.append(c); n -= c
            tile, h, l = _tile_for_command("push", chunks[0], h, l)
            tiles.append(tile)
            for c in chunks[1:]:
                tile, h, l = _tile_for_command("push", c, h, l)
                tiles.append(tile)
                tile, h, l = _tile_for_command("add", None, h, l)
                tiles.append(tile)
        else:
            tile, h, l = _tile_for_command(cmd, arg, h, l)
            tiles.append(tile)
    return tiles


def asm_to_puzzle(text):
    """Ассемблер → 'base64|base64|...'."""
    return "|".join(asm_to_tiles(text))


def execute_asm(text):
    """Ассемблер → результат."""
    return run_tiles(asm_to_tiles(text))


# ======================================================================
#  8. Транспайлеры
# ======================================================================
def _to_python(src):
    merged = _merge_puzzles(src)
    if merged is None:
        return "# Piet: пустая программа\n"
    px, w, h = merged
    try:
        result, _, _ = _run_2d(px, w, h)
    except Exception as e:
        return f"# Piet: {e}\n"
    return (f"# Piet → Python\n_out = {result!r}\nprint(_out, end='')\n")


def _python_to_piet(src):
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            exec(compile(src or "", "<py-to-piet>", "exec"), {})
    except BaseException:
        return _gen_text_puzzle("")
    return _gen_text_puzzle(buf.getvalue())


# ======================================================================
#  9. Шаблоны
# ======================================================================
_TEMPLATE_TEXTS = {
    "Hello, World":     "Hello, World!",
    "Буква A":          "A",
    "Цифры 0-9":        "0123456789",
    "Hi!":              "Hi!",
    "Short":            "Hello",
    "Алфавит A-J":      "ABCDEFGHIJ",
    "Esolang":          "Esolang",
    "LOL":              "LOL",
    "ABC":              "ABC",
    "XYZ":              "XYZ",
    "Длинная":          "The quick brown fox jumps over the lazy dog",
    "Fox":              "The quick brown fox",
    "Lorem":            "Lorem ipsum dolor sit amet",
    "Mix":              "0123456789",
    "Symbols":          "!@#$%^&*()",
    "AZ+az":            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "Digital":          "0 1 2 3 4 5 6 7 8 9",
    "Pan x1":           "The quick brown fox jumps over the lazy dog. " * 3,
    "Hello+":           "Hello, World! Hello, World!",
    "Numbers":          "0 1 2 3 4 5 6 7 8 9",
    "Test 1":           "The quick brown fox jumps over the lazy dog. " * 3,
    "Test 2":           "Lorem ipsum dolor sit amet. " * 2,
    "Test 3":           "Hello, World! 42 ABC xyz !@#",
}


def _load_templates():
    out = {}
    for i, (name, text) in enumerate(_TEMPLATE_TEXTS.items(), 1):
        try:
            out[f"[{i}] {name}"] = _gen_text_puzzle(text)
        except Exception:
            out[f"[{i}] {name}"] = _gen_text_puzzle("")
    return out


_TEMPLATES = _load_templates()


# ======================================================================
#  10. Язык
# ======================================================================
class PietLang(Language):
    name = "piet"
    title = "Piet"
    category = "Э"
    ext = ".png"
    keywords = []
    comment_regex = None
    templates = _TEMPLATES

    def execute(self, src):
        if not src or not src.strip():
            return ""
        # Пазл: 'base64|base64|...'
        if "|" in src and not any(c in src for c in "│─╮╭╰╯"):
            try:
                return run_tiles([p.strip() for p in src.split("|")
                                  if p.strip()])
            except Exception as e:
                return f"// Piet: {e}"
        # Одиночный PNG
        try:
            raw = base64.b64decode(src.strip(), validate=False)
            if raw[:8] != b"\x89PNG\r\n\x1a\n":
                return "// Piet: not a PNG"
            w, h, px = _decode_png(raw)
            result, _, _ = _run_2d(px, w, h)
            return result
        except Exception as e:
            return f"// Piet: {type(e).__name__}: {e}"

    def generate_code(self, output):
        return _gen_text_puzzle(output or "")


# ======================================================================
#  11. Регистрация
# ======================================================================
TRANSPILERS[("piet", "python")] = _to_python
TRANSPILERS[("python", "piet")] = _python_to_piet


# ======================================================================
#  Примеры для Piet-ASM вкладки
# ======================================================================
EXAMPLES = {
    # ─── арифметика ──────────────────────────────────────────────────
    "5 + 3 = 8":      "push 5\npush 3\nadd\nout_num\n",
    "10 - 7 = 3":     "push 10\npush 7\nsub\nout_num\n",
    "5 * 3 = 15":     "push 5\npush 3\nmul\nout_num\n",
    "20 / 4 = 5":     "push 20\npush 4\ndiv\nout_num\n",
    "17 % 5 = 2":     "push 17\npush 5\nmod\nout_num\n",

    # ─── сравнения и логика ─────────────────────────────────────────
    "5 > 3 = 1":      "push 5\npush 3\ngt\nout_num\n",
    "3 > 5 = 0":      "push 3\npush 5\ngt\nout_num\n",
    "not 0 = 1":      "push 0\nnot\nout_num\n",
    "not 5 = 0":      "push 5\nnot\nout_num\n",

    # ─── стек ───────────────────────────────────────────────────────
    "dup 7 7":        "push 7\ndup\nout_num\nout_num\n",
    "pop 9":          "push 9\npop\npush 42\nout_num\n",
    "roll":           "push 1\npush 2\npush 3\npush 3\npush 1\nroll\n"
                      "out_num\nout_num\nout_num\n",

    # ─── вывод символов ─────────────────────────────────────────────
    "print 'A'":      "push 65\nout_char\n",
    "print 'Hi'":     "push 72\nout_char\npush 105\nout_char\n",
    "print 'Hello'":  "push 72\nout_char\npush 101\nout_char\n"
                      "push 108\nout_char\npush 108\nout_char\n"
                      "push 111\nout_char\n",
    "72 - 40 = 32":   "push 72\npush 40\nsub\nout_num\n",

    # ─── размер блока = аргумент ────────────────────────────────────
    "push 1 2 3":     "push 1\nout_num\npush 2\nout_num\npush 3\nout_num\n",
    "push 42":        "push 42\nout_num\n",
    "push 100":       "push 100\nout_num\n",

    # ─── служебное ──────────────────────────────────────────────────
    "no-op":          "nop\n",
    "halt via black": "push 7\nout_num\nnop\n",
}