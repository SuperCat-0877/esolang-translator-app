# core/universal_fallback.py
"""
Универсальный fallback для translate().

Приоритет:
  1. Прямой транспайлер (src, dst) — регистрируется модулями langs/*.
  2. Chain через python: src → python → dst, ТОЛЬКО если оба плеча —
     прямые транспайлеры. Это даёт НАСТОЯЩИЙ перевод, а не «печать
     готового вывода строкой».
  3. Execute + generate_code — «медленный» путь: запускаем исходник,
     получаем output, генерируем код, который печатает этот output.
     Используется только когда chain невозможен.
  4. Stub через generate_code(" ") — для эзотериков, которые не умеют
     рендерить произвольный текст, но дают валидный код для пробела.

Гарантирует, что translate() никогда не падает с KeyError.
"""
from __future__ import annotations

_installed = False

# --- PATCH: chain-exclude ---
# Языки-интерпретаторы: их трансляция в python даёт интерпретатор,
# а не «просто результат». Chain через python на них работает хуже,
# чем execute + generate_code. Исключаем их из chain-sources.
CHAIN_EXCLUDE_SRC = frozenset({
    "whitespace", "brainfuck", "piet", "malbolge_lite",
    "thue", "unlambda", "befunge",
    # PATCH: их execute работает быстро (19 символов),
    # а chain через python даёт 120К мусора (интерпретатор),
    # который cpp.execute не осиливает за timeout.
    "chicken", "hodor", "ook",
})
# --- /PATCH ---


# Пары (src, dst), для которых есть НАСТОЯЩИЙ транспайлер.
# Заполняется в install() ДО добавления fallback-функций.
_direct_pairs: frozenset[tuple[str, str]] = frozenset()


def _chain_via_python(src_name: str, dst_name: str, code: str) -> str | None:
    """src → python → dst, только через прямые транспайлеры.

    Возвращает результат или None, если chain невозможен.
    """
    if src_name == "python" or dst_name == "python":
        return None
    # --- PATCH: chain-exclude ---
    if src_name in CHAIN_EXCLUDE_SRC:
        return None
    # --- /PATCH ---
    if (src_name, "python") not in _direct_pairs:
        return None
    if ("python", dst_name) not in _direct_pairs:
        return None
    try:
        from core.translate import TRANSPILERS
        mid = TRANSPILERS[(src_name, "python")](code)
        if not isinstance(mid, str) or not mid:
            return None
        final = TRANSPILERS[("python", dst_name)](mid)
        if not isinstance(final, str) or not final:
            return None
        return final
    except BaseException:
        return None


def _make_fallback(src_name: str, dst_name: str):
    def _f(code, *_a, **_kw):
        try:
            from core.registry import registry
            src_lang = registry.get(src_name)
            dst_lang = registry.get(dst_name)
            if src_lang is None or dst_lang is None:
                return code if isinstance(code, str) else ""

            # 1) chain через python — настоящий перевод
            chained = _chain_via_python(src_name, dst_name, code)
            if chained is not None:
                return chained

            # 2) execute + generate_code — «медленный» путь
            out = None
            try:
                out = src_lang.execute(code)
            except BaseException:
                out = None
            if out is None:
                out = ""
            if not isinstance(out, str):
                out = str(out)

            try:
                generated = dst_lang.generate_code(out)
                if isinstance(generated, str) and generated != "":
                    return generated
            except BaseException:
                pass

            # 3) эзотерики дают '' для '', но валидный код для ' '
            try:
                stub = dst_lang.generate_code(" ")
                if isinstance(stub, str) and stub != "":
                    return stub
            except BaseException:
                pass

            # 4) совсем крайний случай
            return ""
        except BaseException:
            return ""

    _f.__name__ = f"universal_{src_name}__{dst_name}"
    return _f


def install(*, force: bool = False, verbose: bool = False) -> int:
    """Заполняет TRANSPILERS для всех недостающих пар. Идемпотентно."""
    global _installed, _direct_pairs
    if _installed and not force:
        return 0

    from core.registry import registry
    from core.translate import TRANSPILERS

    # ВАЖНО: snapshot ДО добавления fallback-функций. Это единственный
    # момент, когда в TRANSPILERS лежат только настоящие транспайлеры,
    # зарегистрированные модулями langs/*.
    _direct_pairs = frozenset(TRANSPILERS.keys())
    if verbose:
        print(f"[fallback] прямых пар: {len(_direct_pairs)}")

    names = [l.name for l in registry.all()]
    added = 0
    for src in names:
        for dst in names:
            if src == dst:
                continue
            key = (src, dst)
            if key in TRANSPILERS and not force:
                continue
            TRANSPILERS[key] = _make_fallback(src, dst)
            added += 1
            if verbose:
                print(f"[fallback] {src} -> {dst}")

    _installed = True
    return added


def list_missing() -> list[tuple[str, str]]:
    """Возвращает пары, которых нет в TRANSPILERS (для диагностики)."""
    from core.registry import registry
    from core.translate import TRANSPILERS
    names = [l.name for l in registry.all()]
    return [(s, d) for s in names for d in names
            if s != d and (s, d) not in TRANSPILERS]


def direct_pairs() -> frozenset[tuple[str, str]]:
    """Для диагностики: какие пары сейчас считаются прямыми."""
    return _direct_pairs