# langs/blockpiet2d.py
"""
BlockPiet 2D — настоящий 2D-язык с блоками 2×2 и DP/CC.

Каждый блок 2×2 = одна команда с аргументами:
    [cmd a1]      ← верхняя пара пикселей
    [a2  a3]      ← нижняя пара

20 команд:
    PUSH  POP  ADD  SUB  MUL  DIV  MOD  DUP  SWAP
    LOAD  STORE  OUT_NUM  OUT_CHAR  GT  LT
    JMP   JZ   JNZ   NOP   HALT

Движение: DP (Direction Pointer) + CC (Codel Chooser), как в Piet.
Чёрный блок — стоп. Программа = 2D-сетка блоков 2×2.
"""

import base64
import struct
import zlib

from core.base import Language
from core.translate import TRANSPILERS


# ======================================================================
#  Палитра (20 цветов)
# ======================================================================
PALETTE = [
    (255, 192, 192), (255, 255, 192), (192, 255, 192), (192, 255, 255),
    (192, 192, 255), (255, 192, 255),
    (255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255),
    (0, 0, 255), (255, 0, 255),
    (192, 0, 0), (192, 192, 0), (0, 192, 0), (0, 192, 192),
    (0, 0, 192), (192, 0, 192),
    (255, 255, 255),  # 18 white
    (0, 0, 0),        # 19 black
]
PAL_IDX = {c: i for i, c in enumerate(PALETTE)}
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


# ======================================================================
#  Команды
# ======================================================================
CMDS = [
    "PUSH", "POP", "ADD", "SUB", "MUL", "DIV", "MOD", "DUP", "SWAP",
    "LOAD", "STORE", "OUT_NUM", "OUT_CHAR",
    "GT", "LT",
    "JMP", "JZ", "JNZ", "NOP", "HALT",
]
CMD_ID = {n: i for i, n in enumerate(CMDS)}

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
#  Интерпретатор 2D с DP/CC
# ======================================================================
def _read_block(px, bx, by):
    """Читает блок 2×2 с координатами (bx, by) — в блоках, не пикселях."""
    x = bx * 2
    y = by * 2
    tl = px[y][x]
    tr = px[y][x + 1]
    bl = px[y + 1][x]
    br = px[y + 1][x + 1]
    return (PAL_IDX.get(tl, 19),
            PAL_IDX.get(tr, 0),
            PAL_IDX.get(bl, 0),
            PAL_IDX.get(br, 0))


def run_2d(px, W, H, max_steps: int = 1_000_000) -> str:
    """Исполняет BlockPiet 2D-программу."""
    BW = W // 2
    BH = H // 2

    # старт — верхний левый не-чёрный блок
    bx, by = 0, 0
    found = False
    for j in range(BH):
        for i in range(BW):
            cmd_id, *_ = _read_block(px, i, j)
            if cmd_id != 19:
                bx, by = i, j
                found = True
                break
        if found:
            break
    if not found:
        return ""

    dp = [0]
    cc = [0]
    tape = [0] * 256
    stack = []
    out = []
    steps = 0

    while steps < max_steps:
        steps += 1
        cmd_id, a1, a2, a3 = _read_block(px, bx, by)

        if cmd_id == 19:
            break

        cmd = CMDS[cmd_id] if cmd_id < len(CMDS) else "NOP"

        if cmd == "PUSH":
            stack.append(a1 + a2 * 20)
        elif cmd == "POP":
            if stack:
                stack.pop()
        elif cmd == "ADD":
            if len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(b + a)
        elif cmd == "SUB":
            if len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(b - a)
        elif cmd == "MUL":
            if len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(b * a)
        elif cmd == "DIV":
            if len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(0 if a == 0 else b // a)
        elif cmd == "MOD":
            if len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(0 if a == 0 else b % a)
        elif cmd == "DUP":
            if stack:
                stack.append(stack[-1])
        elif cmd == "SWAP":
            if len(stack) >= 2:
                stack[-1], stack[-2] = stack[-2], stack[-1]
        elif cmd == "LOAD":
            stack.append(tape[(a1 + a2 * 20) % 256])
        elif cmd == "STORE":
            if stack:
                tape[(a1 + a2 * 20) % 256] = stack.pop() & 0xFF
        elif cmd == "OUT_NUM":
            if stack:
                out.append(str(stack.pop()))
        elif cmd == "OUT_CHAR":
            if stack:
                out.append(chr(stack.pop() & 0xFF))
        elif cmd == "GT":
            if len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(1 if b > a else 0)
        elif cmd == "LT":
            if len(stack) >= 2:
                a, b = stack.pop(), stack.pop()
                stack.append(1 if b < a else 0)
        elif cmd == "NOP":
            pass
        elif cmd == "HALT":
            break
        elif cmd in ("JMP", "JZ", "JNZ"):
            target = a1 + a2 * 20
            do_jump = False
            if cmd == "JMP":
                do_jump = True
            elif cmd == "JZ":
                if stack and stack.pop() == 0:
                    do_jump = True
            elif cmd == "JNZ":
                if stack and stack.pop() != 0:
                    do_jump = True
            if do_jump:
                target_bx = target % BW
                target_by = target // BW
                if 0 <= target_bx < BW and 0 <= target_by < BH:
                    bx, by = target_bx, target_by
                    continue

        moved = False
        for attempt in range(2):
            dx, dy = DP_VECTORS[dp[0]]
            nx, ny = bx + dx, by + dy
            if (0 <= nx < BW and 0 <= ny < BH
                    and _read_block(px, nx, ny)[0] != 19):
                bx, by = nx, ny
                moved = True
                break
            cc[0] = 1 - cc[0]
        if not moved:
            break

    return "".join(out)


# ======================================================================
#  Serpentine-упаковка команд в 2D PNG
# ======================================================================
def commands_to_png(commands, W: int = 0) -> bytes:
    n = len(commands)
    if W <= 0:
        W = max(8, n)
    rows = max(1, (n + W - 1) // W)
    BW = W
    BH = rows
    px = [[WHITE] * (BW * 2) for _ in range(BH * 2)]

    for i, cmd_tuple in enumerate(commands):
        r = i // W
        c = i % W
        cmd_name = cmd_tuple[0]
        a1 = cmd_tuple[1] if len(cmd_tuple) > 1 else 0
        a2 = cmd_tuple[2] if len(cmd_tuple) > 2 else 0
        a3 = cmd_tuple[3] if len(cmd_tuple) > 3 else 0
        cid = CMD_ID.get(cmd_name, 18)

        x = c * 2
        y = r * 2
        px[y][x]         = PALETTE[cid % 20]
        px[y][x + 1]     = PALETTE[a1 % 20]
        px[y + 1][x]     = PALETTE[a2 % 20]
        px[y + 1][x + 1] = PALETTE[a3 % 20]

    return _encode_png(px)


# ======================================================================
#  Python → команды
# ======================================================================
def python_to_commands(src: str) -> list:
    """Python → команды BlockPiet 2D. Умеет if/while/for/+=."""
    import ast
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return [("HALT", 0, 0, 0)]

    cmds = []
    vars_addr = {}
    next_addr = [0]

    def addr(name):
        if name not in vars_addr:
            vars_addr[name] = next_addr[0]
            next_addr[0] += 1
        return vars_addr[name]

    def emit_jump(op, target_idx):
        a1 = target_idx % 20
        a2 = (target_idx // 20) % 20
        cmds.append((op, a1, a2, 0))

    def patch_jump(idx, target_idx):
        op = cmds[idx][0]
        cmds[idx] = (op, target_idx % 20, (target_idx // 20) % 20, 0)

    _BINOP = {"Add": "ADD", "Sub": "SUB", "Mult": "MUL",
              "Div": "DIV", "Mod": "MOD"}

    def emit_expr(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                cmds.append(("PUSH", 1 if node.value else 0, 0, 0))
            elif isinstance(node.value, (int, float)):
                n = int(node.value)
                cmds.append(("PUSH", n % 20, (n // 20) % 20, 0))
            return
        if isinstance(node, ast.Name):
            a = addr(node.id)
            cmds.append(("LOAD", a % 20, (a // 20) % 20, 0))
            return
        if isinstance(node, ast.BinOp):
            emit_expr(node.left)
            emit_expr(node.right)
            op = _BINOP.get(type(node.op).__name__)
            if op:
                cmds.append((op, 0, 0, 0))
            return
        if isinstance(node, ast.Compare):
            if len(node.comparators) != 1:
                return
            emit_expr(node.left)
            emit_expr(node.comparators[0])
            op = type(node.ops[0]).__name__
            if op == "Gt":
                cmds.append(("GT", 0, 0, 0))
            elif op == "Lt":
                cmds.append(("LT", 0, 0, 0))

    def emit_print(arg):
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            for ch in arg.value:
                code = ord(ch) & 0xFF
                cmds.append(("PUSH", code % 20, (code // 20) % 20, 0))
                cmds.append(("OUT_CHAR", 0, 0, 0))
        else:
            emit_expr(arg)
            cmds.append(("OUT_NUM", 0, 0, 0))
        # перенос строки после print
        cmds.append(("PUSH", 10, 0, 0))
        cmds.append(("OUT_CHAR", 0, 0, 0))

    def emit_stmt(stmt):
        if isinstance(stmt, ast.Assign):
            tgt = stmt.targets[0]
            if isinstance(tgt, ast.Name):
                emit_expr(stmt.value)
                a = addr(tgt.id)
                cmds.append(("STORE", a % 20, (a // 20) % 20, 0))
            return

        if isinstance(stmt, ast.AugAssign):
            if isinstance(stmt.target, ast.Name):
                a = addr(stmt.target.id)
                cmds.append(("LOAD", a % 20, (a // 20) % 20, 0))
                emit_expr(stmt.value)
                op = _BINOP.get(type(stmt.op).__name__)
                if op:
                    cmds.append((op, 0, 0, 0))
                cmds.append(("STORE", a % 20, (a // 20) % 20, 0))
            return

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if (isinstance(call.func, ast.Name)
                    and call.func.id == "print"
                    and call.args):
                emit_print(call.args[0])
            return

        if isinstance(stmt, ast.If):
            emit_expr(stmt.test)
            jz_pos = len(cmds)
            cmds.append(("JZ", 0, 0, 0))

            for s in stmt.body:
                emit_stmt(s)

            if stmt.orelse:
                jmp_pos = len(cmds)
                cmds.append(("JMP", 0, 0, 0))
                patch_jump(jz_pos, len(cmds))
                for s in stmt.orelse:
                    emit_stmt(s)
                patch_jump(jmp_pos, len(cmds))
            else:
                patch_jump(jz_pos, len(cmds))
            return

        if isinstance(stmt, ast.While):
            loop_start = len(cmds)
            emit_expr(stmt.test)
            jz_pos = len(cmds)
            cmds.append(("JZ", 0, 0, 0))
            for s in stmt.body:
                emit_stmt(s)
            emit_jump("JMP", loop_start)
            patch_jump(jz_pos, len(cmds))
            return

        if isinstance(stmt, ast.For):
            if not isinstance(stmt.target, ast.Name):
                return
            it = stmt.iter
            if not (isinstance(it, ast.Call)
                    and isinstance(it.func, ast.Name)
                    and it.func.id == "range"
                    and len(it.args) == 1):
                return
            a = addr(stmt.target.id)
            cmds.append(("PUSH", 0, 0, 0))
            cmds.append(("STORE", a % 20, (a // 20) % 20, 0))

            loop_start = len(cmds)
            cmds.append(("LOAD", a % 20, (a // 20) % 20, 0))
            emit_expr(it.args[0])
            cmds.append(("LT", 0, 0, 0))
            jz_pos = len(cmds)
            cmds.append(("JZ", 0, 0, 0))

            for s in stmt.body:
                emit_stmt(s)

            cmds.append(("LOAD", a % 20, (a // 20) % 20, 0))
            cmds.append(("PUSH", 1, 0, 0))
            cmds.append(("ADD", 0, 0, 0))
            cmds.append(("STORE", a % 20, (a // 20) % 20, 0))
            emit_jump("JMP", loop_start)
            patch_jump(jz_pos, len(cmds))
            return

    for stmt in tree.body:
        emit_stmt(stmt)

    cmds.append(("HALT", 0, 0, 0))
    return cmds


# ======================================================================
#  Language
# ======================================================================
class BlockPiet2DLang(Language):
    name = "blockpiet2d"
    title = "BlockPiet 2D"
    category = "Э"
    ext = ".bpng2d"
    keywords = []
    comment_regex = None

    def __init__(self):
        examples = {
            "[1] print 42":     "print(42)",
            "[2] print 'Hi'":   "print('Hi')",
            "[3] x = 5":        "x = 5\nprint(x)",
            "[4] 5 + 3":        "x = 5 + 3\nprint(x)",
            "[5] Hello":        "print('Hello')",
        }
        self.templates = {}
        for name, src in examples.items():
            cmds = python_to_commands(src)
            png = commands_to_png(cmds)
            self.templates[name] = base64.b64encode(png).decode("ascii")

    def execute(self, src):
        if not src or not src.strip():
            return ""
        try:
            raw = base64.b64decode(src.strip())
            if raw[:8] != b"\x89PNG\r\n\x1a\n":
                return "// BlockPiet2D: not PNG"
            w, h, px = _decode_png(raw)
            return run_2d(px, w, h)
        except Exception as e:
            return f"// BlockPiet2D: {type(e).__name__}: {e}"

    def generate_code(self, output):
        if not output:
            return base64.b64encode(
                commands_to_png([("HALT", 0, 0, 0)])).decode("ascii")
        src = f"print({output!r})"
        cmds = python_to_commands(src)
        return base64.b64encode(commands_to_png(cmds)).decode("ascii")


TRANSPILERS[("python", "blockpiet2d")] = lambda src: base64.b64encode(
    commands_to_png(python_to_commands(src))).decode("ascii")
TRANSPILERS[("blockpiet2d", "python")] = lambda src: (
    f"# BlockPiet2D → Python\n"
    f"_out = {BlockPiet2DLang().execute(src)!r}\n"
    f"print(_out, end='')\n")