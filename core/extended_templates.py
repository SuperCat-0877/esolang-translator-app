# core/extended_templates.py
"""
Расширенные шаблоны: 25 на каждый язык.
Уровни L1..L5, категории OUT/MATH/STR/LOOP/REC/ALGO/DATA/FUNC/CLASS/META.
Регистрация в lang.templates выполняется поздним update().
"""

# (prefix, level, category, short_name, output_text)
SPECS = [
    # ---------- L1: базовое ----------
    ("E21", "L1", "OUT",   "Greeting",         "Hello from Level 1!"),
    ("E22", "L1", "MATH",  "Sum",              "17 + 5 = 22"),
    ("E23", "L1", "MATH",  "Difference",       "17 - 5 = 12"),
    ("E24", "L1", "MATH",  "Product",          "17 * 5 = 85"),
    ("E25", "L1", "MATH",  "Integer division", "17 // 5 = 3"),

    # ---------- L2: элементарное ----------
    ("M21", "L2", "MATH",  "Modulo",           "17 % 5 = 2"),
    ("M22", "L2", "MATH",  "Power",            "2 ** 10 = 1024"),
    ("M23", "L2", "STR",   "Concatenation",    "Hello, World!"),
    ("M24", "L2", "STR",   "Uppercase",        "HELLO"),
    ("M25", "L2", "STR",   "Lowercase",        "hello"),

    # ---------- L3: средний ----------
    ("H21", "L3", "LOOP",  "Sum 1..10",        "55"),
    ("H22", "L3", "LOOP",  "Squares 1..10",    "1 4 9 16 25 36 49 64 81 100"),
    ("H23", "L3", "REC",   "Factorial 5",      "120"),
    ("H24", "L3", "ALGO",  "Fibonacci 10",     "0 1 1 2 3 5 8 13 21 34"),
    ("H25", "L3", "ALGO",  "GCD 100/25",       "25"),

    # ---------- L4: продвинутый ----------
    ("W21", "L4", "ALGO",  "Primes < 20",      "2 3 5 7 11 13 17 19"),
    ("W22", "L4", "DATA",  "List comprehension","[1, 4, 9, 16]"),
    ("W23", "L4", "DATA",  "Dict lookup",      "a=1 b=2 c=3"),
    ("W24", "L4", "FUNC",  "Apply twice",      "f(f(5)) = 9"),
    ("W25", "L4", "CLASS", "Point class",      "Point(3, 4) |p| = 5.0"),

    # ---------- L5: метапрограммирование ----------
    ("T21", "L5", "META",  "Reflection",       "type name = int"),
    ("T22", "L5", "META",  "Decorator @log",   "f(3) called -> 6"),
    ("T23", "L5", "META",  "eval()",           "eval('3+4*2') = 11"),
    ("T24", "L5", "META",  "Code generation",  "def f(): return 42; f() = 42"),
    ("T25", "L5", "META",  "Metaprogramming",  "Hello, metaprogramming!"),
]


def _key(prefix, level, cat, short):
    return f"[{prefix}] {level}-{cat}: {short}"


# ------------------------------------------------------------------
#  Реальные сниппеты метапрограммирования (там, где язык умеет).
#  Ключ — lang.name. Ключи внутри — точное имя шаблона.
# ------------------------------------------------------------------
META_SNIPPETS: dict[str, dict[str, str]] = {

    # ============== Python ==============
    "python": {
        "[T21] L5-META: Reflection": (
            'x = 42\n'
            'print("type name =", type(x).__name__)\n'
        ),
        "[T22] L5-META: Decorator @log": (
            'def log(f):\n'
            '    def w(*a):\n'
            '        r = f(*a)\n'
            '        print(f"f({a[0]}) called -> {r}")\n'
            '        return r\n'
            '    return w\n'
            '@log\n'
            'def f(x): return x * 2\n'
            'f(3)\n'
        ),
        "[T23] L5-META: eval()": (
            'r = eval("3 + 4 * 2")\n'
            'print(f"eval(\'3+4*2\') = {r}")\n'
        ),
        "[T24] L5-META: Code generation": (
            'src = "def f(): return 42"\n'
            'ns = {}\n'
            'exec(src, ns)\n'
            'print(f"{src}; f() = {ns[\'f\']()}")\n'
        ),
        "[T25] L5-META: Metaprogramming": (
            'def make_greeter(msg):\n'
            '    def g(): print(msg)\n'
            '    return g\n'
            'make_greeter("Hello, metaprogramming!")()\n'
        ),
    },

    # ============== JavaScript ==============
    "javascript": {
        "[T21] L5-META: Reflection": (
            'let x = 42;\n'
            'console.log("type name =", typeof x);\n'
        ),
        "[T22] L5-META: Decorator @log": (
            'function log(f) {\n'
            '  return function(x) {\n'
            '    const r = f(x);\n'
            '    console.log(`f(${x}) called -> ${r}`);\n'
            '    return r;\n'
            '  };\n'
            '}\n'
            'const f = log(x => x * 2);\n'
            'f(3);\n'
        ),
        "[T23] L5-META: eval()": (
            'const r = eval("3 + 4 * 2");\n'
            'console.log(`eval(\'3+4*2\') = ${r}`);\n'
        ),
        "[T24] L5-META: Code generation": (
            'const f = new Function("return 42");\n'
            'console.log(`def f(): return 42; f() = ${f()}`);\n'
        ),
        "[T25] L5-META: Metaprogramming": (
            'function makeGreeter(msg) {\n'
            '  return () => console.log(msg);\n'
            '}\n'
            'makeGreeter("Hello, metaprogramming!")();\n'
        ),
    },

    # ============== Ruby ==============
    "ruby": {
        "[T21] L5-META: Reflection": (
            'x = 42\n'
            'puts "type name = #{x.class}"\n'
        ),
        "[T22] L5-META: Decorator @log": (
            'def log(f)\n'
            '  ->(x) { r = f.(x); puts "f(#{x}) called -> #{r}"; r }\n'
            'end\n'
            'f = log(->(x) { x * 2 })\n'
            'f.(3)\n'
        ),
        "[T23] L5-META: eval()": (
            'r = eval("3 + 4 * 2")\n'
            'puts "eval(\'3+4*2\') = #{r}"\n'
        ),
        "[T24] L5-META: Code generation": (
            'src = "def f; 42; end"\n'
            'eval(src)\n'
            'puts "#{src}; f() = #{f}"\n'
        ),
        "[T25] L5-META: Metaprogramming": (
            'define_method(:greet) { puts "Hello, metaprogramming!" }\n'
            'greet\n'
        ),
    },

    # ============== C++ ==============
    "cpp": {
        "[T21] L5-META: Reflection": (
            '#include <iostream>\n'
            '#include <typeinfo>\n'
            'int main(){\n'
            '    int x = 42;\n'
            '    std::cout << "type name = " << typeid(x).name() << "\\n";\n'
            '    return 0;\n'
            '}\n'
        ),
        "[T22] L5-META: Decorator @log": (
            '#include <iostream>\n'
            'template <typename F> int log_call(F f, int x) {\n'
            '    int r = f(x);\n'
            '    std::cout << "f(" << x << ") called -> " << r << "\\n";\n'
            '    return r;\n'
            '}\n'
            'int main(){\n'
            '    log_call([](int v){ return v * 2; }, 3);\n'
            '    return 0;\n'
            '}\n'
        ),
        "[T23] L5-META: eval()": (
            '#include <iostream>\n'
            'int main(){\n'
            '    int r = 3 + 4 * 2;\n'
            '    std::cout << "eval(3+4*2) = " << r << "\\n";\n'
            '    return 0;\n'
            '}\n'
        ),
        "[T24] L5-META: Code generation": (
            '#include <iostream>\n'
            'int f(){ return 42; }\n'
            'int main(){\n'
            '    std::cout << "def f(): return 42; f() = " << f() << "\\n";\n'
            '    return 0;\n'
            '}\n'
        ),
        "[T25] L5-META: Metaprogramming": (
            '#include <iostream>\n'
            'int main(){\n'
            '    std::cout << "Hello, metaprogramming!" << "\\n";\n'
            '    return 0;\n'
            '}\n'
        ),
    },

    # ============== Go ==============
    "go": {
        "[T21] L5-META: Reflection": (
            'package main\n'
            'import ("fmt"; "reflect")\n'
            'func main() {\n'
            '    var x int = 42\n'
            '    fmt.Println("type name =", reflect.TypeOf(x).Name())\n'
            '}\n'
        ),
        "[T22] L5-META: Decorator @log": (
            'package main\n'
            'import "fmt"\n'
            'func logCall(f func(int) int, x int) int {\n'
            '    r := f(x)\n'
            '    fmt.Printf("f(%d) called -> %d\\n", x, r)\n'
            '    return r\n'
            '}\n'
            'func main() { logCall(func(v int) int { return v * 2 }, 3) }\n'
        ),
        "[T23] L5-META: eval()": (
            'package main\n'
            'import "fmt"\n'
            'func main(){ fmt.Println("eval(3+4*2) =", 3+4*2) }\n'
        ),
        "[T24] L5-META: Code generation": (
            'package main\n'
            'import "fmt"\n'
            'func f() int { return 42 }\n'
            'func main(){ fmt.Println("def f(): return 42; f() =", f()) }\n'
        ),
        "[T25] L5-META: Metaprogramming": (
            'package main\n'
            'import "fmt"\n'
            'func main(){ fmt.Println("Hello, metaprogramming!") }\n'
        ),
    },

    # ============== Java ==============
    "java": {
        "[T21] L5-META: Reflection": (
            'public class Main {\n'
            '    public static void main(String[] a) {\n'
            '        Object x = 42;\n'
            '        System.out.println("type name = " + x.getClass().getSimpleName());\n'
            '    }\n'
            '}\n'
        ),
        "[T22] L5-META: Decorator @log": (
            'import java.util.function.IntUnaryOperator;\n'
            'public class Main {\n'
            '    static int logCall(IntUnaryOperator f, int x){\n'
            '        int r = f.applyAsInt(x);\n'
            '        System.out.println("f(" + x + ") called -> " + r);\n'
            '        return r;\n'
            '    }\n'
            '    public static void main(String[] a){\n'
            '        logCall(v -> v * 2, 3);\n'
            '    }\n'
            '}\n'
        ),
        "[T23] L5-META: eval()": (
            'public class Main {\n'
            '    public static void main(String[] a){\n'
            '        int r = 3 + 4 * 2;\n'
            '        System.out.println("eval(3+4*2) = " + r);\n'
            '    }\n'
            '}\n'
        ),
        "[T24] L5-META: Code generation": (
            'public class Main {\n'
            '    static int f(){ return 42; }\n'
            '    public static void main(String[] a){\n'
            '        System.out.println("def f(): return 42; f() = " + f());\n'
            '    }\n'
            '}\n'
        ),
        "[T25] L5-META: Metaprogramming": (
            'public class Main {\n'
            '    public static void main(String[] a){\n'
            '        System.out.println("Hello, metaprogramming!");\n'
            '    }\n'
            '}\n'
        ),
    },

    # ============== Rust ==============
    "rust": {
        "[T21] L5-META: Reflection": (
            'fn main() {\n'
            '    let x: i32 = 42;\n'
            '    println!("type name = {}", std::any::type_name_of_val(&x));\n'
            '}\n'
        ),
        "[T22] L5-META: Decorator @log": (
            'fn log_call<F: Fn(i32) -> i32>(f: F, x: i32) -> i32 {\n'
            '    let r = f(x);\n'
            '    println!("f({}) called -> {}", x, r);\n'
            '    r\n'
            '}\n'
            'fn main() { log_call(|v| v * 2, 3); }\n'
        ),
        "[T23] L5-META: eval()": (
            'fn main() { println!("eval(3+4*2) = {}", 3 + 4 * 2); }\n'
        ),
        "[T24] L5-META: Code generation": (
            'fn f() -> i32 { 42 }\n'
            'fn main() { println!("def f(): return 42; f() = {}", f()); }\n'
        ),
        "[T25] L5-META: Metaprogramming": (
            'fn main() { println!("Hello, metaprogramming!"); }\n'
        ),
    },

    # ============== Lua ==============
    "lua": {
        "[T21] L5-META: Reflection": (
            'x = 42\n'
            'print("type name =", type(x))\n'
        ),
        "[T22] L5-META: Decorator @log": (
            'function log(f)\n'
            '  return function(x)\n'
            '    local r = f(x)\n'
            '    print("f("..x..") called -> "..r)\n'
            '    return r\n'
            '  end\n'
            'end\n'
            'local f = log(function(x) return x * 2 end)\n'
            'f(3)\n'
        ),
        "[T23] L5-META: eval()": (
            'local r = load("return 3 + 4 * 2")()\n'
            'print("eval(\'3+4*2\') = "..r)\n'
        ),
        "[T24] L5-META: Code generation": (
            'local src = "return 42"\n'
            'local f = load(src)\n'
            'print("def f(): return 42; f() = "..f())\n'
        ),
        "[T25] L5-META: Metaprogramming": (
            'local function make_greeter(msg)\n'
            '  return function() print(msg) end\n'
            'end\n'
            'make_greeter("Hello, metaprogramming!")()\n'
        ),
    },
}


def build_templates(lang, *, only_missing: bool = True) -> dict[str, str]:
    """
    Возвращает dict из 25 расширенных шаблонов для `lang`.
    Если only_missing=True — не перезаписывает уже существующие ключи.
    """
    result: dict[str, str] = {}
    meta = META_SNIPPETS.get(lang.name, {})

    for prefix, level, cat, short, output in SPECS:
        key = _key(prefix, level, cat, short)
        if only_missing and key in lang.templates:
            continue

        # 1) реальный сниппет, если есть
        if key in meta:
            result[key] = meta[key]
            continue

        # 2) fallback — generate_code() из самого языка
        try:
            src = lang.generate_code(output)
        except Exception as e:
            src = f"# generate_code error: {type(e).__name__}: {e}\n"

        if isinstance(src, str) and src.strip():
            result[key] = src

    return result


def attach(lang, *, only_missing: bool = True) -> int:
    """Мутирует lang.templates, добавляя расширенные шаблоны."""
    extra = build_templates(lang, only_missing=only_missing)
    if extra:
        lang.templates.update(extra)
    return len(extra)

# ==================================================================
#  ПОЛНАЯ ЗАМЕНА ШАБЛОНОВ
# ==================================================================
def replace(lang) -> int:
    """
    Полностью заменяет lang.templates на новые (25 шт. L1..L5).
    Старые шаблоны удаляются.

    НИКОГДА не вызываем .strip() по значению шаблона: у Whitespace
    программа состоит из одних пробелов/табов/\\n, и strip() обнулил
    бы все 25 записей.
    """
    fresh: dict[str, str] = {}

    for prefix, level, cat, short, output in SPECS:
        key = _key(prefix, level, cat, short)

        # 1) настоящий сниппет метапрограммирования, если есть
        meta = META_SNIPPETS.get(lang.name, {})
        if key in meta:
            fresh[key] = meta[key]
            continue

        # 2) иначе — generate_code() самого языка
        try:
            src = lang.generate_code(output)
        except Exception as e:
            src = f"# generate_code error: {type(e).__name__}: {e}\n"

        # 3) считаем «пустым» только None и буквально "",
        #    пробелы/табы/переводы строк — валидный код для Whitespace
        if isinstance(src, str) and src != "":
            fresh[key] = src

    # 4) если язык не умеет генерировать вообще ничего —
    #    кладём одну заглушку, чтобы UI не показывал пустой Combobox
    if not fresh:
        stub = _fallback_template(lang)
        if stub != "":
            fresh = {"[E21] L1-OUT: Greeting": stub}

    lang.templates.clear()
    lang.templates.update(fresh)
    return len(lang.templates)


def _fallback_template(lang) -> str:
    """
    Минимальный валидный код языка, если generate_code не справился.
    Для Whitespace возвращаем один пробел — файл валиден, ничего не делает.
    """
    if lang.name == "whitespace":
        return " "
    try:
        src = lang.generate_code("Hi")
        if isinstance(src, str) and src != "":
            return src
    except Exception:
        pass
    return ""


def replace_all(*, verbose: bool = True) -> dict[str, tuple[int, int]]:
    """
    Проходит по всем языкам реестра и заменяет у них шаблоны.
    Возвращает {lang.name: (было, стало)}.
    """
    from core.registry import registry
    report: dict[str, tuple[int, int]] = {}
    for lang in registry.all():
        before = len(lang.templates)
        after = replace(lang)
        report[lang.name] = (before, after)
        if verbose:
            print(f"[templates] {lang.name:<18} {before:>3} -> {after}")
    return report


# ==================================================================
#  ПРОЧИЕ УТИЛИТЫ
# ==================================================================
def stats_by_level(lang) -> dict[str, int]:
    """
    Сколько у языка шаблонов на каждом уровне (L1..L5).
    Работает по имени: '[E21] L1-OUT: Greeting' -> ключ 'L1'.
    """
    import re as _re
    out = {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5": 0, "other": 0}
    for name in lang.templates:
        m = _re.search(r"\bL([1-5])-", name)
        if m:
            out[f"L{m.group(1)}"] += 1
        else:
            out["other"] += 1
    return out


def list_level(lang, level: str) -> list[str]:
    """Возвращает имена шаблонов указанного уровня ('L1'..'L5')."""
    level = level.upper()
    if level not in ("L1", "L2", "L3", "L4", "L5"):
        return []
    return [n for n in lang.templates if f"{level}-" in n]