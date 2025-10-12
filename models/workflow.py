from typing import Any, Literal

from pydantic import BaseModel


StepType = Literal["split", "transcribe", "translate", "speak", "quiz"]


class ServiceConfig(BaseModel):
    """Runtime service description that can be resolved by the registry."""

    name: str
    impl: str
    options: dict[str, Any] = {}


class StepConfig(BaseModel):
    """Single workflow step executed by a specific service."""

    id: str
    type: StepType
    service: str
    enabled: bool = True
    params: dict[str, Any] = {}


class AssetConfig(BaseModel):
    """Input asset handled by the workflow (audio, text, etc.)."""

    id: str
    source_uri: str
    metadata: dict[str, Any] = {}


class WorkflowConfig(BaseModel):
    """Declarative workflow definition."""

    id: str
    title: str
    services: list[ServiceConfig]
    steps: list[StepConfig]
    assets: list[AssetConfig]

