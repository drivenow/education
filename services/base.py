from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, MutableMapping, Optional, Protocol

from models.workflow import AssetConfig, StepConfig, WorkflowConfig


class ServiceError(RuntimeError):
    """Raised when a service fails to execute a workflow step."""


@dataclass
class StepContext:
    """
    Unified runtime context that each service receives when executing a step.

    Fields:
        workflow:  The immutable workflow definition driving the execution.
        asset:     Current asset (TaskMeta) being processed — carries progress state.
        step:      The workflow step definition resolved for this execution.
        settings:  Fully merged parameters for the step (global + asset overrides + runtime overrides).
        artifacts: Shared, mutable storage for pipeline outputs (chunks, transcripts, playback info, etc.).
        extras:    Optional caller-supplied metadata (e.g. callbacks, ad-hoc step overrides).
    """

    workflow: WorkflowConfig
    asset: AssetConfig
    step: StepConfig
    settings: Dict[str, Any]
    artifacts: MutableMapping[str, Any] = field(default_factory=dict)
    extras: Optional[MutableMapping[str, Any]] = None

    def ensure_step_store(self) -> MutableMapping[str, Any]:
        """
        Return a mutable store attached to the current step id, creating it if necessary.

        This allows each service to stash data under a namespaced key without
        worrying about collisions with other steps.
        """
        store = self.artifacts.setdefault(self.step.id, {})
        if not isinstance(store, MutableMapping):
            raise ServiceError(f"Artifact store for step '{self.step.id}' is not mutable.")
        return store

    def get_callback(self, name: str) -> Any:
        """
        Fetch a named callback from ``extras['callbacks']`` if available.

        Returns:
            The callback callable if registered, otherwise ``None``.
        """
        if not self.extras:
            return None
        callbacks = self.extras.get("callbacks")
        if callbacks:
            return callbacks.get(name)
        return None


class BaseService(Protocol):
    """Protocol that all service implementations must follow."""

    def run(self, context: StepContext) -> Any:
        ...
