# core/runtime_validator.py
"""
Меняет входные данные и сравнивает вывод оригинала и перевода.
Нужны адаптеры запуска для каждого языка.
"""
import subprocess
import tempfile
from pathlib import Path


def run_fsharp(code: str, timeout: int = 10) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "prog.fsx"
        p.write_text(code)
        r = subprocess.run(
            ["dotnet", "fsi", str(p)],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr


def run_kotlin(code: str, timeout: int = 30) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "Main.kt"
        p.write_text(code)
        # kotlinc + java — медленно, но работает
        r = subprocess.run(
            ["kotlinc", str(p), "-include-runtime", "-d", f"{d}/out.jar"],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            return r.returncode, "", r.stderr
        r2 = subprocess.run(
            ["java", "-jar", f"{d}/out.jar"],
            capture_output=True, text=True, timeout=timeout,
        )
        return r2.returncode, r2.stdout, r2.stderr


RUNNERS = {
    "fsharp": run_fsharp,
    "kotlin": run_kotlin,
    # добавьте свои языки
}


def mutate_input(code: str, lang: str) -> str:
    """
    Меняет константы, чтобы hardcode не совпал.
    Здесь — простой пример для вашего случая.
    """
    if lang == "fsharp":
        # let k = 7  →  let k = 3
        import re
        code = re.sub(r'let\s+(\w+)\s*=\s*\d+', r'let \1 = 3', code)
        # 1..10 → 1..3
        code = re.sub(r'(\d+)\.\.(\d+)', '1..3', code)
    if lang == "kotlin":
        # в переводе ничего менять не надо — если он hardcoded,
        # вывод не изменится и не совпадёт с оригиналом
        pass
    return code


def validate(original: str, translated: str, src_lang: str, dst_lang: str):
    """
    Возвращает (ok: bool, message: str).
    """
    if src_lang not in RUNNERS or dst_lang not in RUNNERS:
        return True, "нет раннера — пропущено"

    orig_mod = mutate_input(original, src_lang)
    trans_mod = mutate_input(translated, dst_lang)

    rc1, out1, err1 = RUNNERS[src_lang](orig_mod)
    rc2, out2, err2 = RUNNERS[dst_lang](trans_mod)

    if rc2 != 0:
        return False, f"перевод не запустился: {err2[:200]}"

    if out1.strip() != out2.strip():
        return False, (
            f"выводы расходятся.\n"
            f"--- оригинал (изменённый вход) ---\n{out1}\n"
            f"--- перевод ---\n{out2}"
        )

    return True, "ok"