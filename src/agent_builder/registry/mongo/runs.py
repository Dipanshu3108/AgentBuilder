"""The `runs` collection: traces of agent, pipe, and orchestrator runs."""
from __future__ import annotations

from pymongo import DESCENDING
from pymongo.database import Database

from ...core.schemas import RunTrace


class MongoRunStore:
    def __init__(self, db: Database, collection: str = "runs"):
        self.runs = db[collection]
        self.runs.create_index("run_id", unique=True)
        self.runs.create_index([("target", 1), ("started_at", DESCENDING)])

    def save_run(self, run: RunTrace) -> RunTrace:
        self.runs.insert_one(run.model_dump(mode="python"))
        return run

    def get_run(self, run_id: str) -> RunTrace | None:
        doc = self.runs.find_one({"run_id": run_id}, projection={"_id": False})
        return RunTrace.model_validate(doc) if doc else None

    def list_runs(self, target: str | None = None, limit: int = 20) -> list[RunTrace]:
        query = {"target": target} if target else {}
        docs = self.runs.find(query, projection={"_id": False}).sort("started_at", DESCENDING).limit(limit)
        return [RunTrace.model_validate(doc) for doc in docs]
