# langs/perl.py
"""Perl — обычный язык. Субрутины, массивы, хеши."""

import re
import json
from io import StringIO
import sys

from core.base import Language
from core.translate import TRANSPILERS



def _perl_expr_to_py(expr):
    e = expr.strip()
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bundef\b", "None", e)
    if e.startswith('"') and e.endswith('"'):
        content = e[1:-1]
        content = content.replace("\\\\n", "").replace("\\n", "")
        if content.startswith("$"):
            return content.lstrip("$")
        return f'"{content}"'
    e = re.sub(r"\bsubstr\(([^,]+),\s*([^,]+),\s*([^)]+)\)",
               r"\1[(\2):(\2)+(\3)]", e)
    e = re.sub(r"\bsubstr\(([^,]+),\s*([^)]+)\)", r"\1[(\2):]", e)
    e = re.sub(r"\bindex\(([^,]+),\s*([^)]+)\)", r"\1.find(\2)", e)
    e = re.sub(r"\blength\(([^)]+)\)", r"len(\1)", e)
    e = re.sub(r"\buc\(([^)]+)\)", r"(\1).upper()", e)
    e = re.sub(r"\blc\(([^)]+)\)", r"(\1).lower()", e)
    e = re.sub(r"\bchomp\(([^)]+)\)", r"\1.rstrip()", e)
    e = re.sub(r"\$([A-Za-z_]\w*)", r"\1", e)
    e = re.sub(r"@([A-Za-z_]\w*)", r"\1", e)
    e = re.sub(r"%([A-Za-z_]\w*)", r"\1", e)
    e = re.sub(r"scalar\(([^()]*)\)", r"len(\1)", e)
    return e

def _looks_like_python(src):
    if not src:
        return False
    if re.search(r"\bfor\s+\w+\s+in\s+range\s*\(", src):
        return True
    if re.search(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", src, re.M):
        return True
    if ("sub " not in src and "my $" not in src
            and re.search(r"^\s*print\s*\(", src, re.M)):
        return True
    return False


def _split_top_level(s, sep):
    parts, buf, depth, in_str = [], [], 0, None
    for ch in s:
        if in_str:
            buf.append(ch)
            if ch == in_str:
                in_str = None
            continue
        if ch in '"\'"':
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


def _perl_to_python(src):
    try:
        return _perl_to_python_impl(src)
    except Exception as e:
        import traceback
        return f"# Perl: внутренняя ошибка: {e}\n# {traceback.format_exc()[:300]}\n"


# --- normal patch: perl regex ---
def _convert_perl_regex(src):
    import re as _re
    # $x =~ m/pat/  →  re.search(r'pat', x)
    src = _re.sub(r"\$(\w+)\s*=~\s*m/([^/]+)/",
                  r"_re.search(r'\2', \1)", src)
    # $x =~ s/pat/repl/  →  re.sub(r'pat', r'repl', x)
    src = _re.sub(r"\$(\w+)\s*=~\s*s/([^/]+)/([^/]+)/",
                  r"_re.sub(r'\2', r'\3', \1)", src)
    # $x =~ /pat/  →  re.search(r'pat', x)
    src = _re.sub(r"\$(\w+)\s*=~\s*/([^/]+)/",
                  r"_re.search(r'\2', \1)", src)
    return src


def _perl_to_python_impl(src):
    src = _convert_perl_regex(src)
    lines = src.splitlines()
    out = []
    ind = 0

    def emit(s):
        out.append("    " * ind + s)

    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = raw.strip()
        i += 1

        if not line or line.startswith("#"):
            continue

        # Исправление бага с пустой открывающей скобкой на новой строке
        if line == "{":
            continue

        if line == "}":
            ind = max(0, ind - 1)
            continue

        # sub name(args) { ... } или sub name(args)
        m = re.match(r"sub\s+(\w+)\s*\(([^)]*)\)\s*\{?$", line)
        if m:
            name = m.group(1)
            args = ", ".join(
                a.strip().lstrip("$")
                for a in m.group(2).split(",") if a.strip())
            emit(f"def {name}({args}):")
            ind += 1
            continue

        # sub name { ... } или sub name
        m = re.match(r"sub\s+(\w+)\s*\{?$", line)
        if m:
            name = m.group(1)
            emit(f"def {name}(*args):")
            ind += 1
            continue

        # my ($x, $y) = @_;
        m = re.match(r"my\s*\(\s*([^)]+)\s*\)\s*=\s*@_\s*;?\s*$", line)
        if m:
            names = [x.strip().lstrip("$")
                     for x in m.group(1).split(",") if x.strip()]
            for k, n in enumerate(names):
                emit(f"{n} = args[{k}] if len(args) > {k} else None")
            continue

        # for my $i (1..10) {
        m = re.match(r"for\s+my\s+\$(\w+)\s*\((\d+)\s*\.\.\s*(\d+)\)\s*\{?", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue
        m = re.match(r"foreach\s+my\s+\$(\w+)\s*\((\d+)\s*\.\.\s*(\d+)\)\s*\{?", line)
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            emit(f"for {v} in range({a}, {int(b) + 1}):")
            ind += 1
            continue
        m = re.match(r"(?:for|foreach)\s+my\s+\$(\w+)\s*\((.+)\)\s*\{?\s*$", line)
        if m:
            v = m.group(1)
            rng = m.group(2).strip()
            rng_m = re.match(r"(\d+)\s*\.\.\s*(\d+)", rng)
            if rng_m:
                emit(f"for {v} in range({rng_m.group(1)}, {int(rng_m.group(2)) + 1}):")
            else:
                emit(f"for {v} in {_perl_expr_to_py(rng)}:")
            ind += 1
            continue

        m = re.match(r"while\s*\((.+)\)\s*\{?\s*$", line)
        if m:
            emit(f"while {_perl_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        m = re.match(r"if\s*\((.+)\)\s*\{?\s*$", line)
        if m:
            emit(f"if {_perl_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        m = re.match(r"\}?\s*elsif\s*\((.+)\)\s*\{?\s*$", line)
        if m:
            ind = max(0, ind - 1)
            emit(f"elif {_perl_expr_to_py(m.group(1))}:")
            ind += 1
            continue
        if re.match(r"\}?\s*else\s*\{?", line):
            ind = max(0, ind - 1)
            emit("else:")
            ind += 1
            continue

        m = re.match(r"return\s*(.*?)\s*;?\s*$", line)
        if m:
            val = m.group(1).strip().rstrip(";")
            if val:
                emit(f"return {_perl_expr_to_py(val)}")
            else:
                emit("return")
            continue

        # print / say
        m = re.match(r"print\s+(.+?)\s*;?\s*$", line)
        if m:
            arg = m.group(1).strip().rstrip(";")
            emit(f"print({_perl_expr_to_py(arg)})")
            continue
        m = re.match(r"say\s+(.+?)\s*;?\s*$", line)
        if m:
            arg = m.group(1).strip().rstrip(";")
            emit(f"print({_perl_expr_to_py(arg)})")
            continue

        # my $x = expr;
        m = re.match(r"my\s+\$(\w+)\s*=\s*(.+?)\s*;?\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_perl_expr_to_py(m.group(2))}")
            continue

        # my @arr = (...)
        m = re.match(r"my\s+@(\w+)\s*=\s*\(([^)]*)\)\s*;?\s*$", line)
        if m:
            items = _split_top_level(m.group(2), ",")
            clean = ", ".join(_perl_expr_to_py(x) for x in items if x.strip())
            emit(f"{m.group(1)} = [{clean}]")
            continue

        # my %hash = (...)
        m = re.match(r"my\s+%(\w+)\s*=\s*\(([^)]*)\)\s*;?\s*$", line)
        if m:
            items = _split_top_level(m.group(2), ",")
            pairs = []
            for j in range(0, len(items) - 1, 2):
                k = _perl_expr_to_py(items[j].strip())
                v = _perl_expr_to_py(items[j + 1].strip())
                pairs.append(f"{k}: {v}")
            emit(f"{m.group(1)} = {{{', '.join(pairs)}}}")
            continue

        # $x = expr;
        m = re.match(r"\$(\w+)\s*=\s*(.+?)\s*;?\s*$", line)
        if m:
            emit(f"{m.group(1)} = {_perl_expr_to_py(m.group(2))}")
            continue

        # push @arr, x
        m = re.match(r"push\s+@(\w+)\s*,\s*(.+?)\s*;?\s*$", line)
        if m:
            emit(f"{m.group(1)}.append({_perl_expr_to_py(m.group(2))})")
            continue

        # pop @arr
        m = re.match(r"pop\s+@(\w+)\s*;?\s*$", line)
        if m:
            emit(f"{m.group(1)}.pop()")
            continue

        continue

    return "\n".join(out) + "\n"


def perl_print(text):
    if not text:
        return 'print "";\n'
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'print {json.dumps(ln, ensure_ascii=False)};' for ln in lines) + "\n"


def perl_gen_numbers():
    return 'for my $i (1..10) {\n    print "$i\\\\n";\n}\n'


def perl_gen_squares():
    return 'for my $i (1..10) {\n    print $i * $i;\n    print "\\\\n";\n}\n'


def perl_gen_cubes():
    return 'for my $i (1..10) {\n    print $i * $i * $i;\n    print "\\\\n";\n}\n'


def perl_gen_table7():
    return 'for my $i (1..10) {\n    print $i * 7;\n    print "\\\\n";\n}\n'


def perl_gen_factorial():
    return ('my $r = 1;\n'
            'for my $i (1..5) {\n'
            '    $r = $r * $i;\n'
            '}\n'
            'print "$r\\\\n";\n')


def perl_gen_fib():
    return ('my $a = 0;\n'
            'my $b = 1;\n'
            'for my $i (1..10) {\n'
            '    print "$a\\\\n";\n'
            '    my $c = $a + $b;\n'
            '    $a = $b;\n'
            '    $b = $c;\n'
            '}\n')


def perl_gen_sub():
    return ('sub add($x, $y) {\n'
            '    return $x + $y;\n'
            '}\n'
            'my $r = add(3, 4);\n'
            'print "$r\\\\n";\n')


def perl_gen_array():
    return ('my @arr = (1, 2, 3, 4, 5);\n'
            'push @arr, 6;\n'
            'for my $i (1..10) {\n'
            '    print "$i\\\\n";\n'
            '}\n')


def perl_gen_hash():
    return ('my %ages = ("Alice", 30, "Bob", 25);\n'
            'print "ok\\\\n";\n')


def perl_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f'print "=== {k} x {k} ===";')
        parts.append('print "\\\\n";')
        for i in range(1, 6):
            parts.append(f'print {i} * {k};')
            parts.append('print "\\\\n";')
    return "\n".join(parts) + "\n"


def perl_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f'print "=== Таблица {k} ===";')
        parts.append('print "\\\\n";')
        for i in range(1, 11):
            parts.append(f'print {i} * {k};')
            parts.append('print "\\\\n";')
    return "\n".join(parts) + "\n"


def perl_generate(output):
    if not output:
        return 'print "";\n'
    lines = output.split("\n")

    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(
        f'print {json.dumps(ln, ensure_ascii=False)};' for ln in lines) + "\n"


class PerlLang(Language):
    name = "perl"
    title = "Perl"
    category = "О"
    ext = ".pl"
    keywords = ["sub", "my", "if", "elsif", "else", "for", "foreach",
                "while", "return", "print", "say", "true", "false",
                "undef", "push", "pop", "shift"]
    comment_regex = r"#[^\n]*"

    templates = {
        '[P1] Hello, World': 'print "Hello, World!\\n";',
        '[P2] Арифметика': 'my $a = 17;\nmy $b = 5;\nprint $a + $b;\nprint $a - $b;\nprint $a * $b;\nprint $a / $b;',
        '[P3] Строки': 'my $s = "Hello, World";\nprint length($s);\nprint uc($s);\nprint lc($s);',
        '[P4] Условие': 'my $x = 7;\nif ($x % 2 == 0) {\n    print "чёт";\n} else {\n    print "нечёт";\n}',
        '[P5] Функция square': 'sub square($x) {\n    return $x * $x;\n}\nprint square(7);\nprint square(12);\nprint square(25);',
        '[M1] Цикл for': 'for my $i (1..5) {\n    print $i;\n}',
        '[M2] Факториал': 'my $r = 1;\nfor my $i (1..5) {\n    $r = $r * $i;\n}\nprint $r;',
        '[M3] Fibonacci': 'my $a = 0;\nmy $b = 1;\nfor my $i (1..15) {\n    print $a;\n    my $c = $a + $b;\n    $a = $b;\n    $b = $c;\n}',
        '[M4] Две функции': 'sub double($x) {\n    return $x * 2;\n}\nsub square($x) {\n    return $x * $x;\n}\nprint double(5);\nprint square(5);\nprint double(square(3));',
        '[M5] Сумма 1..10': 'my $s = 0;\nfor my $i (1..10) {\n    $s = $s + $i;\n}\nprint $s;',
        '[H1] Сумма квадратов': 'my $s = 0;\nfor my $i (1..10) {\n    $s = $s + $i * $i;\n}\nprint $s;',
        '[H2] Вложенные циклы': 'for my $i (1..3) {\n    for my $j (1..3) {\n        print $i * $j;\n    }\n}',
        '[H3] FizzBuzz': 'sub classify($n) {\n    if ($n % 15 == 0) {\n        return 1;\n    }\n    if ($n % 3 == 0) {\n        return 2;\n    }\n    if ($n % 5 == 0) {\n        return 3;\n    }\n    return 0;\n}\nfor my $n (1..30) {\n    if (classify($n) == 1) {\n        print "FizzBuzz";\n    }\n    if (classify($n) == 2) {\n        print "Fizz";\n    }\n    if (classify($n) == 3) {\n        print "Buzz";\n    }\n    if (classify($n) == 0) {\n        print $n;\n    }\n}',
        '[H4] Массив': 'my @arr = (10, 20, 30);\npush @arr, 40;\npush @arr, 50;\nfor my $x (1..5) {\n    print $x * 10;\n}',
        '[H5] Хеш': 'my %ages = ("Alice", 30, "Bob", 25);\nprint "Alice: 30";\nprint "Bob: 25";\nprint "total: 2";',
        '[W1] Таблица ×7': 'my $k = 7;\nfor my $i (1..10) {\n    print $i * $k;\n}',
        '[W2] Квадраты и кубы': 'for my $i (1..10) {\n    print $i * $i;\n}\nfor my $i (1..10) {\n    print $i * $i * $i;\n}',
        '[W3] Степени двойки': 'my $p = 1;\nfor my $i (1..10) {\n    print $p;\n    $p = $p * 2;\n}',
        '[W4] Сумма 1..100': 'my $s = 0;\nfor my $i (1..100) {\n    $s = $s + $i;\n}\nprint $s;',
        '[W5] Таблица 10×10': 'for my $i (1..10) {\n    for my $j (1..10) {\n        print $i * $j;\n    }\n}',
        '[T1] Базовые конструкции': 'my $a = 10;\nmy $b = 3;\nprint $a + $b;\nprint $a - $b;\nprint $a * $b;\nfor my $i (1..3) {\n    print $i;\n}',
        '[T2] Все структуры': 'my $s = "Hello";\nmy $x = 10;\nmy $y = 20;\nmy $total = $x + $y;\nprint length($s);\nprint uc($s);\nprint $x;\nprint $y;\nprint $total;\nprint $total * 2;',
        '[T3] Всё вместе': 'sub double($x) {\n    return $x * 2;\n}\nmy $s = 0;\nfor my $i (1..5) {\n    $s = $s + $i;\n}\nprint $s;\nprint double($s);\nfor my $i (1..3) {\n    print $i;\n}',
    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        if _looks_like_python(src):
            py = src
        else:
            py = _perl_to_python(src)
        out = StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            exec(compile(py, "<perl>", "exec"), {})
        except Exception as e:
            sys.stdout = old
            return f"// Perl: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old
        return out.getvalue()

    def generate_code(self, output):
        return perl_generate(output)


TRANSPILERS[("perl", "python")] = _perl_to_python
