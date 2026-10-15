# tools/piet_pack.py
"""Упаковка команд в одну плитку 16×16 вместо одной плитки на команду."""
from __future__ import annotations
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIET = ROOT / "langs" / "piet.py"

OLD = '''def asm_to_tiles(text):
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
'''

NEW = '''def _build_codels_for_commands(commands):
    """Строит цепочку (h, l, block_size) кодлов для всех команд."""
    codels = []
    h, l = 0, 0
    codels.append((h, l, 1))   # стартовый
    for cmd, arg in commands:
        if cmd == "push":
            n = max(1, arg or 1)
            while n > 0:
                chunk = min(15, n)
                dh, dl = COMMANDS["push"]
                h = (h + dh) % 6
                l = (l + dl) % 3
                codels.append((h, l, chunk))
                n -= chunk
                if n > 0:
                    dh, dl = COMMANDS["add"]
                    h = (h + dh) % 6
                    l = (l + dl) % 3
                    codels.append((h, l, 1))
        else:
            dh, dl = COMMANDS[cmd]
            h = (h + dh) % 6
            l = (l + dl) % 3
            codels.append((h, l, 1))
    return codels


def asm_to_tiles(text):
    """Ассемблер → список 16×16 плиток с упаковкой команд."""
    commands = parse_asm(text)
    codels = _build_codels_for_commands(commands)

    # Упаковываем codels в плитки по 15 клеток (1 клетка под разделитель)
    PER_TILE = 15
    tiles = []

    # Группируем: (h, l, count) → плоский список (h, l)
    flat = []
    for h, l, count in codels:
        for _ in range(count):
            flat.append((h, l))

    for i in range(0, len(flat), PER_TILE):
        chunk = flat[i:i + PER_TILE]
        px = [[BLACK] * TILE for _ in range(TILE)]
        for j, (hh, ll) in enumerate(chunk):
            px[0][j] = _rgb(hh, ll)
        png = _px_to_png(px)
        tiles.append(base64.b64encode(png).decode("ascii"))

    if not tiles:
        px = [[BLACK] * TILE for _ in range(TILE)]
        px[0][0] = WHITE
        tiles = [base64.b64encode(_px_to_png(px)).decode("ascii")]

    return tiles
'''


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    text = PIET.read_text(encoding="utf-8")
    if "_build_codels_for_commands" in text:
        print("  [=] уже пропатчен")
        return

    if OLD not in text:
        print("  [!] не найден asm_to_tiles")
        return

    bak = PIET.with_suffix(PIET.suffix + ".bak_pack")
    if not bak.exists():
        shutil.copy2(PIET, bak)
        print(f"    бэкап: {bak.name}")

    text = text.replace(OLD, NEW, 1)
    PIET.write_text(text, encoding="utf-8")
    print("  [+] piet.py: команды упакованы в общие плитки")


if __name__ == "__main__":
    main()