# Esolang Translator

**🌐 Languages:** [Русский](#russian) · [English](#english) · [Deutsch](#german) · [Español](#spanish) · [Français](#french) · [Italiano](#italian)

[![Release](https://img.shields.io/github/v/release/SuperCat-0877/esolang-translator-app)](https://github.com/SuperCat-0877/esolang-translator-app/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Changelog](https://img.shields.io/badge/changelog-v2.6.0-blue)](CHANGELOG.md)

Get-Item .\CHANGELOG.md
Get-Content .\CHANGELOG.md | Select-Object -First 5
---

## Russian

**Многоязычная среда разработки для эзотерических и обычных языков программирования.**

43 языка · 1746 направлений перевода · 38 тем · 2D-редакторы Rivulet и Piet

[↑ К языкам](#esolang-translator)

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
- **1746 направлений перевода** между всеми парами языков.
- **4 режима перевода** — О=О, О=Э, Э=О, Э=Э.
- **38 тем** — 3 базовые, 5 классических, радуга, оттенки голубого / красного / фиолетового, 10 светлых пастельных.
- **2D-редакторы** — Rivulet Canvas и Piet Canvas с сеткой глифов.
- **Piet-ASM** — текстовый ассемблер Piet с плитками 16×16.
- **Мозаика** — плиточная визуализация кода (BlockPiet).
- **Песочница** — изолированный запуск кода с таймаутом.
- **Плагины** `.py` — загрузка без перезапуска приложения.
- **Шаблоны** — редактирование в UI, импорт/экспорт в `.txt`.
- **Переименование** языков, кнопок, пользовательские цвета списков.
- **6 языков интерфейса** — English, Русский, Deutsch, Español, Français, Italiano.

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
Текущий код рассчитан на **Python 3.10+**.

### Из исходников

```bash
git clone https://github.com/SuperCat-0877/esolang-translator-app.git
cd esolang-translator-app
pip install -r requirements.txt
python Main.py
```

---

## 🙏 Благодарности

- [Daniel Temkin](https://github.com/danieltemkin) — оригинальный интерпретатор Rivulet
- [rdbende](https://github.com/rdbende) — Sun Valley ttk theme (`sv-ttk`)

---

## ⚠️ Важное примечание: BlockPiet и BrainPiet

В списке языков есть **BlockPiet** и **BrainPiet**, которые могут ввести
в заблуждение. Это **не самостоятельные языки** — это **разновидности Piet**
(и частично Brainfuck), адаптированные для демонстрации разных подходов
к визуальному программированию.

### BlockPiet

**Что это:** модификация Piet, где программа собирается из **плиток (blocks)**,
а не рисуется вручную.

**Чем отличается от Piet:**
- Плитки уже заданы — пользователь выбирает из библиотеки `BYTE #0`–`BYTE #14`
- Есть готовые шаблоны: `print(0)`, `print(1)`, `print(42)`, `print(100)`, `print(a)`, `print(b)` и т. д.
- Работает через вкладку **«Мозаика»** — визуальный конструктор
- Собирается на лету, без ручного рисования сетки

**Для чего:** обучение, быстрая визуализация базовых операций Piet,
демонстрация идеи «программа = набор плиток».

### BrainPiet

**Что это:** гибрид **Brainfuck и Piet** — где логика выражения заимствована
из Brainfuck, а визуализация — из Piet.

**Чем отличается:**
- Внутри — команды Brainfuck (`+`, `-`, `>`, `<`, `.`, `,`)
- Снаружи — визуальное представление через **2D-сетку глифов Piet**
- Промежуточный вариант: проще, чем чистый Piet, но визуальнее, чем обычный Brainfuck

**Для чего:** плавный переход от линейных языков (Brainfuck) к 2D-языкам (Piet) — учебный мост.

### Что это значит для вас

- **Не ожидайте** от BlockPiet и BrainPiet полной совместимости с оригинальным Piet или Brainfuck.
- **Не путайте** их с оригинальными реализациями — эти языки созданы **внутри проекта** как учебные / демонстрационные.
- **Используйте** их как **дополнительные примеры** — они показывают, что эзотерические языки могут быть адаптированы под разные задачи.

### Настоящие Piet и Brainfuck

Оригинальные реализации тоже **присутствуют**:

| Язык | Что это |
|---|---|
| **Piet** | Полноценный Piet с холстом 16×16 и 20 цветами |
| **Piet-ASM** | Ассемблер Piet — текст → плитки |
| **Brainfuck** | Полная реализация классического Brainfuck |

Если хотите **чистый** Piet или Brainfuck — используйте **эти** названия в списке языков, а не BlockPiet / BrainPiet.

---

## 💬 Обратная связь

**Почта:** [Kanadegameyalybly@gmail.com](mailto:Kanadegameyalybly@gmail.com)

Проект развивается как одиночная разработка, и **любое сообщение помогает сделать его лучше**. Пишите — я читаю всё, даже если не отвечаю мгновенно.

### 🐛 Сообщить об ошибке

Что-то не работает, падает, выдаёт неправильный результат? Пришлите описание — я исправлю в следующей версии. Особенно важно для:

- Переводов между редкими парами языков
- Rivulet / Piet — 2D-редакторов
- Песочницы и Piet-ASM
- Сборки `.exe` на вашей системе

### 💡 Предложить идею

Есть мысль, чего не хватает? Присылайте:

- **Новый язык** — эзотерический или обычный. Если знаете интересный — добавлю
- **Новую тему** — цветовая схема, тёмная / светлая / пастельная
- **Новый режим перевода** или комбинацию
- **Улучшение интерфейса** — что неудобно, где запутанно
- **Новую вкладку** или функцию

### 🔧 Попросить функцию

Если чего-то не хватает в текущей версии — скажите. Например:

- Экспорт в другой формат (не только `.txt`)
- Интеграция с внешним редактором
- Автосохранение при закрытии
- Поддержка конкретного языка или диалекта

### 🌐 Прислать свой плагин

Написали язык в `plugins/mylang.py`? Пришлите код — **добавлю в коллекцию** и упомяну вас в благодарностях.

### 📝 Исправить опечатки и перевод

Русский интерфейс, тексты в About, README — если нашли ошибку или кривой перевод, пришлите. Такие мелочи видны только со стороны.

### 🤝 Сотрудничество

Хотите помочь с развитием проекта?

- **Тестирование** на другой ОС (Linux, macOS, Windows 7)
- **Сборка `.exe`** под Python 3.8.10 для Windows 7 SP1 / 8
- **Документация** — гайды, туториалы, статьи
- **Дизайн** — иконки, темы, скриншоты
- **Код** — если готовы прислать PR на GitHub

### 📜 Вопросы по лицензии

Использование в коммерческом проекте, форки, распространение в составе другого продукта — если что-то неясно, спросите. MIT разрешает почти всё, но иногда лучше уточнить.

### 🎓 Обучение и вопросы

Если вы **преподаёте эзотерические языки** или **учитесь сами** — расскажите, как используете проект. Мне интересно, что помогает, а что мешает. Обратная связь от преподавателей особенно ценна.

### 📋 Что указать в письме

Чтобы я мог быстро разобраться, в **первом письме** укажите:

| Пункт | Пример |
|---|---|
| **Версия** | `2.6.0` — видно во вкладке «О программе» (F1) |
| **ОС** | Windows 10 22H2 / Windows 11 / Linux Mint 21 |
| **Как запускаете** | `.exe` или `python Main.py` |
| **Что делали** | «Выбрал Python → Brainfuck, нажал F5» |
| **Что ожидали** | «Перевод появится справа» |
| **Что получили** | «Пустое поле, в терминале ошибка» |
| **Скриншот** | Если ошибка визуальная |
| **Лог** | `app.log` рядом с `.exe`, если был краш |

**Тема письма:** кратко — например, `[Bug] Rivulet не открывает .riv-файл`.

### 🕐 Сроки ответа

Отвечаю в течение **2–3 рабочих дней**. Баги исправляю в первую очередь, фичи — по мере возможности. Если письмо потерялось — напишите повторно, почта иногда глючит.

### 🔗 Альтернативы

Если предпочитаете GitHub:

- 🐛 [**Issues**](https://github.com/SuperCat-0877/esolang-translator-app/issues) — баги и идеи
- 💬 [**Discussions**](https://github.com/SuperCat-0877/esolang-translator-app/discussions) — общие вопросы (если включу)

**Но почта — быстрее.** Присылайте туда.

---

**© 2026 Esolang Translator**

[↑ К языкам](#esolang-translator)

---

## English

**Multilingual IDE for esoteric and regular programming languages.**

43 languages · 1746 translation directions · 38 themes · 2D editors for Rivulet and Piet

[↑ Languages](#esolang-translator)

---

## 📸 Screenshots

### Translation between languages

![Main window](docs/screenshots/main.png)

*Python → Brainfuck. Pick languages, mode, template — press F5.*

### Rivulet Canvas

![Rivulet Canvas](docs/screenshots/rivulet.png)

*2D editor for Rivulet with a glyph grid and command palette.*

### Piet-ASM

![Piet-ASM](docs/screenshots/piet_asm.png)

*Text assembler for Piet: `push`, `add`, `out_num` → compiled to Piet.*

### Mosaic (BlockPiet)

![Mosaic](docs/screenshots/mosaic.png)

*Tile-based code view: BYTE tiles, templates, visual program assembly.*

### Sandbox

![Sandbox](docs/screenshots/sandbox.png)

*Isolated code execution with timeout and an “Explain” tab.*

### 38 themes

![Themes](docs/screenshots/themes.png)

*From dark to light pastel. Automatic UI contrast.*

---

## ✨ Features

- **43 languages** — regular (Python, JavaScript, C++, Java, Go, Rust, Ruby, PHP, Kotlin, Swift, Scala, Julia, Dart, TypeScript, Elixir, F#, R, Perl, Lua, C#) and esoteric (Brainfuck, Piet, Rivulet, Whitespace, Ook, Malbolge, Cow, Chicken, Shakespeare, LOLCODE, Befunge, Intercal, Unlambda, Deadfish, Pika, Thue, Hodor, ArnoldC).
- **1746 translation directions** between all language pairs.
- **4 translation modes** — R=R, R=E, E=R, E=E.
- **38 themes** — 3 base, 5 classic, rainbow, shades of blue / red / purple, 10 light pastel.
- **2D editors** — Rivulet Canvas and Piet Canvas with glyph grid.
- **Piet-ASM** — text assembler for Piet with 16×16 tiles.
- **Mosaic** — tile-based code view (BlockPiet).
- **Sandbox** — isolated code execution with timeout.
- **Plugins** `.py` — loaded without restarting the app.
- **Templates** — edit in UI, import/export to `.txt`.
- **Rename** languages, buttons, custom list colors.
- **6 UI languages** — English, Русский, Deutsch, Español, Français, Italiano.

---

## 🚀 Installation

### Pre-built `.exe` (recommended)

Download `EsolangTranslator.exe` from [**Releases**](../../releases).

1. Put the `.exe` in any folder (e.g. `D:\Apps\EsolangTranslator\`)
2. Run it

On first launch the following appear next to it:

- `config.json` — settings
- `plugins/` — user plugins
- `langs_disabled/` — disabled languages

**Requirements:**
- Windows 10 / 11 (64-bit)
- Nothing else to install — Python and libraries are bundled

**Windows 7 SP1 / 8:** requires a separate build with Python 3.8.10 (see below).
The current codebase targets **Python 3.10+**.

### From source

```bash
git clone https://github.com/SuperCat-0877/esolang-translator-app.git
cd esolang-translator-app
pip install -r requirements.txt
python Main.py
```

---

## 🙏 Credits

- [Daniel Temkin](https://github.com/danieltemkin) — original Rivulet interpreter
- [rdbende](https://github.com/rdbende) — Sun Valley ttk theme (`sv-ttk`)

---

## ⚠️ Important: BlockPiet and BrainPiet

The language list contains **BlockPiet** and **BrainPiet**, which can be misleading.
They are **not standalone languages** — they are **variants of Piet** (partly
Brainfuck) adapted to demonstrate different approaches to visual programming.

### BlockPiet

**What it is:** a Piet variant where a program is assembled from **tiles (blocks)**
rather than drawn by hand.

**Differences from Piet:**
- Tiles are predefined — pick from the `BYTE #0`–`BYTE #14` library
- Ready-made templates: `print(0)`, `print(1)`, `print(42)`, `print(100)`, `print(a)`, `print(b)`, etc.
- Works through the **Mosaic** tab — a visual builder
- Assembled on the fly, no manual grid drawing

**Use for:** learning, quick visualisation of basic Piet operations, demoing
the idea “program = set of tiles”.

### BrainPiet

**What it is:** a hybrid of **Brainfuck and Piet** — the expression logic
comes from Brainfuck, the visualisation from Piet.

**Differences:**
- Inside — Brainfuck commands (`+`, `-`, `>`, `<`, `.`, `,`)
- Outside — visual representation via a **2D grid of Piet glyphs**
- Intermediate option: simpler than pure Piet, more visual than plain Brainfuck

**Use for:** smooth transition from linear languages (Brainfuck) to 2D languages
(Piet) — a learning bridge.

### What this means for you

- **Do not expect** full compatibility with original Piet or Brainfuck from BlockPiet / BrainPiet.
- **Do not confuse** them with the original implementations — these languages
  are created **inside the project** as learning / demo.
- **Use them** as **additional examples** — they show how esoteric languages
  can be adapted for different tasks.

### Real Piet and Brainfuck

The original implementations are **also present**:

| Language | What it is |
|---|---|
| **Piet** | Full Piet with 16×16 canvas and 20 colors |
| **Piet-ASM** | Piet assembler — text → tiles |
| **Brainfuck** | Full implementation of classic Brainfuck |

If you want **pure** Piet or Brainfuck — use **those** names in the language list,
not BlockPiet / BrainPiet.

---

## 💬 Feedback

**Email:** [Kanadegameyalybly@gmail.com](mailto:Kanadegameyalybly@gmail.com)

The project is developed solo, and **every message helps make it better**.
Write — I read everything, even if I don’t reply instantly.

### 🐛 Report a bug

Something doesn’t work, crashes, gives a wrong result? Send a description —
I’ll fix it in the next version. Especially important for:

- Translations between rare language pairs
- Rivulet / Piet — 2D editors
- Sandbox and Piet-ASM
- Building the `.exe` on your system

### 💡 Suggest an idea

Have an idea of what’s missing? Send:

- **New language** — esoteric or regular. If you know an interesting one — I’ll add it
- **New theme** — color scheme, dark / light / pastel
- **New translation mode** or combination
- **UI improvement** — what’s inconvenient, what’s confusing
- **New tab** or feature

### 🔧 Request a feature

If something’s missing in the current version — say so. For example:

- Export to another format (not only `.txt`)
- Integration with an external editor
- Autosave on close
- Support for a specific language or dialect

### 🌐 Submit your plugin

Wrote a language in `plugins/mylang.py`? Send the code — **I’ll add it to the
collection** and credit you.

### 📝 Fix typos and translations

Russian UI, About text, README — if you find a mistake or awkward translation,
send it. Such little things are only visible from the outside.

### 🤝 Collaboration

Want to help develop the project?

- **Testing** on another OS (Linux, macOS, Windows 7)
- **Building `.exe`** with Python 3.8.10 for Windows 7 SP1 / 8
- **Documentation** — guides, tutorials, articles
- **Design** — icons, themes, screenshots
- **Code** — if you’re ready to send a PR on GitHub

### 📜 License questions

Commercial use, forks, redistribution as part of another product — if anything
is unclear, ask. MIT allows almost everything, but sometimes it’s better to clarify.

### 🎓 Teaching and questions

If you **teach esoteric languages** or **learn yourself** — tell me how you use
the project. I’m curious what helps and what hinders. Feedback from teachers is
especially valuable.

### 📋 What to include in your message

So I can figure it out fast, in the **first message** include:

| Item | Example |
|---|---|
| **Version** | `2.6.0` — visible in the About tab (F1) |
| **OS** | Windows 10 22H2 / Windows 11 / Linux Mint 21 |
| **How you run it** | `.exe` or `python Main.py` |
| **What you did** | “Selected Python → Brainfuck, pressed F5” |
| **What you expected** | “Translation appears on the right” |
| **What you got** | “Empty field, error in terminal” |
| **Screenshot** | If the error is visual |
| **Log** | `app.log` next to `.exe`, if there was a crash |

**Subject:** short — e.g. `[Bug] Rivulet doesn't open .riv files`.

### 🕐 Response time

I reply within **2–3 business days**. Bugs first, features as I can. If a message
got lost — write again, email sometimes glitches.

### 🔗 Alternatives

If you prefer GitHub:

- 🐛 [**Issues**](https://github.com/SuperCat-0877/esolang-translator-app/issues) — bugs and ideas
- 💬 [**Discussions**](https://github.com/SuperCat-0877/esolang-translator-app/discussions) — general questions (if enabled)

**But email is faster.** Send it there.

---

**© 2026 Esolang Translator**

[↑ Languages](#esolang-translator)

---

## German

**Mehrsprachige IDE für esoterische und reguläre Programmiersprachen.**

43 Sprachen · 1746 Übersetzungsrichtungen · 38 Themes · 2D-Editoren für Rivulet und Piet

[↑ Sprachen](#esolang-translator)

---

## 📸 Screenshots

### Übersetzung zwischen Sprachen

![Hauptfenster](docs/screenshots/main.png)

*Python → Brainfuck. Sprachen, Modus, Vorlage wählen — F5 drücken.*

### Rivulet Canvas

![Rivulet Canvas](docs/screenshots/rivulet.png)

*2D-Editor für Rivulet mit Glyphen-Raster und Befehlspalette.*

### Piet-ASM

![Piet-ASM](docs/screenshots/piet_asm.png)

*Textassembler für Piet: `push`, `add`, `out_num` → Kompilierung nach Piet.*

### Mosaik (BlockPiet)

![Mosaik](docs/screenshots/mosaic.png)

*Kachelbasierte Code-Ansicht: BYTE-Kacheln, Vorlagen, visueller Programmaufbau.*

### Sandkasten

![Sandkasten](docs/screenshots/sandbox.png)

*Isolierte Codeausführung mit Timeout und „Erklären“-Tab.*

### 38 Themes

![Themes](docs/screenshots/themes.png)

*Von dunkel bis hell pastell. Automatischer UI-Kontrast.*

---

## ✨ Funktionen

- **43 Sprachen** — reguläre (Python, JavaScript, C++, Java, Go, Rust, Ruby, PHP, Kotlin, Swift, Scala, Julia, Dart, TypeScript, Elixir, F#, R, Perl, Lua, C#) und esoterische (Brainfuck, Piet, Rivulet, Whitespace, Ook, Malbolge, Cow, Chicken, Shakespeare, LOLCODE, Befunge, Intercal, Unlambda, Deadfish, Pika, Thue, Hodor, ArnoldC).
- **1746 Übersetzungsrichtungen** zwischen allen Sprachpaaren.
- **4 Übersetzungsmodi** — R=R, R=E, E=R, E=E.
- **38 Themes** — 3 Basis, 5 klassisch, Regenbogen, Blau-/Rot-/Violett-Töne, 10 helle Pastell.
- **2D-Editoren** — Rivulet Canvas und Piet Canvas mit Glyphen-Raster.
- **Piet-ASM** — Textassembler für Piet mit 16×16-Kacheln.
- **Mosaik** — kachelbasierte Code-Ansicht (BlockPiet).
- **Sandkasten** — isolierte Codeausführung mit Timeout.
- **Plugins** `.py` — laden ohne App-Neustart.
- **Vorlagen** — Bearbeitung in der UI, Import/Export nach `.txt`.
- **Umbenennen** von Sprachen, Buttons, benutzerdefinierten Listenfarben.
- **6 UI-Sprachen** — English, Русский, Deutsch, Español, Français, Italiano.

---

## 🚀 Installation

### Fertige `.exe` (empfohlen)

Laden Sie `EsolangTranslator.exe` aus [**Releases**](../../releases) herunter.

1. Legen Sie die `.exe` in einen beliebigen Ordner (z. B. `D:\Apps\EsolangTranslator\`)
2. Starten Sie sie

Beim ersten Start erscheinen daneben:

- `config.json` — Einstellungen
- `plugins/` — Benutzer-Plugins
- `langs_disabled/` — deaktivierte Sprachen

**Anforderungen:**
- Windows 10 / 11 (64-Bit)
- Sonst nichts zu installieren — Python und Bibliotheken sind eingebettet

**Windows 7 SP1 / 8:** erfordert einen separaten Build mit Python 3.8.10 (siehe unten).
Der aktuelle Code zielt auf **Python 3.10+**.

### Aus dem Quellcode

```bash
git clone https://github.com/SuperCat-0877/esolang-translator-app.git
cd esolang-translator-app
pip install -r requirements.txt
python Main.py
```

---

## 🙏 Danksagungen

- [Daniel Temkin](https://github.com/danieltemkin) — Original-Rivulet-Interpreter
- [rdbende](https://github.com/rdbende) — Sun Valley ttk theme (`sv-ttk`)

---

## ⚠️ Wichtig: BlockPiet und BrainPiet

In der Sprachliste gibt es **BlockPiet** und **BrainPiet**, die irreführend sein können.
Sie sind **keine eigenständigen Sprachen** — sie sind **Varianten von Piet**
(teilweise Brainfuck), angepasst, um verschiedene Ansätze der visuellen
Programmierung zu demonstrieren.

### BlockPiet

**Was es ist:** eine Piet-Variante, bei der ein Programm aus **Kacheln (blocks)**
zusammengesetzt wird statt von Hand gezeichnet.

**Unterschiede zu Piet:**
- Kacheln sind vorgegeben — Auswahl aus der Bibliothek `BYTE #0`–`BYTE #14`
- Fertige Vorlagen: `print(0)`, `print(1)`, `print(42)`, `print(100)`, `print(a)`, `print(b)` usw.
- Arbeitet über den **Mosaik**-Tab — ein visueller Builder
- Wird on-the-fly zusammengesetzt, kein manuelles Rasterzeichnen

**Nutzen:** Lernen, schnelle Visualisierung grundlegender Piet-Operationen,
Demonstration der Idee „Programm = Satz von Kacheln“.

### BrainPiet

**Was es ist:** ein Hybrid aus **Brainfuck und Piet** — Ausdruckslogik aus
Brainfuck, Visualisierung aus Piet.

**Unterschiede:**
- Innen — Brainfuck-Befehle (`+`, `-`, `>`, `<`, `.`, `,`)
- Außen — visuelle Darstellung über ein **2D-Raster aus Piet-Glyphen**
- Zwischenvariante: einfacher als reines Piet, visueller als normales Brainfuck

**Nutzen:** sanfter Übergang von linearen Sprachen (Brainfuck) zu 2D-Sprachen
(Piet) — eine Lernbrücke.

### Was das für Sie bedeutet

- **Erwarten Sie nicht** volle Kompatibilität mit Original-Piet oder -Brainfuck
  von BlockPiet / BrainPiet.
- **Verwechseln Sie sie nicht** mit den Originalimplementierungen — diese Sprachen
  entstehen **innerhalb des Projekts** als Lern-/Demo-Material.
- **Nutzen Sie sie** als **zusätzliche Beispiele** — sie zeigen, wie esoterische
  Sprachen für verschiedene Aufgaben angepasst werden können.

### Echtes Piet und Brainfuck

Die Originalimplementierungen sind **ebenfalls vorhanden**:

| Sprache | Was es ist |
|---|---|
| **Piet** | Vollständiges Piet mit 16×16-Raster und 20 Farben |
| **Piet-ASM** | Piet-Assembler — Text → Kacheln |
| **Brainfuck** | Vollständige Implementierung des klassischen Brainfuck |

Wenn Sie **reines** Piet oder Brainfuck wollen — verwenden Sie **diese** Namen
in der Sprachliste, nicht BlockPiet / BrainPiet.

---

## 💬 Feedback

**E-Mail:** [Kanadegameyalybly@gmail.com](mailto:Kanadegameyalybly@gmail.com)

Das Projekt wird allein entwickelt, und **jede Nachricht hilft, es besser zu machen**.
Schreiben Sie — ich lese alles, auch wenn ich nicht sofort antworte.

### 🐛 Bug melden

Etwas funktioniert nicht, stürzt ab, liefert ein falsches Ergebnis? Senden Sie
eine Beschreibung — ich behebe es in der nächsten Version. Besonders wichtig für:

- Übersetzungen zwischen seltenen Sprachpaaren
- Rivulet / Piet — 2D-Editoren
- Sandkasten und Piet-ASM
- Build der `.exe` auf Ihrem System

### 💡 Idee vorschlagen

Haben Sie eine Idee, was fehlt? Senden Sie:

- **Neue Sprache** — esoterisch oder regulär. Kennen Sie eine interessante — ich füge sie hinzu
- **Neues Theme** — Farbschema, dunkel / hell / pastell
- **Neuer Übersetzungsmodus** oder Kombination
- **UI-Verbesserung** — was unbequem, was verwirrend ist
- **Neuer Tab** oder Funktion

### 🔧 Funktion anfragen

Fehlt etwas in der aktuellen Version — sagen Sie es. Zum Beispiel:

- Export in ein anderes Format (nicht nur `.txt`)
- Integration mit externem Editor
- Autospeichern beim Schließen
- Unterstützung einer bestimmten Sprache oder eines Dialekts

### 🌐 Plugin einsenden

Haben Sie eine Sprache in `plugins/mylang.py` geschrieben? Senden Sie den Code —
**ich nehme ihn in die Sammlung auf** und nenne Sie in den Danksagungen.

### 📝 Tippfehler und Übersetzungen korrigieren

Russische UI, About-Text, README — wenn Sie einen Fehler oder eine krumme
Übersetzung finden, senden Sie sie. Solche Kleinigkeiten sieht man nur von außen.

### 🤝 Zusammenarbeit

Möchten Sie bei der Entwicklung helfen?

- **Tests** auf einem anderen OS (Linux, macOS, Windows 7)
- **Build der `.exe`** mit Python 3.8.10 für Windows 7 SP1 / 8
- **Dokumentation** — Guides, Tutorials, Artikel
- **Design** — Icons, Themes, Screenshots
- **Code** — wenn Sie einen PR auf GitHub senden möchten

### 📜 Lizenzfragen

Kommerzielle Nutzung, Forks, Weitergabe als Teil eines anderen Produkts — wenn
etwas unklar ist, fragen Sie. MIT erlaubt fast alles, aber manchmal ist es besser,
nachzufragen.

### 🎓 Lehre und Fragen

Wenn Sie **esoterische Sprachen unterrichten** oder **selbst lernen** — erzählen
Sie, wie Sie das Projekt nutzen. Mich interessiert, was hilft und was stört.
Feedback von Lehrenden ist besonders wertvoll.

### 📋 Was in Ihre Nachricht gehört

Damit ich es schnell einordnen kann, geben Sie in der **ersten Nachricht** an:

| Punkt | Beispiel |
|---|---|
| **Version** | `2.6.0` — sichtbar im About-Tab (F1) |
| **OS** | Windows 10 22H2 / Windows 11 / Linux Mint 21 |
| **Start** | `.exe` oder `python Main.py` |
| **Was Sie taten** | „Python → Brainfuck gewählt, F5 gedrückt“ |
| **Was Sie erwarteten** | „Übersetzung erscheint rechts“ |
| **Was Sie bekamen** | „Leeres Feld, Fehler im Terminal“ |
| **Screenshot** | Wenn der Fehler visuell ist |
| **Log** | `app.log` neben der `.exe`, falls es einen Crash gab |

**Betreff:** kurz — z. B. `[Bug] Rivulet öffnet .riv-Dateien nicht`.

### 🕐 Antwortzeit

Ich antworte innerhalb von **2–3 Werktagen**. Bugs zuerst, Features so weit wie
möglich. Wenn eine Nachricht verloren ging — schreiben Sie erneut, E-Mails
hängen manchmal.

### 🔗 Alternativen

Wenn Sie GitHub bevorzugen:

- 🐛 [**Issues**](https://github.com/SuperCat-0877/esolang-translator-app/issues) — Bugs und Ideen
- 💬 [**Discussions**](https://github.com/SuperCat-0877/esolang-translator-app/discussions) — allgemeine Fragen (falls aktiviert)

**Aber E-Mail ist schneller.** Senden Sie dorthin.

---

**© 2026 Esolang Translator**

[↑ Sprachen](#esolang-translator)

---

## Spanish

**IDE multilingüe para lenguajes de programación esotéricos y regulares.**

43 lenguajes · 1746 direcciones de traducción · 38 temas · Editores 2D para Rivulet y Piet

[↑ Idiomas](#esolang-translator)

---

## 📸 Capturas

### Traducción entre lenguajes

![Ventana principal](docs/screenshots/main.png)

*Python → Brainfuck. Elige lenguajes, modo, plantilla — pulsa F5.*

### Rivulet Canvas

![Rivulet Canvas](docs/screenshots/rivulet.png)

*Editor 2D para Rivulet con rejilla de glifos y paleta de comandos.*

### Piet-ASM

![Piet-ASM](docs/screenshots/piet_asm.png)

*Ensamblador de texto para Piet: `push`, `add`, `out_num` → compilación a Piet.*

### Mosaico (BlockPiet)

![Mosaico](docs/screenshots/mosaic.png)

*Vista de código por mosaicos: fichas BYTE, plantillas, montaje visual.*

### Sandbox

![Sandbox](docs/screenshots/sandbox.png)

*Ejecución aislada de código con timeout y pestaña «Explicar».*

### 38 temas

![Temas](docs/screenshots/themes.png)

*De oscuros a pastel claros. Contraste automático de la UI.*

---

## ✨ Características

- **43 lenguajes** — regulares (Python, JavaScript, C++, Java, Go, Rust, Ruby, PHP, Kotlin, Swift, Scala, Julia, Dart, TypeScript, Elixir, F#, R, Perl, Lua, C#) y esotéricos (Brainfuck, Piet, Rivulet, Whitespace, Ook, Malbolge, Cow, Chicken, Shakespeare, LOLCODE, Befunge, Intercal, Unlambda, Deadfish, Pika, Thue, Hodor, ArnoldC).
- **1746 direcciones de traducción** entre todos los pares.
- **4 modos de traducción** — R=R, R=E, E=R, E=E.
- **38 temas** — 3 base, 5 clásicos, arcoíris, tonos azul / rojo / violeta, 10 pastel claros.
- **Editores 2D** — Rivulet Canvas y Piet Canvas con rejilla de glifos.
- **Piet-ASM** — ensamblador de texto para Piet con fichas 16×16.
- **Mosaico** — vista de código por mosaicos (BlockPiet).
- **Sandbox** — ejecución aislada de código con timeout.
- **Plugins** `.py` — cargados sin reiniciar la app.
- **Plantillas** — edición en UI, importación/exportación a `.txt`.
- **Renombrar** lenguajes, botones, colores de listas personalizados.
- **6 idiomas de UI** — English, Русский, Deutsch, Español, Français, Italiano.

---

## 🚀 Instalación

### `.exe` listo (recomendado)

Descarga `EsolangTranslator.exe` desde [**Releases**](../../releases).

1. Pon el `.exe` en cualquier carpeta (p. ej. `D:\Apps\EsolangTranslator\`)
2. Ejecútalo

En el primer arranque aparecen a su lado:

- `config.json` — ajustes
- `plugins/` — plugins de usuario
- `langs_disabled/` — lenguajes deshabilitados

**Requisitos:**
- Windows 10 / 11 (64-bit)
- No hace falta instalar nada más — Python y bibliotecas van dentro

**Windows 7 SP1 / 8:** requiere una compilación aparte con Python 3.8.10 (ver abajo).
El código actual apunta a **Python 3.10+**.

### Desde el código fuente

```bash
git clone https://github.com/SuperCat-0877/esolang-translator-app.git
cd esolang-translator-app
pip install -r requirements.txt
python Main.py
```

---

## 🙏 Créditos

- [Daniel Temkin](https://github.com/danieltemkin) — intérprete Rivulet original
- [rdbende](https://github.com/rdbende) — tema Sun Valley ttk (`sv-ttk`)

---

## ⚠️ Importante: BlockPiet y BrainPiet

En la lista hay **BlockPiet** y **BrainPiet**, que pueden resultar engañosos.
No son **lenguajes independientes** — son **variantes de Piet** (en parte
Brainfuck) adaptadas para demostrar distintos enfoques de programación visual.

### BlockPiet

**Qué es:** una variante de Piet donde el programa se arma con **mosaicos
(blocks)**, no se dibuja a mano.

**Diferencias de Piet:**
- Los mosaicos están predefinidos — se eligen de la biblioteca `BYTE #0`–`BYTE #14`
- Plantillas listas: `print(0)`, `print(1)`, `print(42)`, `print(100)`, `print(a)`, `print(b)`, etc.
- Funciona mediante la pestaña **Mosaico** — constructor visual
- Se arma al vuelo, sin dibujar la rejilla a mano

**Para qué:** aprendizaje, visualización rápida de operaciones básicas de Piet,
demostración de la idea «programa = conjunto de mosaicos».

### BrainPiet

**Qué es:** híbrido de **Brainfuck y Piet** — la lógica de expresión viene
de Brainfuck, la visualización de Piet.

**Diferencias:**
- Dentro — comandos Brainfuck (`+`, `-`, `>`, `<`, `.`, `,`)
- Fuera — representación visual mediante **rejilla 2D de glifos Piet**
- Opción intermedia: más simple que Piet puro, más visual que Brainfuck plano

**Para qué:** transición suave de lenguajes lineales (Brainfuck) a lenguajes 2D
(Piet) — puente de aprendizaje.

### Qué significa para ti

- **No esperes** compatibilidad total con Piet o Brainfuck originales en BlockPiet / BrainPiet.
- **No los confundas** con las implementaciones originales — estos lenguajes
  se crean **dentro del proyecto** como material de aprendizaje / demostración.
- **Úsalos** como **ejemplos adicionales** — muestran cómo se pueden adaptar
  lenguajes esotéricos a distintas tareas.

### Piet y Brainfuck de verdad

Las implementaciones originales **también están**:

| Lenguaje | Qué es |
|---|---|
| **Piet** | Piet completo con lienzo 16×16 y 20 colores |
| **Piet-ASM** | Ensamblador Piet — texto → fichas |
| **Brainfuck** | Implementación completa del Brainfuck clásico |

Si quieres **Piet o Brainfuck puros** — usa **esos** nombres en la lista de lenguajes, no BlockPiet / BrainPiet.

---

## 💬 Contacto

**Correo:** [Kanadegameyalybly@gmail.com](mailto:Kanadegameyalybly@gmail.com)

El proyecto se desarrolla en solitario y **cada mensaje ayuda a mejorarlo**.
Escribe — leo todo, aunque no responda al instante.

### 🐛 Reportar un bug

¿Algo no funciona, se cae, da un resultado equivocado? Manda una descripción —
lo arreglo en la próxima versión. Especialmente importante para:

- Traducciones entre pares de lenguajes raros
- Rivulet / Piet — editores 2D
- Sandbox y Piet-ASM
- Compilación del `.exe` en tu sistema

### 💡 Sugerir una idea

¿Tienes una idea de qué falta? Manda:

- **Nuevo lenguaje** — esotérico o regular. Si conoces uno interesante — lo añado
- **Nuevo tema** — esquema de color, oscuro / claro / pastel
- **Nuevo modo de traducción** o combinación
- **Mejora de UI** — qué es incómodo, qué confunde
- **Nueva pestaña** o función

### 🔧 Pedir una función

Si falta algo en la versión actual — dilo. Por ejemplo:

- Exportación a otro formato (no solo `.txt`)
- Integración con editor externo
- Autoguardado al cerrar
- Soporte de un lenguaje o dialecto concreto

### 🌐 Enviar tu plugin

¿Escribiste un lenguaje en `plugins/mylang.py`? Manda el código — **lo añadiré
a la colección** y te mencionaré en los créditos.

### 📝 Corregir typos y traducciones

UI en ruso, textos de About, README — si encuentras un error o una traducción
torpe, mándala. Estas cositas solo se ven desde fuera.

### 🤝 Colaboración

¿Quieres ayudar a desarrollar el proyecto?

- **Pruebas** en otro SO (Linux, macOS, Windows 7)
- **Compilar `.exe`** con Python 3.8.10 para Windows 7 SP1 / 8
- **Documentación** — guías, tutoriales, artículos
- **Diseño** — iconos, temas, capturas
- **Código** — si quieres enviar un PR en GitHub

### 📜 Dudas sobre la licencia

Uso comercial, forks, redistribución como parte de otro producto — si algo no
queda claro, pregunta. MIT permite casi todo, pero a veces conviene aclararlo.

### 🎓 Enseñanza y dudas

Si **enseñas lenguajes esotéricos** o **aprendes por tu cuenta** — cuéntame
cómo usas el proyecto. Me interesa qué ayuda y qué estorba. El feedback de
docentes vale especialmente.

### 📋 Qué incluir en tu mensaje

Para que lo entienda rápido, en el **primer mensaje** incluye:

| Punto | Ejemplo |
|---|---|
| **Versión** | `2.6.0` — visible en la pestaña About (F1) |
| **SO** | Windows 10 22H2 / Windows 11 / Linux Mint 21 |
| **Cómo ejecutas** | `.exe` o `python Main.py` |
| **Qué hiciste** | «Elegí Python → Brainfuck, pulsé F5» |
| **Qué esperabas** | «La traducción aparece a la derecha» |
| **Qué obtuviste** | «Campo vacío, error en terminal» |
| **Captura** | Si el error es visual |
| **Log** | `app.log` junto al `.exe`, si hubo crash |

**Asunto:** breve — p. ej. `[Bug] Rivulet no abre archivos .riv`.

### 🕐 Tiempo de respuesta

Respondo en **2–3 días laborables**. Bugs primero, funciones en lo posible.
Si un mensaje se perdió — escribe otra vez, el correo a veces falla.

### 🔗 Alternativas

Si prefieres GitHub:

- 🐛 [**Issues**](https://github.com/SuperCat-0877/esolang-translator-app/issues) — bugs e ideas
- 💬 [**Discussions**](https://github.com/SuperCat-0877/esolang-translator-app/discussions) — dudas generales (si lo activo)

**Pero el correo es más rápido.** Manda ahí.

---

**© 2026 Esolang Translator**

[↑ Idiomas](#esolang-translator)

---

## French

**IDE multilingue pour les langages de programmation ésotériques et classiques.**

43 langages · 1746 directions de traduction · 38 thèmes · Éditeurs 2D pour Rivulet et Piet

[↑ Langues](#esolang-translator)

---

## 📸 Captures

### Traduction entre langages

![Fenêtre principale](docs/screenshots/main.png)

*Python → Brainfuck. Choisis langages, mode, modèle — appuie sur F5.*

### Rivulet Canvas

![Rivulet Canvas](docs/screenshots/rivulet.png)

*Éditeur 2D pour Rivulet avec grille de glyphes et palette de commandes.*

### Piet-ASM

![Piet-ASM](docs/screenshots/piet_asm.png)

*Assembleur textuel pour Piet : `push`, `add`, `out_num` → compilation vers Piet.*

### Mosaïque (BlockPiet)

![Mosaïque](docs/screenshots/mosaic.png)

*Vue du code par tuiles : tuiles BYTE, modèles, assemblage visuel.*

### Bac à sable

![Bac à sable](docs/screenshots/sandbox.png)

*Exécution isolée du code avec timeout et onglet « Expliquer ».*

### 38 thèmes

![Thèmes](docs/screenshots/themes.png)

*Du sombre au pastel clair. Contraste automatique de l'interface.*

---

## ✨ Fonctionnalités

- **43 langages** — classiques (Python, JavaScript, C++, Java, Go, Rust, Ruby, PHP, Kotlin, Swift, Scala, Julia, Dart, TypeScript, Elixir, F#, R, Perl, Lua, C#) et ésotériques (Brainfuck, Piet, Rivulet, Whitespace, Ook, Malbolge, Cow, Chicken, Shakespeare, LOLCODE, Befunge, Intercal, Unlambda, Deadfish, Pika, Thue, Hodor, ArnoldC).
- **1746 directions de traduction** entre toutes les paires.
- **4 modes de traduction** — R=R, R=E, E=R, E=E.
- **38 thèmes** — 3 base, 5 classiques, arc-en-ciel, nuances bleu / rouge / violet, 10 pastel clairs.
- **Éditeurs 2D** — Rivulet Canvas et Piet Canvas avec grille de glyphes.
- **Piet-ASM** — assembleur textuel pour Piet avec tuiles 16×16.
- **Mosaïque** — vue du code par tuiles (BlockPiet).
- **Bac à sable** — exécution isolée du code avec timeout.
- **Plugins** `.py` — chargés sans redémarrer l'app.
- **Modèles** — édition dans l'UI, import/export en `.txt`.
- **Renommer** langages, boutons, couleurs de listes personnalisées.
- **6 langues d'interface** — English, Русский, Deutsch, Español, Français, Italiano.

---

## 🚀 Installation

### `.exe` prêt (recommandé)

Télécharge `EsolangTranslator.exe` depuis [**Releases**](../../releases).

1. Mets le `.exe` dans n'importe quel dossier (ex. `D:\Apps\EsolangTranslator\`)
2. Lance-le

Au premier démarrage apparaissent à côté :

- `config.json` — paramètres
- `plugins/` — plugins utilisateur
- `langs_disabled/` — langages désactivés

**Prérequis :**
- Windows 10 / 11 (64-bit)
- Rien à installer en plus — Python et bibliothèques sont inclus

**Windows 7 SP1 / 8 :** nécessite une compilation séparée avec Python 3.8.10 (voir ci-dessous).
Le code actuel cible **Python 3.10+**.

### Depuis les sources

```bash
git clone https://github.com/SuperCat-0877/esolang-translator-app.git
cd esolang-translator-app
pip install -r requirements.txt
python Main.py
```

---

## 🙏 Remerciements

- [Daniel Temkin](https://github.com/danieltemkin) — interpréteur Rivulet original
- [rdbende](https://github.com/rdbende) — thème Sun Valley ttk (`sv-ttk`)

---

## ⚠️ Important : BlockPiet et BrainPiet

Dans la liste figurent **BlockPiet** et **BrainPiet**, qui peuvent être trompeurs.
Ce ne sont **pas des langages autonomes** — ce sont des **variantes de Piet**
(en partie Brainfuck) adaptées pour démontrer différentes approches de la
programmation visuelle.

### BlockPiet

**Ce que c'est :** une variante de Piet où le programme est assemblé à partir
de **tuiles (blocks)** au lieu d'être dessiné à la main.

**Différences avec Piet :**
- Les tuiles sont prédéfinies — à choisir dans la bibliothèque `BYTE #0`–`BYTE #14`
- Modèles prêts : `print(0)`, `print(1)`, `print(42)`, `print(100)`, `print(a)`, `print(b)`, etc.
- Fonctionne via l'onglet **Mosaïque** — constructeur visuel
- Assemblé à la volée, sans dessin manuel de la grille

**Pour quoi :** apprentissage, visualisation rapide des opérations Piet de base,
démonstration de l'idée « programme = ensemble de tuiles ».

### BrainPiet

**Ce que c'est :** un hybride **Brainfuck + Piet** — la logique d'expression
vient de Brainfuck, la visualisation de Piet.

**Différences :**
- À l'intérieur — commandes Brainfuck (`+`, `-`, `>`, `<`, `.`, `,`)
- À l'extérieur — représentation visuelle via une **grille 2D de glyphes Piet**
- Option intermédiaire : plus simple que Piet pur, plus visuelle que Brainfuck plat

**Pour quoi :** transition douce des langages linéaires (Brainfuck) vers les
langages 2D (Piet) — pont pédagogique.

### Ce que ça signifie pour toi

- **N'attends pas** une compatibilité totale avec Piet ou Brainfuck originaux
  de BlockPiet / BrainPiet.
- **Ne les confonds pas** avec les implémentations originales — ces langages
  sont créés **au sein du projet** comme matériel d'apprentissage / démo.
- **Utilise-les** comme **exemples supplémentaires** — ils montrent comment
  les langages ésotériques peuvent être adaptés à différentes tâches.

### Vrais Piet et Brainfuck

Les implémentations originales sont **aussi présentes** :

| Langage | Ce que c'est |
|---|---|
| **Piet** | Piet complet avec grille 16×16 et 20 couleurs |
| **Piet-ASM** | Assembleur Piet — texte → tuiles |
| **Brainfuck** | Implémentation complète du Brainfuck classique |

Si tu veux du **Piet ou Brainfuck pur** — utilise **ces** noms dans la liste
des langages, pas BlockPiet / BrainPiet.

---

## 💬 Contact

**Courriel :** [Kanadegameyalybly@gmail.com](mailto:Kanadegameyalybly@gmail.com)

Le projet est développé en solo, et **chaque message aide à l'améliorer**.
Écris — je lis tout, même si je ne réponds pas immédiatement.

### 🐛 Signaler un bug

Quelque chose ne marche pas, plante, donne un résultat faux ? Envoie une
description — je corrige dans la version suivante. Surtout important pour :

- Traductions entre paires de langages rares
- Rivulet / Piet — éditeurs 2D
- Bac à sable et Piet-ASM
- Compilation du `.exe` sur ton système

### 💡 Suggérer une idée

Une idée de ce qui manque ? Envoie :

- **Nouveau langage** — ésotérique ou classique. Si tu en connais un intéressant — je l'ajoute
- **Nouveau thème** — schéma de couleurs, sombre / clair / pastel
- **Nouveau mode de traduction** ou combinaison
- **Amélioration de l'UI** — ce qui est gênant, ce qui est confus
- **Nouvel onglet** ou fonction

### 🔧 Demander une fonction

Si quelque chose manque dans la version actuelle — dis-le. Par exemple :

- Export vers un autre format (pas seulement `.txt`)
- Intégration avec un éditeur externe
- Sauvegarde auto à la fermeture
- Support d'un langage ou dialecte précis

### 🌐 Envoyer ton plugin

Tu as écrit un langage dans `plugins/mylang.py` ? Envoie le code — **je l'ajoute
à la collection** et je te crédite.

### 📝 Corriger typos et traductions

UI en russe, texte d'About, README — si tu trouves une erreur ou une traduction
maladroite, envoie-la. Ces petits détails ne se voient que de l'extérieur.

### 🤝 Collaboration

Tu veux aider à développer le projet ?

- **Tests** sur un autre OS (Linux, macOS, Windows 7)
- **Compilation du `.exe`** avec Python 3.8.10 pour Windows 7 SP1 / 8
- **Documentation** — guides, tutoriels, articles
- **Design** — icônes, thèmes, captures
- **Code** — si tu veux envoyer une PR sur GitHub

### 📜 Questions de licence

Usage commercial, forks, redistribution au sein d'un autre produit — si quelque
chose n'est pas clair, demande. MIT autorise presque tout, mais parfois mieux
vaut préciser.

### 🎓 Enseignement et questions

Si tu **enseignes les langages ésotériques** ou **apprends toi-même** — raconte
comment tu utilises le projet. Ça m'intéresse de savoir ce qui aide et ce qui
gêne. Le retour des enseignants est particulièrement précieux.

### 📋 Quoi inclure dans ton message

Pour que je comprenne vite, dans le **premier message** indique :

| Point | Exemple |
|---|---|
| **Version** | `2.6.0` — visible dans l'onglet About (F1) |
| **OS** | Windows 10 22H2 / Windows 11 / Linux Mint 21 |
| **Lancement** | `.exe` ou `python Main.py` |
| **Ce que tu as fait** | « Choisi Python → Brainfuck, appuyé F5 » |
| **Ce que tu attendais** | « La traduction apparaît à droite » |
| **Ce que tu as eu** | « Champ vide, erreur dans le terminal » |
| **Capture** | Si l'erreur est visuelle |
| **Log** | `app.log` à côté du `.exe`, s'il y a eu un crash |

**Objet :** court — ex. `[Bug] Rivulet n'ouvre pas les fichiers .riv`.

### 🕐 Délai de réponse

Je réponds sous **2–3 jours ouvrés**. Bugs d'abord, fonctionnalités au mieux.
Si un message s'est perdu — réécris, les mails plantent parfois.

### 🔗 Alternatives

Si tu préfères GitHub :

- 🐛 [**Issues**](https://github.com/SuperCat-0877/esolang-translator-app/issues) — bugs et idées
- 💬 [**Discussions**](https://github.com/SuperCat-0877/esolang-translator-app/discussions) — questions générales (si activé)

**Mais le courriel est plus rapide.** Écris là-bas.

---

**© 2026 Esolang Translator**

[↑ Langues](#esolang-translator)

---

## Italian

**IDE multilingue per linguaggi di programmazione esoterici e regolari.**

43 linguaggi · 1746 direzioni di traduzione · 38 temi · Editor 2D per Rivulet e Piet

[↑ Lingue](#esolang-translator)

---

## 📸 Screenshot

### Traduzione tra linguaggi

![Finestra principale](docs/screenshots/main.png)

*Python → Brainfuck. Scegli linguaggi, modalità, modello — premi F5.*

### Rivulet Canvas

![Rivulet Canvas](docs/screenshots/rivulet.png)

*Editor 2D per Rivulet con griglia di glifi e palette dei comandi.*

### Piet-ASM

![Piet-ASM](docs/screenshots/piet_asm.png)

*Assembler testuale per Piet: `push`, `add`, `out_num` → compilazione in Piet.*

### Mosaico (BlockPiet)

![Mosaico](docs/screenshots/mosaic.png)

*Vista del codice a tessere: tessere BYTE, modelli, assemblaggio visivo.*

### Sandbox

![Sandbox](docs/screenshots/sandbox.png)

*Esecuzione isolata del codice con timeout e scheda «Spiega».*

### 38 temi

![Temi](docs/screenshots/themes.png)

*Dallo scuro al pastello chiaro. Contrasto automatico dell'interfaccia.*

---

## ✨ Funzionalità

- **43 linguaggi** — regolari (Python, JavaScript, C++, Java, Go, Rust, Ruby, PHP, Kotlin, Swift, Scala, Julia, Dart, TypeScript, Elixir, F#, R, Perl, Lua, C#) ed esoterici (Brainfuck, Piet, Rivulet, Whitespace, Ook, Malbolge, Cow, Chicken, Shakespeare, LOLCODE, Befunge, Intercal, Unlambda, Deadfish, Pika, Thue, Hodor, ArnoldC).
- **1746 direzioni di traduzione** tra tutte le coppie.
- **4 modalità di traduzione** — R=R, R=E, E=R, E=E.
- **38 temi** — 3 base, 5 classici, arcobaleno, tonalità blu / rosso / viola, 10 pastello chiari.
- **Editor 2D** — Rivulet Canvas e Piet Canvas con griglia di glifi.
- **Piet-ASM** — assembler testuale per Piet con tessere 16×16.
- **Mosaico** — vista del codice a tessere (BlockPiet).
- **Sandbox** — esecuzione isolata del codice con timeout.
- **Plugin** `.py` — caricati senza riavviare l'app.
- **Modelli** — modifica nella UI, import/export in `.txt`.
- **Rinomina** linguaggi, pulsanti, colori delle liste personalizzati.
- **6 lingue dell'interfaccia** — English, Русский, Deutsch, Español, Français, Italiano.

---

## 🚀 Installazione

### `.exe` pronto (consigliato)

Scarica `EsolangTranslator.exe` da [**Releases**](../../releases).

1. Metti il `.exe` in una cartella qualsiasi (es. `D:\Apps\EsolangTranslator\`)
2. Avvialo

Al primo avvio compaiono accanto:

- `config.json` — impostazioni
- `plugins/` — plugin utente
- `langs_disabled/` — linguaggi disattivati

**Requisiti:**
- Windows 10 / 11 (64-bit)
- Nient'altro da installare — Python e librerie sono inclusi

**Windows 7 SP1 / 8:** richiede una build separata con Python 3.8.10 (vedi sotto).
Il codice attuale è pensato per **Python 3.10+**.

### Dai sorgenti

```bash
git clone https://github.com/SuperCat-0877/esolang-translator-app.git
cd esolang-translator-app
pip install -r requirements.txt
python Main.py
```

---

## 🙏 Ringraziamenti

- [Daniel Temkin](https://github.com/danieltemkin) — interprete Rivulet originale
- [rdbende](https://github.com/rdbende) — tema Sun Valley ttk (`sv-ttk`)

---

## ⚠️ Importante: BlockPiet e BrainPiet

Nella lista ci sono **BlockPiet** e **BrainPiet**, che possono trarre in inganno.
Non sono **linguaggi autonomi** — sono **varianti di Piet** (in parte Brainfuck)
adattate per mostrare diversi approcci alla programmazione visuale.

### BlockPiet

**Cos'è:** una variante di Piet in cui il programma si assembla da **tessere
(blocks)** invece di essere disegnato a mano.

**Differenze da Piet:**
- Le tessere sono predefinite — si scelgono dalla libreria `BYTE #0`–`BYTE #14`
- Modelli pronti: `print(0)`, `print(1)`, `print(42)`, `print(100)`, `print(a)`, `print(b)`, ecc.
- Funziona tramite la scheda **Mosaico** — costruttore visuale
- Si assembla al volo, senza disegnare la griglia a mano

**A cosa serve:** apprendimento, visualizzazione rapida delle operazioni di base
di Piet, dimostrazione dell'idea «programma = insieme di tessere».

### BrainPiet

**Cos'è:** un ibrido **Brainfuck + Piet** — la logica di espressione viene da
Brainfuck, la visualizzazione da Piet.

**Differenze:**
- Dentro — comandi Brainfuck (`+`, `-`, `>`, `<`, `.`, `,`)
- Fuori — rappresentazione visuale tramite **griglia 2D di glifi Piet**
- Opzione intermedia: più semplice di Piet puro, più visuale di Brainfuck piatto

**A cosa serve:** transizione morbida dai linguaggi lineari (Brainfuck) ai
linguaggi 2D (Piet) — ponte didattico.

### Cosa significa per te

- **Non aspettarti** piena compatibilità con Piet o Brainfuck originali da BlockPiet / BrainPiet.
- **Non confonderli** con le implementazioni originali — questi linguaggi
  sono creati **dentro il progetto** come materiale didattico / demo.
- **Usali** come **esempi aggiuntivi** — mostrano come i linguaggi esoterici
  possano essere adattati a compiti diversi.

### Piet e Brainfuck veri

Le implementazioni originali sono **anch'esse presenti**:

| Linguaggio | Cos'è |
|---|---|
| **Piet** | Piet completo con tela 16×16 e 20 colori |
| **Piet-ASM** | Assembler Piet — testo → tessere |
| **Brainfuck** | Implementazione completa del Brainfuck classico |

Se vuoi **Piet o Brainfuck puri** — usa **quei** nomi nella lista dei linguaggi,
non BlockPiet / BrainPiet.

---

## 💬 Contatti

**Email:** [Kanadegameyalybly@gmail.com](mailto:Kanadegameyalybly@gmail.com)

Il progetto è sviluppato in solitaria, e **ogni messaggio aiuta a migliorarlo**.
Scrivi — leggo tutto, anche se non rispondo subito.

### 🐛 Segnalare un bug

Qualcosa non funziona, va in crash, dà un risultato sbagliato? Manda una
descrizione — lo sistemo nella prossima versione. Particolarmente importante per:

- Traduzioni tra coppie di linguaggi rari
- Rivulet / Piet — editor 2D
- Sandbox e Piet-ASM
- Compilazione del `.exe` sul tuo sistema

### 💡 Suggerire un'idea

Hai un'idea di cosa manca? Manda:

- **Nuovo linguaggio** — esoterico o regolare. Se ne conosci uno interessante — lo aggiungo
- **Nuovo tema** — schema di colori, scuro / chiaro / pastello
- **Nuova modalità di traduzione** o combinazione
- **Miglioramento UI** — cosa è scomodo, cosa confonde
- **Nuova scheda** o funzione

### 🔧 Richiedere una funzione

Se manca qualcosa nella versione attuale — dillo. Per esempio:

- Export in un altro formato (non solo `.txt`)
- Integrazione con editor esterno
- Salvataggio automatico alla chiusura
- Supporto di un linguaggio o dialetto specifico

### 🌐 Inviare il tuo plugin

Hai scritto un linguaggio in `plugins/mylang.py`? Manda il codice — **lo aggiungo
alla collezione** e ti cito nei ringraziamenti.

### 📝 Correggere typo e traduzioni

UI in russo, testi di About, README — se trovi un errore o una traduzione goffa,
mandala. Queste piccole cose si vedono solo dall'esterno.

### 🤝 Collaborazione

Vuoi aiutare a sviluppare il progetto?

- **Test** su un altro OS (Linux, macOS, Windows 7)
- **Build del `.exe`** con Python 3.8.10 per Windows 7 SP1 / 8
- **Documentazione** — guide, tutorial, articoli
- **Design** — icone, temi, screenshot
- **Codice** — se vuoi mandare una PR su GitHub

### 📜 Domande sulla licenza

Uso commerciale, fork, ridistribuzione all'interno di un altro prodotto — se
qualcosa non è chiaro, chiedi. MIT permette quasi tutto, ma a volte è meglio chiarire.

### 🎓 Insegnamento e domande

Se **insegni linguaggi esoterici** o **studi da solo** — racconta come usi il
progetto. Mi interessa cosa aiuta e cosa ostacola. Il feedback di chi insegna
è particolarmente prezioso.

### 📋 Cosa includere nel messaggio

Per farmi capire in fretta, nel **primo messaggio** indica:

| Punto | Esempio |
|---|---|
| **Versione** | `2.6.0` — visibile nella scheda About (F1) |
| **OS** | Windows 10 22H2 / Windows 11 / Linux Mint 21 |
| **Come lo avvii** | `.exe` o `python Main.py` |
| **Cosa hai fatto** | «Scelto Python → Brainfuck, premuto F5» |
| **Cosa ti aspettavi** | «La traduzione appare a destra» |
| **Cosa hai ottenuto** | «Campo vuoto, errore nel terminale» |
| **Screenshot** | Se l'errore è visuale |
| **Log** | `app.log` accanto al `.exe`, se c'è stato un crash |

**Oggetto:** breve — es. `[Bug] Rivulet non apre file .riv`.

### 🕐 Tempi di risposta

Rispondo entro **2–3 giorni lavorativi**. Bug per primi, funzioni come posso.
Se un messaggio si è perso — riscrivi, la posta a volte fa i capricci.

### 🔗 Alternative

Se preferisci GitHub:

- 🐛 [**Issues**](https://github.com/SuperCat-0877/esolang-translator-app/issues) — bug e idee
- 💬 [**Discussions**](https://github.com/SuperCat-0877/esolang-translator-app/discussions) — domande generali (se attivo)

**Ma l'email è più veloce.** Scrivi lì.

---

**© 2026 Esolang Translator**

[↑ Lingue](#esolang-translator)