from __future__ import annotations

from importlib import import_module
from typing import Any, Callable

from services.base import BaseService


Factory = Callable[[dict[str, Any]], BaseService]


class ServiceRegistry:
    """Simple registry/factory resolver for workflow services."""

    def __init__(self) -> None:
        self._factories: dict[str, Factory] = {}

    def register(self, impl: str, factory: Factory) -> None:
        self._factories[impl] = factory

    def create(self, impl: str, options: dict[str, Any]) -> BaseService:
        if impl not in self._factories:
            module_path, attr = impl.rsplit(".", 1)
            module = import_module(module_path)
            factory = getattr(module, attr)
            if not callable(factory):
                raise TypeError(f"Registered object {impl} must be callable.")
            self._factories[impl] = factory  # cache for next time
        return self._factories[impl](options)

