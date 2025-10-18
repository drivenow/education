from __future__ import annotations

import importlib
from typing import Any, Dict

from models.workflow import ServiceConfig
from services.base import BaseService


class ServiceRegistry:
    """Resolve and cache service instances declared in workflow configuration."""

    def __init__(self) -> None:
        self._instances: Dict[str, BaseService] = {}

    def get(self, config: ServiceConfig) -> BaseService:
        if config.name not in self._instances:
            self._instances[config.name] = self._create(config)
        return self._instances[config.name]

    def _create(self, config: ServiceConfig) -> BaseService:
        module_name, attr = config.impl.rsplit(".", 1)
        module = importlib.import_module(module_name)
        factory: Any = getattr(module, attr)
        options = config.options or {}

        try:
            instance = factory(**options)
        except TypeError:
            # Fallback: try passing the options as a single argument.
            instance = factory(options)

        if not hasattr(instance, "run"):
            raise TypeError(f"Factory '{config.impl}' did not produce a valid service instance.")
        return instance

