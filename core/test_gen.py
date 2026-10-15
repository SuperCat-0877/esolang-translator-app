# core/test_gen.py
"""
Генераторы длинных (50+ и 200+ строк) тестовых программ.
Используются только циклы, print / console.log / std::cout
и простая арифметика — всё, что понимают транспайлеры.
"""


# ==================================================================
#  PYTHON
# ==================================================================
def gen_python_50():
    return "\n".join([
        "print('=== Квадраты 1..10 ===')",
        "for i in range(1, 11):",
        "    print(i * i)", "",
        "print('=== Кубы 1..10 ===')",
        "for i in range(1, 11):",
        "    print(i * i * i)", "",
        "print('=== Факториал 1..10 ===')",
        "f = 1",
        "for i in range(1, 11):",
        "    f = f * i",
        "    print(f)", "",
        "print('=== Фибоначчи 0..10 ===')",
        "a = 0",
        "b = 1",
        "for i in range(0, 11):",
        "    print(a)",
        "    c = a + b",
        "    a = b",
        "    b = c", "",
        "print('=== Треугольные 1..10 ===')",
        "t = 0",
        "for i in range(1, 11):",
        "    t = t + i",
        "    print(t)", "",
        "print('=== Умножение на 7 ===')",
        "for i in range(1, 11):",
        "    print(7 * i)", "",
        "print('=== Суммы 1..10 ===')",
        "s = 0",
        "for k in range(1, 11):",
        "    s = s + k",
        "    print(s)", "",
        "print('Готово.')",
    ])


def gen_python_200():
    p = []
    for b, n in [(2, 15), (3, 10), (5, 8)]:
        p += [
            f"print('=== Степени {b} ===')",
            "p = 1",
            f"for i in range(0, {n + 1}):",
            "    print(p)",
            f"    p = p * {b}",
            "",
        ]
    for n in (5, 10, 15, 20):
        p += [
            f"print('=== Квадраты 1..{n} ===')",
            f"for i in range(1, {n + 1}):",
            "    print(i * i)",
            "",
        ]
    for n in (5, 10, 15):
        p += [
            f"print('=== Кубы 1..{n} ===')",
            f"for i in range(1, {n + 1}):",
            "    print(i * i * i)",
            "",
        ]
    for n in (5, 10, 15):
        p += [
            f"print('=== Факториалы 1..{n} ===')",
            "f = 1",
            f"for i in range(1, {n + 1}):",
            "    f = f * i",
            "    print(f)",
            "",
        ]
    for n in (10, 15, 20, 25):
        p += [
            f"print('=== Фибоначчи 0..{n} ===')",
            "a = 0",
            "b = 1",
            f"for i in range(0, {n + 1}):",
            "    print(a)",
            "    c = a + b",
            "    a = b",
            "    b = c",
            "",
        ]
    for n in (10, 20, 30, 40):
        p += [
            f"print('=== Треугольные 1..{n} ===')",
            "t = 0",
            f"for i in range(1, {n + 1}):",
            "    t = t + i",
            "    print(t)",
            "",
        ]
    for m in (2, 3, 4, 5, 6, 7, 8, 9, 10):
        p += [
            f"print('=== Умножение на {m} ===')",
            "for i in range(1, 11):",
            f"    print({m} * i)",
            "",
        ]
    for n in (5, 10, 15, 20):
        p += [
            f"print('=== Суммы 1..{n} ===')",
            "s = 0",
            f"for k in range(1, {n + 1}):",
            "    s = s + k",
            "    print(s)",
            "",
        ]
    p.append("print('Готово.')")
    return "\n".join(p)


# ==================================================================
#  JAVASCRIPT / TYPESCRIPT
# ==================================================================
def gen_js_50():
    return "\n".join([
        "console.log('=== Квадраты 1..10 ===');",
        "for (let i = 1; i < 11; i++) {",
        "    console.log(i * i);",
        "}", "",
        "console.log('=== Кубы 1..10 ===');",
        "for (let i = 1; i < 11; i++) {",
        "    console.log(i * i * i);",
        "}", "",
        "console.log('=== Факториал 1..10 ===');",
        "let f = 1;",
        "for (let i = 1; i < 11; i++) {",
        "    f = f * i;",
        "    console.log(f);",
        "}", "",
        "console.log('=== Фибоначчи 0..10 ===');",
        "let a = 0;",
        "let b = 1;",
        "for (let i = 0; i < 11; i++) {",
        "    console.log(a);",
        "    let c = a + b;",
        "    a = b;",
        "    b = c;",
        "}", "",
        "console.log('=== Треугольные 1..10 ===');",
        "let t = 0;",
        "for (let i = 1; i < 11; i++) {",
        "    t = t + i;",
        "    console.log(t);",
        "}", "",
        "console.log('=== Умножение на 7 ===');",
        "for (let i = 1; i < 11; i++) {",
        "    console.log(7 * i);",
        "}", "",
        "console.log('=== Суммы 1..10 ===');",
        "let s = 0;",
        "for (let k = 1; k < 11; k++) {",
        "    s = s + k;",
        "    console.log(s);",
        "}", "",
        "console.log('Готово.');",
    ])


def gen_js_200():
    p = []
    for b, n in [(2, 15), (3, 10), (5, 8)]:
        p += [
            f"console.log('=== Степени {b} ===');",
            "let p = 1;",
            f"for (let i = 0; i < {n + 1}; i++) {{",
            "    console.log(p);",
            f"    p = p * {b};",
            "}",
            "",
        ]
    for n in (5, 10, 15, 20):
        p += [
            f"console.log('=== Квадраты 1..{n} ===');",
            f"for (let i = 1; i < {n + 1}; i++) {{",
            "    console.log(i * i);",
            "}",
            "",
        ]
    for n in (5, 10, 15):
        p += [
            f"console.log('=== Кубы 1..{n} ===');",
            f"for (let i = 1; i < {n + 1}; i++) {{",
            "    console.log(i * i * i);",
            "}",
            "",
        ]
    for n in (5, 10, 15):
        p += [
            f"console.log('=== Факториалы 1..{n} ===');",
            "let f = 1;",
            f"for (let i = 1; i < {n + 1}; i++) {{",
            "    f = f * i;",
            "    console.log(f);",
            "}",
            "",
        ]
    for n in (10, 15, 20, 25):
        p += [
            f"console.log('=== Фибоначчи 0..{n} ===');",
            "let a = 0;",
            "let b = 1;",
            f"for (let i = 0; i < {n + 1}; i++) {{",
            "    console.log(a);",
            "    let c = a + b;",
            "    a = b;",
            "    b = c;",
            "}",
            "",
        ]
    for n in (10, 20, 30, 40):
        p += [
            f"console.log('=== Треугольные 1..{n} ===');",
            "let t = 0;",
            f"for (let i = 1; i < {n + 1}; i++) {{",
            "    t = t + i;",
            "    console.log(t);",
            "}",
            "",
        ]
    for m in (2, 3, 4, 5, 6, 7, 8, 9, 10):
        p += [
            f"console.log('=== Умножение на {m} ===');",
            "for (let i = 1; i < 11; i++) {",
            f"    console.log({m} * i);",
            "}",
            "",
        ]
    for n in (5, 10, 15, 20):
        p += [
            f"console.log('=== Суммы 1..{n} ===');",
            "let s = 0;",
            f"for (let k = 1; k < {n + 1}; k++) {{",
            "    s = s + k;",
            "    console.log(s);",
            "}",
            "",
        ]
    p.append("console.log('Готово.');")
    return "\n".join(p)


# ==================================================================
#  C++
# ==================================================================
def gen_cpp_50():
    return "\n".join([
        '#include <iostream>',
        'int main() {',
        '    int f = 1;',
        '    for (int i = 1; i < 11; i++) {',
        '        f = f * i;',
        '        std::cout << f << "\\n";',
        '    }',
        '    std::cout << "----\\n";',
        '    int total = 0;',
        '    for (int i = 1; i < 101; i++) total = total + i;',
        '    std::cout << total << "\\n";',
        '    int sqsum = 0;',
        '    for (int i = 1; i < 51; i++) sqsum = sqsum + i * i;',
        '    std::cout << sqsum << "\\n";',
        '    std::cout << "Готово.\\n";',
        '    return 0;',
        '}',
    ])


def gen_cpp_200():
    p = ["#include <iostream>", "int main() {"]
    I = "    "
    for b, n in [(2, 15), (3, 10), (5, 8)]:
        p += [
            f'{I}std::cout << "=== Степени {b} ===\\n";',
            f"{I}int p = 1;",
            f"{I}for (int i = 0; i < {n + 1}; i++) {{",
            f'{I}    std::cout << p << "\\n";',
            f"{I}    p = p * {b};",
            f"{I}}}",
        ]
    for n in (5, 10, 15, 20):
        p += [
            f'{I}std::cout << "=== Квадраты 1..{n} ===\\n";',
            f"{I}for (int i = 1; i < {n + 1}; i++) {{",
            f'{I}    std::cout << i * i << "\\n";',
            f"{I}}}",
        ]
    for n in (5, 10, 15):
        p += [
            f'{I}std::cout << "=== Кубы 1..{n} ===\\n";',
            f"{I}for (int i = 1; i < {n + 1}; i++) {{",
            f'{I}    std::cout << i * i * i << "\\n";',
            f"{I}}}",
        ]
    for n in (5, 10, 15):
        p += [
            f'{I}std::cout << "=== Факториалы 1..{n} ===\\n";',
            f"{I}int f = 1;",
            f"{I}for (int i = 1; i < {n + 1}; i++) {{",
            f"{I}    f = f * i;",
            f'{I}    std::cout << f << "\\n";',
            f"{I}}}",
        ]
    for n in (10, 15, 20, 25):
        p += [
            f'{I}std::cout << "=== Фибоначчи 0..{n} ===\\n";',
            f"{I}int a = 0;",
            f"{I}int b = 1;",
            f"{I}for (int i = 0; i < {n + 1}; i++) {{",
            f'{I}    std::cout << a << "\\n";',
            f"{I}    int c = a + b;",
            f"{I}    a = b;",
            f"{I}    b = c;",
            f"{I}}}",
        ]
    for n in (10, 20, 30, 40):
        p += [
            f'{I}std::cout << "=== Треугольные 1..{n} ===\\n";',
            f"{I}int t = 0;",
            f"{I}for (int i = 1; i < {n + 1}; i++) {{",
            f"{I}    t = t + i;",
            f'{I}    std::cout << t << "\\n";',
            f"{I}}}",
        ]
    for m in (2, 3, 4, 5, 6, 7, 8, 9, 10):
        p += [
            f'{I}std::cout << "=== Умножение на {m} ===\\n";',
            f"{I}for (int i = 1; i < 11; i++) {{",
            f'{I}    std::cout << {m} * i << "\\n";',
            f"{I}}}",
        ]
    for n in (5, 10, 15, 20):
        p += [
            f'{I}std::cout << "=== Суммы 1..{n} ===\\n";',
            f"{I}int s = 0;",
            f"{I}for (int k = 1; k < {n + 1}; k++) {{",
            f"{I}    s = s + k;",
            f'{I}    std::cout << s << "\\n";',
            f"{I}}}",
        ]
    p.append(f'{I}std::cout << "Готово.\\n";')
    p.append(f"{I}return 0;")
    p.append("}")
    return "\n".join(p)


# ==================================================================
#  LUA
# ==================================================================
def gen_lua_50():
    return "\n".join([
        "print('=== Квадраты 1..10 ===')",
        "for i = 1, 10 do",
        "    print(i * i)",
        "end", "",
        "print('=== Кубы 1..10 ===')",
        "for i = 1, 10 do",
        "    print(i * i * i)",
        "end", "",
        "print('=== Факториал 1..10 ===')",
        "local f = 1",
        "for i = 1, 10 do",
        "    f = f * i",
        "    print(f)",
        "end", "",
        "print('=== Фибоначчи 0..10 ===')",
        "local a = 0",
        "local b = 1",
        "for i = 0, 10 do",
        "    print(a)",
        "    local c = a + b",
        "    a = b",
        "    b = c",
        "end", "",
        "print('=== Треугольные 1..10 ===')",
        "local t = 0",
        "for i = 1, 10 do",
        "    t = t + i",
        "    print(t)",
        "end", "",
        "print('=== Умножение на 7 ===')",
        "for i = 1, 10 do",
        "    print(7 * i)",
        "end", "",
        "print('Готово.')",
    ])


def gen_lua_200():
    p = []
    for b, n in [(2, 15), (3, 10), (5, 8)]:
        p += [
            f"print('=== Степени {b} ===')",
            "local p = 1",
            f"for i = 0, {n} do",
            "    print(p)",
            f"    p = p * {b}",
            "end",
            "",
        ]
    for n in (5, 10, 15, 20):
        p += [
            f"print('=== Квадраты 1..{n} ===')",
            f"for i = 1, {n} do",
            "    print(i * i)",
            "end",
            "",
        ]
    for n in (5, 10, 15):
        p += [
            f"print('=== Кубы 1..{n} ===')",
            f"for i = 1, {n} do",
            "    print(i * i * i)",
            "end",
            "",
        ]
    for n in (5, 10, 15):
        p += [
            f"print('=== Факториалы 1..{n} ===')",
            "local f = 1",
            f"for i = 1, {n} do",
            "    f = f * i",
            "    print(f)",
            "end",
            "",
        ]
    for n in (10, 15, 20, 25):
        p += [
            f"print('=== Фибоначчи 0..{n} ===')",
            "local a = 0",
            "local b = 1",
            f"for i = 0, {n} do",
            "    print(a)",
            "    local c = a + b",
            "    a = b",
            "    b = c",
            "end",
            "",
        ]
    for n in (10, 20, 30, 40):
        p += [
            f"print('=== Треугольные 1..{n} ===')",
            "local t = 0",
            f"for i = 1, {n} do",
            "    t = t + i",
            "    print(t)",
            "end",
            "",
        ]
    for m in (2, 3, 4, 5, 6, 7, 8, 9, 10):
        p += [
            f"print('=== Умножение на {m} ===')",
            "for i = 1, 10 do",
            f"    print({m} * i)",
            "end",
            "",
        ]
    for n in (5, 10, 15, 20):
        p += [
            f"print('=== Суммы 1..{n} ===')",
            "local s = 0",
            f"for k = 1, {n} do",
            "    s = s + k",
            "    print(s)",
            "end",
            "",
        ]
    p.append("print('Готово.')")
    return "\n".join(p)