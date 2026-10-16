# tools/fix_app_i18n3.py
"""
Финальный патч локализации ui/app.py (v3).
Добивает строки, которые не покрыл v2:
  • MODES -> функция _modes() с tr()
  • превью темы -> английский текст
  • забытые self.log(...)

Запуск из корня проекта:
    python tools/fix_app_i18n3.py
"""

from __future__ import annotations
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "ui" / "app.py"


RULES: list[tuple[str, str, str]] = [

    # ---------- 1. MODES -> функция _modes() ---------------------------------
    (r'MODES\s*=\s*\[\s*\(\s*"О\s*=\s*О"\s*,\s*"О"\s*,\s*"О"\s*\)\s*,\s*'
     r'\(\s*"О\s*=\s*Э"\s*,\s*"О"\s*,\s*"Э"\s*\)\s*,\s*'
     r'\s*\(\s*"Э\s*=\s*О"\s*,\s*"Э"\s*,\s*"О"\s*\)\s*,\s*'
     r'\(\s*"Э\s*=\s*Э"\s*,\s*"Э"\s*,\s*"Э"\s*\)\s*\]',

     'def _modes() -> list[tuple[str, str, str]]:\n'
     '    """Отображаемые метки + внутренние коды категорий (О/Э)."""\n'
     '    r = tr("cat_regular")\n'
     '    e = tr("cat_esoteric")\n'
     '    return [\n'
     '        (f"{r} = {r}", "О", "О"),\n'
     '        (f"{r} = {e}", "О", "Э"),\n'
     '        (f"{e} = {r}", "Э", "О"),\n'
     '        (f"{e} = {e}", "Э", "Э"),\n'
     '    ]',

     'MODES -> _modes()'),

    # ---------- 2. Использование MODES в Combobox ----------------------------
    (r'values\s*=\s*\[\s*m\[0\]\s*for\s+m\s+in\s+MODES\s*\]',
     'values=[m[0] for m in _modes()]',
     'MODES usage 1'),

    # ---------- 3. next(m for m in MODES ...) --------------------------------
    (r'next\(\s*m\s+for\s+m\s+in\s+MODES\s+if\s+m\[0\]\s*==\s*label\s*\)',
     'next(m for m in _modes() if m[0] == label)',
     'MODES usage 2'),

    # ---------- 4. Отчёт о переклассификации ---------------------------------
    (r'self\.log\(\s*f"\[templates\]\s*переклассифицировано:\s*"\s*\n?'
     r'\s*f"\{len\(renamed_langs\)\}\s*языков"\s*\)',
     'self.log("[templates] " + tf("msg_tpl_reclassified",\n'
     '                                          n=len(renamed_langs)))',
     'msg_tpl_reclassified'),

    # ---------- 5. Отчёт о fallback-парах ------------------------------------
    (r'self\.log\(\s*f"\[translate\]\s*универсальных пар:\s*\{_uf_added\}"\s*\)',
     'self.log("[translate] " + tf("msg_universal_pairs", n=_uf_added))',
     'msg_universal_pairs'),

    # ---------- 6. Заголовок LabelFrame «Язык / Language» --------------------
    (r'ttk\.LabelFrame\(\s*tab\s*,\s*text\s*=\s*"Язык\s*/\s*Language"\s*,',
     'ttk.LabelFrame(tab, text=tr("lang_section"),',
     'lang_section'),

    # ---------- 7. Подсказка про перезапуск ----------------------------------
    (r'text\s*=\s*"\(перезапустите\s*/\s*restart\)"\s*,',
     'text=tr("restart_hint"),',
     'restart_hint'),

    # ---------- 8. Превью темы: комментарий и print ---------------------------
    (r'self\.theme_preview\.insert\(\s*"end"\s*,\s*"    # комментарий\\n"\s*\)',
     'self.theme_preview.insert("end", "    # comment\\n")',
     'theme preview comment'),
    (r'self\.theme_preview\.insert\(\s*"end"\s*,\s*"    print\(f\'Привет,\s*\{name\}!\'\)\\n"\s*\)',
     'self.theme_preview.insert(\n'
     '            "end", "    print(f\'Hello, {name}!\')\\n")',
     'theme preview print'),

    # ---------- 9. Забытый self.log("--- шаблоны ---") -----------------------
    (r'self\.log\(\s*"---\s*шаблоны\s*---"\s*\)',
     'self.log("--- " + tr("shablony_list") + " ---")',
     'shablony header'),

    # ---------- 10. Забытый self.log("$ результат в буфере ...") -------------
    (r'self\.log\(\s*f"\$\s*результат в буфере\s*\(\{len\(text\)\}\)"\s*\)',
     'self.log("$ " + tf("msg_clip_result", n=len(text)))',
     'msg_clip_result'),
]


def main() -> int:
    if not APP.exists():
        print(f"!! не найден: {APP}")
        return 1

    src = APP.read_text(encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = APP.with_suffix(APP.suffix + f".bak_i18n3_{stamp}")
    shutil.copy2(APP, bak)
    print(f"бэкап:  {bak.name}\n")

    total = 0
    skipped: list[str] = []

    for pattern, repl, label in RULES:
        try:
            new, n = re.subn(pattern, repl, src,
                             flags=re.MULTILINE | re.DOTALL)
        except re.error as e:
            print(f"!! regex error [{label}]: {e}")
            skipped.append(label)
            continue
        if n == 0:
            skipped.append(label)
            continue
        src = new
        total += n
        print(f"+  [{n:>2}]  {label}")

    APP.write_text(src, encoding="utf-8")

    print()
    print(f"заменено вхождений: {total}")
    if skipped:
        print(f"\nне найдено ({len(skipped)}):")
        for s in skipped:
            print(f"  - {s}")

    # --- финальный отчёт ---
    print("\n--- остались русские буквы в СТРОКАХ (без комментариев) ---")
    ru = re.compile(r'[А-Яа-яЁё]')
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        # пропускаем чистые комментарии и docstrings-триггеры
        if stripped.startswith("#"):
            continue
        if not ru.search(line):
            continue
        print(f"  {i:>5}: {line.strip()[:90]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())