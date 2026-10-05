"""The `tools` collection: generated tool versions. The MCP server loads the approved ones."""
from __future__ import annotations

from pymongo import DESCENDING
from pymongo.database import Database

from ...core.schemas import ToolRecord


class MongoToolStore:
    def __init__(self, db: Database, collection: str = "tools"):
        self.tools = db[collection]
        self.tools.create_index([("spec.name", 1), ("version", DESCENDING)], unique=True)

    def save_tool(self, record: ToolRecord) -> ToolRecord:
        self.tools.insert_one(record.model_dump(mode="python"))
        return record

    def get_tool(self, name: str, version: int | None = None) -> ToolRecord | None:
        query: dict = {"spec.name": name}
        if version is not None:
            query["version"] = version
        doc = self.tools.find_one(query, sort=[("version", DESCENDING)], projection={"_id": False})
        return ToolRecord.model_validate(doc) if doc else None

    def list_tools(self) -> list[ToolRecord]:
        docs = self.tools.find({}, projection={"_id": False}).sort([("spec.name", 1), ("version", DESCENDING)])
        return [ToolRecord.model_validate(doc) for doc in docs]

    def set_tool_status(self, name: str, version: int, status: str) -> None:
        self.tools.update_one({"spec.name": name, "version": version}, {"$set": {"status": status}})
