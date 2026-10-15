# tools/_exec_daemon.py
"""
Persistent executor для lang.execute().
Один процесс на worker. Общение — JSON-строки:

  stdin:  {"id": N, "lang": "...", "code": "..."}\n
  stdout: {"id": N, "ok": bool, "out": "...", "err": "..."}\n

Демон долгоживущий: если запускаемый код повесится — родитель
убьёт демон и поднимет новый. Никаких pickle и никакого spawn
на каждый тест.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# capture-return: daemon captures return value of lang.execute
def main() -> None:
    _force_utf8()

    from core.config import load as load_config
    from core.registry import registry
    load_config()
    registry.discover_builtin()
    langs = {l.name: l for l in registry.all()}

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except Exception:
            continue

        req_id = req.get("id")
        name = req.get("lang")
        code = req.get("code", "")

        lang = langs.get(name)
        if lang is None:
            resp = {"id": req_id, "ok": False, "out": "",
                    "err": f"no such lang: {name}"}
        else:
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf), \
                     contextlib.redirect_stderr(buf):
                    _ret = lang.execute(code)
                resp = {"id": req_id, "ok": True,
                        "out": (_ret if isinstance(_ret, str) and _ret else buf.getvalue()), "err": ""}
            except BaseException as e:
                resp = {"id": req_id, "ok": False,
                        "out": buf.getvalue(),
                        "err": f"{type(e).__name__}: {e}"}

        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()