# tools/fix_translate_priority.py
"""
Ставит fallback последним в translate():

Было:
  1. Прямой (включая universal_*)
  2. Chain
  3. IR
  4. Отказ

Станет:
  1. Прямой (только настоящий, не universal_*)
  2. Chain через python
  3. IR
  4. universal_* fallback
  5. Отказ

Запуск:
    python tools/fix_translate_priority.py --check
    python tools/fix_translate_priority.py
    python tools/fix_translate_priority.py --revert
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "core" / "translate.py"

MARKER = "# --- PATCH: fallback-last ---"


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _force_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    if args.revert:
        bak = TR.with_suffix(TR.suffix + ".bak_prio")
        if bak.is_file():
            shutil.copy2(bak, TR)
            print("  [<] восстановлен")
        return

    text = TR.read_text(encoding="utf-8")

    if MARKER in text or "_is_universal_fallback" in text:
        print("  [=] уже пропатчен")
        return

    # Ищем блок translate() целиком
    start = text.find("def translate(")
    if start < 0:
        print("  [!] не найден def translate")
        return

    # Ищем конец: следующий def на верхнем уровне
    import re
    m = re.search(r"\ndef \w+\(", text[start + 1:])
    end = start + 1 + m.start() if m else len(text)

    old_block = text[start:end]

    new_block = '''def _is_universal_fallback(fn) -> bool:
    name = getattr(fn, "__name__", "")
    return name.startswith("universal_")


def translate(src_name, dst_name, code, piet_program=None):
    src = registry.get(src_name)
    dst = registry.get(dst_name)
    if not src or not dst:
        return "// Неизвестный язык\\n"

    if src_name == dst_name:
        return code

    fn = TRANSPILERS.get((src_name, dst_name))
    real_direct = fn is not None and not _is_universal_fallback(fn)

    # 1. Прямой транспайлер (только настоящий)
    if real_direct:
        try:
            r = fn(code)
            if r and r.strip():
                return r
        except Exception:
            pass

    # 2. Chain через python
    try:
        from .universal_fallback import _chain_via_python
        chained = _chain_via_python(src_name, dst_name, code)
        if chained:
            return chained
    except Exception:
        pass

    # 3. IR
    ok, result = _ir_translate(src_name, dst_name, code)
    if ok:
        return result

    # 4. universal_* fallback
    if fn is not None and _is_universal_fallback(fn):
        try:
            r = fn(code)
            if r and r.strip():
                return r
        except Exception:
            pass

    # 5. Отказ
    return (
        f"// {src.title if src else src_name} → "
        f"{dst.title if dst else dst_name}: нет перевода.\\n"
        f"{result}"
    )
'''

    if args.check:
        print("  ✓ translate найден, 1 замена")
        print(f"      старый блок: {len(old_block)} символов")
        print(f"      новый блок:  {len(new_block)} символов")
        return

    bak = TR.with_suffix(TR.suffix + ".bak_prio")
    if not bak.exists():
        shutil.copy2(TR, bak)
        print(f"    бэкап: {bak.name}")

    text = text[:start] + new_block + text[end:]
    TR.write_text(text, encoding="utf-8")
    print("  [+] translate.py: fallback на 4-м месте")


if __name__ == "__main__":
    main()