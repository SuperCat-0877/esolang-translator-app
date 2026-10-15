# tools/diag_3_modes.py
"""Диагностика: почему IS2 не меняется между brainpiet/blockpiet/piet."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _force_utf8()
    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()
    from core.universal_fallback import install
    install()
    from core.translate import translate, TRANSPILERS

    src = 'print("Hi")'

    for dst in ("brainpiet", "blockpiet", "piet"):
        print(f"\n{'='*60}")
        print(f"  python → {dst}")
        print(f"{'='*60}")

        # 1. Зарегистрирован ли прямой транспайлер?
        direct = TRANSPILERS.get(("python", dst))
        print(f"  TRANSPILERS[('python', '{dst}')] = "
              f"{direct.__name__ if direct else 'None'}")

        # 2. Что возвращает translate?
        try:
            r = translate("python", dst, src, None)
            if isinstance(r, tuple):
                r = r[0]
            if isinstance(r, str):
                print(f"  translate OK: len={len(r)}")
                print(f"    первые 100: {r[:100]!r}")
                # Разбираем если это puzzle
                if "|" in r:
                    parts = r.split("|")
                    print(f"    puzzle: {len(parts)} плиток")
                    import base64, struct
                    try:
                        raw = base64.b64decode(parts[0])
                        w, h = struct.unpack(">II", raw[16:24])
                        print(f"    первая плитка: {w}×{h}")
                    except Exception:
                        pass
                else:
                    # одна плитка?
                    import base64, struct
                    try:
                        raw = base64.b64decode(r.strip())
                        if raw[:8] == b"\x89PNG\r\n\x1a\n":
                            w, h = struct.unpack(">II", raw[16:24])
                            print(f"    PNG: {w}×{h}")
                        else:
                            print(f"    не PNG")
                    except Exception:
                        pass
            else:
                print(f"  translate вернул: {type(r).__name__}")
        except Exception as e:
            print(f"  translate ERR: {type(e).__name__}: {e}")

        # 3. Генерируем напрямую через lang.generate_code
        lang = registry.get(dst)
        if lang:
            try:
                gc = lang.generate_code("Hi")
                print(f"  {dst}.generate_code('Hi'): len={len(gc)}")
                if isinstance(gc, str):
                    print(f"    первые 80: {gc[:80]!r}")
            except Exception as e:
                print(f"  generate_code ERR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()