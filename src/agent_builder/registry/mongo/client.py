"""MongoDB connection shared by every collection store."""
from pymongo import MongoClient
from pymongo.database import Database


def connect(url: str) -> Database:
    client: MongoClient = MongoClient(url)
    db_name = url.rsplit("/", 1)[-1].split("?")[0] or "agent_builder"
    return client[db_name]
