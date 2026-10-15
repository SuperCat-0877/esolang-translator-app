# Esolang Translator

**Многоязычная среда разработки для эзотерических и обычных языков программирования.**

43 языка · 1806 направлений перевода · 38 тем · 2D-редакторы Rivulet и Piet

[![Release](https://img.shields.io/github/v/release/SuperCat-0877/esolang-translator-app)](https://github.com/SuperCat-0877/esolang-translator-app/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

---

## 📸 Скриншоты

### Перевод между языками

![Главное окно](docs/screenshots/main.png)

*Python → Brainfuck. Выбираете языки, режим, шаблон — нажимаете F5.*

### Rivulet Canvas

![Rivulet Canvas](docs/screenshots/rivulet.png)

*2D-редактор Rivulet с сеткой глифов и палитрой команд.*

### Piet-ASM

![Piet-ASM](docs/screenshots/piet_asm.png)

*Текстовый ассемблер Piet: `push`, `add`, `out_num` → компиляция в Piet.*

### Мозаика (BlockPiet)

![Мозаика](docs/screenshots/mosaic.png)

*Плиточная визуализация кода: BYTE-плитки, шаблоны, визуальная сборка программ.*

### Песочница

![Песочница](docs/screenshots/sandbox.png)

*Изолированный запуск кода с таймаутом и вкладкой «Разбор».*

### 38 тем оформления

![Темы](docs/screenshots/themes.png)

*От тёмных до светлых пастельных. Автоматическая глубина интерфейса.*

---

## ✨ Возможности

- **43 языка** — от обычных (Python, JavaScript, C++, Java, Go, Rust, Ruby, PHP, Kotlin, Swift, Scala, Julia, Dart, TypeScript, Elixir, F#, R, Perl, Lua, C#) до эзотерических (Brainfuck, Piet, Rivulet, Whitespace, Ook, Malbolge, Cow, Chicken, Shakespeare, LOLCODE, Befunge, Intercal, Unlambda, Deadfish, Pika, Thue, Hodor, ArnoldC).
- **1806 направлений перевода** между всеми парами языков.
- **4 режима перевода** — О=О, О=Э, Э=О, Э=Э.
- **38 тем** — 3 базовые, 5 классических, радуга, оттенки голубого / красного / фиолетового, 10 светлых пастельных.
- **2D-редакторы** — Rivulet Canvas и Piet Canvas с сеткой глифов.
- **Piet-ASM** — текстовый ассемблер Piet с плитками 16×16.
- **Мозаика** — плиточная визуализация кода (BlockPiet).
- **Песочница** — изолированный запуск кода с таймаутом.
- **Плагины** `.py` — загрузка без перезапуска приложения.
- **Шаблоны** — редактирование в UI, импорт/экспорт в `.txt`.
- **Переименование** языков, кнопок, пользовательские цвета списков.

---

## 🚀 Установка

### Готовый `.exe` (рекомендуется)

Скачайте `EsolangTranslator.exe` из раздела [**Releases**](../../releases).

1. Положите `.exe` в любую папку (например, `D:\Apps\EsolangTranslator\`)
2. Запустите

При первом запуске рядом появятся:
- `config.json` — настройки
- `plugins/` — пользовательские плагины
- `langs_disabled/` — отключённые языки

**Требования:**
- Windows 10 / 11 (64-bit)
- Ничего дополнительно ставить не нужно — Python и библиотеки внутри

**Для Windows 7 SP1 / 8:** требуется отдельная сборка под Python 3.8.10 (см. ниже).

### Из исходников

```bash
git clone https://github.com/SuperCat-0877/esolang-translator-app.git
cd esolang-translator-app
pip install -r requirements.txt
python Main.py