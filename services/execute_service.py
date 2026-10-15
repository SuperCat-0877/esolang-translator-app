# services/execute_service.py
"""Единая точка запуска кода.

При обычном запуске (`python Main.py`) — через subprocess в отдельном
процессе с таймаутом.
В frozen-режиме (`.exe`) — in-process через registry: subprocess
невозможен, т.к. sys.executable = сам .exe.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class ExecResult:
    ok: bool
    output: str
    error: str
    elapsed: float
    lang: str = ""
    code_len: int = 0


class ExecuteService:
    def __init__(self, default_timeout: float = 5.0):
        self._default_timeout = default_timeout
        self._frozen = getattr(sys, "frozen", False)
        self._ex = None
        if not self._frozen:
            # subprocess работает только в dev-режиме
            from tools.test_matrix import Executor
            self._ex = Executor()

    def run(self, lang: str, code: str,
            timeout: float | None = None) -> ExecResult:
        t0 = time.monotonic()
        err, out = "", ""

        try:
            if self._frozen:
                # In-process: без изоляции и таймаута.
                out = self._run_inprocess(lang, code)
            else:
                err, out = self._ex.run_full(
                    lang, code,
                    timeout=timeout or self._default_timeout)
        except BaseException as e:
            err = f"{type(e).__name__}: {e}"
            out = ""

        dt = time.monotonic() - t0
        return ExecResult(
            ok=(err == ""), output=out, error=err,
            elapsed=round(dt, 3), lang=lang, code_len=len(code))

    def _run_inprocess(self, lang: str, code: str) -> str:
        """Прямое исполнение через registry. Для .exe."""
        from core.registry import registry
        l = registry.get(lang)
        if l is None:
            raise ValueError(f"Язык {lang!r} не найден")
        result = l.execute(code)
        return "" if result is None else str(result)

    def close(self) -> None:
        if self._ex is not None:
            try:
                self._ex.close()
            except Exception:
                pass


# ---------------------------------------------------------------------
_instance: "ExecuteService | None" = None


def get_execute_service() -> ExecuteService:
    global _instance
    if _instance is None:
        _instance = ExecuteService()
    return _instance