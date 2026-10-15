# tools/fix_canvas_autodetect2.py
"""Замена _auto_detect_mode: по высоте, а не по цветам."""
from __future__ import annotations
import re
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


NEW = '''    def _auto_detect_mode(self):
        """Автодетект по форме PNG.

        BrainPiet 2D — H нечётная (serpentine: 2N-1)
        BlockPiet 2D — H чётная, маленькая (2, 4, 6...)
        Piet++       — H = 16
        """
        if not self._tiles:
            return
        try:
            import struct
            raw = base64.b64decode(self._tiles[0])
            if raw[:8] != b"\\x89PNG\\r\\n\\x1a\\n":
                return
            w, h = struct.unpack(">II", raw[16:24])
        except Exception:
            return

        if h == 16 and w > 100:
            detected = "PIET++"
        elif h % 2 == 1:
            detected = "BRAINPIET2D"
        elif h <= 8:
            detected = "BLOCKPIET2D"
        else:
            detected = "PIET++"

        if detected != self._mode:
            self._mode = detected
            for m, btn in self._mode_btns.items():
                btn.state(["pressed"] if m == detected else ["!pressed"])
            if self.app:
                self.app.log(
                    f"$ Piet Canvas: автодетект → {detected} ({w}×{h})")

'''


def main():
    _force_utf8()
    text = PC.read_text(encoding="utf-8")

    pat = re.compile(
        r"    def _auto_detect_mode\(self\):.*?(?=\n    def |\n# |\Z)",
        re.DOTALL)

    if not pat.search(text):
        print("  [!] не найден _auto_detect_mode")
        return

    if "h % 2 == 1" in text:
        print("  [=] уже пропатчен (h-based)")
        return

    bak = PC.with_suffix(PC.suffix + ".bak_auto2")
    if not bak.exists():
        shutil.copy2(PC, bak)
        print(f"    бэкап: {bak.name}")

    # lambda — чтобы \x89 не интерпретировался как escape
    text = pat.sub(lambda m: NEW, text, count=1)
    PC.write_text(text, encoding="utf-8")
    print("  [+] _auto_detect_mode → по высоте")


if __name__ == "__main__":
    main()