# core/helpers.py
def run_brainfuck(src, step_limit=10_000_000, out_limit=65536):
    code = [c for c in src if c in '><+-.,[]']
    pairs, stack = {}, []
    for i, c in enumerate(code):
        if c == '[':
            stack.append(i)
        elif c == ']':
            s = stack.pop()
            pairs[s] = i; pairs[i] = s
    tape = [0] * 30000
    ptr = 0; out = []; pc = 0; steps = 0
    while pc < len(code):
        steps += 1
        if steps > step_limit or len(out) > out_limit:
            raise TimeoutError()
        c = code[pc]
        if c == '>': ptr = (ptr + 1) % 30000
        elif c == '<': ptr = (ptr - 1) % 30000
        elif c == '+': tape[ptr] = (tape[ptr] + 1) & 0xFF
        elif c == '-': tape[ptr] = (tape[ptr] - 1) & 0xFF
        elif c == '.': out.append(chr(tape[ptr]))
        elif c == ',': raise RuntimeError("нужен ввод")
        elif c == '[' and tape[ptr] == 0: pc = pairs[pc]
        elif c == ']' and tape[ptr] != 0: pc = pairs[pc]
        pc += 1
    return "".join(out)


def bf_print_string(text):
    if not text: return ""
    targets = [ord(c) & 0xFF for c in text]
    best_base, best_len = 8, float('inf')
    for base in range(2, 32):
        l = base
        for t in targets: l += (t // base) + (t % base) + 6
        if l < best_len: best_len, best_base = l, base
    base = best_base
    parts = ['+' * base]
    for i, t in enumerate(targets):
        m, r = t // base, t % base
        parts.append('[>' + '+' * m + '<-]')
        parts.append('>'); parts.append('+' * r); parts.append('.')
        if i < len(targets) - 1:
            parts.append('>'); parts.append('+' * base)
    return ''.join(parts)


def ws_enc_num(n):
    s = ' ' if n >= 0 else '\t'
    n = abs(n)
    if n == 0: return s + ' \n'
    return s + ''.join('\t' if b == '1' else ' ' for b in bin(n)[2:]) + '\n'

def ws_push(n): return '  ' + ws_enc_num(n)
def ws_out_char(): return '\t\n  '
def ws_end(): return '\n\n\n'

def ws_print_str(s):
    return ''.join(ws_push(ord(c)) + ws_out_char() for c in s)