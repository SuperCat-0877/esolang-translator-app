# core/standard_templates.py
"""
13 реальных шаблонов для каждого обычного языка.
Все используют простые конструкции (for, print, арифметика),
которые понимают все транспайлеры.
"""

from core.test_gen import (
    gen_python_50, gen_python_200,
    gen_js_50, gen_js_200,
    gen_cpp_50, gen_cpp_200,
    gen_lua_50, gen_lua_200,
)


# ==================================================================
#  PYTHON
# ==================================================================
def std_python():
    return {
        "[1] Hello, World":     "print('Hello, World!')",
        "[2] Буква A":          "print('A')",
        "[3] Цифры 0-9":        "print('0123456789')",
        "[4] Алфавит A-J":      "print('ABCDEFGHIJ')",
        "[5] Числа 1-10":       "for i in range(1, 11):\n    print(i)",
        "[6] Квадраты 1-10":    "for i in range(1, 11):\n    print(i * i)",
        "[7] Кубы 1-10":        "for i in range(1, 11):\n    print(i * i * i)",
        "[8] Таблица ×7":       "for i in range(1, 11):\n    print(i * 7)",
        "[9] Факториал 5":      "r = 1\nfor i in range(1, 6):\n    r = r * i\nprint(r)",
        "[10] Фибоначчи 10":    "a = 0\nb = 1\nfor i in range(10):\n    print(a)\n    c = a + b\n    a = b\n    b = c",
        "[11] Сумма 1-100":     "s = 0\nfor i in range(1, 101):\n    s = s + i\nprint(s)",
        "[Test] 50+ строк — таблицы":          gen_python_50(),
        "[Test] 200+ строк — большие таблицы": gen_python_200(),
    }


# ==================================================================
#  JAVASCRIPT / TYPESCRIPT
# ==================================================================
def std_js():
    return {
        "[1] Hello, World":     "console.log('Hello, World!');",
        "[2] Буква A":          "console.log('A');",
        "[3] Цифры 0-9":        "console.log('0123456789');",
        "[4] Алфавит A-J":      "console.log('ABCDEFGHIJ');",
        "[5] Числа 1-10":       "for (let i = 1; i < 11; i++) console.log(i);",
        "[6] Квадраты 1-10":    "for (let i = 1; i < 11; i++) console.log(i * i);",
        "[7] Кубы 1-10":        "for (let i = 1; i < 11; i++) console.log(i * i * i);",
        "[8] Таблица ×7":       "for (let i = 1; i < 11; i++) console.log(i * 7);",
        "[9] Факториал 5":
            "let r = 1;\n"
            "for (let i = 1; i < 6; i++) r = r * i;\n"
            "console.log(r);",
        "[10] Фибоначчи 10":
            "let a = 0, b = 1;\n"
            "for (let i = 0; i < 10; i++) {\n"
            "    console.log(a);\n"
            "    let c = a + b; a = b; b = c;\n"
            "}",
        "[11] Сумма 1-100":
            "let s = 0;\n"
            "for (let i = 1; i < 101; i++) s = s + i;\n"
            "console.log(s);",
        "[Test] 50+ строк — таблицы":          gen_js_50(),
        "[Test] 200+ строк — большие таблицы": gen_js_200(),
    }


# ==================================================================
#  C++
# ==================================================================
def std_cpp():
    INC = '#include <iostream>\n'
    def wrap(body):
        return INC + "int main() {\n" + body + "\n    return 0;\n}"

    return {
        "[1] Hello, World":
            wrap('    std::cout << "Hello, World!\\n";'),
        "[2] Буква A":
            wrap('    std::cout << "A\\n";'),
        "[3] Цифры 0-9":
            wrap('    std::cout << "0123456789\\n";'),
        "[4] Алфавит A-J":
            wrap('    std::cout << "ABCDEFGHIJ\\n";'),
        "[5] Числа 1-10":
            wrap('    for (int i = 1; i < 11; i++) std::cout << i << "\\n";'),
        "[6] Квадраты 1-10":
            wrap('    for (int i = 1; i < 11; i++) std::cout << i * i << "\\n";'),
        "[7] Кубы 1-10":
            wrap('    for (int i = 1; i < 11; i++) std::cout << i * i * i << "\\n";'),
        "[8] Таблица ×7":
            wrap('    for (int i = 1; i < 11; i++) std::cout << i * 7 << "\\n";'),
        "[9] Факториал 5":
            wrap('    int r = 1;\n'
                 '    for (int i = 1; i < 6; i++) r = r * i;\n'
                 '    std::cout << r << "\\n";'),
        "[10] Фибоначчи 10":
            wrap('    int a = 0, b = 1;\n'
                 '    for (int i = 0; i < 10; i++) {\n'
                 '        std::cout << a << "\\n";\n'
                 '        int c = a + b; a = b; b = c;\n'
                 '    }'),
        "[11] Сумма 1-100":
            wrap('    int s = 0;\n'
                 '    for (int i = 1; i < 101; i++) s = s + i;\n'
                 '    std::cout << s << "\\n";'),
        "[Test] 50+ строк — таблицы":          gen_cpp_50(),
        "[Test] 200+ строк — большие таблицы": gen_cpp_200(),
    }


# ==================================================================
#  LUA
# ==================================================================
def std_lua():
    return {
        "[1] Hello, World":     'print("Hello, World!")',
        "[2] Буква A":          'print("A")',
        "[3] Цифры 0-9":        'print("0123456789")',
        "[4] Алфавит A-J":      'print("ABCDEFGHIJ")',
        "[5] Числа 1-10":       'for i = 1, 10 do\n    print(i)\nend',
        "[6] Квадраты 1-10":    'for i = 1, 10 do\n    print(i * i)\nend',
        "[7] Кубы 1-10":        'for i = 1, 10 do\n    print(i * i * i)\nend',
        "[8] Таблица ×7":       'for i = 1, 10 do\n    print(i * 7)\nend',
        "[9] Факториал 5":
            'local r = 1\n'
            'for i = 1, 5 do\n    r = r * i\nend\n'
            'print(r)',
        "[10] Фибоначчи 10":
            'local a, b = 0, 1\n'
            'for i = 1, 10 do\n'
            '    print(a)\n'
            '    a, b = b, a + b\n'
            'end',
        "[11] Сумма 1-100":
            'local s = 0\n'
            'for i = 1, 100 do\n    s = s + i\nend\n'
            'print(s)',
        "[Test] 50+ строк — таблицы":          gen_lua_50(),
        "[Test] 200+ строк — большие таблицы": gen_lua_200(),
    }


# ==================================================================
#  RUBY
# ==================================================================
def std_ruby():
    return {
        "[1] Hello, World":     'puts "Hello, World!"',
        "[2] Буква A":          'puts "A"',
        "[3] Цифры 0-9":        'puts "0123456789"',
        "[4] Алфавит A-J":      'puts "ABCDEFGHIJ"',
        "[5] Числа 1-10":       'for i in 1..10\n    puts i\nend',
        "[6] Квадраты 1-10":    'for i in 1..10\n    puts i * i\nend',
        "[7] Кубы 1-10":        'for i in 1..10\n    puts i * i * i\nend',
        "[8] Таблица ×7":       'for i in 1..10\n    puts i * 7\nend',
        "[9] Факториал 5":
            'r = 1\nfor i in 1..5\n    r = r * i\nend\nputs r',
        "[10] Фибоначчи 10":
            'a = 0\nb = 1\nfor i in 0...10\n'
            '    puts a\n    c = a + b\n    a = b\n    b = c\nend',
        "[11] Сумма 1-100":
            's = 0\nfor i in 1..100\n    s = s + i\nend\nputs s',
        "[Test] 50+ строк — таблицы":          gen_python_50(),
        "[Test] 200+ строк — большие таблицы": gen_python_200(),
    }


# ==================================================================
#  PHP
# ==================================================================
def std_php():
    def php(body):
        return "<?php " + body + " ?>"

    return {
        "[1] Hello, World":     php('echo "Hello, World!";'),
        "[2] Буква A":          php('echo "A";'),
        "[3] Цифры 0-9":        php('echo "0123456789";'),
        "[4] Алфавит A-J":      php('echo "ABCDEFGHIJ";'),
        "[5] Числа 1-10":       php('for ($i = 1; $i < 11; $i++) echo $i . "\\n";'),
        "[6] Квадраты 1-10":    php('for ($i = 1; $i < 11; $i++) echo $i * $i . "\\n";'),
        "[7] Кубы 1-10":        php('for ($i = 1; $i < 11; $i++) echo $i * $i * $i . "\\n";'),
        "[8] Таблица ×7":       php('for ($i = 1; $i < 11; $i++) echo $i * 7 . "\\n";'),
        "[9] Факториал 5":      php('$r = 1; for ($i = 1; $i < 6; $i++) $r = $r * $i; echo $r;'),
        "[10] Фибоначчи 10":
            php('$a = 0; $b = 1; for ($i = 0; $i < 10; $i++) { echo $a . "\\n"; '
                '$c = $a + $b; $a = $b; $b = $c; }'),
        "[11] Сумма 1-100":
            php('$s = 0; for ($i = 1; $i < 101; $i++) $s = $s + $i; echo $s;'),
        "[Test] 50+ строк — таблицы":          gen_python_50(),
        "[Test] 200+ строк — большие таблицы": gen_python_200(),
    }


# ==================================================================
#  GO
# ==================================================================
def std_go():
    def go(body):
        return 'package main\n\nimport "fmt"\n\nfunc main() {\n' + body + '\n}'

    return {
        "[1] Hello, World":     go('    fmt.Println("Hello, World!")'),
        "[2] Буква A":          go('    fmt.Println("A")'),
        "[3] Цифры 0-9":        go('    fmt.Println("0123456789")'),
        "[4] Алфавит A-J":      go('    fmt.Println("ABCDEFGHIJ")'),
        "[5] Числа 1-10":       go('    for i := 1; i < 11; i++ {\n        fmt.Println(i)\n    }'),
        "[6] Квадраты 1-10":    go('    for i := 1; i < 11; i++ {\n        fmt.Println(i * i)\n    }'),
        "[7] Кубы 1-10":        go('    for i := 1; i < 11; i++ {\n        fmt.Println(i * i * i)\n    }'),
        "[8] Таблица ×7":       go('    for i := 1; i < 11; i++ {\n        fmt.Println(i * 7)\n    }'),
        "[9] Факториал 5":      go('    r := 1\n    for i := 1; i < 6; i++ {\n        r = r * i\n    }\n    fmt.Println(r)'),
        "[10] Фибоначчи 10":    go('    a := 0\n    b := 1\n    for i := 0; i < 10; i++ {\n        fmt.Println(a)\n        c := a + b\n        a = b\n        b = c\n    }'),
        "[11] Сумма 1-100":     go('    s := 0\n    for i := 1; i < 101; i++ {\n        s = s + i\n    }\n    fmt.Println(s)'),
        "[Test] 50+ строк — таблицы":          gen_python_50(),
        "[Test] 200+ строк — большие таблицы": gen_python_200(),
    }


# ==================================================================
#  JAVA
# ==================================================================
def std_java():
    def java(body):
        return ('public class Main {\n'
                '    public static void main(String[] args) {\n'
                + body +
                '\n    }\n}')

    return {
        "[1] Hello, World":     java('        System.out.println("Hello, World!");'),
        "[2] Буква A":          java('        System.out.println("A");'),
        "[3] Цифры 0-9":        java('        System.out.println("0123456789");'),
        "[4] Алфавит A-J":      java('        System.out.println("ABCDEFGHIJ");'),
        "[5] Числа 1-10":       java('        for (int i = 1; i < 11; i++) {\n            System.out.println(i);\n        }'),
        "[6] Квадраты 1-10":    java('        for (int i = 1; i < 11; i++) {\n            System.out.println(i * i);\n        }'),
        "[7] Кубы 1-10":        java('        for (int i = 1; i < 11; i++) {\n            System.out.println(i * i * i);\n        }'),
        "[8] Таблица ×7":       java('        for (int i = 1; i < 11; i++) {\n            System.out.println(i * 7);\n        }'),
        "[9] Факториал 5":      java('        int r = 1;\n        for (int i = 1; i < 6; i++) {\n            r = r * i;\n        }\n        System.out.println(r);'),
        "[10] Фибоначчи 10":    java('        int a = 0, b = 1;\n        for (int i = 0; i < 10; i++) {\n            System.out.println(a);\n            int c = a + b;\n            a = b;\n            b = c;\n        }'),
        "[11] Сумма 1-100":     java('        int s = 0;\n        for (int i = 1; i < 101; i++) {\n            s = s + i;\n        }\n        System.out.println(s);'),
        "[Test] 50+ строк — таблицы":          gen_python_50(),
        "[Test] 200+ строк — большие таблицы": gen_python_200(),
    }


# ==================================================================
#  RUST
# ==================================================================
def std_rust():
    def rs(body):
        return 'fn main() {\n' + body + '\n}'

    return {
        "[1] Hello, World":     rs('    println!("Hello, World!");'),
        "[2] Буква A":          rs('    println!("A");'),
        "[3] Цифры 0-9":        rs('    println!("0123456789");'),
        "[4] Алфавит A-J":      rs('    println!("ABCDEFGHIJ");'),
        "[5] Числа 1-10":       rs('    for i in 1..11 {\n        println!("{}", i);\n    }'),
        "[6] Квадраты 1-10":    rs('    for i in 1..11 {\n        println!("{}", i * i);\n    }'),
        "[7] Кубы 1-10":        rs('    for i in 1..11 {\n        println!("{}", i * i * i);\n    }'),
        "[8] Таблица ×7":       rs('    for i in 1..11 {\n        println!("{}", i * 7);\n    }'),
        "[9] Факториал 5":      rs('    let mut r = 1;\n    for i in 1..6 {\n        r = r * i;\n    }\n    println!("{}", r);'),
        "[10] Фибоначчи 10":    rs('    let mut a = 0;\n    let mut b = 1;\n    for _ in 0..10 {\n        println!("{}", a);\n        let c = a + b;\n        a = b;\n        b = c;\n    }'),
        "[11] Сумма 1-100":     rs('    let mut s = 0;\n    for i in 1..101 {\n        s = s + i;\n    }\n    println!("{}", s);'),
        "[Test] 50+ строк — таблицы":          gen_python_50(),
        "[Test] 200+ строк — большие таблицы": gen_python_200(),
    }


# ==================================================================
#  C#
# ==================================================================
def std_cs():
    def cs(body):
        return ('using System;\n\n'
                'public class Program {\n'
                '    public static void Main() {\n'
                + body +
                '\n    }\n}')

    return {
        "[1] Hello, World":     cs('        Console.WriteLine("Hello, World!");'),
        "[2] Буква A":          cs('        Console.WriteLine("A");'),
        "[3] Цифры 0-9":        cs('        Console.WriteLine("0123456789");'),
        "[4] Алфавит A-J":      cs('        Console.WriteLine("ABCDEFGHIJ");'),
        "[5] Числа 1-10":       cs('        for (int i = 1; i < 11; i++) {\n            Console.WriteLine(i);\n        }'),
        "[6] Квадраты 1-10":    cs('        for (int i = 1; i < 11; i++) {\n            Console.WriteLine(i * i);\n        }'),
        "[7] Кубы 1-10":        cs('        for (int i = 1; i < 11; i++) {\n            Console.WriteLine(i * i * i);\n        }'),
        "[8] Таблица ×7":       cs('        for (int i = 1; i < 11; i++) {\n            Console.WriteLine(i * 7);\n        }'),
        "[9] Факториал 5":      cs('        int r = 1;\n        for (int i = 1; i < 6; i++) {\n            r = r * i;\n        }\n        Console.WriteLine(r);'),
        "[10] Фибоначчи 10":    cs('        int a = 0, b = 1;\n        for (int i = 0; i < 10; i++) {\n            Console.WriteLine(a);\n            int c = a + b;\n            a = b;\n            b = c;\n        }'),
        "[11] Сумма 1-100":     cs('        int s = 0;\n        for (int i = 1; i < 101; i++) {\n            s = s + i;\n        }\n        Console.WriteLine(s);'),
        "[Test] 50+ строк — таблицы":          gen_python_50(),
        "[Test] 200+ строк — большие таблицы": gen_python_200(),
    }