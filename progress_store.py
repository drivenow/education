from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional

from models.taskmeta import TaskMeta
from models.workflow import AssetConfig, WorkflowConfig


class ProgressStore:
    """Persist and restore playback progress for workflow assets."""

    def __init__(
        self,
        path: Path | str,
        *,
        workflow_id: str,
        assets: Optional[Iterable[AssetConfig]] = None,
    ) -> None:
        """Initialise the store, loading existing data and optionally attaching assets.
        path: The path to the progress file.
        workflow_id: The ID of the workflow.
        assets: Optional iterable of assets to attach.
        """
        self.path = Path(path)
        self.workflow_id = workflow_id
        self._data: Dict[str, object] = {}
        self._records: Dict[str, TaskMeta] = {}
        self._record_ids: list[str] = []
        self._dirty: bool = False

        if self.path.exists():
            self._load()

        self._data.setdefault("id", workflow_id)

        if assets:
            self.attach_assets(assets)

    # ------------------------------------------------------------------ factories
    @classmethod
    def from_config_path(
        cls,
        config_path: Path | str,
        *,
        workflow_id: str | None = None,
    ) -> "ProgressStore":
        """Construct a store from a workflow config file, eager-loading its assets."""
        path = Path(config_path)
        raw = path.read_text(encoding="utf-8")
        if hasattr(WorkflowConfig, "model_validate_json"):
            config = WorkflowConfig.model_validate_json(raw)  # type: ignore[attr-defined]
        else:
            config = WorkflowConfig.parse_raw(raw)
        store = cls(path, workflow_id=workflow_id or config.id, assets=config.assets)
        if hasattr(config, "model_dump"):
            store._data = config.model_dump(mode="python")  # type: ignore[attr-defined]
        else:
            store._data = config.dict()
        store._sync_records_from_data()
        return store

    # ---------------------------------------------------------------- operations
    def attach_assets(self, assets: Iterable[AssetConfig]) -> None:
        """Merge the provided assets into the tracked record set."""
        for asset in assets:
            record = TaskMeta.from_raw(asset.to_dict())
            record.apply_lang_defaults()
            existing = self._records.get(record.id)
            if existing:
                existing.merge_structural(record)
            else:
                self._records[record.id] = record
                self._record_ids.append(record.id)
                self._dirty = True

    def mark_started(self, asset: AssetConfig) -> None:
        """Mark an asset as started and ensure a record exists."""
        record = self._ensure_record(asset)
        record.mark_started(self._now())
        self._dirty = True

    def update_checkpoint(
        self,
        asset: AssetConfig,
        *,
        last_item: str | None = None,
        progress_played: int | None = None,
        progress_total: int | None = None,
    ) -> None:
        """Persist intermediate playback position for the given asset."""
        record = self._ensure_record(asset)
        record.update_progress(
            self._now(),
            last_item=last_item,
            played=progress_played,
            total=progress_total,
        )
        self._dirty = True

    def mark_completed(self, asset: AssetConfig) -> None:
        """Mark the asset as fully processed/played."""
        record = self._ensure_record(asset)
        record.mark_completed(self._now())
        self._dirty = True

    def is_completed(self, asset_id: str) -> bool:
        """Return True if the stored record is marked completed."""
        record = self._records.get(asset_id)
        return bool(record and record.completed)

    def get_record(self, asset_id: str) -> TaskMeta | None:
        """Return the stored TaskMeta for a given asset if present."""
        return self._records.get(asset_id)

    def flush(self) -> None:
        """Write in-memory records back to the backing JSON file if dirty."""
        if not self._dirty and self.path.exists():
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(self._data)
        assets = []
        for asset_id in self._record_ids:
            record = self._records.get(asset_id)
            if record:
                assets.append(record.to_dict())
        for asset_id, record in self._records.items():
            if asset_id not in self._record_ids:
                assets.append(record.to_dict())
        data["assets"] = assets

        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._dirty = False

    # ---------------------------------------------------------------- utilities
    def _ensure_record(self, asset: AssetConfig) -> TaskMeta:
        """Fetch or create the TaskMeta record corresponding to an asset."""
        record = self._records.get(asset.id)
        if not record:
            record = TaskMeta.from_raw(asset.to_dict())
            self._records[asset.id] = record
            self._record_ids.append(asset.id)
        else:
            record.merge_structural(TaskMeta.from_raw(asset.to_dict()))
        return record

    def _now(self) -> str:
        """Return the current UTC timestamp as an ISO string."""
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def _load(self) -> None:
        """Load persisted data from disk into memory."""
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._data = raw
        self._sync_records_from_data()

    def _sync_records_from_data(self) -> None:
        """Rebuild the in-memory TaskMeta map from the serialized data."""
        assets = self._data.get("assets", [])
        self._records.clear()
        self._record_ids = []
        for item in assets:
            record = TaskMeta.from_raw(item)
            self._records[record.id] = record
            self._record_ids.append(record.id)
