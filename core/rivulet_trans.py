# core/rivulet_trans.py
"""Трассирующий переводчик Rivulet → Python."""

import math


def _looks_like_binary(out):
    if not out:
        return False
    control = sum(1 for c in out if ord(c) < 32)
    printable = sum(1 for c in out if 32 <= ord(c) < 127)
    return control > 0 and control >= printable


def _bytes_to_numbers(out):
    return [ord(c) for c in out]


def _is_int_str(s):
    s = s.strip()
    if not s:
        return False
    if s.startswith("-"):
        s = s[1:]
    return s.isdigit()


def _find_arith(nums):
    if len(nums) < 3:
        return None
    step = nums[1] - nums[0]
    for i in range(1, len(nums)):
        if nums[i] - nums[i - 1] != step:
            return None
    return nums[0], step, len(nums)


def _find_geom(nums):
    if len(nums) < 3 or nums[0] == 0 or any(n == 0 for n in nums):
        return None
    r = nums[1] / nums[0]
    if r != int(r):
        return None
    for i in range(1, len(nums)):
        if nums[i] != nums[i - 1] * r:
            return None
    return nums[0], int(r), len(nums)


def _find_squares(nums):
    if len(nums) < 3:
        return None
    roots = []
    for n in nums:
        if n < 0:
            return None
        r = int(round(math.sqrt(n)))
        if r * r != n:
            return None
        roots.append(r)
    return _find_arith(roots)


def _find_fib(nums):
    if len(nums) < 4:
        return None
    for i in range(2, len(nums)):
        if nums[i] != nums[i - 1] + nums[i - 2]:
            return None
    return nums[0], nums[1], len(nums)


def _gen_loop(nums, indent=0):
    ind = "    " * indent

    a = _find_arith(nums)
    if a and a[2] >= 3:
        start, step, n = a
        end = start + step * (n - 1)
        if step == 1:
            return (f"{ind}for i in range({start}, {end + 1}):\n"
                    f"{ind}    print(i)\n")
        return (f"{ind}for i in range({n}):\n"
                f"{ind}    print({start} + i * {step})\n")

    s = _find_squares(nums)
    if s and s[2] >= 3:
        start, step, n = s
        end = start + step * (n - 1)
        return (f"{ind}for i in range({start}, {end + 1}):\n"
                f"{ind}    print(i * i)\n")

    g = _find_geom(nums)
    if g and g[2] >= 3:
        start, ratio, n = g
        return (f"{ind}for i in range({n}):\n"
                f"{ind}    print({start} * {ratio} ** i)\n")

    f = _find_fib(nums)
    if f and f[2] >= 4:
        a0, b0, n = f
        return (f"{ind}a = {a0}\n"
                f"{ind}b = {b0}\n"
                f"{ind}for _ in range({n}):\n"
                f"{ind}    print(a)\n"
                f"{ind}    a, b = b, a + b\n")

    return None


def rivulet_to_python(src, execute_fn):
    if not src or not src.strip():
        return "# пустая Rivulet-программа\n"

    try:
        out = execute_fn(src)
    except Exception as e:
        return f"# Rivulet: ошибка выполнения — {e}\n"

    if out is None:
        return "# Rivulet: не удалось выполнить\n"
    if isinstance(out, str) and out.startswith("// Ошибка"):
        return f"# {out}\n"
    if not out:
        return "# Rivulet: пустой вывод\n"

    header = ("# Автоматически сгенерировано из Rivulet-программы\n"
              "# (трассирующий переводчик core.rivulet_trans)\n\n")

    if _looks_like_binary(out):
        nums = _bytes_to_numbers(out)
        loop = _gen_loop(nums)
        if loop:
            return header + loop
        body = "\n".join(f"print({n})" for n in nums)
        return (header +
                "# Rivulet вывел последовательность чисел:\n" +
                body + "\n")

    lines = out.rstrip("\n").split("\n")

    if all(_is_int_str(l) for l in lines if l.strip()):
        nums = [int(l.strip()) for l in lines if l.strip()]
        loop = _gen_loop(nums)
        if loop:
            return header + loop
        body = "\n".join(f"print({n})" for n in nums)
        return header + body + "\n"

    body = "\n".join(f"print({l!r})" for l in lines)
    return header + body + "\n"