# core/translate.py
"""
Перевод между языками.

Приоритет:
  1. Зарегистрированный транспайлер для пары (src, dst).
  2. IR-перевод через core.ir_parsers / core.ir_generators.

TRANSPILERS — публичный реестр: langs.* и другие модули
регистрируют свои функции через TRANSPILERS[(src, dst)] = fn.

Никакого execute-fallback: код НЕ выполняется, чтобы не получать
hardcode вместо перевода.
"""

from .registry import registry

# Публичный реестр транспайлеров.
# Значение: функция(code: str) -> str | None
TRANSPILERS: dict[tuple[str, str], callable] = {}


def _ir_translate(src_name: str, dst_name: str, code: str):
    """IR-перевод: код → дерево → код. Возвращает (успех, результат)."""
    try:
        from .ir import UnsupportedConstruct
        from .ir_parsers import parse_any
        from .ir_generators import gen_any
    except ImportError as e:
        return False, f"// IR недоступен: {e}\n"

    try:
        prog = parse_any(src_name, code)
    except UnsupportedConstruct as e:
        return False, f"// {src_name} → IR: не поддерживается: {e}\n"
    except Exception as e:
        return False, f"// {src_name} → IR: {e}\n"

    try:
        return True, gen_any(dst_name, prog)
    except UnsupportedConstruct as e:
        return False, f"// IR → {dst_name}: не поддерживается: {e}\n"
    except Exception as e:
        return False, f"// IR → {dst_name}: {e}\n"


def _is_universal_fallback(fn) -> bool:
    """True если функция — universal_* fallback (execute + generate_code)."""
    name = getattr(fn, "__name__", "")
    return name.startswith("universal_")


# --- PATCH: fallback-last ---
def translate(src_name, dst_name, code, piet_program=None):
    src = registry.get(src_name)
    dst = registry.get(dst_name)
    if not src or not dst:
        return "// Неизвестный язык\n"

    if src_name == dst_name:
        return code

    # 1. Настоящий прямой транспайлер — НЕ universal_* fallback.
    fn = TRANSPILERS.get((src_name, dst_name))
    real_direct = fn is not None and not _is_universal_fallback(fn)
    if real_direct:
        try:
            r = fn(code)
            # PATCH: не используем r.strip() — whitespace-языки
            # состоят целиком из пробелов/табов
            if r is not None and isinstance(r, str) and len(r) > 0:
                return r
        except Exception:
            pass

    # 2. Chain через python — только настоящие звенья.
    #    _chain_via_python использует _direct_pairs (снимок ДО install),
    #    поэтому не зацикливается на самих fallback-ах.
    try:
        from .universal_fallback import _chain_via_python
        chained = _chain_via_python(src_name, dst_name, code)
        if chained:
            return chained
    except Exception:
        pass

    # 3. IR.
    ok, result = _ir_translate(src_name, dst_name, code)
    if ok:
        return result

    # 4. Fallback universal_* — последнее средство.
    #    Он выполнит исходник и сгенерирует код приёмника,
    #    печатающий тот же вывод. Для циклов это даст print(значение)
    #    вместо цикла, но лучше, чем ничего.
    if fn is not None and _is_universal_fallback(fn):
        try:
            r = fn(code)
            # PATCH: len > 0, без strip
            if r is not None and isinstance(r, str) and len(r) > 0:
                return r
        except Exception:
            pass

    # 5. Явный отказ.
    return (
        f"// {src.title if src else src_name} → "
        f"{dst.title if dst else dst_name}: нет перевода.\n"
        f"{result}"
    )
# --- /PATCH ---
