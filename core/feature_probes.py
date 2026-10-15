# core/feature_probes.py
"""
Per-language feature probes.

Структура:
    PROBES[lang.name] = { feature_name: source_snippet }

Каждый snippet должен быть валидным кодом на ЯЗЫКЕ lang.name и
печатать детерминированный вывод (или не печатать, но не падать).
"""

PROBES: dict[str, dict[str, str]] = {

    # ============================================================
    "python": {
        "assign":     "x = 42\nprint(x)",
        "arith":      "print(17 + 5, 17 - 5, 17 * 5, 17 // 5, 17 % 5)",
        "string_ops": "s = 'hello'\nprint(s.upper(), s[::-1], len(s))",
        "if_else":    "x = 7\nprint('even' if x % 2 == 0 else 'odd')",
        "for_loop":   "for i in range(1, 6):\n    print(i)",
        "while_loop": "i = 0\nwhile i < 5:\n    i += 1\nprint(i)",
        "def_func":   "def f(x):\n    return x * 2\nprint(f(5))",
        "recursion":  "def fact(n):\n    return 1 if n <= 1 else n * fact(n-1)\nprint(fact(5))",
        "list_comp":  "print([x*x for x in range(5)])",
        "dict_ops":   "d = {'a': 1}\nd['b'] = 2\nprint(sorted(d.items()))",
        "try_except": "try:\n    _ = 1 / 0\nexcept ZeroDivisionError:\n    print('caught')",
        "class_def":  "class P:\n    def __init__(self, x): self.x = x\n    def get(self): return self.x\nprint(P(7).get())",
        "lambda":     "print((lambda x: x + 1)(5))",
        "set_ops":    "s = {1, 2, 3}\nprint(sorted(s | {3, 4}))",
        "tuple":      "t = (1, 2, 3)\nprint(t, sum(t))",
        "slice":      "xs = [1, 2, 3, 4, 5]\nprint(xs[1:4], xs[::-1])",
        "fstring":    "n = 7\nprint(f'n = {n}, n^2 = {n*n}')",
        "generator":  "def g():\n    yield 1\n    yield 2\nprint(list(g()))",
        "ternary":    "x = 5\nprint('big' if x > 3 else 'small')",
        "import_math":"import math\nprint(int(math.sqrt(16)))",
    },

    # ============================================================
    "javascript": {
        "assign":     "let x = 42;\nconsole.log(x);",
        "arith":      "console.log(17 + 5, 17 - 5, 17 * 5, Math.floor(17 / 5), 17 % 5);",
        "string_ops": "let s = 'hello';\nconsole.log(s.toUpperCase(), s.length);",
        "if_else":    "let x = 7;\nif (x % 2 === 0) console.log('even'); else console.log('odd');",
        "for_loop":   "for (let i = 1; i <= 5; i++) console.log(i);",
        "while_loop": "let i = 0;\nwhile (i < 5) i++;\nconsole.log(i);",
        "def_func":   "function f(x){ return x * 2; }\nconsole.log(f(5));",
        "recursion":  "function fact(n){ return n <= 1 ? 1 : n * fact(n-1); }\nconsole.log(fact(5));",
        "arrow":      "const f = x => x + 1;\nconsole.log(f(5));",
        "array_map":  "const xs = [1,2,3,4,5];\nconsole.log(xs.map(x => x*x));",
        "object":     "const o = {a: 1, b: 2};\nconsole.log(o.a + o.b);",
        "ternary":    "let x = 5;\nconsole.log(x > 3 ? 'big' : 'small');",
        "template":   "let n = 7;\nconsole.log(`n = ${n}, n^2 = ${n*n}`);",
        "try_catch":  "try { throw new Error('boom'); } catch (e) { console.log('caught'); }",
        "spread":     "const a = [1, 2];\nconst b = [...a, 3];\nconsole.log(b);",
    },

    # ============================================================
    "cpp": {
        "assign":     '#include <iostream>\nint main(){ int x = 42; std::cout << x << "\\n"; return 0; }',
        "arith":      '#include <iostream>\nint main(){ std::cout << (17+5) << " " << (17-5) << "\\n"; return 0; }',
        "for_loop":   '#include <iostream>\nint main(){ for(int i=1;i<=5;i++) std::cout << i << "\\n"; return 0; }',
        "while_loop": '#include <iostream>\nint main(){ int i=0; while(i<5) i++; std::cout << i << "\\n"; return 0; }',
        "def_func":   '#include <iostream>\nint f(int x){ return x*2; }\nint main(){ std::cout << f(5) << "\\n"; return 0; }',
        "recursion":  '#include <iostream>\nint fact(int n){ return n<=1?1:n*fact(n-1); }\nint main(){ std::cout << fact(5) << "\\n"; return 0; }',
        "vector":     '#include <iostream>\n#include <vector>\nint main(){ std::vector<int> v={1,2,3}; std::cout << v[0]+v[1]+v[2] << "\\n"; return 0; }',
        "string":     '#include <iostream>\n#include <string>\nint main(){ std::string s="hi"; std::cout << s.size() << "\\n"; return 0; }',
    },

    # ============================================================
    "java": {
        "assign":     'public class Main { public static void main(String[] a){ int x = 42; System.out.println(x); } }',
        "arith":      'public class Main { public static void main(String[] a){ System.out.println(17 + 5); } }',
        "for_loop":   'public class Main { public static void main(String[] a){ for(int i=1;i<=5;i++) System.out.println(i); } }',
        "while_loop": 'public class Main { public static void main(String[] a){ int i=0; while(i<5) i++; System.out.println(i); } }',
        "def_func":   'public class Main { static int f(int x){ return x*2; } public static void main(String[] a){ System.out.println(f(5)); } }',
        "recursion":  'public class Main { static int fact(int n){ return n<=1?1:n*fact(n-1); } public static void main(String[] a){ System.out.println(fact(5)); } }',
        "string":     'public class Main { public static void main(String[] a){ String s="hello"; System.out.println(s.length()); } }',
    },

    # ============================================================
    "go": {
        "assign":     'package main\nimport "fmt"\nfunc main(){ x := 42; fmt.Println(x) }',
        "arith":      'package main\nimport "fmt"\nfunc main(){ fmt.Println(17+5, 17-5, 17*5, 17/5) }',
        "for_loop":   'package main\nimport "fmt"\nfunc main(){ for i:=1; i<=5; i++ { fmt.Println(i) } }',
        "if_else":    'package main\nimport "fmt"\nfunc main(){ x:=7; if x%2==0 { fmt.Println("even") } else { fmt.Println("odd") } }',
        "def_func":   'package main\nimport "fmt"\nfunc f(x int) int { return x*2 }\nfunc main(){ fmt.Println(f(5)) }',
        "recursion":  'package main\nimport "fmt"\nfunc fact(n int) int { if n<=1 { return 1 }; return n*fact(n-1) }\nfunc main(){ fmt.Println(fact(5)) }',
    },

    # ============================================================
    "rust": {
        "assign":     'fn main(){ let x = 42; println!("{}", x); }',
        "arith":      'fn main(){ println!("{}", 17 + 5); }',
        "for_loop":   'fn main(){ for i in 1..=5 { println!("{}", i); } }',
        "while_loop": 'fn main(){ let mut i = 0; while i < 5 { i += 1; } println!("{}", i); }',
        "def_func":   'fn f(x: i32) -> i32 { x * 2 }\nfn main(){ println!("{}", f(5)); }',
        "recursion":  'fn fact(n: i32) -> i32 { if n <= 1 { 1 } else { n * fact(n-1) } }\nfn main(){ println!("{}", fact(5)); }',
    },

    # ============================================================
    "ruby": {
        "assign":     'x = 42\nputs x',
        "arith":      'puts 17 + 5',
        "for_loop":   'for i in 1..5\n  puts i\nend',
        "if_else":    'x = 7\nif x % 2 == 0\n  puts "even"\nelse\n  puts "odd"\nend',
        "def_func":   'def f(x)\n  x * 2\nend\nputs f(5)',
        "recursion":  'def fact(n)\n  n <= 1 ? 1 : n * fact(n-1)\nend\nputs fact(5)',
        "string":     's = "hello"\nputs s.upcase\nputs s.length',
    },

    # ============================================================
    "lua": {
        "assign":     'local x = 42\nprint(x)',
        "arith":      'print(17 + 5)',
        "for_loop":   'for i = 1, 5 do print(i) end',
        "while_loop": 'local i = 0\nwhile i < 5 do i = i + 1 end\nprint(i)',
        "def_func":   'function f(x) return x * 2 end\nprint(f(5))',
        "recursion":  'function fact(n) if n <= 1 then return 1 end return n * fact(n-1) end\nprint(fact(5))',
        "string":     'local s = "hello"\nprint(#s)',
    },

    # ============================================================
    "csharp": {
        "assign":     'using System;\nclass P { static void Main(){ int x = 42; Console.WriteLine(x); } }',
        "arith":      'using System;\nclass P { static void Main(){ Console.WriteLine(17+5); } }',
        "for_loop":   'using System;\nclass P { static void Main(){ for(int i=1;i<=5;i++) Console.WriteLine(i); } }',
        "def_func":   'using System;\nclass P { static int F(int x){ return x*2; } static void Main(){ Console.WriteLine(F(5)); } }',
        "recursion":  'using System;\nclass P { static int Fact(int n){ return n<=1?1:n*Fact(n-1); } static void Main(){ Console.WriteLine(Fact(5)); } }',
    },

    # ============================================================
    "dart": {
        "assign":     'void main(){ var x = 42; print(x); }',
        "arith":      'void main(){ print(17 + 5); }',
        "for_loop":   'void main(){ for (var i = 1; i <= 5; i++) print(i); }',
        "if_else":    'void main(){ var x = 7; if (x % 2 == 0) print("even"); else print("odd"); }',
        "def_func":   'int f(int x) => x * 2;\nvoid main(){ print(f(5)); }',
        "recursion":  'int fact(int n) => n <= 1 ? 1 : n * fact(n - 1);\nvoid main(){ print(fact(5)); }',
    },
}


def features_for(lang_name: str) -> dict[str, str]:
    """Возвращает probes для языка или {}."""
    return PROBES.get(lang_name, {})