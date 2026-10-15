# langs/rivulet.py

# --- PATCH: rivulet-quiet ---
import os as _os_riv
import sys as _sys_riv

_RIV_VERBOSE = _os_riv.environ.get("RIVULET_VERBOSE") == "1"

def _riv_log(*args, **kw):
    if _RIV_VERBOSE:
        kw.setdefault("file", _sys_riv.stderr)
        print(*args, **kw)
# --- /PATCH ---
"""Rivulet — 2D-эзотерический язык. Шаблоны из Rivulet_examples/*.riv."""

import sys
from io import StringIO
from pathlib import Path

from core.base import Language
from core.translate import TRANSPILERS
from core.rivulet_trans import rivulet_to_python


_HERE = Path(__file__).parent.parent
_RIVULET_DIR = _HERE / "rivulet"
_EXAMPLES_DIR = _HERE / "Rivulet_examples"

if _RIVULET_DIR.is_dir() and str(_RIVULET_DIR) not in sys.path:
    sys.path.insert(0, str(_RIVULET_DIR))

try:
    from riv_interpreter import Interpreter
    HAS_INTERPRETER = True
    _IMPORT_ERROR = None
except Exception as _e:
    Interpreter = None
    HAS_INTERPRETER = False
    _IMPORT_ERROR = _e


_GLYPHS = set(
    "─│╮╭╰╯╵╷╶╴"      # базовые (round + углы + стрелки)
    "┌┐└┘"             # острые углы
    "├┤┬┴┼"            # перекрёстки
    "═║╔╗╚╝╠╣╦╩╬"     # двойные линии
)
_DIGITS = set("0123456789")
_ALLOWED = _GLYPHS | _DIGITS | {" "}


# ==================================================================
#  Очистка текста
# ==================================================================
_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def _try_decodings(raw):
    """Пробует все кодировки. Возвращает текст или None."""
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def _clean_rivulet_text(text):
    out = []
    for line in text.splitlines():
        cleaned = "".join(ch if ch in _ALLOWED else " " for ch in line)
        out.append(cleaned.rstrip())

    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()

    # Схлопнуть подряд идущие пустые строки до одной
    compact = []
    prev_empty = False
    for line in out:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        compact.append(line)
        prev_empty = is_empty

    return "\n".join(compact)


# ==================================================================
#  Расширенный детектор бинарных файлов
# ==================================================================
_MAGIC_PREFIXES = (
    b"\x89PNG\r\n\x1a\n",       # PNG
    b"\xff\xd8\xff",            # JPEG
    b"GIF87a", b"GIF89a",       # GIF
    b"PK\x03\x04",              # ZIP / docx / xlsx / jar
    b"%PDF",                    # PDF
    b"BM",                      # BMP
    b"RIFF",                    # WAV / WEBP / AVI
    b"\x00\x00\x01\x00",        # ICO
    b"II*\x00", b"MM\x00*",     # TIFF
    b"\x1f\x8b",                # GZIP
    b"7z\xbc\xaf",              # 7z
    b"Rar!\x1a",                # RAR
    b"\xca\xfe\xba\xbe",        # Java class
    b"\x7fELF",                 # ELF
    b"MZ",                      # Windows PE
)


def _is_binary(data: bytes) -> bool:
    if not data:
        return False

    for m in _MAGIC_PREFIXES:
        if data.startswith(m):
            return True

    if b"\x00" in data[:2048]:
        return True

    sample = data[:4096]
    if sample:
        non_printable = sum(
            1 for b in sample
            if b < 9 or (13 < b < 32) or b > 126
        )
        if non_printable / len(sample) > 0.30:
            return True

    return False


def _has_rivulet_glyph(text: str) -> bool:
    return any(ch in _GLYPHS for ch in text)


# ==================================================================
#  Пробное исполнение
# ==================================================================
def _try_execute(text: str):
    """Возвращает (ok: bool, error: str | None)."""
    if not HAS_INTERPRETER:
        return (True, None)
    try:
        interp = Interpreter()
        interp.output = Interpreter.OutputOption.unicode
        interp.verbose = False
        old = sys.stdout
        sys.stdout = StringIO()
        try:
            interp.interpret_program(text, verbose=False)
        finally:
            sys.stdout = old
        return (True, None)
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


# ==================================================================
#  Загрузка шаблонов
# ==================================================================
def _load_templates():
    templates = {}
    skipped = []

    if not _EXAMPLES_DIR.is_dir():
        return templates

    for path in sorted(_EXAMPLES_DIR.glob("*.riv")):
        # 1) Читаем байты
        try:
            raw = path.read_bytes()
        except Exception:
            continue

        # 2) Пробуем все кодировки
        text = _try_decodings(raw)
        if text is None:
            skipped.append((path.name, "decode"))
            continue

        # 3) Бинарники определяем по магии
        if _is_binary(raw) and not _has_rivulet_glyph(text):
            skipped.append((path.name, "binary"))
            continue

        # 4) Чистим
        cleaned = _clean_rivulet_text(text)
        if not cleaned.strip():
            skipped.append((path.name, "empty"))
            continue
        if not _has_rivulet_glyph(cleaned):
            skipped.append((path.name, "no glyph"))
            continue

        # 5) Пробуем выполнить — но если падает, всё равно добавляем
        ok, err = _try_execute(cleaned)
        if not ok:
            # не пропускаем — при выборе из UI просто покажет пусто
            pass

        templates[f"[{len(templates) + 1}] {path.stem}"] = cleaned

    if skipped:
        _riv_log(f"[rivulet] пропущено {len(skipped)} файлов:")
        for name, why in skipped:
            print(f"    - {name}: {why}")

    total = sum(1 for _ in _EXAMPLES_DIR.glob("*.riv")) if _EXAMPLES_DIR.is_dir() else 0
    _riv_log(f"[rivulet] загружено {len(templates)} из {total} шаблонов")
    if skipped:
        reasons = {}
        for _, why in skipped:
            reasons[why] = reasons.get(why, 0) + 1
        _riv_log(f"[rivulet] причины пропусков: {reasons}")
    return templates


_TEMPLATES = _load_templates()


# ==================================================================
#  Класс языка
# ==================================================================

# ==================================================================
#  Генератор кода — настоящий round-trip
# ==================================================================

def _rows_for_char(code):
    """7 строк для одного символа `code`.
    Strand на y=0 (list=1 = вывод), разложение по простым y=0,2,4,6.
    """
    K6 = code // 13
    rem = code % 13
    K4 = rem // 7
    rem = rem % 7
    K2 = rem // 3
    K0 = rem % 3

    rows = []

    # y=0: ╰, K0×─, ╮
    row = "╰" + "─" * K0 + "╮"
    rows.append(row)

    # y=1: │
    x = len(row) - 1
    rows.append(" " * x + "│")

    # y=2: ╰, K2×─, ╮
    row = " " * x + "╰" + "─" * K2 + "╮"
    rows.append(row)

    # y=3: │
    x = len(row) - 1
    rows.append(" " * x + "│")

    # y=4: ╰, K4×─, ╮
    row = " " * x + "╰" + "─" * K4 + "╮"
    rows.append(row)

    # y=5: │
    x = len(row) - 1
    rows.append(" " * x + "│")

    # y=6: ╰, K6×─
    row = " " * x + "╰" + "─" * K6 + "╴"
    rows.append(row)

    return rows


def _rivulet_generate(text):
    """Настоящий генератор Rivulet для строки `text`."""
    if not text:
        return ""
    # PATCH: newline не поддерживается интерпретатором Rivulet.
    # Заменяем \n и \r на пробел — ближайший валидный вывод.
    if "\n" in text or "\r" in text:
        text = (text
                .replace("\r\n", " ")
                .replace("\n", " ")
                .replace("\r", " "))

    all_rows = [_rows_for_char(ord(c)) for c in text]
    widths = [max(len(r) for r in rows) for rows in all_rows]

    result = []
    for y in range(7):
        parts = []
        for i, rows in enumerate(all_rows):
            parts.append(rows[y].ljust(widths[i]))
        line = " ".join(parts)

        if y == 0:
            result.append(" 1 ╵ " + line)
        else:
            result.append("     " + line)

    result[-1] += " ╷"
    return "\n".join(result) + "\n"



class RivuletLang(Language):
    name = "rivulet"
    title = "Rivulet"
    category = "Э"
    ext = ".riv"
    templates = _TEMPLATES

    def execute(self, src):
        if not HAS_INTERPRETER:
            return f"// Rivulet: интерпретатор недоступен ({_IMPORT_ERROR})"
        if not src.strip():
            return ""
        try:
            interp = Interpreter()
            interp.output = Interpreter.OutputOption.unicode
            interp.verbose = False
            old_stdout = sys.stdout
            sys.stdout = captured = StringIO()
            try:
                interp.interpret_program(src, verbose=False)
            finally:
                sys.stdout = old_stdout
            return captured.getvalue().rstrip("\n")  # PATCH: rstrip-newline
        except IndexError:
            # риvulet-интерпретатор падает на некоторых примерах
            return ""
        except Exception as e:
            return f"// Ошибка Rivulet: {e}"

    def generate_code(self, output):
        return _rivulet_generate(output or "")


# ==================================================================
#  Регистрация транспайлеров
# ==================================================================
def _rivulet_to_python(src):
    return rivulet_to_python(src, lambda s: RivuletLang().execute(s))


TRANSPILERS[("rivulet", "python")] = _rivulet_to_python

# --- RECEIVER: python-to-rivulet ---
def _python_to_rivulet(src):
    """Исполнить Python-код, взять stdout, сгенерировать Rivulet."""
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            exec(compile(src or "", "<py-to-rivulet>", "exec"), {})
    except BaseException:
        return ""
    return _rivulet_generate(buf.getvalue())


TRANSPILERS[("python", "rivulet")] = _python_to_rivulet
# --- /RECEIVER ---


try:
    from core.py_to_rivulet import py_to_rivulet as _py_to_riv
    # === PATCH: no-similarity ===
# py_to_rivulet — подбор по сходству, не генерация. Для произвольного
# кода даёт мусор. Отключаем: пусть fallback честно генерирует
# rivulet-диаграмму из execute(X) → generate_code(text).
# TRANSPILERS[("python", "rivulet")] = _py_to_riv
# === /PATCH ===
    # python→rivulet регистрируется ниже через _python_to_rivulet
except Exception as _e:
    _riv_log(f"[rivulet] Ошибка регистрации python→rivulet: {_e}")
