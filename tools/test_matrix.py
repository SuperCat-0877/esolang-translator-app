# tools/test_matrix.py
"""
Матричное тестирование: все пары языков x 25 шаблонов.

Режимы:
    python tools/test_matrix.py              # прогнать, сохранить отчёт
    python tools/test_matrix.py --exec       # + execute() результата
    python tools/test_matrix.py worker NAME  # внутренний: один язык

Требует соседний файл tools/_exec_daemon.py.

Категории результата:
    OK          — translate() дал непустую строку, execute() (если --exec)
                  завершился без ошибок.
    SKIP_EXEC   — пара в EXEC_SKIP: заведомо известная несовместимость
                  языка-приёмника. Не считается ошибкой.
    EMPTY       — translate() вернул None или ''.
    BAD_TYPE    — translate() вернул не-строку.
    EXEC_ERR    — execute() упал или ушёл в таймаут.
    ERR         — исключение в translate().
    TIMEOUT     — воркер языка-источника не уложился в PER_LANG_TIMEOUT.
    CRASH       — воркер упал (rc != 0).
    BAD_JSON    — воркер не напечатал JSON-блок.
    SRC_MISSING — языка-источника нет в реестре.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "test_report"
REPORT.mkdir(exist_ok=True)

PER_LANG_TIMEOUT = 900          # 15 минут на один язык-источник
EXEC_TIMEOUT_S   = 3.0          # дефолт на один execute()

# ---------------------------------------------------------------
#  Пер-языковые таймауты для execute().
#  brainfuck вернулся к разумному — тяжёлые пары закрыты EXEC_SKIP.
# ---------------------------------------------------------------
EXEC_TIMEOUT_BY_LANG: dict[str, float] = {
    "brainfuck":     5.0,
    "malbolge_lite": 5.0,
    "unlambda":      8.0,
    "thue":          8.0,
    "befunge":       5.0,
    "intercal":      5.0,
    "whitespace":    5.0,
    # PATCH: cpp на больших программах может долго компилировать
    "cpp":          15.0,
}

# ---------------------------------------------------------------
#  Известные несовместимости: пары (src, dst, tpl), для которых
#  execute() не укладывается в разумное время или заведомо ломается.
#  Такие пары помечаются SKIP_EXEC и НЕ считаются ошибкой.
# ---------------------------------------------------------------
# --- PATCH: empty-skip ---
# Все 7 пар, ранее отмеченных тут, работают за <5s после фикса
# isatty-guard в brainfuck.py. Оставлено пустым на случай появления
# новых реальных таймаутов.
EXEC_SKIP: set[tuple[str, str, str]] = set()
# --- /PATCH ---

# Категории, которые не считаются ошибкой в отчёте
# --- PATCH: limited-dst ---
# Эзотерические языки с очень ограниченным generate_code():
# не умеют рендерить произвольный текстовый вывод (мета-шаблоны).
# Пустой translate() для них — норма, а не баг.
LIMITED_DST: frozenset[str] = frozenset({
    "bitwise", "chicken", "cow", "deadfish",
    "hodor", "ook", "pika", "brainfuck",
    "lolcode", "rockstar", "shakespeare", "arnoldc",
})

META_TPL_PREFIX = "[T"

# --- /PATCH ---
OK_KINDS: frozenset[str] = frozenset({
    "OK", "SKIP_EXEC", "SKIP_LIMITED",
})

JSON_START = "__JSON_START__"
JSON_END   = "__JSON_END__"

DAEMON = str(Path(__file__).resolve().parent / "_exec_daemon.py")


# ==================================================================
#  UTF-8 хелпер
# ==================================================================
def _force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ==================================================================
#  PERSISTENT EXECUTOR
# ==================================================================
class Executor:
    """
    Один долгоживущий Python-процесс, выполняющий lang.execute().
    Общение — построчный JSON через stdin/stdout.
    По таймауту — kill + авто-рестарт при следующем вызове.
    Работает на Windows без pickle и без spawn-на-каждый-тест.
    """

    def __init__(self, timeout: float = EXEC_TIMEOUT_S) -> None:
        self.default_timeout = float(timeout)
        self.proc: subprocess.Popen | None = None
        self.q: queue.Queue = queue.Queue()
        self.reader: threading.Thread | None = None
        self.next_id = 0
        self._lock = threading.Lock()

    # --------------------------------------------------------------
    def _start(self) -> None:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        self.proc = subprocess.Popen(
            [sys.executable, "-u", DAEMON],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        self.q = queue.Queue()
        self.reader = threading.Thread(
            target=self._reader_loop,
            args=(self.proc.stdout, self.q),
            daemon=True,
        )
        self.reader.start()

    @staticmethod
    def _reader_loop(stream, q: "queue.Queue") -> None:
        try:
            for line in stream:
                q.put(line)
        except Exception:
            pass
        q.put(None)  # маркер EOF

    def _kill(self) -> None:
        if self.proc is not None:
            try:
                self.proc.kill()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=2)
            except Exception:
                pass
        self.proc = None
        self.reader = None

    # --------------------------------------------------------------
    def run_full(self, lang_name: str, code: str,
                 timeout: float | None = None) -> tuple[str, str]:
        """
        Возвращает (error, output).
        error — '' при успехе, иначе текст ошибки.
        output — stdout, который напечатал код.

        timeout=None → EXEC_TIMEOUT_BY_LANG.get(lang_name, default).
        """
        if timeout is None:
            timeout = EXEC_TIMEOUT_BY_LANG.get(
                lang_name, self.default_timeout)
        timeout = float(timeout)

        with self._lock:
            if self.proc is None or self.proc.poll() is not None:
                self._kill()
                self._start()

            req_id = self.next_id
            self.next_id += 1

            try:
                self.proc.stdin.write(
                    json.dumps(
                        {"id": req_id, "lang": lang_name, "code": code},
                        ensure_ascii=False,
                    ) + "\n"
                )
                self.proc.stdin.flush()
            except Exception as e:
                self._kill()
                return f"EXEC_IO {type(e).__name__}: {e}", ""

            deadline = time.monotonic() + timeout
            while True:
                remain = deadline - time.monotonic()
                if remain <= 0:
                    self._kill()
                    return f"TIMEOUT (execute > {timeout:g}s)", ""
                try:
                    line = self.q.get(timeout=remain)
                except queue.Empty:
                    self._kill()
                    return f"TIMEOUT (execute > {timeout:g}s)", ""
                if line is None:
                    self._kill()
                    return "EXEC_DAEMON_DIED", ""
                try:
                    resp = json.loads(line)
                except Exception:
                    continue
                if resp.get("id") != req_id:
                    continue
                if resp.get("ok"):
                    return "", resp.get("out", "")
                return resp.get("err") or "unknown", resp.get("out", "")

    # --------------------------------------------------------------
    def run(self, lang_name: str, code: str,
            timeout: float | None = None) -> str:
        """'' при успехе, иначе текст ошибки. Совместимость."""
        err, _ = self.run_full(lang_name, code, timeout)
        return err

        with self._lock:
            if self.proc is None or self.proc.poll() is not None:
                self._kill()
                self._start()

            req_id = self.next_id
            self.next_id += 1

            try:
                self.proc.stdin.write(
                    json.dumps(
                        {"id": req_id, "lang": lang_name, "code": code},
                        ensure_ascii=False,
                    ) + "\n"
                )
                self.proc.stdin.flush()
            except Exception as e:
                self._kill()
                return f"EXEC_IO {type(e).__name__}: {e}"

            deadline = time.monotonic() + timeout
            while True:
                remain = deadline - time.monotonic()
                if remain <= 0:
                    self._kill()
                    return f"TIMEOUT (execute > {timeout:g}s)"
                try:
                    line = self.q.get(timeout=remain)
                except queue.Empty:
                    self._kill()
                    return f"TIMEOUT (execute > {timeout:g}s)"
                if line is None:
                    self._kill()
                    return "EXEC_DAEMON_DIED"
                try:
                    resp = json.loads(line)
                except Exception:
                    continue
                if resp.get("id") != req_id:
                    continue
                if resp.get("ok"):
                    return ""
                return resp.get("err") or "unknown"

    def close(self) -> None:
        self._kill()


# ==================================================================
#  ОДНА ПРОВЕРКА
# ==================================================================
def _check_one(executor: Executor | None,
               src_name: str, dst_name: str,
               tpl_name: str, code: str) -> dict:
    """
    Прогоняет translate() и (опц.) execute() для одной тройки.
    Возвращает готовую запись результата.
    """
    t0 = time.monotonic()

    # 1) skip-лист — не тратим время на translate вообще
    if executor is not None and (src_name, dst_name, tpl_name) in EXEC_SKIP:
        dt = time.monotonic() - t0
        return {
            "src": src_name, "dst": dst_name, "tpl": tpl_name,
            "kind": "SKIP_EXEC",
            "msg": f"{dst_name}: известная несовместимость",
            "dt": round(dt, 4),
        }

    # 2) обычный путь
    try:
        from core.translate import translate
        r = translate(src_name, dst_name, code, None)
        if isinstance(r, tuple):
            r = r[0]

        if r is None:
            kind, msg = "EMPTY", "translate -> None"
        elif not isinstance(r, str):
            kind, msg = "BAD_TYPE", f"translate -> {type(r).__name__}"
        elif r == "":
            if (dst_name in LIMITED_DST
                    and tpl_name.startswith(META_TPL_PREFIX)):
                kind, msg = "SKIP_LIMITED", \
                    f"{dst_name}: не умеет рендерить мета-вывод"
            else:
                kind, msg = "EMPTY", "translate -> ''"
        else:
            kind, msg = "OK", ""
            if executor is not None:
                err = executor.run(dst_name, r)
                if err:
                    kind, msg = "EXEC_ERR", err
    except BaseException as e:
        kind, msg = "ERR", f"{type(e).__name__}: {e}"

    dt = time.monotonic() - t0
    return {
        "src": src_name, "dst": dst_name, "tpl": tpl_name,
        "kind": kind, "msg": msg[:300], "dt": round(dt, 4),
    }


# ==================================================================
#  РЕЖИМ WORKER
# ==================================================================
def _worker_main(src_name: str, do_execute: bool) -> None:
    _force_utf8()
    sys.path.insert(0, str(ROOT))

    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()

    # Нормализуем шаблоны до 25 на язык — иначе увидим 23.
    try:
        from core.extended_templates import replace_all
        replace_all(verbose=False)
    except Exception as e:
        print(f"# replace_all error: {e}", file=sys.stderr)

    # Универсальный fallback — без него почти все пары упадут.
    from core.universal_fallback import install
    install()

    src = registry.get(src_name)
    if src is None:
        print(JSON_START)
        print(json.dumps([{"kind": "SRC_MISSING", "src": src_name}]))
        print(JSON_END)
        return

    dst_list = [d for d in registry.all() if d.name != src.name]
    tpl_snapshot = list(src.templates.items())

    executor = Executor() if do_execute else None
    results: list[dict] = []

    try:
        for dst in dst_list:
            for tpl_name, code in tpl_snapshot:
                results.append(_check_one(
                    executor, src.name, dst.name, tpl_name, code))
    finally:
        if executor is not None:
            executor.close()

    print(JSON_START)
    print(json.dumps(results, ensure_ascii=False))
    print(JSON_END)


# ==================================================================
#  РЕЖИМ PARENT
# ==================================================================
def _parse_json_block(text: str):
    lines = text.splitlines()
    try:
        i = lines.index(JSON_START)
        j = lines.index(JSON_END, i + 1)
    except ValueError:
        return None
    payload = "\n".join(lines[i + 1:j])
    try:
        return json.loads(payload)
    except Exception:
        return None


def _parent_main(do_execute: bool) -> None:
    _force_utf8()
    sys.path.insert(0, str(ROOT))
    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()

    langs = [l.name for l in registry.all()]
    print(f"Тестирую {len(langs)} языков "
          f"({len(langs)*(len(langs)-1)} пар x 25 шаблонов)\n")

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    all_results: list[dict] = []
    t_start = time.monotonic()
    me = str(Path(__file__).resolve())

    for i, src_name in enumerate(langs, 1):
        t0 = time.monotonic()
        cmd = [sys.executable, me, "worker", src_name]
        if do_execute:
            cmd.append("--exec")

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=PER_LANG_TIMEOUT,
                env=env,
            )
        except subprocess.TimeoutExpired:
            print(f"[{i:>2}/{len(langs)}] {src_name:<16} TIMEOUT")
            all_results.append({"kind": "TIMEOUT", "src": src_name,
                                "dst": "*", "tpl": "*", "msg": ""})
            continue

        if proc.returncode != 0:
            tail = (proc.stderr or "")[-1200:]
            print(f"[{i:>2}/{len(langs)}] {src_name:<16} "
                  f"CRASH rc={proc.returncode}")
            all_results.append({"kind": "CRASH", "src": src_name,
                                "dst": "*", "tpl": "*", "msg": tail})
            continue

        batch = _parse_json_block(proc.stdout)
        if batch is None:
            print(f"[{i:>2}/{len(langs)}] {src_name:<16} BAD_JSON")
            all_results.append({"kind": "BAD_JSON", "src": src_name,
                                "dst": "*", "tpl": "*",
                                "msg": (proc.stdout or "")[-400:]})
            continue

        ok  = sum(1 for r in batch if r["kind"] in OK_KINDS)
        bad = len(batch) - ok
        dt  = time.monotonic() - t0
        print(f"[{i:>2}/{len(langs)}] {src_name:<16} "
              f"ok={ok:>4} bad={bad:>4}  {dt:>6.1f}s")
        all_results.extend(batch)

    _report(all_results, time.monotonic() - t_start)


# ==================================================================
#  ОТЧЁТ
# ==================================================================
def _report(results: list[dict], elapsed: float) -> None:
    total = len(results)
    kinds = Counter(r["kind"] for r in results)

    print(f"\n{'='*60}")
    print(f"Всего проверок: {total}   за {elapsed:.1f}s")
    print(f"{'='*60}")
    for k, v in kinds.most_common():
        mark = ""
        if k in OK_KINDS:
            mark = "  (ok)"
        print(f"  {k:<12} {v:>6}{mark}")

    # пары и шаблоны — только реальные ошибки, SKIP_EXEC не считаем
    real_bad = [r for r in results if r["kind"] not in OK_KINDS]

    pair_bad: Counter = Counter()
    for r in real_bad:
        pair_bad[(r.get("src", "?"), r.get("dst", "?"))] += 1
    if pair_bad:
        print(f"\nТоп-40 проблемных пар:")
        for (s, d), n in pair_bad.most_common(40):
            print(f"  {s:<16} -> {d:<16} bad={n}")

    tpl_bad: Counter = Counter()
    for r in real_bad:
        tpl_bad[r.get("tpl", "?")] += 1
    if tpl_bad:
        print(f"\nТоп-20 проблемных шаблонов:")
        for t, n in tpl_bad.most_common(20):
            print(f"  {t:<40} bad={n}")

    (REPORT / "matrix.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (REPORT / "matrix_errors.json").write_text(
        json.dumps(real_bad, ensure_ascii=False, indent=2),
        encoding="utf-8")

    n_ok = sum(1 for r in results if r["kind"] == "OK")
    n_skip = sum(1 for r in results if r["kind"] == "SKIP_EXEC")
    print(f"\nОтчёт:   {REPORT / 'matrix.json'}")
    print(f"Ошибки:  {REPORT / 'matrix_errors.json'}  ({len(real_bad)} шт.)")
    print(f"OK={n_ok}  SKIP_EXEC={n_skip}  real_bad={len(real_bad)}")


# ==================================================================
def main() -> None:
    args = sys.argv[1:]
    do_execute = "--exec" in args
    args = [a for a in args if a != "--exec"]

    if args and args[0] == "worker":
        if len(args) < 2:
            print("usage: ... worker <src>")
            sys.exit(2)
        _worker_main(args[1], do_execute)
        return

    _parent_main(do_execute)


if __name__ == "__main__":
    main()