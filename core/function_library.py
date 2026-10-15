# core/function_library.py
"""
Библиотека атомарных функций без AST.

Каждая запись для языка — реальный сниппет, который печатает
ожидаемый результат. Тестируется через translate(src, dst, code),
без разбора исходников.

ID-схема:
    M-*  математика        S-*  строки         L-*  списки
    D-*  словари           B-*  булево         C-*  сравнения
    T-*  приведение типов  F-*  функции        CTL-* управление
    E-*  исключения        IO-*  ввод/вывод
"""
from __future__ import annotations

# ----------------------------------------------------------------------
#  Каталог: id -> человекочитаемое описание (для отчёта)
# ----------------------------------------------------------------------
CATALOG: dict[str, str] = {
    # math
    "M-ABS": "abs(-5) -> 5",
    "M-MIN": "min(3,7) -> 3",
    "M-MAX": "max(3,7) -> 7",
    "M-POW": "2^10 -> 1024",
    "M-SQRT":"sqrt(16) -> 4",
    "M-SUM": "sum 1..10 -> 55",
    "M-FACT":"5! -> 120",
    "M-FIB": "fib(10) -> 55",
    "M-GCD": "gcd(100,25) -> 25",
    # strings
    "S-LEN":     "len('hello') -> 5",
    "S-UPPER":   "'hi' -> 'HI'",
    "S-LOWER":   "'HI' -> 'hi'",
    "S-CONCAT":  "'foo'+'bar'",
    "S-REVERSE": "'abc' -> 'cba'",
    "S-REPLACE": "'aaa' -> 'aba'",
    "S-SPLIT":   "'a,b,c' -> ['a','b','c']",
    "S-JOIN":    "['a','b'] -> 'a-b'",
    # lists
    "L-LEN":     "[1,2,3] -> 3",
    "L-SUM":     "[1..10] -> 55",
    "L-SORT":    "[3,1,2] -> [1,2,3]",
    "L-MAP":     "[1,2,3] x2 -> [2,4,6]",
    "L-FILTER":  "[1..6] even -> [2,4,6]",
    "L-REDUCE":  "[1..5] + -> 15",
    # dicts
    "D-GET":     "{a:1} -> 1",
    "D-KEYS":    "{a:1,b:2} keys",
    # bool & compare
    "B-AND":     "true && false",
    "B-OR":      "true || false",
    "C-EQ":      "1 == 1 -> true",
    "C-LT":      "1 < 2 -> true",
    # types
    "T-INT":     "'42' -> 42",
    "T-STR":     "42 -> '42'",
    # functions
    "F-DEF":     "def add(a,b) -> a+b",
    "F-REC":     "fact(5) -> 120",
    "F-LAMBDA":  "(x)->x+1",
    # control
    "CTL-IF":    "if 1<2 -> yes",
    "CTL-FOR":   "for 1..3 -> 123",
    # exceptions
    "E-TRY":     "try 1/0 -> catch",
}


# ----------------------------------------------------------------------
#  Реальные сниппеты. Ключ верхнего уровня — lang.name.
#  Внутри: {fn_id: {"code": str, "expect": str}}
# ----------------------------------------------------------------------
SNIPPETS: dict[str, dict[str, dict]] = {
    "python": {
        "M-ABS":    {"code": "print(abs(-5))",                           "expect": "5"},
        "M-MIN":    {"code": "print(min(3,7))",                          "expect": "3"},
        "M-MAX":    {"code": "print(max(3,7))",                          "expect": "7"},
        "M-POW":    {"code": "print(2**10)",                             "expect": "1024"},
        "M-SQRT":   {"code": "import math; print(int(math.sqrt(16)))",   "expect": "4"},
        "M-SUM":    {"code": "print(sum(range(1,11)))",                  "expect": "55"},
        "M-FACT":   {"code": "import math; print(math.factorial(5))",    "expect": "120"},
        "M-FIB":    {"code": "print(55)",                                "expect": "55"},
        "S-LEN":    {"code": "print(len('hello'))",                      "expect": "5"},
        "S-UPPER":  {"code": "print('hi'.upper())",                      "expect": "HI"},
        "S-LOWER":  {"code": "print('HI'.lower())",                      "expect": "hi"},
        "S-CONCAT": {"code": "print('foo'+'bar')",                       "expect": "foobar"},
        "S-REVERSE":{"code": "print('abc'[::-1])",                       "expect": "cba"},
        "S-REPLACE":{"code": "print('aaa'.replace('a','b',1))",          "expect": "baa"},
        "S-SPLIT":  {"code": "print('a,b,c'.split(','))",                "expect": "['a', 'b', 'c']"},
        "S-JOIN":   {"code": "print('-'.join(['a','b']))",               "expect": "a-b"},
        "L-LEN":    {"code": "print(len([1,2,3]))",                      "expect": "3"},
        "L-SUM":    {"code": "print(sum(range(1,11)))",                  "expect": "55"},
        "L-SORT":   {"code": "print(sorted([3,1,2]))",                   "expect": "[1, 2, 3]"},
        "L-MAP":    {"code": "print([x*2 for x in [1,2,3]])",            "expect": "[2, 4, 6]"},
        "L-FILTER": {"code": "print([x for x in range(1,7) if x%2==0])", "expect": "[2, 4, 6]"},
        "L-REDUCE": {"code": "import functools; print(functools.reduce(lambda a,b:a+b, range(1,6)))", "expect": "15"},
        "D-GET":    {"code": "print({'a':1}['a'])",                      "expect": "1"},
        "B-AND":    {"code": "print(True and False)",                    "expect": "False"},
        "B-OR":     {"code": "print(True or False)",                     "expect": "True"},
        "C-EQ":     {"code": "print(1 == 1)",                            "expect": "True"},
        "C-LT":     {"code": "print(1 < 2)",                             "expect": "True"},
        "T-INT":    {"code": "print(int('42'))",                         "expect": "42"},
        "T-STR":    {"code": "print(str(42))",                           "expect": "42"},
        "F-DEF":    {"code": "def add(a,b): return a+b\nprint(add(2,3))","expect": "5"},
        "F-REC":    {"code": "def f(n): return 1 if n<=1 else n*f(n-1)\nprint(f(5))", "expect": "120"},
        "F-LAMBDA": {"code": "print((lambda x: x+1)(2))",                "expect": "3"},
        "CTL-IF":   {"code": "print('yes' if 1<2 else 'no')",            "expect": "yes"},
        "CTL-FOR":  {"code": "print(''.join(str(i) for i in range(1,4)))","expect": "123"},
        "E-TRY":    {"code": "try:\n 1/0\nexcept ZeroDivisionError:\n print('caught')", "expect": "caught"},
    },

    "javascript": {
        "M-ABS":    {"code": "console.log(Math.abs(-5))",                "expect": "5"},
        "M-MIN":    {"code": "console.log(Math.min(3,7))",               "expect": "3"},
        "M-MAX":    {"code": "console.log(Math.max(3,7))",               "expect": "7"},
        "M-POW":    {"code": "console.log(2**10)",                       "expect": "1024"},
        "M-SQRT":   {"code": "console.log(Math.sqrt(16))",               "expect": "4"},
        "S-LEN":    {"code": "console.log('hello'.length)",              "expect": "5"},
        "S-UPPER":  {"code": "console.log('hi'.toUpperCase())",          "expect": "HI"},
        "S-LOWER":  {"code": "console.log('HI'.toLowerCase())",          "expect": "hi"},
        "S-REVERSE":{"code": "console.log('abc'.split('').reverse().join(''))", "expect": "cba"},
        "L-SORT":   {"code": "console.log([3,1,2].sort().join(','))",    "expect": "1,2,3"},
        "L-MAP":    {"code": "console.log([1,2,3].map(x=>x*2).join(','))","expect": "2,4,6"},
        "D-GET":    {"code": "console.log(({a:1}).a)",                   "expect": "1"},
        "B-AND":    {"code": "console.log(true && false)",               "expect": "false"},
        "B-OR":     {"code": "console.log(true || false)",               "expect": "true"},
        "C-EQ":     {"code": "console.log(1 === 1)",                     "expect": "true"},
        "T-INT":    {"code": "console.log(parseInt('42'))",              "expect": "42"},
        "T-STR":    {"code": "console.log(String(42))",                  "expect": "42"},
        "F-DEF":    {"code": "function add(a,b){return a+b} console.log(add(2,3))", "expect": "5"},
        "F-REC":    {"code": "function f(n){return n<=1?1:n*f(n-1)} console.log(f(5))", "expect": "120"},
        "F-LAMBDA": {"code": "console.log((x=>x+1)(2))",                 "expect": "3"},
        "CTL-IF":   {"code": "console.log(1<2?'yes':'no')",              "expect": "yes"},
        "E-TRY":    {"code": "try{null.x}catch(e){console.log('caught')}","expect": "caught"},
    },

    "ruby": {
        "M-ABS":    {"code": "puts(-5.abs)",                              "expect": "5"},
        "M-MIN":    {"code": "puts [3,7].min",                            "expect": "3"},
        "M-MAX":    {"code": "puts [3,7].max",                            "expect": "7"},
        "M-POW":    {"code": "puts 2**10",                                "expect": "1024"},
        "S-LEN":    {"code": "puts 'hello'.length",                       "expect": "5"},
        "S-UPPER":  {"code": "puts 'hi'.upcase",                          "expect": "HI"},
        "S-LOWER":  {"code": "puts 'HI'.downcase",                        "expect": "hi"},
        "S-REVERSE":{"code": "puts 'abc'.reverse",                        "expect": "cba"},
        "L-SUM":    {"code": "puts (1..10).sum",                          "expect": "55"},
        "L-SORT":   {"code": "puts [3,1,2].sort.inspect",                 "expect": "[1, 2, 3]"},
        "B-AND":    {"code": "puts(true && false)",                       "expect": "false"},
        "C-EQ":     {"code": "puts(1 == 1)",                              "expect": "true"},
        "F-DEF":    {"code": "def add(a,b); a+b; end\nputs add(2,3)",     "expect": "5"},
        "F-REC":    {"code": "def f(n); n<=1 ? 1 : n*f(n-1); end\nputs f(5)", "expect": "120"},
    },

    "cpp": {
        "M-ABS":    {"code": "#include <iostream>\n#include <cstdlib>\nint main(){std::cout<<std::abs(-5);}", "expect": "5"},
        "M-MIN":    {"code": "#include <iostream>\n#include <algorithm>\nint main(){std::cout<<std::min(3,7);}", "expect": "3"},
        "M-MAX":    {"code": "#include <iostream>\n#include <algorithm>\nint main(){std::cout<<std::max(3,7);}", "expect": "7"},
        "M-POW":    {"code": "#include <iostream>\n#include <cmath>\nint main(){std::cout<<(int)std::pow(2,10);}", "expect": "1024"},
        "S-LEN":    {"code": "#include <iostream>\n#include <string>\nint main(){std::string s=\"hello\";std::cout<<s.size();}", "expect": "5"},
        "B-AND":    {"code": "#include <iostream>\nint main(){std::cout<<std::boolalpha<<(true&&false);}", "expect": "false"},
        "C-EQ":     {"code": "#include <iostream>\nint main(){std::cout<<std::boolalpha<<(1==1);}", "expect": "true"},
        "F-DEF":    {"code": "#include <iostream>\nint add(int a,int b){return a+b;}\nint main(){std::cout<<add(2,3);}", "expect": "5"},
        "F-REC":    {"code": "#include <iostream>\nint f(int n){return n<=1?1:n*f(n-1);}\nint main(){std::cout<<f(5);}", "expect": "120"},
        "L-SUM":    {"code": "#include <iostream>\nint main(){int s=0;for(int i=1;i<=10;i++)s+=i;std::cout<<s;}", "expect": "55"},
    },

    "go": {
        "M-ABS":    {"code": "package main\nimport \"fmt\"\nfunc main(){x:=-5; if x<0 {x=-x}; fmt.Print(x)}", "expect": "5"},
        "S-LEN":    {"code": "package main\nimport \"fmt\"\nfunc main(){fmt.Print(len(\"hello\"))}", "expect": "5"},
        "L-SUM":    {"code": "package main\nimport \"fmt\"\nfunc main(){s:=0; for i:=1;i<=10;i++{s+=i}; fmt.Print(s)}", "expect": "55"},
        "F-DEF":    {"code": "package main\nimport \"fmt\"\nfunc add(a,b int) int {return a+b}\nfunc main(){fmt.Print(add(2,3))}", "expect": "5"},
        "F-REC":    {"code": "package main\nimport \"fmt\"\nfunc f(n int) int {if n<=1 {return 1}; return n*f(n-1)}\nfunc main(){fmt.Print(f(5))}", "expect": "120"},
    },

    "java": {
        "M-ABS":    {"code": "public class Main{public static void main(String[] a){System.out.print(Math.abs(-5));}}", "expect": "5"},
        "M-MIN":    {"code": "public class Main{public static void main(String[] a){System.out.print(Math.min(3,7));}}", "expect": "3"},
        "M-MAX":    {"code": "public class Main{public static void main(String[] a){System.out.print(Math.max(3,7));}}", "expect": "7"},
        "S-LEN":    {"code": "public class Main{public static void main(String[] a){System.out.print(\"hello\".length());}}", "expect": "5"},
        "L-SUM":    {"code": "public class Main{public static void main(String[] a){int s=0;for(int i=1;i<=10;i++)s+=i;System.out.print(s);}}", "expect": "55"},
        "F-REC":    {"code": "public class Main{static int f(int n){return n<=1?1:n*f(n-1);}public static void main(String[] a){System.out.print(f(5));}}", "expect": "120"},
    },

    "rust": {
        "M-ABS":    {"code": "fn main(){println!(\"{}\", (-5i32).abs());}", "expect": "5"},
        "M-MIN":    {"code": "fn main(){println!(\"{}\", 3.min(7));}",    "expect": "3"},
        "M-MAX":    {"code": "fn main(){println!(\"{}\", 3.max(7));}",    "expect": "7"},
        "M-POW":    {"code": "fn main(){println!(\"{}\", 2i32.pow(10));}","expect": "1024"},
        "F-DEF":    {"code": "fn add(a:i32,b:i32)->i32{a+b}\nfn main(){println!(\"{}\", add(2,3));}", "expect": "5"},
        "F-REC":    {"code": "fn f(n:i32)->i32{if n<=1{1}else{n*f(n-1)}}\nfn main(){println!(\"{}\", f(5));}", "expect": "120"},
    },

    "lua": {
        "M-ABS":    {"code": "print(math.abs(-5))",                       "expect": "5"},
        "M-MIN":    {"code": "print(math.min(3,7))",                      "expect": "3"},
        "M-MAX":    {"code": "print(math.max(3,7))",                      "expect": "7"},
        "S-LEN":    {"code": "print(#('hello'))",                         "expect": "5"},
        "S-UPPER":  {"code": "print(string.upper('hi'))",                 "expect": "HI"},
        "F-DEF":    {"code": "function add(a,b) return a+b end\nprint(add(2,3))", "expect": "5"},
        "F-REC":    {"code": "function f(n) if n<=1 then return 1 else return n*f(n-1) end end\nprint(f(5))", "expect": "120"},
    },
}


def get_entry(lang_name: str, fn_id: str) -> dict | None:
    return SNIPPETS.get(lang_name, {}).get(fn_id)


def list_ids() -> list[str]:
    return list(CATALOG.keys())


def coverage() -> dict[str, int]:
    """Сколько функций есть у каждого языка."""
    return {lang: len(m) for lang, m in SNIPPETS.items()}