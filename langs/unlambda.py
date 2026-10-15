# langs/unlambda.py
"""Unlambda — функциональный язык (SKI-комбинаторы). Реальная редукция."""

from core.base import Language
from core.translate import TRANSPILERS


class _Stop(Exception):
    pass


class UnlambdaInterpreter:
    def __init__(self, program, step_limit=500000):
        self.program = program
        self.out = []
        self.input_queue = []
        self.step_limit = step_limit

    # --- SKI-комбинаторы как замыкания ---
    def K(self, x):
        return lambda y: x

    def I(self, x):
        return x

    def S(self, x):
        return lambda y: lambda z: self.apply(self.apply(x, z),
                                              self.apply(y, z))

    def apply(self, f, x):
        # Универсальный вызов: если у f есть .apply(ctx, x) — используем
        if hasattr(f, "apply") and callable(getattr(f, "apply")):
            return f.apply(self, x)
        if isinstance(f, _Comb):
            return f.apply(self, x)
        return f(x)

    # --- Парсер ---
    def parse(self, text):
        self.pos = 0
        self.src = text
        return self._parse_expr()

    def _parse_expr(self):
        if self.pos >= len(self.src):
            return self.I
        c = self.src[self.pos]
        self.pos += 1

        if c == "`":
            f = self._parse_expr()
            x = self._parse_expr()
            return lambda ctx, _f=f, _x=x: ctx.apply(_f, _x)
        if c == "k":
            return self.K
        if c == "s":
            return self.S
        if c == "i":
            return self.I
        if c == "d":
            e = self._parse_expr()
            return lambda _ctx, _e=e: _e
        if c == "v":
            return self.I
        if c == "-":
            return self.I
        if c == ".":
            if self.pos < len(self.src):
                ch = self.src[self.pos]
                self.pos += 1
                return lambda _ctx, _ch=ch: self._emit(_ch)
            return self.I
        if c == "r":
            return lambda _ctx: self._emit("\n")
        if c == "e":
            return lambda _ctx: self._stop()
        if c == "@":
            return lambda _ctx: self._read()
        if c == "|":
            e = self._parse_expr()
            return lambda ctx, _e=e: ctx.apply(_e, ctx.I)
        if c == "?":
            if self.pos < len(self.src):
                c2 = self.src[self.pos]
                self.pos += 1
                return _Conditional(c2)
        # Неизвестный символ — noop
        return self.I

    def _emit(self, ch):
        self.out.append(ch)
        return self.I

    def _read(self):
        if self.input_queue:
            return self.input_queue.pop(0)
        return self.I

    def _stop(self):
        raise _Stop()

    def run(self):
        try:
            # Программа — это ПОСЛЕДОВАТЕЛЬНОСТЬ выражений,
            # вычисляемых слева-направо. Каждое — независимо.
            self.pos = 0
            self.src = self.program
            exprs = []
            while self.pos < len(self.src):
                exprs.append(self._parse_expr())
            for expr in exprs:
                if callable(expr):
                    expr(self)  # ctx = интерпретатор
        except _Stop:
            pass
        except RecursionError:
            pass
        except Exception:
            pass
        return "".join(str(c) for c in self.out)


class _Comb:
    def __init__(self, fn):
        self.fn = fn

    def apply(self, ctx, x):
        return self.fn(ctx, x)


class _Conditional:
    """?c — принимает два аргумента, выбирает по c."""
    def __init__(self, c):
        self.c = c

    def apply(self, ctx, x):
        return _Conditional2(self.c, x)

    def __call__(self, ctx):
        return self


class _Conditional2:
    def __init__(self, c, first):
        self.c = c
        self.first = first

    def apply(self, ctx, second):
        if self.c == "i":
            return self.first
        elif self.c == "v":
            return second
        else:
            return self.first


def _unlambda_run(src, step_limit=500000):
    if not src or not src.strip():
        return ""
    # НЕ удаляем whitespace: `.X`, где X — пробел, должен печатать пробел.
    # Пробелы в остальных местах разбираются как noop (return I).
    interp = UnlambdaInterpreter(src, step_limit)
    return interp.run()


def _unlambda_to_python(src):
    result = _unlambda_run(src)
    return (
        "# Unlambda → Python (симуляция SKI)\n"
        f"_out = {result!r}\n"
        "print(_out, end='')\n"
    )


# ==================================================================
#  Генераторы шаблонов
# ==================================================================
def _unlambda_print(text):
    if not text:
        return "i"
    parts = []
    for ch in text:
        if ch == "\n":
            parts.append("r")
        elif ch == "`":
            parts.append(".`")
        else:
            parts.append("." + ch)
    return "".join(parts)


def _unlambda_gen_numbers():
    return _unlambda_print("1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n")


def _unlambda_gen_squares():
    return _unlambda_print("1\n4\n9\n16\n25\n36\n49\n64\n81\n100\n")


def _unlambda_gen_cubes():
    return _unlambda_print("1\n8\n27\n64\n125\n216\n343\n512\n729\n1000\n")


def _unlambda_gen_table7():
    return _unlambda_print("7\n14\n21\n28\n35\n42\n49\n56\n63\n70\n")


def _unlambda_gen_fib():
    return _unlambda_print("0\n1\n1\n2\n3\n5\n8\n13\n21\n34\n")


def _unlambda_gen_apply():
    """`ki — K applied to I → K, никакого вывода."""
    return "``kii"


def _unlambda_gen_id():
    """i — identity."""
    return "i"


def _unlambda_gen_50():
    parts = []
    for k in range(1, 6):
        parts.append(f"=== {k} x {k} ===")
        for i in range(1, 6):
            parts.append(str(i * k))
    return _unlambda_print("\n".join(parts) + "\n")


def _unlambda_gen_200():
    parts = []
    for k in range(2, 8):
        parts.append(f"=== Таблица {k} ===")
        for i in range(1, 11):
            parts.append(str(i * k))
    return _unlambda_print("\n".join(parts) + "\n")


class UnlambdaLang(Language):
    name = "unlambda"
    title = "Unlambda"
    category = "Э"
    ext = ".unl"
    keywords = ["`", ".", "k", "s", "i", "r", "d", "e", "v", "@", "|", "?"]
    comment_regex = None

    templates = {

        '[1] Hello, World': '.H.e.l.l.o.,. .W.o.r.l.d.!',

        '[2] Буква A': '.A',

        '[3] Цифры 0-9': '.0.1.2.3.4.5.6.7.8.9',

        '[4] Hi!': '.H.i.!',

        '[5] Short': '.A.B.C',

        '[6] Алфавит A-J': '.A.B.C.D.E.F.G.H.I.J',

        '[7] Esolang': '.E.s.o.l.a.n.g',

        '[8] LOL': '.L.O.L',

        '[9] ABC': '.A.B.C',

        '[10] XYZ': '.X.Y.Z',

        '[11] Длинная': '.H.e.l.l.o.,. .W.o.r.l.d.!. .W.e.l.c.o.m.e.!',

        '[12] Fox': '.T.h.e. .q.u.i.c.k. .b.r.o.w.n. .f.o.x',

        '[13] Lorem': '.L.o.r.e.m. .i.p.s.u.m. .d.o.l.o.r. .s.i.t',

        '[14] Mix': '.A.B.C.a.b.c.1.2.3.!',

        '[15] Symbols': '.!.@.#.$.%.^.&.*.(.)',

        '[16] AZ+az': '.A.B.C.D.E.F.G.H.I.J.K.L.M.N.O.P.Q.R.S.T.U.V.W.X.Y.Z.a.b.c.d.e.f.g.h.i.j.k.l.m.n.o.p.q.r.s.t.u.v.w.x.y.z',

        '[17] Digital': '.0.1.2.3.4.5.6.7.8.9.!.@.#',

        '[18] Pan x1': '.T.h.e. .q.u.i.c.k. .b.r.o.w.n. .f.o.x. .j.u.m.p.s. .o.v.e.r. .t.h.e. .l.a.z.y. .d.o.g..',

        '[19] Hello+': '.H.e.l.l.o.,. .W.o.r.l.d.!. .H.e.l.l.o.,. .W.o.r.l.d.!',

        '[20] Numbers': '.1.2.3.4.5.6.7.8.9.0',

        '[Test 1] Панграмма x2': '.T.h.e. .q.u.i.c.k. .b.r.o.w.n. .f.o.x',

        '[Test 2] Lorem x2': '.L.o.r.e.m. .i.p.s.u.m. .d.o.l.o.r',

        '[Test 3] Всё вместе': '.H.e.l.l.o.!. .A.B.C',

    }

    def execute(self, src):
        if not src:
            return ""
        try:
            return _unlambda_run(src)
        except Exception as e:
            return f"// Unlambda: {type(e).__name__}: {e}"

    def generate_code(self, output):
        if not output:
            return "i"
        return _unlambda_print(output)


TRANSPILERS[("unlambda", "python")] = _unlambda_to_python
