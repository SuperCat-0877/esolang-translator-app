# tools/measure.py
"""Замер полноты всех языков проекта: шаблоны, round-trip, цели."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import langs  # регистрация всех транспайлеров
from core.translate import TRANSPILERS

from langs.python_lang import PythonLang
from langs.javascript_lang import JavaScriptLang
from langs.Typescript_lang import TypeScriptLang
from langs.php_lang import PhpLang
from langs.cpp_lang import CppLang
from langs.csharp_lang import CSharpLang
from langs.java_lang import JavaLang
from langs.go_lang import GoLang
from langs.rust_lang import RustLang
from langs.Lua_lang import LuaLang

from langs.brainfuck import BrainfuckLang
from langs.ook import OokLang
from langs.cow import CowLang
from langs.pika import PikaLang
from langs.whitespace import WhitespaceLang
from langs.malbolge_lite import MalbolgeLiteLang
from langs.deadfish import DeadfishLang
from langs.bitwise import BitwiseLang
from langs.lolcode import LolcodeLang
from langs.rivulet import RivuletLang
# В блок импортов:
from langs.hodor import HodorLang
from langs.chicken import ChickenLang
from langs.arnoldc import ArnoldCLang
from langs.rockstar import RockstarLang
from langs.befunge import BefungeLang
# В блок импортов добавь:
from langs.kotlin import KotlinLang
from langs.ruby import RubyLang
from langs.julia import JuliaLang
from langs.dart import DartLang
from langs.swift import SwiftLang
from langs.perl import PerlLang
from langs.scala import ScalaLang
from langs.r_lang import RlangLang
from langs.elixir import ElixirLang
from langs.fsharp import FsharpLang

REGULAR = [
    PythonLang, JavaScriptLang, TypeScriptLang, PhpLang,
    CppLang, CSharpLang, JavaLang, GoLang, RustLang, LuaLang,
    KotlinLang, SwiftLang, RubyLang, DartLang, JuliaLang,
    PerlLang, ScalaLang, RlangLang, ElixirLang, FsharpLang,
]

# В ESOTERIC добавь (если ещё не добавлены):
from langs.hodor import HodorLang
from langs.chicken import ChickenLang
from langs.arnoldc import ArnoldCLang
from langs.rockstar import RockstarLang
from langs.befunge import BefungeLang
# В блок импортов добавь:
from langs.thue import ThueLang
from langs.unlambda import UnlambdaLang
from langs.intercal import IntercalLang
from langs.shakespeare import ShakespeareLang
from langs.piet import PietLang

# В ESOTERIC:
ESOTERIC = [
    BrainfuckLang, OokLang, CowLang, PikaLang,
    WhitespaceLang, MalbolgeLiteLang, DeadfishLang,
    BitwiseLang, LolcodeLang, RivuletLang,
    HodorLang, ChickenLang, ArnoldCLang, RockstarLang, BefungeLang,
    ThueLang, UnlambdaLang, IntercalLang, ShakespeareLang, PietLang,
]

ALL = REGULAR + ESOTERIC


def _is_error(out):
    return isinstance(out, str) and out.startswith("// ")


def score(cls):
    """Возвращает (t_ok, t_total, rt_ok, rt_total, targets, error)."""
    try:
        inst = cls()
    except Exception as e:
        return 0, 0, 0, 0, [], f"init: {e}"

    tmpl = getattr(inst, "templates", {})
    if not tmpl:
        return 0, 0, 0, 0, [], "нет шаблонов"

    t_ok = t_total = 0
    outputs = {}

    for name, src in tmpl.items():
        t_total += 1
        try:
            out = inst.execute(src)
        except Exception as e:
            out = f"// {inst.title}: {type(e).__name__}: {e}"

        if _is_error(out):
            outputs[name] = None
            continue
        t_ok += 1
        outputs[name] = out

    # Проверяем, поддерживает ли язык генерацию кода
    has_gen = True
    try:
        test = inst.generate_code("test")
        if isinstance(test, str) and "не поддерживается" in test:
            has_gen = False
    except Exception:
        has_gen = False

    if has_gen:
        rt_ok = rt_total = 0
        for name, out in outputs.items():
            if out is None or out == "":
                continue
            rt_total += 1
            try:
                gen = inst.generate_code(out)
            except Exception:
                continue
            try:
                out2 = inst.execute(gen)
            except Exception:
                continue
            if out2 == out:
                rt_ok += 1
    else:
        rt_ok = rt_total = 0

    targets = sorted({t for (s, t) in TRANSPILERS if s == inst.name})
    return t_ok, t_total, rt_ok, rt_total, targets, None


def print_table(title, classes):
    print(f"\n=== {title} ===\n")
    header = (f"{'Язык':14} {'Шаблоны':>16} {'Round-trip':>16}  Цели")
    print(header)
    print("-" * 100)

    total_t = total_ok = 0
    total_rt = total_rt_ok = 0

    for cls in classes:
        t_ok, t_total, rt_ok, rt_total, targets, err = score(cls)
        if err:
            print(f"{cls.title:14} {'—':>16} {'—':>16}  ошибка: {err}")
            continue

        p_t = 100 * t_ok / max(1, t_total)
        p_rt = 100 * rt_ok / max(1, rt_total) if rt_total else 0

        t_str = f"{t_ok}/{t_total} ({p_t:>3.0f}%)"
        rt_str = f"{rt_ok}/{rt_total} ({p_rt:>3.0f}%)" if rt_total else "—"
        tg_str = ", ".join(targets) if targets else "—"

        print(f"{cls.title:14} {t_str:>16} {rt_str:>16}  {tg_str}")

        total_t += t_total
        total_ok += t_ok
        total_rt += rt_total
        total_rt_ok += rt_ok

    return total_ok, total_t, total_rt_ok, total_rt


def main():
    r = print_table("Обычные языки", REGULAR)
    e = print_table("Эзотерические языки", ESOTERIC)

    total_ok = r[0] + e[0]
    total_t = r[1] + e[1]
    total_rt_ok = r[2] + e[2]
    total_rt = r[3] + e[3]

    print()
    print("=" * 80)
    p_t = 100 * total_ok / max(1, total_t)
    p_rt = 100 * total_rt_ok / max(1, total_rt) if total_rt else 0
    print(f"ИТОГО шаблоны:    {total_ok}/{total_t} ({p_t:.1f}%)")
    print(f"ИТОГО round-trip: {total_rt_ok}/{total_rt} ({p_rt:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()