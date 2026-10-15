# core/ir_generators.py
"""IR → код языка."""
from .ir import (
    Program, Assign, Print, ForLoop, While,
    Num, Str, Var, BinOp, Compare, UnsupportedConstruct,
)


def gen_expr(expr, lang):
    if isinstance(expr, Num):
        return str(expr.value)
    if isinstance(expr, Str):
        return f'"{expr.value}"'
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, BinOp):
        return f"{gen_expr(expr.left, lang)} {expr.op} {gen_expr(expr.right, lang)}"
    if isinstance(expr, Compare):
        return f"{gen_expr(expr.left, lang)} {expr.op} {gen_expr(expr.right, lang)}"
    raise UnsupportedConstruct(f"выражение: {expr!r}")


def _ind(level):
    return "    " * level


def _assign_line(lang, ind, n, v):
    if lang == "python":     return f"{ind}{n} = {v}"
    if lang == "go":         return f"{ind}{n} := {v}"
    if lang in ("kotlin", "scala"): return f"{ind}val {n} = {v}"
    if lang == "fsharp":     return f"{ind}let {n} = {v}"
    if lang == "elixir":     return f"{ind}{n} = {v}"
    if lang == "lua":        return f"{ind}{n} = {v}"
    if lang == "ruby":       return f"{ind}{n} = {v}"
    if lang == "perl":       return f"{ind}my ${n} = {v};"
    if lang == "php":        return f"{ind}${n} = {v};"
    if lang == "rust":       return f"{ind}let mut {n} = {v};"
    if lang == "swift":      return f"{ind}var {n} = {v}"
    if lang == "js":         return f"{ind}let {n} = {v};"
    if lang == "dart":       return f"{ind}var {n} = {v};"
    if lang in ("cpp","c","java","csharp"): return f"{ind}int {n} = {v};"
    raise UnsupportedConstruct(lang)


def _reassign_line(lang, ind, n, v):
    if lang == "php":  return f"{ind}${n} = {v};"
    if lang == "perl": return f"{ind}${n} = {v};"
    if lang in ("go","rust","cpp","c","java","csharp"): return f"{ind}{n} = {v};"
    if lang == "swift": return f"{ind}{n} = {v}"
    if lang in ("js","dart"): return f"{ind}{n} = {v};"
    return f"{ind}{n} = {v}"


def _print_line(lang, ind, e, expr):
    if lang == "python":  return f"{ind}print({e})"
    if lang == "go":      return f"{ind}fmt.Println({e})"
    if lang in ("kotlin","scala"): return f"{ind}println({e})"
    if lang == "fsharp":  return f'{ind}printfn "%d" ({e})'
    if lang == "elixir":  return f"{ind}IO.puts({e})"
    if lang == "lua":     return f"{ind}print({e})"
    if lang == "ruby":    return f"{ind}puts {e}"
    if lang == "perl":    return f"{ind}print {e};"
    if lang == "php":     return f"{ind}echo {e};"
    if lang == "rust":    return f'{ind}println!("{{}}", {e});'
    if lang == "swift":   return f"{ind}print({e})"
    if lang == "js":      return f"{ind}console.log({e});"
    if lang == "dart":    return f"{ind}print({e});"
    if lang in ("cpp","c"):
        if isinstance(expr, Str): return f'{ind}cout << "{expr.value}" << endl;'
        return f"{ind}cout << {e} << endl;"
    if lang == "java":    return f"{ind}System.out.println({e});"
    if lang == "csharp":  return f"{ind}Console.WriteLine({e});"
    raise UnsupportedConstruct(lang)


def gen_stmt(stmt, lang, level=0, in_loop=False):
    ind = _ind(level)

    if isinstance(stmt, Assign):
        v = gen_expr(stmt.value, lang)
        return [_reassign_line(lang, ind, stmt.name, v) if in_loop
                else _assign_line(lang, ind, stmt.name, v)]

    if isinstance(stmt, Print):
        e = gen_expr(stmt.expr, lang)
        return [_print_line(lang, ind, e, stmt.expr)]

    if isinstance(stmt, ForLoop):
        return _gen_for(stmt, lang, level)

    if isinstance(stmt, While):
        return _gen_while(stmt, lang, level)

    raise UnsupportedConstruct(f"узел: {stmt!r}")


def _gen_for(stmt, lang, level):
    ind = _ind(level)
    var = stmt.var
    start = gen_expr(stmt.start, lang)
    end = gen_expr(stmt.end, lang)
    out = []

    def body_lines():
        res = []
        for s in stmt.body:
            res += gen_stmt(s, lang, level + 1, in_loop=True)
        return res

    if lang == "python":
        e = int(stmt.end.value) + 1 if isinstance(stmt.end, Num) else f"{end} + 1"
        out.append(f"{ind}for {var} in range({start}, {e}):")
        out += body_lines()
        return out
    if lang == "go":
        out.append(f"{ind}for {var} := {start}; {var} <= {end}; {var}++ {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang in ("kotlin","scala"):
        out.append(f"{ind}for ({var} in {start}..{end}) {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang == "fsharp":
        out.append(f"{ind}for {var} in {start}..{end} do")
        out += body_lines()
        return out
    if lang == "elixir":
        out.append(f"{ind}for {var} <- {start}..{end} do")
        out += body_lines()
        out.append(f"{ind}end")
        return out
    if lang == "lua":
        out.append(f"{ind}for {var} = {start}, {end} do")
        out += body_lines()
        out.append(f"{ind}end")
        return out
    if lang == "ruby":
        out.append(f"{ind}for {var} in {start}..{end} do")
        out += body_lines()
        out.append(f"{ind}end")
        return out
    if lang == "perl":
        out.append(f"{ind}for my ${var} ({start}..{end}) {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang == "php":
        out.append(f"{ind}for (${var} = {start}; ${var} <= {end}; ${var}++) {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang == "rust":
        out.append(f"{ind}for {var} in {start}..={end} {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang == "swift":
        out.append(f"{ind}for {var} in {start}...{end} {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang == "js":
        out.append(f"{ind}for (let {var} = {start}; {var} <= {end}; {var}++) {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang == "dart":
        out.append(f"{ind}for (var {var} = {start}; {var} <= {end}; {var}++) {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang in ("cpp","c","java","csharp"):
        out.append(f"{ind}for (int {var} = {start}; {var} <= {end}; {var}++) {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    raise UnsupportedConstruct(lang)


def _gen_while(stmt, lang, level):
    ind = _ind(level)
    cond = gen_expr(stmt.cond, lang)
    out = []

    def body_lines():
        res = []
        for s in stmt.body:
            res += gen_stmt(s, lang, level + 1, in_loop=True)
        return res

    if lang == "python":
        out.append(f"{ind}while {cond}:")
        out += body_lines()
        return out
    if lang in ("go",):
        out.append(f"{ind}for {cond} {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang in ("kotlin","scala","js","dart","rust","swift","java","csharp","cpp","c","php","perl"):
        out.append(f"{ind}while ({cond}) {{")
        out += body_lines()
        out.append(f"{ind}}}")
        return out
    if lang == "lua":
        out.append(f"{ind}while {cond} do")
        out += body_lines()
        out.append(f"{ind}end")
        return out
    if lang == "ruby":
        out.append(f"{ind}while {cond} do")
        out += body_lines()
        out.append(f"{ind}end")
        return out
    if lang == "fsharp":
        out.append(f"{ind}while {cond} do")
        out += body_lines()
        return out
    if lang == "elixir":
        out.append(f"{ind}while {cond} do")
        out += body_lines()
        out.append(f"{ind}end")
        return out
    raise UnsupportedConstruct(lang)


def gen_any(lang, prog):
    body = []
    for stmt in prog.body:
        body += gen_stmt(stmt, lang, 0)

    if lang == "python": return "\n".join(body) + "\n"
    if lang == "go":
        return ("package main\n\nimport \"fmt\"\n\nfunc main() {\n"
                + _indent_block(body, 1) + "\n}\n")
    if lang == "kotlin":
        return "fun main() {\n" + _indent_block(body, 1) + "\n}\n"
    if lang == "scala":
        return "object Main {\n    def main(args: Array[String]): Unit = {\n" \
            + _indent_block(body, 2) + "\n    }\n}\n"
    if lang in ("fsharp","elixir","lua","ruby","perl","swift","js"):
        return "\n".join(body) + "\n"
    if lang == "php":
        return "<?php\n" + "\n".join(body) + "\n?>\n"
    if lang == "rust":
        return "fn main() {\n" + _indent_block(body, 1) + "\n}\n"
    if lang == "dart":
        return "void main() {\n" + _indent_block(body, 1) + "\n}\n"
    if lang in ("cpp","c"):
        return ("#include <iostream>\nusing namespace std;\n\n"
                "int main() {\n" + _indent_block(body, 1)
                + "\n    return 0;\n}\n")
    if lang == "java":
        return ("public class Main {\n"
                "    public static void main(String[] args) {\n"
                + _indent_block(body, 2) + "\n    }\n}\n")
    if lang == "csharp":
        return ("using System;\n\nclass Program {\n"
                "    static void Main() {\n"
                + _indent_block(body, 2) + "\n    }\n}\n")
    raise UnsupportedConstruct(f"нет генератора для {lang!r}")


def _indent_block(lines, level):
    ind = "    " * level
    return "\n".join(ind + l for l in lines)
