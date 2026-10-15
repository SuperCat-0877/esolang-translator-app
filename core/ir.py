# core/ir.py
"""Промежуточное представление (IR)."""

from dataclasses import dataclass, field
from typing import Any, List, Union


class UnsupportedConstruct(Exception):
    pass


# --- выражения ---

@dataclass
class Num:
    value: Union[int, float]

@dataclass
class Str:
    value: str

@dataclass
class Var:
    name: str

@dataclass
class BinOp:
    op: str
    left: Any
    right: Any

@dataclass
class Compare:
    op: str   # > < >= <= == !=
    left: Any
    right: Any


# --- операторы ---

@dataclass
class Assign:
    name: str
    value: Any

@dataclass
class Print:
    expr: Any

@dataclass
class ForLoop:
    var: str
    start: Any
    end: Any
    body: List[Any] = field(default_factory=list)

@dataclass
class While:
    cond: Any
    body: List[Any] = field(default_factory=list)

@dataclass
class Program:
    body: List[Any] = field(default_factory=list)
