# core/py_to_rivulet.py

# --- PATCH: quiet log ---
import os as _os_patch
import sys as _sys_patch

_RIV_VERBOSE = _os_patch.environ.get("RIVULET_VERBOSE") == "1"

def _log(*args, **kw):
    if _RIV_VERBOSE:
        kw.setdefault("file", _sys_patch.stderr)
        print(*args, **kw)
# --- /PATCH ---
"""Python → Rivulet (поиск ближайшей программы из библиотеки)."""

import difflib

_LIB_CACHE = None


def _norm(s):
    if s is None:
        return ""
    return " ".join(s.strip().lower().split())


def _similarity(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _build_library():
    global _LIB_CACHE
    if _LIB_CACHE is not None:
        return _LIB_CACHE

    lib = []
    try:
        from langs.rivulet import RivuletLang
        lang = RivuletLang()
    except Exception as e:
        _log(f"[py_to_rivulet] RivuletLang: {e}")
        _LIB_CACHE = lib
        return lib

    for name, code in lang.templates.items():
        if not code or not code.strip():
            continue
        try:
            out = lang.execute(code)
        except Exception as e:
            _log(f"[py_to_rivulet] {name}: {e}")
            continue
        if out:
            lib.append((_norm(out), out, code, name))

    _log(f"[py_to_rivulet] библиотека: {len(lib)} программ")
    _LIB_CACHE = lib
    return lib


def py_to_rivulet(src):
    if not src or not src.strip():
        return "# пустой Python-код\n"

    try:
        from langs.python_lang import PythonLang
        py_lang = PythonLang()
        py_out = py_lang.execute(src)
    except Exception as e:
        return f"# Python: ошибка выполнения — {e}\n"

    if py_out is None:
        return "# Python: не удалось выполнить\n"
    if isinstance(py_out, str) and py_out.startswith("// Python:"):
        return f"# {py_out}\n"

    py_norm = _norm(py_out)
    lib = _build_library()
    if not lib:
        return ("# Rivulet_examples/ пуста или программы не выполняются.\n")

    scored = []
    for norm, orig, code, name in lib:
        scored.append((_similarity(py_norm, norm), name, code, orig, norm))
    scored.sort(reverse=True, key=lambda x: x[0])

    score, name, code, orig, norm = scored[0]
    _log(f"[py_to_rivulet] лучшее совпадение: {name}  ({score:.0%})")

    if score >= 0.5:
        return (
            "# ────────────────────────────────────────────────\n"
            f"# Ближайшая Rivulet-программа: {name}  ({score:.0%})\n"
            f"# Её вывод:    {orig!r}\n"
            f"# Вывод Python: {py_out!r}\n"
            "# ────────────────────────────────────────────────\n\n"
            + code
        )

    body_lines = py_out.split("\n")
    if body_lines and body_lines[-1] == "":
        body_lines = body_lines[:-1]
    preview = "\n".join(f"#   {l!r}" for l in body_lines[:20])
    top = "\n".join(f"#   {s:.0%}  {n}" for s, n, _, _, _ in scored[:5])

    return (
        "# ────────────────────────────────────────────────\n"
        "# Rivulet-программа с похожим выводом не найдена.\n"
        "# Ближайшие:\n"
        + top + "\n"
        "# ────────────────────────────────────────────────\n"
        "#\n"
        "# Что печатает Python:\n"
        + preview + "\n"
    )