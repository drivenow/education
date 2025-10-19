from __future__ import annotations
from typing import Any, ClassVar, Iterable, Mapping
from pydantic import BaseModel, ConfigDict, Field


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="python")  # type: ignore[attr-defined]
    return model.dict()  # type: ignore[attr-defined]


def _model_fields(model: BaseModel) -> Mapping[str, Any]:
    fields = getattr(type(model), "model_fields", None)
    if fields is not None:
        return fields
    return getattr(model, "__fields__", {})  # type: ignore[attr-defined]


class TaskMeta(BaseModel):
    """Standard task metadata used across assets and progress tracking."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    id: str
    source_uri: str
    file_name: str | None = None
    lang: str | None = None
    is_valid: bool = True
    completed: bool = False
    status: str | None = None
    create_time: str | None = None
    update_time: str | None = None
    play_count: int = 0  # Number of times the entire audio has been played.
    progress_played: int = 0  # Segments already played; used to resume playback.
    progress_total: int = 0  # Total segments produced by the splitter; stays 0 until splitting finishes.
    last_item: str | None = None
    steps: dict[str, Any] = Field(default_factory=dict)

    STRUCT_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_uri",
        "file_name",
        "lang",
        "is_valid",
        "steps",
    )

    def to_dict(self) -> dict[str, Any]:
        """Dump task for persistence."""
        if hasattr(self, "model_dump"):
            return self.model_dump(mode="python", exclude_none=True)  # type: ignore[attr-defined]
        return self.dict(exclude_none=True)  # type: ignore[attr-defined]

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "TaskMeta":
        raw = dict(raw)
        progress = raw.pop("progress", None)
        if progress:
            raw.setdefault("progress_played", int(progress.get("played", 0) or 0))
            raw.setdefault("progress_total", int(progress.get("total", 0) or 0))
        return cls(**raw)

    @classmethod
    def many_from_assets(cls, assets: Iterable["TaskMeta"]) -> dict[str, "TaskMeta"]:
        return {asset.id: cls.from_raw(_model_dump(asset)) for asset in assets}

    # ------------------------------------------------------------------ defaults
    def apply_lang_defaults(self) -> None:
        """Ensure steps default align with language."""
        lang = (self.lang or "").lower()
        split_cfg = self.steps.setdefault("split", {})
        play_cfg = self.steps.setdefault("play", {})

        split_cfg.setdefault("enabled", True)
        if lang.startswith("en"):
            play_cfg.setdefault("translate", True)
        else:
            play_cfg.setdefault("translate", False)
        play_cfg.setdefault("skip_first", False)

    # ---------------------------------------------------------------- operations
    def ensure_created(self, timestamp: str) -> None:
        if not self.create_time:
            self.create_time = timestamp

    def mark_started(self, timestamp: str) -> None:
        self.ensure_created(timestamp)
        self.update_time = timestamp
        self.status = "in_progress"
        self.completed = False
        self.progress_played = int(self.progress_played or 0)
        self.progress_total = int(self.progress_total or 0)

    def update_progress(
        self,
        timestamp: str,
        *,
        last_item: str | None = None,
        played: int | None = None,
        total: int | None = None,
    ) -> None:
        self.mark_started(timestamp)
        if last_item is not None:
            self.last_item = last_item
        if total is not None:
            self.progress_total = max(int(total), self.progress_total)
        if played is not None:
            self.progress_played = max(int(played), self.progress_played)

    def mark_completed(self, timestamp: str) -> None:
        self.mark_started(timestamp)
        total = int(self.progress_total or 0)
        played = int(self.progress_played or 0)
        if total and played >= total:
            self.play_count = int(self.play_count) + 1
            self.completed = True
            self.status = "completed"
        else:
            self.completed = False
            self.status = "in_progress"
        self.update_time = timestamp

    # ---------------------------------------------------------------- utilities
    def should_skip(self) -> bool:
        return bool(self.progress_total and self.progress_played >= self.progress_total)

    def update_from(self, other: "TaskMeta") -> None:
        fields = _model_fields(self)
        for field in fields:
            setattr(self, field, getattr(other, field))

    def merge_structural(self, other: "TaskMeta") -> None:
        for field in self.STRUCT_FIELDS:
            value = getattr(other, field, None)
            if value is not None:
                setattr(self, field, value)
        if other.create_time and not self.create_time:
            self.create_time = other.create_time
        if other.update_time:
            # Keep the latest timestamp
            self.update_time = other.update_time
