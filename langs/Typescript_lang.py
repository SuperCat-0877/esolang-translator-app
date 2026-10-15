# langs/Typescript_lang.py
import re
import sys
from io import StringIO

from langs.javascript_lang import JavaScriptLang, _js_to_python
from core.translate import TRANSPILERS
from core.standard_templates import std_js


_TS_TYPE_RE = re.compile(
    r":\s*(number|string|boolean|any|void|never|unknown|object|"
    r"number\[\]|string\[\]|Array<[^>]+>)\b"
)


# --- normal patch: ts assertions ---
def _strip_ts_assertions(src):
    # `x as Type` → x
    src = re.sub(r"\s+as\s+[A-Za-z_]\w*(?:\[\])?", "", src)
    # `x!` (non-null) → x
    src = re.sub(r"([A-Za-z_]\w*)!(?=[\s,;)\]}.]|$)", r"\1", src)
    return src


def _strip_ts_types(src):
    if not src:
        return ""
    return _TS_TYPE_RE.sub("", src)


def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    return False


def _convert_enum(src):
    """enum Name { A, B, C } → class Name: A = 0; B = 1; C = 2"""
    def repl(m):
        name = m.group(1)
        body = m.group(2)
        lines = [f"class {name}:"]
        for i, item in enumerate(_split_top(body, ",")):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                k, v = item.split("=", 1)
                lines.append(f"    {k.strip()} = {v.strip()}")
            else:
                lines.append(f"    {item} = {i}")
        if len(lines) == 1:
            lines.append("    pass")
        return "\n".join(lines) + "\n}"
    return re.sub(r"\benum\s+(\w+)\s*\{([^}]*)\}", repl, src)


def _split_top(s, sep):
    parts, buf, depth = [], [], 0
    in_str = None
    for ch in s:
        if in_str:
            buf.append(ch)
            if ch == in_str:
                in_str = None
            continue
        if ch in '"\'':
            in_str = ch
            buf.append(ch)
        elif ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _strip_ts_decls(src):
    """interface/type/abstract — удаляем (stub)."""
    src = re.sub(r"\binterface\s+\w+(?:\s+extends\s+[^{]+)?\s*\{[^}]*\}",
                 "", src)
    src = re.sub(r"\btype\s+\w+\s*=\s*[^;]+;", "", src)
    src = re.sub(r"\babstract\s+", "", src)
    src = re.sub(r"\breadonly\s+", "", src)
    return src


def _ts_to_python(src):
    if _looks_like_python(src):
        return src
    src = _convert_enum(src)
    src = _strip_ts_decls(src)
    src = _strip_ts_types(src)
    src = _strip_ts_assertions(src)
    return _js_to_python(src)


class TypeScriptLang(JavaScriptLang):
    name = "typescript"
    title = "TypeScript"
    ext = ".ts"
    keywords = [
        "let", "const", "function", "class", "interface", "type", "enum",
        "public", "private", "protected", "readonly",
        "if", "else", "for", "while", "return",
        "true", "false", "null", "undefined", "new", "this",
        "try", "catch", "finally", "throw", "console",
    ]

    templates = {
        '[E1] Hello, World': 'const msg: string = "Hello, World!";\nconsole.log(msg);',
        '[E2] Арифметика': 'const a: number = 17, b: number = 5;\nconsole.log(a + b, a - b, a * b, Math.floor(a / b), a % b, a ** b);',
        '[E3] Template literals': 'const n: string = "World";\nconsole.log(`Hello, ${n}! 2+2=${2 + 2}`);',
        '[E4] Стрелочные функции': 'const sq = (x: number): number => x * x;\nconst add = (a: number, b: number): number => a + b;\nconsole.log(sq(7), add(3, 4));',
        '[E5] Условие': 'let x: number = 7;\nif (x % 2 === 0) {\n  console.log("чёт");\n} else {\n  console.log("нечёт");\n}',
        '[M1] Циклы': 'for (let i: number = 1; i <= 5; i++) {\n  console.log(i, i * i);\n}\nfor (const x of [10, 20, 30]) {\n  console.log(x);\n}',
        '[M2] Методы массива': 'const xs = [1, 2, 3, 4, 5];\nconst sq = xs.map(x => x * x);\nconsole.log(sq);',
        '[M3] Строковые методы': 'const s: string = "Hello, World";\nconsole.log(s.toUpperCase());\nconsole.log(s.toLowerCase());\nconsole.log(s.length);',
        '[M4] Reduce': 'const nums = [1, 2, 3, 4, 5];\nconst sum = nums.reduce((a, b) => a + b, 0);\nconsole.log(sum);',
        '[M5] try/catch/finally': 'try {\n  throw new Error("boom");\n} catch (e) {\n  console.log("Caught");\n} finally {\n  console.log("done");\n}',
        '[H1] Классы с типами': 'class Point {\n  constructor(x: number, y: number) {\n    this.x = x;\n    this.y = y;\n  }\n  sum(): number {\n    return this.x + this.y;\n  }\n}\nconst p = new Point(3, 4);\nconsole.log(p.sum());',
        '[H2] Наследование': 'class Animal {\n  constructor(name: string) {\n    this.name = name;\n  }\n  speak(): string {\n    return this.name + " makes a sound";\n  }\n}\nclass Dog extends Animal {\n  speak(): string {\n    return this.name + " barks";\n  }\n}\nconst d = new Dog("Rex");\nconsole.log(d.speak());',
        '[H3] Карри и замыкания': 'const mkAdd = (x: number) => (y: number) => x + y;\nconst add5 = mkAdd(5);\nconsole.log(add5(3));\nconsole.log(add5(10));',
        '[H4] Композиция функций': 'const compose = (f, g) => x => f(g(x));\nconst inc = x => x + 1;\nconst dbl = x => x * 2;\nconst sq = x => x * x;\nconst step = compose(dbl, inc);\nconst result = compose(sq, step)(3);\nconsole.log(result);',
        '[H5] Функция с типами': 'const greet = (name: string): string => "Hello, " + name;\nconsole.log(greet("World"));\nconsole.log(greet("TypeScript"));',
        '[W1] Fibonacci (итеративный)': 'function fib(n: number): number {\n  if (n < 2) return n;\n  let a = 0;\n  let b = 1;\n  for (let i = 2; i <= n; i++) {\n    const t = a + b;\n    a = b;\n    b = t;\n  }\n  return b;\n}\nfor (let i = 0; i < 15; i++) {\n  console.log(fib(i));\n}',
        '[W2] Конвейер': 'const inc = x => x + 1;\nconst dbl = x => x * 2;\nconst sq = x => x * x;\nlet r = 5;\nr = inc(r);\nr = dbl(r);\nr = sq(r);\nconsole.log(r);',
        '[W3] Рекурсия (Ackermann)': 'function ackermann(m: number, n: number): number {\n  if (m === 0) return n + 1;\n  if (n === 0) return ackermann(m - 1, 1);\n  return ackermann(m - 1, ackermann(m, n - 1));\n}\nconsole.log(ackermann(2, 3));',
        '[W4] Свёртка': 'const nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];\nconst factorial = nums.reduce((a, b) => a * b, 1);\nconst sum = nums.reduce((a, b) => a + b, 0);\nconsole.log(factorial);\nconsole.log(sum);',
        '[W5] Сортировка': 'const words = ["banana", "apple", "cherry", "date"];\nwords.sort();\nconsole.log(words);',
        '[T1] Базовые конструкции': 'function gcd(a: number, b: number): number {\n  while (b) {\n    const t = b;\n    b = a % b;\n    a = t;\n  }\n  return a;\n}\nconsole.log(gcd(12, 8));\nconsole.log(gcd(100, 25));\nconsole.log(gcd(17, 5));',
        '[T2] Все структуры': 'const arr = [1, 2, 3];\nconst obj = {};\nobj["a"] = 1;\nobj["b"] = 2;\nconsole.log(arr.length);\nconsole.log(obj["a"] + obj["b"]);',
        '[T3] Класс Counter': 'class Counter {\n  constructor() {\n    this.n = 0;\n  }\n  inc(): number {\n    this.n = this.n + 1;\n    return this.n;\n  }\n}\nconst c = new Counter();\nconsole.log(c.inc());\nconsole.log(c.inc());\nconsole.log(c.inc());',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            return self._exec_python(src)
        # Честные stubs
        if re.search(r"\bdecorator\b", src) or re.search(r"@\w+\s*\(", src):
            return "// TypeScript: decorators не поддержаны (нужен AST)"
        py = _ts_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<ts>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// TypeScript: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def _exec_python(self, src):
        from io import StringIO
        import sys as _sys
        out = StringIO()
        old = _sys.stdout
        _sys.stdout = out
        try:
            exec(compile(src, "<ts>", "exec"), {})
        except Exception as e:
            _sys.stdout = old
            return f"// TypeScript: {type(e).__name__}: {e}"
        finally:
            _sys.stdout = old
        return out.getvalue()


TRANSPILERS[("typescript", "python")] = _ts_to_python
TRANSPILERS[("typescript", "javascript")] = _strip_ts_types
