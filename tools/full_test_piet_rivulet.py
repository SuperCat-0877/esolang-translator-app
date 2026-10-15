# tools/full_test_piet_rivulet.py
"""Полная проверка Piet и Rivulet: что работает, что нет."""

from __future__ import annotations
import base64
import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _force_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def section(t):
    print(f"\n{'='*75}\n  {t}\n{'='*75}")


def ok():
    return "✓"


def bad():
    return "✗"


def warn():
    return "⚠"


# ======================================================================
def test_piet_core():
    section("PIET 1. Ядро: generate_code + execute")
    from core.registry import registry
    p = registry.get("piet")

    tests = ["A", "Hi", "Hi!", "Hello", "Hello, World!",
             "0123456789", "!@#$%", "The quick brown fox"]
    pass_n, fail_n = 0, 0
    for text in tests:
        try:
            code = p.generate_code(text)
            ret = p.execute(code)
            n_tiles = len(code.split("|"))
            match = ret == text
            mark = ok() if match else bad()
            if match:
                pass_n += 1
            else:
                fail_n += 1
            shown = repr(text) if len(text) < 25 else repr(text[:22] + "...")
            rshown = repr(ret) if len(ret) < 30 else repr(ret[:27] + "...")
            print(f"  {mark} {shown:<28} tiles={n_tiles:>3}  ret={rshown}")
        except Exception as e:
            fail_n += 1
            print(f"  {bad()} {text!r:<28} ERR {type(e).__name__}: {e}")

    print(f"\n  Итого: {pass_n} OK, {fail_n} FAIL")
    return pass_n, fail_n


def test_piet_templates():
    section("PIET 2. Шаблоны (25 после replace_all)")
    from core.registry import registry
    from core.extended_templates import replace_all, SPECS
    replace_all(verbose=False)
    p = registry.get("piet")

    # Ожидания для шаблонов
    expected_by_name = {}
    for prefix, level, cat, short, output in SPECS:
        key = f"[{prefix}] {level}-{cat}: {short}"
        expected_by_name[key] = output

    ok_n, fail_n, empty_n = 0, 0, 0
    for name, code in p.templates.items():
        if not code:
            empty_n += 1
            print(f"  {warn()} {name[:50]:<50} ПУСТОЙ")
            continue
        try:
            ret = p.execute(code)
        except Exception as e:
            fail_n += 1
            print(f"  {bad()} {name[:50]:<50} ERR {e}")
            continue
        expected = expected_by_name.get(name, "")
        if ret == expected:
            ok_n += 1
        else:
            fail_n += 1
            print(f"  {bad()} {name}")
            print(f"      ожидалось: {expected[:60]!r}")
            print(f"      получено:  {ret[:60]!r}")

    print(f"\n  Итого: {ok_n} OK, {fail_n} FAIL, {empty_n} пустых")
    return ok_n, fail_n


def test_piet_asm():
    section("PIET 3. Ассемблер")
    from langs.piet import execute_asm, asm_to_tiles, EXAMPLES

    pass_n, fail_n = 0, 0
    for name, code in EXAMPLES.items():
        try:
            ret = execute_asm(code)
            tiles = asm_to_tiles(code)
            # проверяем базовый результат
            checks = {
                "5 + 3": "8", "5 * 3": "15",
                "10 - 7 + 2": "5", "print 'Hi'": "Hi",
                "72 - 40 = 32": "32",
            }
            expected = checks.get(name, None)
            mark = ok() if (expected and ret == expected) else warn()
            if expected and ret == expected:
                pass_n += 1
            else:
                fail_n += 1
            print(f"  {mark} {name:<20} → {ret!r}  (tiles={len(tiles)})")
        except Exception as e:
            fail_n += 1
            print(f"  {bad()} {name:<20} ERR {e}")
    print(f"\n  Итого: {pass_n} OK, {fail_n} FAIL")


def test_piet_translate():
    section("PIET 4. Перевод python ↔ piet")
    from core.translate import TRANSPILERS, translate
    from core.universal_fallback import install, direct_pairs
    install()

    dp = direct_pairs()
    print(f"  Прямые пары:")
    for p in sorted(dp):
        if "piet" in p:
            print(f"    {p}")
    print()

    # python → piet
    cases = [
        ("python", "piet", 'print("Hi")'),
        ("python", "piet", 'print("Hello, World!")'),
        ("go", "piet", 'package main\nfunc main() {}'),
    ]
    for src, dst, code in cases:
        try:
            r = translate(src, dst, code, None)
            if isinstance(r, tuple):
                r = r[0]
            n_tiles = len(r.split("|")) if isinstance(r, str) else 0
            print(f"  {src:<8} → {dst:<6} len={len(r):>5}  tiles={n_tiles}")
        except Exception as e:
            print(f"  {bad()} {src} → {dst} ERR {e}")

    # piet → python
    from core.registry import registry
    p = registry.get("piet")
    piet_code = p.generate_code("Hi")
    try:
        r = translate("piet", "python", piet_code, None)
        print(f"\n  piet → python len={len(r)}")
        print(f"    {r[:100]!r}")
    except Exception as e:
        print(f"  {bad()} piet → python ERR {e}")


def test_piet_canvas_import():
    section("PIET 5. Canvas: импорт и методы")
    try:
        from ui.piet_canvas import PietCanvasTab
        print(f"  {ok()} PietCanvasTab импортируется")
        # методы
        methods = ["_tile_prev", "_tile_next", "_set_zoom", "_enter_png",
                   "_render_png", "from_text", "to_text", "clear"]
        for m in methods:
            has = hasattr(PietCanvasTab, m)
            print(f"  {'✓' if has else '✗'} {m}")
    except Exception as e:
        print(f"  {bad()} импорт ERR {e}")


# ======================================================================
def test_rivulet_core():
    section("RIVULET 1. Ядро: generate_code + execute")
    from core.registry import registry
    riv = registry.get("rivulet")

    tests = ["", " ", "Hi", "Hi!", "Hello", "Hello, World!",
             "17 + 5 = 22", "0123456789"]
    pass_n, fail_n = 0, 0
    for text in tests:
        try:
            code = riv.generate_code(text)
            ret = riv.execute(code)
            match = ret == text
            mark = ok() if match else bad()
            if match:
                pass_n += 1
            else:
                fail_n += 1
            shown = repr(text) if len(text) < 25 else repr(text[:22] + "...")
            rshown = repr(ret) if len(ret) < 30 else repr(ret[:27] + "...")
            print(f"  {mark} {shown:<28} gc={len(code):>5}  ret={rshown}")
        except Exception as e:
            fail_n += 1
            print(f"  {bad()} {text!r:<28} ERR {type(e).__name__}: {e}")

    print(f"\n  Итого: {pass_n} OK, {fail_n} FAIL")
    return pass_n, fail_n


def test_rivulet_templates():
    section("RIVULET 2. Шаблоны (25)")
    from core.registry import registry
    from core.extended_templates import replace_all, SPECS
    replace_all(verbose=False)
    riv = registry.get("rivulet")

    expected_by_name = {}
    for prefix, level, cat, short, output in SPECS:
        key = f"[{prefix}] {level}-{cat}: {short}"
        expected_by_name[key] = output

    ok_n, fail_n = 0, 0
    for name, code in riv.templates.items():
        if not code:
            print(f"  {warn()} {name[:50]} ПУСТОЙ")
            continue
        try:
            ret = riv.execute(code)
        except Exception as e:
            fail_n += 1
            print(f"  {bad()} {name[:50]} ERR {e}")
            continue
        expected = expected_by_name.get(name, "")
        if ret == expected:
            ok_n += 1
        elif expected and ret != expected:
            fail_n += 1
            print(f"  {bad()} {name}")
            print(f"      ожидалось: {expected[:55]!r}")
            print(f"      получено:  {ret[:55]!r}")
        else:
            ok_n += 1   # для не-EXPECTED шаблонов просто "есть вывод"
    print(f"\n  Итого: {ok_n} OK, {fail_n} FAIL")


def test_rivulet_translate():
    section("RIVULET 3. Перевод")
    from core.translate import translate
    from core.registry import registry
    from core.universal_fallback import install, direct_pairs
    install()

    dp = direct_pairs()
    print(f"  Прямые пары:")
    for p in sorted(dp):
        if "rivulet" in p:
            print(f"    {p}")
    print()

    riv = registry.get("rivulet")
    code = riv.generate_code("Hi")

    cases = [
        ("rivulet", "python", code),
        ("rivulet", "javascript", code),
        ("python", "rivulet", 'print("Hi")'),
        ("go", "rivulet", 'package main\nfunc main() {}'),
    ]
    for src, dst, c in cases:
        try:
            r = translate(src, dst, c, None)
            if isinstance(r, tuple):
                r = r[0]
            print(f"  {src:<8} → {dst:<12} len={len(r):>5}  "
                  f"{r[:60]!r}")
        except Exception as e:
            print(f"  {bad()} {src} → {dst} ERR {e}")


def test_rivulet_canvas_import():
    section("RIVULET 4. Canvas: импорт и методы")
    try:
        from ui.rivulet_canvas import RivuletCanvasTab
        print(f"  {ok()} RivuletCanvasTab импортируется")
        methods = ["from_text", "to_text", "clear_all",
                   "send_to_editor", "run_program",
                   "from_editor", "from_editor2"]
        for m in methods:
            has = hasattr(RivuletCanvasTab, m)
            print(f"  {'✓' if has else '✗'} {m}")
    except Exception as e:
        print(f"  {bad()} импорт ERR {e}")


# ======================================================================
def test_ui_integration():
    section("UI 1. Интеграция: наличие кнопок и вкладок")
    app_path = ROOT / "ui" / "app.py"
    text = app_path.read_text(encoding="utf-8")

    checks = {
        "_build_tab_piet_asm":  "def _build_tab_piet_asm" in text,
        "_build_tab_piet":      "def _build_tab_piet" in text,
        "_build_tab_rivulet":   "def _build_tab_rivulet" in text,
        "_build_tab_sandbox":   "def _build_tab_sandbox" in text,
        "_asm_run":             "def _asm_run" in text,
        "_asm_explain":         "def _asm_explain" in text,
        "Разобрать":            "🔍 Разобрать" in text,
        "Запустить":            "▶ Запустить" in text,
        "В Piet Canvas":        "📦 В Piet Canvas" in text,
    }
    for name, has in checks.items():
        print(f"  {'✓' if has else '✗'} {name}")


def test_sandbox_panel():
    section("UI 2. SandboxPanel")
    sp = ROOT / "ui" / "widgets" / "sandbox_panel.py"
    if not sp.is_file():
        print(f"  {bad()} файла нет")
        return
    text = sp.read_text(encoding="utf-8")
    checks = {
        "on_run":       "def on_run" in text,
        "on_explain":   "def on_explain" in text,
        "set_lang":     "def set_lang" in text,
        "get_code":     "def get_code" in text,
        "_tpl_cb":      "self.tpl_cb" in text,
        "_on_lang_change": "def _on_lang_change" in text,
    }
    for name, has in checks.items():
        print(f"  {'✓' if has else '✗'} {name}")


# ======================================================================
def test_piet_in_sandbox():
    section("UI 3. Что происходит в Песочнице для piet/rivulet")
    # Пробуем симулировать, что делает песочница
    from core.registry import registry
    from services import get_execute_service

    svc = get_execute_service()
    try:
        for lang_name in ("piet", "rivulet"):
            lang = registry.get(lang_name)
            # что делает песочница: берёт шаблон, отправляет в сервис
            first_tpl = next(iter(lang.templates))
            code = lang.templates[first_tpl]
            print(f"\n  {lang_name}: шаблон {first_tpl}")
            print(f"    код: len={len(code)}, первые 80: {code[:80]!r}")
            res = svc.run(lang_name, code, timeout=5.0)
            print(f"    execute ok={res.ok}  out={res.output[:60]!r}")
            if res.error:
                print(f"    ошибка: {res.error[:80]}")
    finally:
        svc.close()


# ======================================================================
def main():
    _force_utf8()

    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()

    section("ИТОГОВАЯ ПРОВЕРКА PIET + RIVULET + UI")
    print("Проверка 12 секций. Смотри, где ✗ — там баг.")

    # PIET
    test_piet_core()
    test_piet_templates()
    test_piet_asm()
    test_piet_translate()
    test_piet_canvas_import()

    # RIVULET
    test_rivulet_core()
    test_rivulet_templates()
    test_rivulet_translate()
    test_rivulet_canvas_import()

    # UI
    test_ui_integration()
    test_sandbox_panel()
    test_piet_in_sandbox()

    section("КОНЕЦ ПРОВЕРКИ")
    print("Если где-то ✗ — пришли этот блок, я вижу что чинить.")


if __name__ == "__main__":
    main()