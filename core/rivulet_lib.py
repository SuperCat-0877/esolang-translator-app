# core/rivulet_lib.py
import json
from pathlib import Path

_LIB_FILE = Path(__file__).parent.parent / "rivulet_library.json"


def load_library():
    if not _LIB_FILE.exists():
        return {}
    try:
        return json.loads(_LIB_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_entry(output_key: str, rivulet_code: str):
    lib = load_library()
    lib[output_key] = rivulet_code
    _LIB_FILE.write_text(
        json.dumps(lib, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def library_path():
    return _LIB_FILE