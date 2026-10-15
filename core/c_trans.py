# core/c_trans.py
"""
C++ → Python (минимальный транспайлер для CppLang.execute()).

Понимает:
  • int main() { ... } — отбрасывает обёртку
  • int name(args) { ... } — превращает в def
  • for (int i = A; i < B; i++) { ... }
  • for (auto x : coll) { ... }
  • while (cond) { ... }
  • if / else if / else
  • return expr;
  • std::cout << ... << std::endl;
  • std::vector<int> v = {...};
  • int/auto/string x = ...;
  • x = ...;  x += ...; и т.д.
"""

import re


# ------------------------------------------------------------------
#  C++-выражение → Python
# ------------------------------------------------------------------
def _cpp_expr_to_py(expr):
    e = expr.strip()

    # литералы
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\bnullptr\b", "None", e)
    e = re.sub(r"\bNULL\b", "None", e)

    # std::to_string(x) → str(x)
    e = re.sub(r"\bstd::to_string\(([^)]+)\)", r"str(\1)", e)

    # vector<int> v → v  (внутри выражений не встречается,
    # но на всякий случай)
    e = re.sub(r"std::vector<\w+>\s+(\w+)", r"\1", e)

    # size() / length()
    e = re.sub(r"(\w+)\.size\(\)", r"len(\1)", e)
    e = re.sub(r"(\w+)\.length\(\)", r"len(\1)", e)

    # push_back / pop_back
    e = re.sub(r"(\w+)\.push_back\(([^)]+)\)", r"\1.append(\2)", e)
    e = re.sub(r"(\w+)\.pop_back\(\)", r"\1.pop()", e)

    # std::swap(a, b) → a, b = b, a
    e = re.sub(r"std::swap\((\w+),\s*(\w+)\)", r"\1, \2 = \2, \1", e)

    # математика
    e = re.sub(r"std::floor\(([^)]+)\)", r"int(\1)", e)
    e = re.sub(r"std::ceil\(([^)]+)\)", r"int(\1) + (1 if (\1) % 1 else 0)", e)
    e = re.sub(r"std::sqrt\(([^)]+)\)", r"((\1) ** 0.5)", e)
    e = re.sub(r"std::abs\(([^)]+)\)", r"abs(\1)", e)

    return e


# ------------------------------------------------------------------
#  C++ → Python
# ------------------------------------------------------------------
def cpp_to_python(src):
    lines = src.splitlines()
    out = []
    ind = 0

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # Пропускаем #include, using namespace
        if line.startswith("#include") or line.startswith("using namespace"):
            continue

        # int main() { — пропускаем
        if re.match(r"int\s+main\s*\([^)]*\)\s*\{", line):
            continue

        # --- функция (не main): int name(args) { ---
        m = re.match(r"int\s+(\w+)\s*\(([^)]*)\)\s*\{", line)
        if m and m.group(1) != "main":
            args = ", ".join(
                a.strip().split()[-1]
                for a in m.group(2).split(",")
                if a.strip()
            )
            out.append("    " * ind + f"def {m.group(1)}({args}):")
            ind += 1
            continue

        # --- for (int i = A; i < B; i++) { ---
        m = re.match(
            r"for\s*\(\s*int\s+(\w+)\s*=\s*(-?\d+)\s*;\s*"
            r"\1\s*<\s*(.+?)\s*;\s*\1\+\+\s*\)\s*\{?\s*$",
            line,
        )
        if m:
            v, a, b = m.group(1), m.group(2), m.group(3)
            out.append(
                "    " * ind +
                f"for {v} in range({a}, {_cpp_expr_to_py(b)}):"
            )
            ind += 1
            continue

        # --- for (auto x : coll) { ---
        m = re.match(
            r"for\s*\(\s*auto\s+(\w+)\s*:\s*(\w+)\s*\)\s*\{?\s*$",
            line,
        )
        if m:
            out.append("    " * ind + f"for {m.group(1)} in {m.group(2)}:")
            ind += 1
            continue

        # --- while (cond) { ---
        m = re.match(r"while\s*\((.+?)\)\s*\{?\s*$", line)
        if m:
            out.append("    " * ind + f"while {_cpp_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        # --- if (cond) { ---
        m = re.match(r"if\s*\((.+?)\)\s*\{?\s*$", line)
        if m:
            out.append("    " * ind + f"if {_cpp_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        # --- } else if (cond) { ---
        m = re.match(r"\}\s*else\s+if\s*\((.+?)\)\s*\{?\s*$", line)
        if m:
            ind -= 1
            out.append("    " * ind + f"elif {_cpp_expr_to_py(m.group(1))}:")
            ind += 1
            continue

        # --- } else { ---
        if re.match(r"\}\s*else\s*\{?\s*$", line):
            ind -= 1
            out.append("    " * ind + "else:")
            ind += 1
            continue

        # --- return expr; ---
        m = re.match(r"return\s*(.*?)\s*;?\s*$", line)
        if m:
            val = m.group(1).strip()
            if val == "0" and ind == 0:
                # return 0 в main — пропускаем
                continue
            out.append("    " * ind + f"return {_cpp_expr_to_py(val)}")
            continue

        # --- std::cout << ... << ...; ---
        m = re.match(r"std::cout\s*<<\s*(.+?)\s*;\s*$", line)
        if m:
            parts = [p.strip() for p in m.group(1).split("<<")]
            args = []
            for p in parts:
                if p in ("std::endl", '"\\n"'):
                    continue
                if p.startswith('"') and p.endswith('"'):
                    text = p[1:-1].replace("\\n", "")
                    args.append(repr(text))
                else:
                    args.append(_cpp_expr_to_py(p))
            if not args:
                continue
            if len(args) == 1:
                out.append("    " * ind + f"print({args[0]})")
            else:
                joined = ", ".join(args)
                out.append("    " * ind + f"print({joined})")
            continue

        # --- std::vector<int> v = {...}; ---
        m = re.match(r"std::vector<\w+>\s+(\w+)\s*=\s*\{(.*)\}\s*;", line)
        if m:
            out.append("    " * ind + f"{m.group(1)} = [{m.group(2)}]")
            continue

        # --- int / auto / string x = ...; ---
        m = re.match(
            r"(?:int|long|double|float|auto|std::string|string)\s+"
            r"(\w+)\s*=\s*(.+?)\s*;",
            line,
        )
        if m:
            out.append(
                "    " * ind +
                f"{m.group(1)} = {_cpp_expr_to_py(m.group(2))}"
            )
            continue

        # --- x += ... / x -= ... / x *= ... / x /= ...; ---
        m = re.match(r"(\w+(?:\[[^\]]+\])?)\s*([+\-*/])=\s*(.+?)\s*;", line)
        if m:
            out.append(
                "    " * ind +
                f"{m.group(1)} {m.group(2)}= {_cpp_expr_to_py(m.group(3))}"
            )
            continue

        # --- x = ...; ---
        m = re.match(r"(\w+(?:\[[^\]]+\])?)\s*=\s*(.+?)\s*;", line)
        if m:
            out.append(
                "    " * ind +
                f"{m.group(1)} = {_cpp_expr_to_py(m.group(2))}"
            )
            continue

        # --- методы вектора: v.push_back(x) ---
        m = re.match(r"(\w+)\.push_back\s*\((.*)\)\s*;", line)
        if m:
            out.append(
                "    " * ind +
                f"{m.group(1)}.append({_cpp_expr_to_py(m.group(2))})"
            )
            continue

        # --- v.pop_back() ---
        m = re.match(r"(\w+)\.pop_back\s*\(\s*\)\s*;", line)
        if m:
            out.append("    " * ind + f"{m.group(1)}.pop()")
            continue

        # --- v.clear() ---
        m = re.match(r"(\w+)\.clear\s*\(\s*\)\s*;", line)
        if m:
            out.append("    " * ind + f"{m.group(1)}.clear()")
            continue

        # --- закрывающая } или }; ---
        if re.match(r"^\}\s*;?\s*$", line):
            ind = max(0, ind - 1)
            continue


        # --- вызов функции как оператор: foo(...); ---
        m = re.match(r"(\w+)\s*\((.*)\)\s*;", line)
        if m:
            out.append(
                "    " * ind +
                f"{m.group(1)}({_cpp_expr_to_py(m.group(2))})"
            )
            continue

        # --- всё остальное — комментарий ---
        out.append("    " * ind + f"# C++: не поддержано: {line}")

    return "\n".join(out) + "\n"