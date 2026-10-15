# tools/fix_all_strings.py
"""
Все string-aware фиксы в одном скрипте.

  1. Создаёт core/str_utils.py (утилиты)
  2. JS: line.split("//", 1)[0] → string-aware
  3. CPP: _rewrite_cout через защиту ; и << внутри строк
  4. Диагностика lolcode / elixir

Запуск:
    python tools/fix_all_strings.py --check
    python tools/fix_all_strings.py
    python tools/fix_all_strings.py --revert
    python tools/fix_all_strings.py --test
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SU = ROOT / "core" / "str_utils.py"
JS = ROOT / "langs" / "javascript_lang.py"
CPP = ROOT / "langs" / "cpp_lang.py"
LC = ROOT / "langs" / "lolcode.py"
EL = ROOT / "langs" / "elixir.py"


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ======================================================================
#  STR_UTILS
# ======================================================================
STR_UTILS = r'''# core/str_utils.py
"""String-aware утилиты: split/find вне строковых литералов."""
from __future__ import annotations


def cut_line_comment(line: str, marker: str = "//") -> str:
    """Срезает маркер и всё после, если он вне строк."""
    i, n = 0, len(line)
    in_str = None
    while i < n:
        c = line[i]
        if in_str:
            if c == "\\" and i + 1 < n:
                i += 2; continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c == '"' or c == "'":
            in_str = c; i += 1; continue
        if line.startswith(marker, i):
            return line[:i]
        i += 1
    return line


def split_statements(src: str) -> list[str]:
    """Разбивает по ; вне строк и вне скобок."""
    parts = []
    i, n = 0, len(src)
    depth = 0
    in_str = None
    cur_start = 0
    while i < n:
        c = src[i]
        if in_str:
            if c == "\\" and i + 1 < n:
                i += 2; continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c == '"' or c == "'":
            in_str = c; i += 1; continue
        if c == "(" or c == "[" or c == "{":
            depth += 1
        elif c == ")" or c == "]" or c == "}":
            depth -= 1
        elif c == ";" and depth == 0:
            parts.append(src[cur_start:i])
            cur_start = i + 1
        i += 1
    if cur_start < n:
        parts.append(src[cur_start:])
    return [p for p in parts if p.strip()]
'''


# ======================================================================
#  JS
# ======================================================================
JS_OLD = '''            line = line.split("//", 1)[0]'''
JS_NEW = '''            # PATCH: string-aware cut комментария
            from core.str_utils import cut_line_comment as _jsl_cut
            line = _jsl_cut(line, "//")'''


# ======================================================================
#  CPP — защита строк перед regex
# ======================================================================
CPP_OLD = '''def _rewrite_cout(src):
    """cout << A << B << "C";  →  print(A, B, "C", sep='', end='')"""
    def repl(m):
        body = m.group(1)
        parts = _split_by_op(body, '<<')
        args = [_cpp_expr(p.strip()) for p in parts if p.strip()]
        return f"print({', '.join(args)}, sep='', end='')"
    return re.sub(r"(?:std::)?cout\\s*<<\\s*(.+?)\\s*;", repl, src)'''

CPP_NEW = '''def _protect_cpp_strings(src):
    """Заменяет ; и << внутри строк на маркеры. Возвращает (текст, словарь)."""
    MARK_SEMI = "\\x01S\\x01"
    MARK_LT   = "\\x01L\\x01"
    out = []
    in_str = None
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if in_str:
            if c == "\\\\" and i + 1 < n:
                out.append(c); out.append(src[i + 1])
                i += 2; continue
            if c == in_str:
                in_str = None
                out.append(c); i += 1; continue
            if src.startswith(";", i):
                out.append(MARK_SEMI); i += 1; continue
            if src.startswith("<<", i):
                out.append(MARK_LT); i += 2; continue
            out.append(c); i += 1; continue
        if c == '"' or c == "'":
            in_str = c; out.append(c); i += 1; continue
        out.append(c); i += 1
    return "".join(out), MARK_SEMI, MARK_LT


def _restore_cpp_strings(text, mark_semi, mark_lt):
    return text.replace(mark_semi, ";").replace(mark_lt, "<<")


def _rewrite_cout(src):
    """cout << A << "B; C"; → print(A, "B; C", sep='', end='')

    PATCH: ; и << внутри строк защищены маркерами, чтобы regex
    не рвал выражение по ; и не путал << внутри строк с оператором.
    """
    protected, M_SEMI, M_LT = _protect_cpp_strings(src)

    def repl(m):
        body = m.group(1)
        # Восстановить << для корректного split
        body_for_split = body.replace(M_LT, "<<")
        parts = _split_by_op(body_for_split, "<<")
        args = []
        for p in parts:
            if not p.strip():
                continue
            # Восстановить оригинальные ; и << в аргументе
            p2 = p.replace(M_SEMI, ";").replace(M_LT, "<<")
            args.append(_cpp_expr(p2.strip()))
        return f"print({', '.join(args)}, sep='', end='')"

    result = re.sub(r"(?:std::)?cout\\s*<<\\s*(.+?)\\s*;", repl, protected)
    return _restore_cpp_strings(result, M_SEMI, M_LT)'''


# ======================================================================
def ensure_str_utils(dry=False):
    if SU.is_file() and "def cut_line_comment" in SU.read_text(encoding="utf-8"):
        print("  [=] core/str_utils.py уже есть")
        return 0
    if dry:
        print("  [dry] создать core/str_utils.py")
        return 0
    SU.parent.mkdir(exist_ok=True)
    SU.write_text(STR_UTILS, encoding="utf-8")
    print("  [+] core/str_utils.py создан")
    return 1


def patch(p, old, new, marker, dry=False, check=False):
    if not p.is_file():
        print(f"  [!] нет файла: {p.name}")
        return 0
    text = p.read_text(encoding="utf-8")
    if marker in text:
        print(f"  [=] {p.name}: уже пропатчен")
        return 0
    if old not in text:
        print(f"  [!] {p.name}: блок не найден")
        return 0
    if check:
        print(f"  ✓ {p.name}: найден")
        return 1
    if dry:
        print(f"  [dry] {p.name}: 1 замена")
        return 1
    bak = p.with_suffix(p.suffix + ".bak_strings2")
    if not bak.exists():
        shutil.copy2(p, bak)
        print(f"    бэкап: {bak.name}")
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print(f"  [+] {p.name}: пропатчен")
    return 1


def diagnose():
    print("\n  Диагностика lolcode.py и elixir.py:")
    for name, p in (("lolcode", LC), ("elixir", EL)):
        if not p.is_file():
            print(f"    [!] {name}: файла нет")
            continue
        text = p.read_text(encoding="utf-8")
        issues = []
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if (("split" in s or "re.sub" in s or "re.match" in s)
                    and '";"' not in s and "';'" not in s):
                if any(ch in s for ch in (";", "//", "#")):
                    issues.append((i, s[:100]))
        if issues:
            print(f"    {name}: {len(issues)} подозрительных")
            for i, s in issues[:6]:
                print(f"      {i:>4}: {s}")
        else:
            print(f"    {name}: явных проблем нет")


def run_test():
    _force_utf8()
    from core.config import load as load_config
    from core.registry import registry
    load_config(); registry.discover_builtin()
    from core.extended_templates import replace_all
    replace_all(verbose=False)
    from core.universal_fallback import install
    install()

    print(f"\n{'='*72}\n  ТЕСТ\n{'='*72}")
    cpp = registry.get("cpp")
    cases = [
        ('int main(){ std::cout << "Hi"; return 0; }', "Hi"),
        ('int main(){ std::cout << "Hello, World!"; return 0; }',
         "Hello, World!"),
        ('int main(){ std::cout << "a; b"; return 0; }', "a; b"),
        ('int main(){ std::cout << "a << b"; return 0; }', "a << b"),
        ('int main(){ std::cout << "x" << " " << "y"; return 0; }', "x y"),
    ]
    print("\nCPP:")
    ok = 0
    for src, exp in cases:
        try:
            r = cpp.execute(src).strip()
            mark = "✓" if r == exp else "✗"
            if r == exp: ok += 1
            print(f"  {mark} {exp!r:<25} → {r!r}")
        except Exception as e:
            print(f"  ✗ {exp!r:<25} ERR {e}")
    print(f"  Итого: {ok}/{len(cases)}")

    js = registry.get("javascript")
    print("\nJS:")
    jcases = [
        ("console.log('17 // 5 = 3');", "17 // 5 = 3"),
        ("console.log('// comm');", "// comm"),
        ("console.log('a; b');", "a; b"),
    ]
    jok = 0
    for src, exp in jcases:
        try:
            r = js.execute(src).strip()
            mark = "✓" if r == exp else "✗"
            if r == exp: jok += 1
            print(f"  {mark} {src[:35]:<35} → {r!r}")
        except Exception as e:
            print(f"  ✗ {src[:35]} ERR {e}")
    print(f"  Итого: {jok}/{len(jcases)}")


def main():
    _force_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--revert", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    if args.revert:
        for p in (JS, CPP):
            bak = p.with_suffix(p.suffix + ".bak_strings2")
            if bak.is_file():
                shutil.copy2(bak, p)
                print(f"  [<] {p.name}: восстановлен")
            else:
                bak2 = p.with_suffix(p.suffix + ".bak_strings")
                if bak2.is_file():
                    shutil.copy2(bak2, p)
                    print(f"  [<] {p.name}: восстановлен из .bak_strings")
        return

    if args.test:
        run_test()
        return

    print(f"Корень: {ROOT}\n")

    if args.check:
        print("Проверка:")
        patch(JS, JS_OLD, JS_NEW, "_jsl_cut", check=True)
        patch(CPP, CPP_OLD, CPP_NEW, "_protect_cpp_strings", check=True)
        diagnose()
        return

    print("1. core/str_utils.py:")
    ensure_str_utils(dry=args.dry)
    print("\n2. JS:")
    patch(JS, JS_OLD, JS_NEW, "_jsl_cut", dry=args.dry)
    print("\n3. CPP:")
    patch(CPP, CPP_OLD, CPP_NEW, "_protect_cpp_strings", dry=args.dry)
    print("\n4. Диагностика:")
    diagnose()

    if not args.dry:
        print("\nГотово. Запусти:")
        print("  python tools/fix_all_strings.py --test")
        print("  python tools/test_rivulet_matrix.py")


if __name__ == "__main__":
    main()