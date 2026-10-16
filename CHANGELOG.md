# ChangeLog

**🌐 Языки / Languages:** [Русский](#russian) · [English](#english)

---

## Russian

Все значимые изменения проекта **Esolang Translator**.
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — по [Semantic Versioning](https://semver.org/lang/ru/).

[↑ К языкам](#changelog)

---

### [2.6.0] — 2026

#### Добавлено

- 🌐 **Многоязычный интерфейс** — 6 языков: English, Русский, Deutsch, Español, Français, Italiano
- 📂 Папка `locales/` — файлы переводов UI
- 📄 `locales/about.json` — вкладка «О программе» на 6 языках
- 🎨 Под-вкладка **«Интерфейс → Язык»** — переключение языка без перезапуска
- 🔧 Утилиты в `tools/`: `i18n_status.py`, `fix_app_i18n.py`
- 📦 `core/i18n.py` — центральный модуль локализации

#### Изменено

- 🔖 Версия проекта: **2.5 → 2.6**
- 📝 `build.ps1` — VERSION = 2.6, в сборку включена папка `locales/`, добавлен `--version-file`
- 📖 `README.md` — единый многоязычный файл (6 секций, переключатель сверху)
- 🌍 Комбобоксы **«Режим»** и **«Тип»** теперь читают локализованные метки
- 🗂️ Вкладки и кнопки переведены через ключи `tab_*`, `btn_*`

#### Исправлено

- 🐛 **Шаблоны пропадали при смене языка** — фильтр типа сравнивал локализованную метку с русскими ключами
- 🐛 **Комбобокс «Режим» показывал `cat_regular = cat_regular`** — добавлены ключи `cat_regular` / `cat_esoteric`
- 🐛 **Синтаксическая ошибка в `ui/app.py`** — разорванный многострочный литерал в `_on_theme_select`
- 🐛 **`_on_btn_select` был определён вне класса** — вынесен на уровень `App`
- 🐛 **Вызов несуществующего `_build_tab_xxx`** в `_build()` — удалён
- 🐛 **`_load_tab_widget` падал** на `RivuletCanvasTab` / `PietCanvasTab` — теперь различает widget и контроллер

#### Удалено

- 🗑️ Функция `_no_mark` — не использовалась
- 🗑️ Поля `_prev_dst`, `_last_result` — не использовались
- 🗑️ Вложенный `def _style_ttk` внутри `_apply_selected_theme` — мёртвый код

---

### [2.5] — 2026

#### Добавлено

- 🎨 Вкладка **Piet Canvas** с тремя режимами отображения
- 🧩 Вкладка **Мозаика** (BlockPiet) с конструктором из плиток
- 🎯 Вкладка **Piet-ASM** с текстовым ассемблером
- 🧪 Вкладка **Песочница** — изолированный запуск кода с таймаутом
- 📝 Вкладка **Примеры (TXT)** — все шаблоны всех языков одним текстом
- 🔌 Поддержка **плагинов** `.py` без перезапуска приложения
- 🎨 **38 тем** оформления
- 🌐 **2D-редакторы** Rivulet и Piet
- 📋 **Переклассификация шаблонов** — `[1] → [E1]`, `[Test] → [T1]`
- 🔄 **Универсальный fallback** — 1746 направлений перевода

---

### [2.0] — 2025

Первый публичный релиз:

- 43 языка (обычных + эзотерических)
- Перевод между парами языков
- Подсветка синтаксиса для каждого языка
- Базовые темы оформления

[↑ К языкам](#changelog)

---

## English

All notable changes to the **Esolang Translator** project.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/).

[↑ Languages](#changelog)

---

### [2.6.0] — 2026

#### Added

- 🌐 **Multilingual UI** — 6 languages: English, Русский, Deutsch, Español, Français, Italiano
- 📂 `locales/` folder — UI translation files
- 📄 `locales/about.json` — About tab in 6 languages
- 🎨 **Interface → Language** sub-tab — switch language without restart
- 🔧 Utilities in `tools/`: `i18n_status.py`, `fix_app_i18n.py`
- 📦 `core/i18n.py` — central localisation module

#### Changed

- 🔖 Project version: **2.5 → 2.6**
- 📝 `build.ps1` — VERSION = 2.6, includes `locales/`, added `--version-file`
- 📖 `README.md` — unified multilingual file (6 sections, switcher on top)
- 🌍 **"Mode"** and **"Type"** comboboxes now read localized labels
- 🗂️ Tabs and buttons translated via `tab_*`, `btn_*` keys

#### Fixed

- 🐛 **Templates disappeared on language switch** — type filter compared localized label with Russian keys
- 🐛 **"Mode" combobox showed `cat_regular = cat_regular`** — added `cat_regular` / `cat_esoteric` keys
- 🐛 **Syntax error in `ui/app.py`** — broken multiline literal in `_on_theme_select`
- 🐛 **`_on_btn_select` defined outside the class** — moved to `App` level
- 🐛 **Call to non-existent `_build_tab_xxx`** in `_build()` — removed
- 🐛 **`_load_tab_widget` crashed** on `RivuletCanvasTab` / `PietCanvasTab` — now distinguishes widget and controller

#### Removed

- 🗑️ `_no_mark` function — unused
- 🗑️ `_prev_dst`, `_last_result` fields — unused
- 🗑️ Nested `def _style_ttk` inside `_apply_selected_theme` — dead code

---

### [2.5] — 2026

#### Added

- 🎨 **Piet Canvas** tab with three display modes
- 🧩 **Mosaic** (BlockPiet) tab with tile constructor
- 🎯 **Piet-ASM** tab with text assembler
- 🧪 **Sandbox** tab — isolated code execution with timeout
- 📝 **Examples (TXT)** tab — all templates in one text
- 🔌 **Plugins** `.py` — load without restart
- 🎨 **38 themes**
- 🌐 **2D editors** Rivulet and Piet
- 📋 **Template reclassification** — `[1] → [E1]`, `[Test] → [T1]`
- 🔄 **Universal fallback** — 1746 translation directions

---

### [2.0] — 2025

First public release:

- 43 languages (regular + esoteric)
- Translation between language pairs
- Syntax highlighting for each language
- Basic themes

[↑ Languages](#changelog)
