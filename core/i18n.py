# core/i18n.py
"""Локализация. Загружает locales/{lang}.json.

Как перевести:
  1. Откройте locales/<lang>.json
  2. Замените значения (справа) на перевод
  3. Ключи (слева) НЕ трогайте
  4. Перезапустите приложение

Прогресс перевода: python tools/i18n_status.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

_current = "ru"
_strings: dict[str, dict[str, str]] = {}
_fallback = "ru"   # если ключа нет — берём из русского


def _locales_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "locales"
    return Path(__file__).resolve().parent.parent / "locales"


def _load(lang: str) -> dict[str, str]:
    if lang in _strings:
        return _strings[lang]
    p = _locales_dir() / f"{lang}.json"
    if not p.exists():
        _strings[lang] = {}
        return {}
    try:
        _strings[lang] = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        _strings[lang] = {}
    return _strings[lang]


def available_langs() -> list[str]:
    """Список доступных языков."""
    d = _locales_dir()
    if not d.exists():
        return ["ru"]
    return sorted(p.stem for p in d.glob("*.json"))


def set_lang(code: str) -> None:
    global _current
    if code in available_langs():
        _current = code
        _load(code)


def get_lang() -> str:
    return _current


def t(key: str, *args, **kwargs) -> str:
    """Перевод по ключу. Fallback: текущий → русский → ключ."""
    s = _load(_current).get(key)
    if s is None or s == "":
        s = _load(_fallback).get(key)
    if s is None:
        return key
    if args or kwargs:
        try:
            return s.format(*args, **kwargs)
        except Exception:
            return s
    return s

def tf(key: str, **kw) -> str:
    """t() + .format(**kw) — с безопасным fallback на сам ключ."""
    s = t(key)
    try:
        return s.format(**kw)
    except (KeyError, IndexError, ValueError):
        return s


def translation_status() -> dict[str, dict]:
    """Прогресс перевода: {lang: {done, total, percent}}."""
    ru = _load("ru")
    total = len(ru)
    out = {}
    for code in available_langs():
        if code == "ru":
            out[code] = {"done": total, "total": total, "percent": 100.0}
            continue
        data = _load(code)
        # строка «переведена», если значение НЕ совпадает с русской
        done = sum(
            1 for k, v in ru.items()
            if data.get(k) and data.get(k) != v
        )
        out[code] = {
            "done": done,
            "total": total,
            "percent": round(done * 100 / total, 1) if total else 0,
        }
    return out
