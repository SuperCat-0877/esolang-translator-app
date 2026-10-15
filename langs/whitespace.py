# langs/whitespace.py
"""
Whitespace — язык, где код состоит только из пробелов, табов и переводов строк.
"""

from core.base import Language


# ==================================================================
#  ЭНКОДЕР
# ==================================================================
def _ws_label(s):
    bits = ""
    for ch in s:
        bits += format(ord(ch), "08b")
    return bits.replace("0", " ").replace("1", "\t")


def ws_build(prog):
    out = []
    for op in prog:
        name = op[0]
        if name == "push":
            out.append("  ")
            n = op[1]
            out.append(" " if n >= 0 else "\t")
            n = abs(n)
            if n == 0:
                out.append(" ")
            else:
                bits = ""
                while n:
                    bits = ("\t" if (n & 1) else " ") + bits
                    n >>= 1
                out.append(bits)
            out.append("\n")
        elif name == "dup":   out.append(" \n ")
        elif name == "swap":  out.append(" \n\t")
        elif name == "pop":   out.append(" \n\n")
        elif name == "add":   out.append("\t   ")
        elif name == "sub":   out.append("\t  \t")
        elif name == "mul":   out.append("\t  \n")
        elif name == "div":   out.append("\t \t ")
        elif name == "mod":   out.append("\t \t\t")
        elif name == "store": out.append("\t\t ")
        elif name == "load":  out.append("\t\t\t")
        elif name == "mark":  out.append("\n  " + _ws_label(op[1]) + "\n")
        elif name == "call":  out.append("\n \t" + _ws_label(op[1]) + "\n")
        elif name == "jmp":   out.append("\n \n" + _ws_label(op[1]) + "\n")
        elif name == "jz":    out.append("\n\t " + _ws_label(op[1]) + "\n")
        elif name == "jn":    out.append("\n\t\t" + _ws_label(op[1]) + "\n")
        elif name == "ret":   out.append("\n\t\n")
        elif name == "end":   out.append("\n\n\n")
        elif name == "out_c": out.append("\t\n  ")
        elif name == "out_n": out.append("\t\n \t")
        elif name == "in_c":  out.append("\t\n\t ")
        elif name == "in_n":  out.append("\t\n\t\t")
    return "".join(out)


def ws_simple_print(text):
    prog = []
    for ch in text:
        prog.append(("push", ord(ch) & 0xFF))
        prog.append(("out_c",))
    prog.append(("end",))
    return ws_build(prog)


def ws_numbers_1_to_10():
    return ws_build([
        ("push", 1),
        ("mark", "LOOP"),
        ("dup",), ("out_n",),
        ("push", 10), ("out_c",),
        ("push", 1), ("add",),
        ("dup",),
        ("push", 11), ("sub",),
        ("jz", "END"),
        ("jmp", "LOOP"),
        ("mark", "END"),
        ("end",),
    ])


def ws_squares_1_to_10():
    return ws_build([
        ("push", 1),
        ("mark", "LOOP"),
        ("dup",), ("dup",), ("mul",),
        ("out_n",),
        ("push", 10), ("out_c",),
        ("push", 1), ("add",),
        ("dup",),
        ("push", 11), ("sub",),
        ("jz", "END"),
        ("jmp", "LOOP"),
        ("mark", "END"),
        ("end",),
    ])


# ==================================================================
#  ПАРСЕР
# ==================================================================
def _parse(src):
    code = "".join(c for c in src if c in " \t\n")
    instrs = []
    i, n = 0, len(code)

    def parse_number():
        nonlocal i
        sign = 1 if code[i] == " " else -1
        i += 1
        val = 0
        while i < n and code[i] != "\n":
            val = (val << 1) | (1 if code[i] == "\t" else 0)
            i += 1
        i += 1
        return sign * val

    def parse_label():
        nonlocal i
        s = ""
        while i < n and code[i] != "\n":
            s += code[i]
            i += 1
        i += 1
        return s

    while i < n:
        c = code[i]
        if c == " ":
            i += 1
            if i >= n: break
            c2 = code[i]
            if c2 == " ":
                i += 1
                instrs.append(("push", parse_number()))
            elif c2 == "\n":
                i += 1
                if i >= n: break
                c3 = code[i]; i += 1
                if c3 == " ":    instrs.append(("dup",))
                elif c3 == "\t": instrs.append(("swap",))
                elif c3 == "\n": instrs.append(("pop",))
        elif c == "\t":
            i += 1
            if i >= n: break
            c2 = code[i]
            if c2 == " ":
                i += 1
                if i >= n: break
                c3 = code[i]; i += 1
                if c3 == " ":
                    if i >= n: break
                    c4 = code[i]; i += 1
                    if c4 == " ":    instrs.append(("add",))
                    elif c4 == "\t": instrs.append(("sub",))
                    elif c4 == "\n": instrs.append(("mul",))
                elif c3 == "\t":
                    if i >= n: break
                    c4 = code[i]; i += 1
                    if c4 == " ":    instrs.append(("div",))
                    elif c4 == "\t": instrs.append(("mod",))
            elif c2 == "\t":
                i += 1
                if i >= n: break
                c3 = code[i]; i += 1
                if c3 == " ":    instrs.append(("store",))
                elif c3 == "\t": instrs.append(("load",))
            elif c2 == "\n":
                i += 1
                if i >= n: break
                c3 = code[i]; i += 1
                if c3 == " ":
                    if i >= n: break
                    c4 = code[i]; i += 1
                    if c4 == " ":    instrs.append(("out_c",))
                    elif c4 == "\t": instrs.append(("out_n",))
                elif c3 == "\t":
                    if i >= n: break
                    c4 = code[i]; i += 1
                    if c4 == " ":    instrs.append(("in_c",))
                    elif c4 == "\t": instrs.append(("in_n",))
        elif c == "\n":
            i += 1
            if i >= n: break
            c2 = code[i]
            if c2 == " ":
                i += 1
                if i >= n: break
                c3 = code[i]; i += 1
                if c3 == " ":    instrs.append(("mark", parse_label()))
                elif c3 == "\t": instrs.append(("call", parse_label()))
                elif c3 == "\n": instrs.append(("jmp", parse_label()))
            elif c2 == "\t":
                i += 1
                if i >= n: break
                c3 = code[i]; i += 1
                if c3 == " ":    instrs.append(("jz", parse_label()))
                elif c3 == "\t": instrs.append(("jn", parse_label()))
                elif c3 == "\n": instrs.append(("ret",))
            elif c2 == "\n":
                i += 1
                if i >= n: break
                c3 = code[i]; i += 1
                if c3 == "\n": instrs.append(("end",))

    labels = {}
    for idx, ins in enumerate(instrs):
        if ins[0] == "mark":
            labels[ins[1]] = idx
    return instrs, labels


# ==================================================================
#  ИНТЕРПРЕТАТОР
# ==================================================================
def ws_run(src, step_limit=1_000_000, input_data=None):
    instrs, labels = _parse(src)
    stack = []
    heap = {}
    output = []
    _input = list(input_data) if input_data else []
    pc = 0
    call_stack = []
    steps = 0

    while pc < len(instrs):
        steps += 1
        if steps > step_limit:
            raise TimeoutError("Whitespace: превышен лимит шагов")
        op = instrs[pc][0]

        if op == "push":   stack.append(instrs[pc][1])
        elif op == "dup":
            if not stack: break
            stack.append(stack[-1])
        elif op == "swap":
            if len(stack) < 2: break
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif op == "pop":
            if not stack: break
            stack.pop()
        elif op == "add":
            if len(stack) < 2: break
            a = stack.pop(); b = stack.pop(); stack.append(a + b)
        elif op == "sub":
            if len(stack) < 2: break
            a = stack.pop(); b = stack.pop(); stack.append(b - a)
        elif op == "mul":
            if len(stack) < 2: break
            a = stack.pop(); b = stack.pop(); stack.append(a * b)
        elif op == "div":
            if len(stack) < 2: break
            a = stack.pop(); b = stack.pop()
            stack.append(0 if a == 0 else b // a)
        elif op == "mod":
            if len(stack) < 2: break
            a = stack.pop(); b = stack.pop()
            stack.append(0 if a == 0 else b % a)
        elif op == "store":
            if len(stack) < 2: break
            a = stack.pop(); b = stack.pop(); heap[b] = a
        elif op == "load":
            if not stack: break
            a = stack.pop(); stack.append(heap.get(a, 0))
        elif op == "mark":
            pass
        elif op == "call":
            call_stack.append(pc + 1)
            pc = labels.get(instrs[pc][1], len(instrs) - 1)
            continue
        elif op == "jmp":
            pc = labels.get(instrs[pc][1], len(instrs) - 1)
            continue
        elif op == "jz":
            if not stack: break
            if stack.pop() == 0:
                pc = labels.get(instrs[pc][1], len(instrs) - 1)
                continue
        elif op == "jn":
            if not stack: break
            if stack.pop() < 0:
                pc = labels.get(instrs[pc][1], len(instrs) - 1)
                continue
        elif op == "ret":
            if call_stack:
                pc = call_stack.pop()
                continue
        elif op == "end":
            break
        elif op == "out_c":
            if not stack: break
            output.append(chr(stack.pop() % 256))
        elif op == "out_n":
            if not stack: break
            output.append(str(stack.pop()))
        elif op == "in_c":
            stack.append(ord(_input.pop(0)) if _input else 0)
        elif op == "in_n":
            stack.append(int(_input.pop(0)) if _input else 0)

        pc += 1

    return "".join(output)


# ==================================================================
#  КЛАСС ЯЗЫКА
# ==================================================================
class WhitespaceLang(Language):
    name = "whitespace"
    title = "Whitespace"
    category = "Э"
    ext = ".ws"
    templates = {}

    def __init__(self):
        pangram = ("The quick brown fox jumps over the lazy dog. " * 2)

        long_text = (
                        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
                        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
                    ) * 2

        self.templates = {

            '[1] Hello, World': '   \t  \t   \n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t \t\t  \n\t\n     \t     \n\t\n     \t \t \t\t\t\n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t\t \t\t  \n\t\n     \t\t  \t  \n\t\n     \t    \t\n\t\n  \n\n\n',

            '[2] Буква A': '   \t     \t\n\t\n  \n\n\n',

            '[3] Цифры 0-9': '   \t\t    \n\t\n     \t\t   \t\n\t\n     \t\t  \t \n\t\n     \t\t  \t\t\n\t\n     \t\t \t  \n\t\n     \t\t \t \t\n\t\n     \t\t \t\t \n\t\n     \t\t \t\t\t\n\t\n     \t\t\t   \n\t\n     \t\t\t  \t\n\t\n  \n\n\n',

            '[4] Hi!': '   \t  \t   \n\t\n     \t\t \t  \t\n\t\n     \t    \t\n\t\n  \n\n\n',

            '[5] Short': '   \t     \t\n\t\n     \t    \t \n\t\n     \t    \t\t\n\t\n  \n\n\n',

            '[6] Алфавит A-J': '   \t     \t\n\t\n     \t    \t \n\t\n     \t    \t\t\n\t\n     \t   \t  \n\t\n     \t   \t \t\n\t\n     \t   \t\t \n\t\n     \t   \t\t\t\n\t\n     \t  \t   \n\t\n     \t  \t  \t\n\t\n     \t  \t \t \n\t\n  \n\n\n',

            '[7] Esolang': '   \t   \t \t\n\t\n     \t\t\t  \t\t\n\t\n     \t\t \t\t\t\t\n\t\n     \t\t \t\t  \n\t\n     \t\t    \t\n\t\n     \t\t \t\t\t \n\t\n     \t\t  \t\t\t\n\t\n  \n\n\n',

            '[8] LOL': '   \t  \t\t  \n\t\n     \t  \t\t\t\t\n\t\n     \t  \t\t  \n\t\n  \n\n\n',

            '[9] ABC': '   \t     \t\n\t\n     \t    \t \n\t\n     \t    \t\t\n\t\n  \n\n\n',

            '[10] XYZ': '   \t \t\t   \n\t\n     \t \t\t  \t\n\t\n     \t \t\t \t \n\t\n  \n\n\n',

            '[11] Длинная': '   \t  \t   \n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t \t\t  \n\t\n     \t     \n\t\n     \t \t \t\t\t\n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t\t \t\t  \n\t\n     \t\t  \t  \n\t\n     \t    \t\n\t\n     \t     \n\t\n     \t \t \t\t\t\n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t  \n\t\n     \t\t   \t\t\n\t\n     \t\t \t\t\t\t\n\t\n     \t\t \t\t \t\n\t\n     \t\t  \t \t\n\t\n     \t    \t\n\t\n  \n\n\n',

            '[12] Fox': '   \t \t \t  \n\t\n     \t\t \t   \n\t\n     \t\t  \t \t\n\t\n     \t     \n\t\n     \t\t\t   \t\n\t\n     \t\t\t \t \t\n\t\n     \t\t \t  \t\n\t\n     \t\t   \t\t\n\t\n     \t\t \t \t\t\n\t\n     \t     \n\t\n     \t\t   \t \n\t\n     \t\t\t  \t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t \t\t\t\n\t\n     \t\t \t\t\t \n\t\n     \t     \n\t\n     \t\t  \t\t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t\t   \n\t\n  \n\n\n',

            '[13] Lorem': '   \t  \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t     \n\t\n     \t\t \t  \t\n\t\n     \t\t\t    \n\t\n     \t\t\t  \t\t\n\t\n     \t\t\t \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t     \n\t\n     \t\t  \t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t     \n\t\n     \t\t\t  \t\t\n\t\n     \t\t \t  \t\n\t\n     \t\t\t \t  \n\t\n  \n\n\n',

            '[14] Mix': '   \t     \t\n\t\n     \t    \t \n\t\n     \t    \t\t\n\t\n     \t\t    \t\n\t\n     \t\t   \t \n\t\n     \t\t   \t\t\n\t\n     \t\t   \t\n\t\n     \t\t  \t \n\t\n     \t\t  \t\t\n\t\n     \t    \t\n\t\n  \n\n\n',

            '[15] Symbols': '   \t    \t\n\t\n     \t      \n\t\n     \t   \t\t\n\t\n     \t  \t  \n\t\n     \t  \t \t\n\t\n     \t \t\t\t\t \n\t\n     \t  \t\t \n\t\n     \t \t \t \n\t\n     \t \t   \n\t\n     \t \t  \t\n\t\n  \n\n\n',

            '[16] AZ+az': '   \t     \t\n\t\n     \t    \t \n\t\n     \t    \t\t\n\t\n     \t   \t  \n\t\n     \t   \t \t\n\t\n     \t   \t\t \n\t\n     \t   \t\t\t\n\t\n     \t  \t   \n\t\n     \t  \t  \t\n\t\n     \t  \t \t \n\t\n     \t  \t \t\t\n\t\n     \t  \t\t  \n\t\n     \t  \t\t \t\n\t\n     \t  \t\t\t \n\t\n     \t  \t\t\t\t\n\t\n     \t \t    \n\t\n     \t \t   \t\n\t\n     \t \t  \t \n\t\n     \t \t  \t\t\n\t\n     \t \t \t  \n\t\n     \t \t \t \t\n\t\n     \t \t \t\t \n\t\n     \t \t \t\t\t\n\t\n     \t \t\t   \n\t\n     \t \t\t  \t\n\t\n     \t \t\t \t \n\t\n     \t\t    \t\n\t\n     \t\t   \t \n\t\n     \t\t   \t\t\n\t\n     \t\t  \t  \n\t\n     \t\t  \t \t\n\t\n     \t\t  \t\t \n\t\n     \t\t  \t\t\t\n\t\n     \t\t \t   \n\t\n     \t\t \t  \t\n\t\n     \t\t \t \t \n\t\n     \t\t \t \t\t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t \t\n\t\n     \t\t \t\t\t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t    \n\t\n     \t\t\t   \t\n\t\n     \t\t\t  \t \n\t\n     \t\t\t  \t\t\n\t\n     \t\t\t \t  \n\t\n     \t\t\t \t \t\n\t\n     \t\t\t \t\t \n\t\n     \t\t\t \t\t\t\n\t\n     \t\t\t\t   \n\t\n     \t\t\t\t  \t\n\t\n     \t\t\t\t \t \n\t\n  \n\n\n',

            '[17] Digital': '   \t\t    \n\t\n     \t\t   \t\n\t\n     \t\t  \t \n\t\n     \t\t  \t\t\n\t\n     \t\t \t  \n\t\n     \t\t \t \t\n\t\n     \t\t \t\t \n\t\n     \t\t \t\t\t\n\t\n     \t\t\t   \n\t\n     \t\t\t  \t\n\t\n     \t    \t\n\t\n     \t      \n\t\n     \t   \t\t\n\t\n  \n\n\n',

            '[18] Pan x1': '   \t \t \t  \n\t\n     \t\t \t   \n\t\n     \t\t  \t \t\n\t\n     \t     \n\t\n     \t\t\t   \t\n\t\n     \t\t\t \t \t\n\t\n     \t\t \t  \t\n\t\n     \t\t   \t\t\n\t\n     \t\t \t \t\t\n\t\n     \t     \n\t\n     \t\t   \t \n\t\n     \t\t\t  \t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t \t\t\t\n\t\n     \t\t \t\t\t \n\t\n     \t     \n\t\n     \t\t  \t\t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t\t   \n\t\n     \t     \n\t\n     \t\t \t \t \n\t\n     \t\t\t \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t\t\t    \n\t\n     \t\t\t  \t\t\n\t\n     \t     \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t \t\t \n\t\n     \t\t  \t \t\n\t\n     \t\t\t  \t \n\t\n     \t     \n\t\n     \t\t\t \t  \n\t\n     \t\t \t   \n\t\n     \t\t  \t \t\n\t\n     \t     \n\t\n     \t\t \t\t  \n\t\n     \t\t    \t\n\t\n     \t\t\t\t \t \n\t\n     \t\t\t\t  \t\n\t\n     \t     \n\t\n     \t\t  \t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t  \t\t\t\n\t\n     \t \t\t\t \n\t\n  \n\n\n',

            '[19] Hello+': '   \t  \t   \n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t \t\t  \n\t\n     \t     \n\t\n     \t \t \t\t\t\n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t\t \t\t  \n\t\n     \t\t  \t  \n\t\n     \t    \t\n\t\n     \t     \n\t\n     \t  \t   \n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t \t\t  \n\t\n     \t     \n\t\n     \t \t \t\t\t\n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t\t \t\t  \n\t\n     \t\t  \t  \n\t\n     \t    \t\n\t\n  \n\n\n',

            '[20] Numbers': '   \t\t   \t\n\t\n     \t\t  \t \n\t\n     \t\t  \t\t\n\t\n     \t\t \t  \n\t\n     \t\t \t \t\n\t\n     \t\t \t\t \n\t\n     \t\t \t\t\t\n\t\n     \t\t\t   \n\t\n     \t\t\t  \t\n\t\n     \t\t    \n\t\n  \n\n\n',

            '[Test 1] Панграмма x2': '   \t \t \t  \n\t\n     \t\t \t   \n\t\n     \t\t  \t \t\n\t\n     \t     \n\t\n     \t\t\t   \t\n\t\n     \t\t\t \t \t\n\t\n     \t\t \t  \t\n\t\n     \t\t   \t\t\n\t\n     \t\t \t \t\t\n\t\n     \t     \n\t\n     \t\t   \t \n\t\n     \t\t\t  \t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t \t\t\t\n\t\n     \t\t \t\t\t \n\t\n     \t     \n\t\n     \t\t  \t\t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t\t   \n\t\n     \t     \n\t\n     \t\t \t \t \n\t\n     \t\t\t \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t\t\t    \n\t\n     \t\t\t  \t\t\n\t\n     \t     \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t \t\t \n\t\n     \t\t  \t \t\n\t\n     \t\t\t  \t \n\t\n     \t     \n\t\n     \t\t\t \t  \n\t\n     \t\t \t   \n\t\n     \t\t  \t \t\n\t\n     \t     \n\t\n     \t\t \t\t  \n\t\n     \t\t    \t\n\t\n     \t\t\t\t \t \n\t\n     \t\t\t\t  \t\n\t\n     \t     \n\t\n     \t\t  \t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t  \t\t\t\n\t\n     \t \t\t\t \n\t\n     \t     \n\t\n     \t \t \t  \n\t\n     \t\t \t   \n\t\n     \t\t  \t \t\n\t\n     \t     \n\t\n     \t\t\t   \t\n\t\n     \t\t\t \t \t\n\t\n     \t\t \t  \t\n\t\n     \t\t   \t\t\n\t\n     \t\t \t \t\t\n\t\n     \t     \n\t\n     \t\t   \t \n\t\n     \t\t\t  \t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t \t\t\t\n\t\n     \t\t \t\t\t \n\t\n     \t     \n\t\n     \t\t  \t\t \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t\t   \n\t\n     \t     \n\t\n     \t\t \t \t \n\t\n     \t\t\t \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t\t\t    \n\t\n     \t\t\t  \t\t\n\t\n     \t     \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t \t\t \n\t\n     \t\t  \t \t\n\t\n     \t\t\t  \t \n\t\n     \t     \n\t\n     \t\t\t \t  \n\t\n     \t\t \t   \n\t\n     \t\t  \t \t\n\t\n     \t     \n\t\n     \t\t \t\t  \n\t\n     \t\t    \t\n\t\n     \t\t\t\t \t \n\t\n     \t\t\t\t  \t\n\t\n     \t     \n\t\n     \t\t  \t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t  \t\t\t\n\t\n     \t \t\t\t \n\t\n     \t     \n\t\n  \n\n\n',

            '[Test 2] Lorem x2': '   \t  \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t     \n\t\n     \t\t \t  \t\n\t\n     \t\t\t    \n\t\n     \t\t\t  \t\t\n\t\n     \t\t\t \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t     \n\t\n     \t\t  \t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t     \n\t\n     \t\t\t  \t\t\n\t\n     \t\t \t  \t\n\t\n     \t\t\t \t  \n\t\n     \t     \n\t\n     \t\t    \t\n\t\n     \t\t \t\t \t\n\t\n     \t\t  \t \t\n\t\n     \t\t\t \t  \n\t\n     \t \t\t\t \n\t\n     \t     \n\t\n     \t  \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t     \n\t\n     \t\t \t  \t\n\t\n     \t\t\t    \n\t\n     \t\t\t  \t\t\n\t\n     \t\t\t \t \t\n\t\n     \t\t \t\t \t\n\t\n     \t     \n\t\n     \t\t  \t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t\t\t  \t \n\t\n     \t     \n\t\n     \t\t\t  \t\t\n\t\n     \t\t \t  \t\n\t\n     \t\t\t \t  \n\t\n     \t     \n\t\n     \t\t    \t\n\t\n     \t\t \t\t \t\n\t\n     \t\t  \t \t\n\t\n     \t\t\t \t  \n\t\n     \t \t\t\t \n\t\n     \t     \n\t\n  \n\n\n',

            '[Test 3] Всё вместе': '   \t  \t   \n\t\n     \t\t  \t \t\n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t  \n\t\n     \t\t \t\t\t\t\n\t\n     \t    \t\n\t\n     \t     \n\t\n     \t     \t\n\t\n     \t    \t \n\t\n     \t    \t\t\n\t\n     \t   \t  \n\t\n     \t   \t \t\n\t\n     \t   \t\t \n\t\n     \t   \t\t\t\n\t\n     \t  \t   \n\t\n     \t  \t  \t\n\t\n     \t  \t \t \n\t\n     \t     \n\t\n     \t\t    \n\t\n     \t\t   \t\n\t\n     \t\t  \t \n\t\n     \t\t  \t\t\n\t\n     \t\t \t  \n\t\n     \t\t \t \t\n\t\n     \t\t \t\t \n\t\n     \t\t \t\t\t\n\t\n     \t\t\t   \n\t\n     \t\t\t  \t\n\t\n     \t     \n\t\n     \t    \t\n\t\n     \t      \n\t\n     \t   \t\t\n\t\n     \t  \t  \n\t\n  \n\n\n',

        }

    def execute(self, src, input_data=None):
        if not src:
            return ""
        # Важно: НЕЛЬЗЯ использовать src.strip() — вся программа состоит
        # из пробельных символов, и strip() удалит её целиком.
        try:
            return ws_run(src, input_data=input_data)
        except TimeoutError:
            return "// Whitespace: превышен лимит шагов"
        except Exception as e:
            return f"// Whitespace: {type(e).__name__}: {e}"

    def generate_code(self, output):
        return ws_simple_print(output)

    # ==================================================================
    #  Whitespace → Python (настоящий линейный транспайлер)
    # ==================================================================
    def _ws_to_python(src):
        """Строит Python-код: стек + эмуляция PC."""
        instrs, labels = _parse(src)
        label_addr = {name: str(idx) for name, idx in labels.items()}

        lines = [
            "_s = []",
            "_h = {}",
            "_out = []",
            "_pc = 0",
            "_cs = []",
            "while True:",
        ]

        if not instrs:
            lines.append("    break")
            lines.append("print(''.join(_out), end='')")
            return "\n".join(lines) + "\n"

        for i, ins in enumerate(instrs):
            op = ins[0]
            lines.append(f"    if _pc == {i}:")
            pad = "        "

            if op == "push":
                lines.append(pad + f"_s.append({ins[1]})")
            elif op == "dup":
                lines.append(pad + "_s.append(_s[-1] if _s else 0)")
            elif op == "swap":
                lines.append(pad + "(_a, _b) = (_s.pop(), _s.pop()); _s.append(_a); _s.append(_b)")
            elif op == "pop":
                lines.append(pad + "if _s: _s.pop()")
            elif op == "add":
                lines.append(pad + "_a, _b = _s.pop(), _s.pop(); _s.append(_a + _b)")
            elif op == "sub":
                lines.append(pad + "_a, _b = _s.pop(), _s.pop(); _s.append(_b - _a)")
            elif op == "mul":
                lines.append(pad + "_a, _b = _s.pop(), _s.pop(); _s.append(_a * _b)")
            elif op == "div":
                lines.append(pad + "_a, _b = _s.pop(), _s.pop(); _s.append(0 if _a == 0 else _b // _a)")
            elif op == "mod":
                lines.append(pad + "_a, _b = _s.pop(), _s.pop(); _s.append(0 if _a == 0 else _b % _a)")
            elif op == "store":
                lines.append(pad + "_a, _b = _s.pop(), _s.pop(); _h[_b] = _a")
            elif op == "load":
                lines.append(pad + "_a = _s.pop(); _s.append(_h.get(_a, 0))")
            elif op == "mark":
                lines.append(pad + "pass")
            elif op == "call":
                lines.append(pad + f"_cs.append(_pc + 1); _pc = {label_addr.get(ins[1], 0)}; continue")
            elif op == "jmp":
                lines.append(pad + f"_pc = {label_addr.get(ins[1], 0)}; continue")
            elif op == "jz":
                lines.append(pad + "if (_s.pop() if _s else 0) == 0:")
                lines.append(pad + f"    _pc = {label_addr.get(ins[1], 0)}")
                lines.append(pad + "    continue")
            elif op == "jn":
                lines.append(pad + "if (_s.pop() if _s else 0) < 0:")
                lines.append(pad + f"    _pc = {label_addr.get(ins[1], 0)}")
                lines.append(pad + "    continue")
            elif op == "ret":
                lines.append(pad + "if _cs:")
                lines.append(pad + "    _pc = _cs.pop()")
                lines.append(pad + "    continue")
                lines.append(pad + "else: break")
            elif op == "end":
                lines.append(pad + "break")
            elif op == "out_c":
                lines.append(pad + "_out.append(chr(_s.pop() & 0xFF) if _s else '\\x00')")
            elif op == "out_n":
                lines.append(pad + "_out.append(str(_s.pop()) if _s else '0')")
            elif op == "in_c":
                lines.append(pad + "_s.append(0)")
            elif op == "in_n":
                lines.append(pad + "_s.append(0)")

            lines.append(pad + "_pc += 1")

        lines.append("print(''.join(_out), end='')")
        return "\n".join(lines) + "\n"

    try:
        from core.translate import TRANSPILERS
        TRANSPILERS[("whitespace", "python")] = _ws_to_python
    except Exception:
        pass
