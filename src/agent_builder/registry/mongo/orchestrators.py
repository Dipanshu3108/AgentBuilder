"""The `orchestrators` collection: drafts and approved orchestrator versions."""
from __future__ import annotations

from pymongo import DESCENDING
from pymongo.database import Database

from ...core.schemas import OrchestratorRecord


class MongoOrchestratorStore:
    def __init__(self, db: Database, collection: str = "orchestrators"):
        self.orchestrators = db[collection]
        self.orchestrators.create_index([("spec.name", 1), ("version", DESCENDING)], unique=True)

    def save_orchestrator(self, record: OrchestratorRecord) -> OrchestratorRecord:
        """Insert, or replace the same name+version (a draft being approved or rebuilt)."""
        self.orchestrators.replace_one(
            {"spec.name": record.spec.name, "version": record.version},
            record.model_dump(mode="python"),
            upsert=True,
        )
        return record

    def get_orchestrator(
        self, name: str, version: int | None = None, status: str | None = "approved"
    ) -> OrchestratorRecord | None:
        query: dict = {"spec.name": name}
        if version is not None:
            query["version"] = version
        if status is not None:
            query["status"] = status
        doc = self.orchestrators.find_one(
            query, sort=[("version", DESCENDING)], projection={"_id": False}
        )
        return OrchestratorRecord.model_validate(doc) if doc else None

    def list_orchestrators(self) -> list[OrchestratorRecord]:
        docs = self.orchestrators.find({}, projection={"_id": False}).sort(
            [("spec.name", 1), ("version", DESCENDING)]
        )
        return [OrchestratorRecord.model_validate(doc) for doc in docs]
