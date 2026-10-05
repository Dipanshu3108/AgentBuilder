"""The `agents` collection: immutable approved/archived agent versions."""
from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from pymongo import DESCENDING
from pymongo.database import Database

from ...core.schemas import AgentRecord


class MongoAgentStore:
    def __init__(self, db: Database, collection: str = "agents"):
        self.col = db[collection]
        self.col.create_index([("spec.name", 1), ("version", DESCENDING)], unique=True)
        self.col.create_index("agent_id")
        self._backfill_agent_ids()

    def _backfill_agent_ids(self) -> None:
        legacy_records = self.col.find(
            {"agent_id": {"$exists": False}}, {"spec.name": 1}
        )
        for document in legacy_records:
            name = document.get("spec", {}).get("name")
            if name:
                self.col.update_one(
                    {"_id": document["_id"], "agent_id": {"$exists": False}},
                    {"$set": {"agent_id": str(uuid5(NAMESPACE_URL, f"agent-builder:{name}"))}},
                )

    def save(self, record: AgentRecord) -> AgentRecord:
        self.col.insert_one(record.model_dump(mode="python"))
        return record

    def get(self, name: str, version: int | None = None) -> AgentRecord | None:
        query: dict = {"spec.name": name}
        if version is not None:
            query["version"] = version
        doc = self.col.find_one(query, sort=[("version", DESCENDING)], projection={"_id": False})
        return AgentRecord.model_validate(doc) if doc else None

    def list(self) -> list[AgentRecord]:
        docs = self.col.find({}, projection={"_id": False}).sort([("spec.name", 1), ("version", DESCENDING)])
        return [AgentRecord.model_validate(d) for d in docs]

    def next_version(self, name: str) -> int:
        latest = self.get(name)
        return latest.version + 1 if latest else 1
