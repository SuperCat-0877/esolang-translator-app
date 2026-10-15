# core/validators.py
import re


class HardcodeError(Exception):
    pass


# Паттерны «print с литералом» для разных языков.
_PRINT_LITERAL_PATTERNS = [
    r'^\s*print\s*\(\s*["\'].*["\']\s*\)\s*;?\s*$',
    r'^\s*fmt\.Println\s*\(\s*["\'].*["\']\s*\)\s*$',
    r'^\s*println\s*\(\s*["\'].*["\']\s*\)\s*;?\s*$',
    r'^\s*console\.log\s*\(\s*["\'].*["\']\s*\)\s*;?\s*$',
    r'^\s*System\.out\.println\s*\(\s*["\'].*["\']\s*\)\s*;?\s*$',
]

_LOOP_KEYWORDS = ("for ", "while ", "foreach", "loop", ".iter()", "range(")


def detect_hardcode(original: str, translated: str) -> list[str]:
    """
    Возвращает список проблем. Пустой список = чисто.
    Проверяет: если в оригинале есть цикл/арифметика,
    а в переводе — подряд идущие print с литералами без циклов.
    """
    problems: list[str] = []

    # 1. Подряд идущие print("литерал") в переводе.
    literal_lines = 0
    for line in translated.splitlines():
        for pat in _PRINT_LITERAL_PATTERNS:
            if re.match(pat, line):
                literal_lines += 1
                break

    has_loop_translated = any(kw in translated for kw in _LOOP_KEYWORDS)

    if literal_lines >= 3 and not has_loop_translated:
        problems.append(
            f"hardcode: {literal_lines} подряд print/println с литералами "
            f"и ни одного цикла"
        )

    # 2. Цикл был в оригинале, но пропал в переводе.
    has_loop_original = any(kw in original for kw in _LOOP_KEYWORDS)
    if has_loop_original and not has_loop_translated:
        problems.append("цикл из оригинала не найден в переводе")

    # 3. Арифметика была, но пропала.
    has_arith_original = bool(re.search(r'[*+\-/]', original))
    has_arith_translated = bool(re.search(r'[*+\-/]', translated))
    if has_arith_original and not has_arith_translated:
        problems.append("арифметика из оригинала не найдена в переводе")

    # 4. Переменная была — переменной нет.
    # (простая эвристика: let/val/var/const в оригинале vs переводе)
    vars_original = set(re.findall(r'\b(?:let|val|var|const)\s+(\w+)', original))
    vars_translated = set(re.findall(r'\b(?:let|val|var|const)\s+(\w+)', translated))
    lost = vars_original - vars_translated
    if lost:
        problems.append(f"потеряны переменные: {', '.join(sorted(lost))}")

    return problems