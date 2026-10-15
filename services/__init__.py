# services/__init__.py
"""
Сервисный слой приложения.

Единые точки для запуска кода, уроков, тестов, прогресса.
UI не зовёт core/ напрямую — только через сервисы.
"""
from services.execute_service import (
    ExecuteService,
    ExecResult,
    get_execute_service,
)

__all__ = [
    "ExecuteService",
    "ExecResult",
    "get_execute_service",
]
