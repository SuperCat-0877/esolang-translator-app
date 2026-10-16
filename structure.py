# structure.py
# Структура проекта: 1.txt -> дерево {язык: {пример: код}}
# Пока только описывает/парсит структуру, без изменений файла.

import re
import pathlib
from dataclasses import dataclass, field
from typing import Dict, List

SRC = pathlib.Path("1.txt")

# --- уровни заголовков в файле ---
RE_LANG = re.compile(r"^##\s+(?!#)(.+?)\s*$")          # ## Python
RE_EX   = re.compile(r"^###\s+\[([^\]]+)\]\s*(.+?)\s*$")  # ### [E1] Hello, World


@dataclass
class Example:
    tag: str          # "E1", "M2", "Test 1" ...
    title: str        # "Hello, World"
    code: List[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"[{self.tag}] {self.title}"

    def __repr__(self) -> str:
        return f"<Example {self.key} lines={len(self.code)}>"


@dataclass
class Language:
    name: str                        # "Python"
    examples: Dict[str, Example] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<Language {self.name} examples={len(self.examples)}>"


@dataclass
class Project:
    languages: Dict[str, Language] = field(default_factory=dict)

    # --- API ---
    def lang(self, name: str) -> Language:
        return self.languages.setdefault(name, Language(name))

    def iter_examples(self):
        for lang in self.languages.values():
            for ex in lang.examples.values():
                yield lang, ex

    def stats(self) -> Dict[str, int]:
        return {name: len(l.examples) for name, l in self.languages.items()}


def parse(path: pathlib.Path = SRC) -> Project:
    project = Project()
    current_lang: Language | None = None
    current_ex: Example | None = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\n")

        m = RE_LANG.match(line)
        if m:
            current_lang = project.lang(m.group(1))
            current_ex = None
            continue

        m = RE_EX.match(line)
        if m and current_lang is not None:
            tag, title = m.group(1), m.group(2)
            current_ex = Example(tag=tag, title=title)
            current_lang.examples[current_ex.key] = current_ex
            continue

        if current_ex is not None:
            current_ex.code.append(line)

    # убрать хвостовые пустые строки в каждом примере
    for _, ex in project.iter_examples():
        while ex.code and not ex.code[-1].strip():
            ex.code.pop()

    return project


if __name__ == "__main__":
    p = parse()
    for name, count in p.stats().items():
        print(f"{name:<16} {count} examples")