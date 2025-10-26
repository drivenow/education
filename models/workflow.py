from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field
from pathlib import Path
from .taskmeta import TaskMeta


class ServiceConfig(BaseModel):
    """声明一个工作流服务实例，例如切分、识别或播放。"""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    name: str
    impl: str
    options: Dict[str, Any] = Field(default_factory=dict)


class StepConfig(BaseModel):
    """描述工作流中的一个步骤以及默认参数。"""

    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    service: str
    params: Dict[str, Any] = Field(default_factory=dict)

    def merged_params(self, overrides: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        """Merge step-level parameters with asset overrides."""
        merged: Dict[str, Any] = dict(self.params)
        if overrides:
            merged.update({k: v for k, v in overrides.items() if v is not None})
        return merged


class AssetConfig(TaskMeta):
    """素材配置，继承 TaskMeta 用于跟踪播放进度。"""

    model_config = ConfigDict(extra="allow")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self.apply_lang_defaults()

    def resolved_path(self) -> Path:
        """Return the absolute path to the underlying audio asset."""
        base = Path(self.source_uri)
        if self.file_name:
            return base / self.file_name
        return base

    def step_overrides(self, step_id: str) -> Mapping[str, Any]:
        """Per-asset override parameters for a given step."""
        return self.steps.get(step_id, {}) if self.steps else {}


class WorkflowConfig(BaseModel):
    """顶层工作流配置，包含服务定义、步骤与素材。"""

    model_config = ConfigDict(extra="allow")

    id: str
    title: Optional[str] = None
    max_session_seconds: Optional[int] = None
    flag_loop_assets: bool = False  # 播放完一轮后是否自动循环
    services: List[ServiceConfig] = Field(default_factory=list)
    steps: List[StepConfig] = Field(default_factory=list)
    assets: List[AssetConfig] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._ensure_unique_identifiers()

    def service_map(self) -> Dict[str, ServiceConfig]:
        return {svc.name: svc for svc in self.services}

    def step_map(self) -> Dict[str, StepConfig]:
        return {step.id: step for step in self.steps}

    def iter_assets(self) -> Iterable[AssetConfig]:
        return list(self.assets)

    def _ensure_unique_identifiers(self) -> None:
        service_names = {svc.name for svc in self.services}
        if len(service_names) != len(self.services):
            raise ValueError("Duplicate service names detected in workflow configuration.")
        step_ids = {step.id for step in self.steps}
        if len(step_ids) != len(self.steps):
            raise ValueError("Duplicate step ids detected in workflow configuration.")
        asset_ids = {asset.id for asset in self.assets}
        if len(asset_ids) != len(self.assets):
            raise ValueError("Duplicate asset ids detected in workflow configuration.")
