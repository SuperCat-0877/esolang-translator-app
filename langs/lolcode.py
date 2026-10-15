# langs/lolcode.py
"""LOLCODE — эзотерический язык на основе LOLcats."""

import re
from core.base import Language
from core.translate import TRANSPILERS


def _to_num(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return v
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _lolcode_eval(expr, variables):
    if expr is None:
        return None
    e = expr.strip().rstrip(",").rstrip("!?")

    if e.startswith('"') and e.endswith('"'):
        return e[1:-1]
    if e.startswith("'") and e.endswith("'"):
        return e[1:-1]
    if re.match(r"^-?\d+$", e):
        return int(e)

    m = re.match(r"SUM OF (.+?) AN (.+)$", e)
    if m:
        return _to_num(_lolcode_eval(m.group(1), variables)) + \
               _to_num(_lolcode_eval(m.group(2), variables))
    m = re.match(r"DIFF OF (.+?) AN (.+)$", e)
    if m:
        return _to_num(_lolcode_eval(m.group(1), variables)) - \
               _to_num(_lolcode_eval(m.group(2), variables))
    m = re.match(r"PRODUKT OF (.+?) AN (.+)$", e)
    if m:
        return _to_num(_lolcode_eval(m.group(1), variables)) * \
               _to_num(_lolcode_eval(m.group(2), variables))
    m = re.match(r"QUOSHUNT OF (.+?) AN (.+)$", e)
    if m:
        a = _to_num(_lolcode_eval(m.group(1), variables))
        b = _to_num(_lolcode_eval(m.group(2), variables))
        return 0 if b == 0 else a // b
    m = re.match(r"BOTH SAEM (.+?) AN (.+)$", e)
    if m:
        return _lolcode_eval(m.group(1), variables) == \
               _lolcode_eval(m.group(2), variables)
    m = re.match(r"DIFFRINT (.+?) AN (.+)$", e)
    if m:
        return _lolcode_eval(m.group(1), variables) != \
               _lolcode_eval(m.group(2), variables)
    m = re.match(r"BIGGR OF (.+?) AN (.+)$", e)
    if m:
        return max(_to_num(_lolcode_eval(m.group(1), variables)),
                   _to_num(_lolcode_eval(m.group(2), variables)))
    m = re.match(r"SMALLR OF (.+?) AN (.+)$", e)
    if m:
        return min(_to_num(_lolcode_eval(m.group(1), variables)),
                   _to_num(_lolcode_eval(m.group(2), variables)))

    if e == "WIN":
        return True
    if e == "FAIL":
        return False

    if e in variables:
        return variables[e]

    return e


def _lolcode_run(src):
    if not src:
        return ""
    lines = src.splitlines()
    variables = {}
    out = []
    funcs = {}

    def exec_range_lines(lines_sub):
        # Временная подмена содержимого lines для рекурсивного выполнения.
        # Никакого nonlocal не нужно: мы мутируем список на месте,
        # а он захвачен замыканием в exec_range / find_matching.
        saved = list(lines)
        lines[:] = list(lines_sub)
        try:
            exec_range(0, len(lines))
        finally:
            lines[:] = saved

    def find_matching(open_idx, opener, closer):
        depth = 0
        for j in range(open_idx, len(lines)):
            st = lines[j].strip()
            if st == opener:
                depth += 1
            elif st == closer:
                depth -= 1
                if depth == 0:
                    return j
        return len(lines) - 1

    def exec_range(start, end):
        i = start
        while i < end:
            line = lines[i].strip()
            if not line or line.startswith("BTW"):
                i += 1
                continue
            if line.startswith("HAI") or line == "KTHXBYE":
                i += 1
                continue

            # I HAS A var ITZ expr
            m = re.match(r"I HAS A (\w+)(?:\s+ITZ\s+(.+))?$", line)
            if m:
                name = m.group(1)
                val = _lolcode_eval(m.group(2), variables) if m.group(2) else 0
                variables[name] = val
                i += 1
                continue

            # var R expr
            m = re.match(r"(\w+) R (.+)$", line)
            if m:
                variables[m.group(1)] = _lolcode_eval(m.group(2), variables)
                i += 1
                continue

            # VISIBLE
            m = re.match(r"VISIBLE\s+(.+)$", line)
            if m:
                expr = m.group(1).strip()
                parts = re.split(r"\s*\+\s*", expr)
                for p in parts:
                    p = p.strip()
                    if not p:
                        continue
                    if p.startswith('"') and p.endswith('"'):
                        s = p[1:-1].replace('\\"', '"').replace('\\\\', '\\')
                        out.append(s if s else "\n")
                    else:
                        val = _lolcode_eval(p, variables)
                        if isinstance(val, bool):
                            out.append("WIN" if val else "FAIL")
                        else:
                            out.append(str(val) if val is not None else "")
                i += 1
                continue

            # GIMMEH
            m = re.match(r"GIMMEH\s+(\w+)$", line)
            if m:
                variables[m.group(1)] = input()
                i += 1
                continue

            # O RLY? / BOTH SAEM
            m = re.match(r"BOTH SAEM (.+?) AN (.+?),?\s+O RLY\?\s*$", line)
            if m:
                cond = _lolcode_eval(f"BOTH SAEM {m.group(1)} AN {m.group(2)}",
                                     variables)
                # Найти YA RLY / NO WAI / OIC
                j = i + 1
                ya_start = ya_end = no_start = no_end = None
                current = None
                while j < end:
                    sub = lines[j].strip()
                    if sub == "YA RLY":
                        current = "YA"
                        ya_start = j + 1
                    elif sub == "NO WAI":
                        if current == "YA":
                            ya_end = j
                        current = "NO"
                        no_start = j + 1
                    elif sub == "OIC":
                        if current == "YA":
                            ya_end = j
                        elif current == "NO":
                            no_end = j
                        break
                    j += 1
                if cond:
                    if ya_start is not None and ya_end is not None:
                        exec_range(ya_start, ya_end)
                else:
                    if no_start is not None and no_end is not None:
                        exec_range(no_start, no_end)
                i = j + 1
                continue

            # IM IN YR LOOP ... IM OUTTA YR LOOP
            m = re.match(r"IM IN YR (\w+)(?:\s+(UPPIN|NERFIN)\s+YR\s+(\w+))?(?:\s+TIL\s+(.+))?$", line)
            if m:
                loop_var = m.group(3)
                op = m.group(2)
                cond_str = m.group(4)
                # Найти IM OUTTA YR
                j = i + 1
                depth = 0
                body_start = j
                body_end = j
                while j < end:
                    sub = lines[j].strip()
                    if sub.startswith("IM IN YR"):
                        depth += 1
                    elif sub.startswith("IM OUTTA YR"):
                        if depth == 0:
                            body_end = j
                            break
                        depth -= 1
                    j += 1
                # Инициализация
                if loop_var and loop_var not in variables:
                    variables[loop_var] = 0
                for _ in range(1000):
                    exec_range(body_start, body_end)
                    if loop_var:
                        if op == "UPPIN":
                            variables[loop_var] = variables.get(loop_var, 0) + 1
                        elif op == "NERFIN":
                            variables[loop_var] = variables.get(loop_var, 0) - 1
                    if cond_str:
                        cond = _lolcode_eval(cond_str, variables)
                        if not cond:
                            break
                    else:
                        break
                i = j + 1
                continue

            # HOW IZ I <name> <args>
            m = re.match(r"HOW IZ I (\w+)(?:\s+(.+))?$", line)
            if m:
                fname = m.group(1)
                fargs = m.group(2) or ""
                # Сохраняем тело функции до IF U SAY SO
                j = i + 1
                fbody = []
                while j < end:
                    sub = lines[j].strip()
                    if sub == "IF U SAY SO":
                        break
                    fbody.append(lines[j])
                    j += 1
                funcs[fname] = (fargs, fbody)
                i = j + 1
                continue

            # I IZ <name> <args> MKAY
            m = re.match(r"I IZ (\w+)(?:\s+(.+?))?\s*MKAY$", line)
            if m:
                fname = m.group(1)
                call_args = m.group(2) or ""
                if fname in funcs:
                    fargs, fbody = funcs[fname]
                    # Привязываем аргументы
                    arg_names = [a.strip() for a in fargs.split() if a.strip()]
                    call_vals = [_lolcode_eval(a.strip(), variables) for a in call_args.split() if a.strip()]
                    for an, av in zip(arg_names, call_vals):
                        variables[an] = av
                    # Выполняем тело функции
                    exec_range_lines(fbody)
                i += 1
                continue

            i += 1

    exec_range(0, len(lines))
    return "".join(out)


def _lolcode_to_python(src):
    result = _lolcode_run(src)
    return (
        "# LOLCODE → Python (симуляция + вывод)\n"
        f"_out = {result!r}\n"
        "print(_out, end='')\n"
    )


# ==================================================================
#  Генераторы шаблонов
# ==================================================================
def _lolcode_print(text):
    if not text:
        return "HAI 1.2\nKTHXBYE"
    lines = ["HAI 1.2"]
    parts = text.split("\n")
    for i, part in enumerate(parts):
        if part:
            escaped = part.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'VISIBLE "{escaped}"')
        if i < len(parts) - 1:
            lines.append('VISIBLE ""')
    lines.append("KTHXBYE")
    return "\n".join(lines)


def _lolcode_gen_numbers():
    parts = ["HAI 1.2"]
    for i in range(1, 11):
        parts.append(f"VISIBLE {i}")
    parts.append("KTHXBYE")
    return "\n".join(parts)


def _lolcode_gen_squares():
    parts = ["HAI 1.2"]
    for i in range(1, 11):
        parts.append(f"VISIBLE {i * i}")
    parts.append("KTHXBYE")
    return "\n".join(parts)


def _lolcode_gen_cubes():
    parts = ["HAI 1.2"]
    for i in range(1, 11):
        parts.append(f"VISIBLE {i ** 3}")
    parts.append("KTHXBYE")
    return "\n".join(parts)


def _lolcode_gen_table7():
    parts = ["HAI 1.2"]
    for i in range(1, 11):
        parts.append(f"VISIBLE {i * 7}")
    parts.append("KTHXBYE")
    return "\n".join(parts)


def _lolcode_gen_fib():
    parts = ["HAI 1.2"]
    for n in [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]:
        parts.append(f"VISIBLE {n}")
    parts.append("KTHXBYE")
    return "\n".join(parts)


def _lolcode_gen_arith():
    return (
        "HAI 1.2\n"
        "I HAS A X ITZ 5\n"
        "I HAS A Y ITZ 7\n"
        "VISIBLE SUM OF X AN Y\n"
        "KTHXBYE"
    )


def _lolcode_gen_condition():
    return (
        "HAI 1.2\n"
        "I HAS A X ITZ 10\n"
        "BOTH SAEM X AN 10, O RLY?\n"
        "YA RLY\n"
        'VISIBLE "ten"\n'
        "NO WAI\n"
        'VISIBLE "other"\n'
        "OIC\n"
        "KTHXBYE"
    )


def _lolcode_gen_50():
    parts = ["HAI 1.2"]
    for k in range(1, 6):
        parts.append(f'VISIBLE "=== {k} x {k} ==="')
        for i in range(1, 6):
            parts.append(f"VISIBLE {i * k}")
    parts.append("KTHXBYE")
    return "\n".join(parts)


def _lolcode_gen_200():
    parts = ["HAI 1.2"]
    for k in range(2, 8):
        parts.append(f'VISIBLE "=== Таблица {k} ==="')
        for i in range(1, 11):
            parts.append(f"VISIBLE {i * k}")
    parts.append("KTHXBYE")
    return "\n".join(parts)


class LolcodeLang(Language):
    name = "lolcode"
    title = "LOLCODE"
    category = "Э"
    ext = ".lol"
    keywords = [
        "HAI", "KTHXBYE", "VISIBLE", "GIMMEH", "I HAS A", "ITZ",
        "R", "AN", "SUM OF", "DIFF OF", "PRODUKT OF", "QUOSHUNT OF",
        "BOTH SAEM", "DIFFRINT", "BIGGR OF", "SMALLR OF",
        "O RLY?", "YA RLY", "NO WAI", "OIC",
        "IM IN YR", "IM OUTTA YR", "UPPIN", "NERFIN", "YR", "TIL",
        "WIN", "FAIL",
    ]
    types = []
    comment_regex = r"BTW[^\n]*"

    templates = {

        '[1] Hello, World': 'HAI 1.2\nVISIBLE "Hello, World!"\nKTHXBYE',

        '[2] Буква A': 'HAI 1.2\nVISIBLE "A"\nKTHXBYE',

        '[3] Цифры 0-9': 'HAI 1.2\nVISIBLE "0123456789"\nKTHXBYE',

        '[4] Hi!': 'HAI 1.2\nVISIBLE "Hi!"\nKTHXBYE',

        '[5] Short': 'HAI 1.2\nVISIBLE "ABC"\nKTHXBYE',

        '[6] Алфавит A-J': 'HAI 1.2\nVISIBLE "ABCDEFGHIJ"\nKTHXBYE',

        '[7] Esolang': 'HAI 1.2\nVISIBLE "Esolang"\nKTHXBYE',

        '[8] LOL': 'HAI 1.2\nVISIBLE "LOL"\nKTHXBYE',

        '[9] ABC': 'HAI 1.2\nVISIBLE "ABC"\nKTHXBYE',

        '[10] XYZ': 'HAI 1.2\nVISIBLE "XYZ"\nKTHXBYE',

        '[11] Длинная': 'HAI 1.2\nVISIBLE "Hello, World! Welcome!"\nKTHXBYE',

        '[12] Fox': 'HAI 1.2\nVISIBLE "The quick brown fox"\nKTHXBYE',

        '[13] Lorem': 'HAI 1.2\nVISIBLE "Lorem ipsum dolor sit"\nKTHXBYE',

        '[14] Mix': 'HAI 1.2\nVISIBLE "ABCabc123!"\nKTHXBYE',

        '[15] Symbols': 'HAI 1.2\nVISIBLE "!@#$%^&*()"\nKTHXBYE',

        '[16] AZ+az': 'HAI 1.2\nVISIBLE "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"\nKTHXBYE',

        '[17] Digital': 'HAI 1.2\nVISIBLE "0123456789!@#"\nKTHXBYE',

        '[18] Pan x1': 'HAI 1.2\nVISIBLE "The quick brown fox jumps over the lazy dog."\nKTHXBYE',

        '[19] Hello+': 'HAI 1.2\nVISIBLE "Hello, World! Hello, World!"\nKTHXBYE',

        '[20] Numbers': 'HAI 1.2\nVISIBLE "1234567890"\nKTHXBYE',

        '[Test 1] Панграмма x2': 'HAI 1.2\nVISIBLE "The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. "\nKTHXBYE',

        '[Test 2] Lorem x2': 'HAI 1.2\nVISIBLE "Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet. "\nKTHXBYE',

        '[Test 3] Всё вместе': 'HAI 1.2\nVISIBLE "Hello! ABCDEFGHIJ 0123456789 !@#$"\nKTHXBYE',

    }

    def execute(self, src):
        if not src or not src.strip():
            return ""
        try:
            return _lolcode_run(src)
        except Exception as e:
            return f"// LOLCODE: {type(e).__name__}: {e}"

    def generate_code(self, output):
        if not output:
            return 'HAI 1.2\nVISIBLE ""\nKTHXBYE'
        return _lolcode_print(output)


TRANSPILERS[("lolcode", "python")] = _lolcode_to_python
