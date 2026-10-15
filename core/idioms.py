# core/idioms.py
"""
Соответствия Python → {JS, C++, Lua}:
простая замена методов и функций на ближайшие аналоги целевого языка.
Используется транспайлерами в langs/python_lang.py.
"""

import re


# ==================================================================
#  PYTHON → JAVASCRIPT
# ==================================================================
def py_expr_to_js(e):
    if not e:
        return e

    # --- литералы ---
    e = re.sub(r"\bTrue\b", "true", e)
    e = re.sub(r"\bFalse\b", "false", e)
    e = re.sub(r"\bNone\b", "null", e)
    e = re.sub(r"\band\b", "&&", e)
    e = re.sub(r"\bor\b", "||", e)
    e = re.sub(r"\bnot\b", "!", e)

    # --- встроенные функции ---
    e = re.sub(r"\blen\((\w+)\)", r"\1.length", e)
    e = re.sub(r"\bmin\(([^,()]+),\s*([^,()]+)\)",
               r"Math.min(\1, \2)", e)
    e = re.sub(r"\bmax\(([^,()]+),\s*([^,()]+)\)",
               r"Math.max(\1, \2)", e)
    e = re.sub(r"\babs\(([^)]+)\)", r"Math.abs(\1)", e)
    e = re.sub(r"\bint\(([^)]+)\)", r"Math.floor(\1)", e)
    e = re.sub(r"\bfloat\(([^)]+)\)", r"parseFloat(\1)", e)
    e = re.sub(r"\bstr\(([^)]+)\)", r"String(\1)", e)

    # --- random ---
    e = re.sub(r"random\.seed\([^)]*\)", "0", e)
    e = re.sub(r"random\.randint\(([^,]+),\s*([^)]+)\)",
               r"(Math.floor(Math.random() * ((\2) - (\1) + 1)) + (\1))", e)
    e = re.sub(r"random\.random\(\)", "Math.random()", e)

    # --- методы строк ---
    e = re.sub(r"(\w+)\.lower\(\)", r"\1.toLowerCase()", e)
    e = re.sub(r"(\w+)\.upper\(\)", r"\1.toUpperCase()", e)
    e = re.sub(r"(\w+)\.strip\(\)", r"\1.trim()", e)
    e = re.sub(r"(\w+)\.lstrip\(\)", r"\1.trimStart()", e)
    e = re.sub(r"(\w+)\.rstrip\(\)", r"\1.trimEnd()", e)
    e = re.sub(r"(\w+)\.split\(\)", r"\1.trim().split(/\\s+/)", e)
    e = re.sub(r"(\w+)\.split\(([^)]+)\)", r"\1.split(\2)", e)
    e = re.sub(r"(\w+)\.replace\(([^,]+),\s*([^)]+)\)",
               r"\1.replace(\2, \3)", e)

    # --- join ---
    e = re.sub(r"'([^']*)'\.join\((\w+)\)", r"\2.join('\1')", e)
    e = re.sub(r'"([^"]*)"\.join\((\w+)\)', r"\2.join(\"\1\")", e)

    # --- self → this ---
    e = e.replace("self.", "this.")

    # --- f-строки → template literal ---
    e = re.sub(
        r"f'([^']*)'",
        lambda m: "`" + re.sub(r"\{([^}]+)\}", r"${\1}", m.group(1)) + "`",
        e,
    )
    e = re.sub(
        r'f"([^"]*)"',
        lambda m: "`" + re.sub(r"\{([^}]+)\}", r"${\1}", m.group(1)) + "`",
        e,
    )

    return e


# ==================================================================
#  PYTHON → C++
# ==================================================================
def py_expr_to_cpp(e):
    if not e:
        return e

    e = re.sub(r"\bTrue\b", "true", e)
    e = re.sub(r"\bFalse\b", "false", e)
    e = re.sub(r"\bNone\b", "nullptr", e)
    e = re.sub(r"\band\b", "&&", e)
    e = re.sub(r"\bor\b", "||", e)
    e = re.sub(r"\bnot\b", "!", e)

    e = re.sub(r"\blen\((\w+)\)", r"((int)\1.size())", e)
    e = re.sub(r"\bmin\(([^,()]+),\s*([^,()]+)\)",
               r"std::min(\1, \2)", e)
    e = re.sub(r"\bmax\(([^,()]+),\s*([^,()]+)\)",
               r"std::max(\1, \2)", e)
    e = re.sub(r"\babs\(([^)]+)\)", r"std::abs(\1)", e)
    e = re.sub(r"\bint\(([^)]+)\)", r"((int)(\1))", e)
    e = re.sub(r"\bfloat\(([^)]+)\)", r"((double)(\1))", e)

    e = re.sub(r"random\.seed\(([^)]+)\)", r"std::srand(\1)", e)
    e = re.sub(r"random\.randint\(([^,]+),\s*([^)]+)\)",
               r"(std::rand() % ((\2) - (\1) + 1) + (\1))", e)

    # строковые методы без прямого аналога — оставляем как есть
    e = re.sub(r"(\w+)\.lower\(\)", r"\1", e)
    e = re.sub(r"(\w+)\.upper\(\)", r"\1", e)
    e = re.sub(r"(\w+)\.strip\(\)", r"\1", e)

    e = e.replace("self.", "this->")

    def _fstr(m):
        inner = m.group(1)
        parts = re.split(r"\{([^}]+)\}", inner)
        pieces = []
        for i, p in enumerate(parts):
            if i % 2 == 0:
                if p:
                    pieces.append(f'"{p}"')
            else:
                pieces.append(f"std::to_string({p})")
        return " + ".join(pieces) if pieces else '""'

    e = re.sub(r"f'([^']*)'", _fstr, e)
    e = re.sub(r'f"([^"]*)"', _fstr, e)

    return e


# ==================================================================
#  PYTHON → LUA
# ==================================================================
def py_expr_to_lua(e):
    if not e:
        return e

    e = re.sub(r"\bTrue\b", "true", e)
    e = re.sub(r"\bFalse\b", "false", e)
    e = re.sub(r"\bNone\b", "nil", e)

    e = re.sub(r"\blen\((\w+)\)", r"#\1", e)
    e = re.sub(r"\bmin\(([^,()]+),\s*([^,()]+)\)",
               r"math.min(\1, \2)", e)
    e = re.sub(r"\bmax\(([^,()]+),\s*([^,()]+)\)",
               r"math.max(\1, \2)", e)
    e = re.sub(r"\babs\(([^)]+)\)", r"math.abs(\1)", e)
    e = re.sub(r"\bint\(([^)]+)\)", r"math.floor(\1)", e)

    e = re.sub(r"random\.seed\(([^)]+)\)", r"math.randomseed(\1)", e)
    e = re.sub(r"random\.randint\(([^,]+),\s*([^)]+)\)",
               r"math.random(\1, \2)", e)

    e = re.sub(r"(\w+)\.lower\(\)", r"\1:lower()", e)
    e = re.sub(r"(\w+)\.upper\(\)", r"\1:upper()", e)

    def _fstr(m):
        inner = m.group(1)
        parts = re.split(r"\{([^}]+)\}", inner)
        pieces = []
        for i, p in enumerate(parts):
            if i % 2 == 0:
                if p:
                    pieces.append(f'"{p}"')
            else:
                pieces.append(f"tostring({p})")
        return " .. ".join(pieces) if pieces else '""'

    e = re.sub(r"f'([^']*)'", _fstr, e)
    e = re.sub(r'f"([^"]*)"', _fstr, e)

    return e


# ==================================================================
#  МАППИНГ СТРОК ДЛЯ МЕТОДОВ СПИСКОВ
# ==================================================================
def map_python_line_to_js(line):
    line = re.sub(r"(\w+)\.append\(([^)]*)\)", r"\1.push(\2)", line)
    line = re.sub(r"(\w+)\.pop\(\)", r"\1.pop()", line)
    line = re.sub(r"(\w+)\.extend\(([^)]+)\)", r"\1.push(...\2)", line)
    line = re.sub(r"(\w+)\.insert\(([^,]+),\s*([^)]+)\)",
                  r"\1.splice(\2, 0, \3)", line)
    line = re.sub(r"(\w+)\.remove\(([^)]+)\)",
                  r"\1.splice(\1.indexOf(\2), 1)", line)
    line = re.sub(r"(\w+)\.clear\(\)", r"\1.length = 0", line)
    return line


def map_python_line_to_cpp(line):
    line = re.sub(r"(\w+)\.append\(([^)]*)\)", r"\1.push_back(\2)", line)
    line = re.sub(r"(\w+)\.pop\(\)", r"\1.pop_back()", line)
    line = re.sub(r"(\w+)\.extend\(([^)]+)\)",
                  r"\1.insert(\1.end(), \2.begin(), \2.end())", line)
    line = re.sub(r"(\w+)\.clear\(\)", r"\1.clear()", line)
    return line


def map_python_line_to_lua(line):
    line = re.sub(r"(\w+)\.append\(([^)]*)\)",
                  r"table.insert(\1, \2)", line)
    line = re.sub(r"(\w+)\.pop\(\)", r"table.remove(\1)", line)
    return line