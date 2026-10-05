"""Pick a registry backend from the connection string scheme."""
from ..config import settings
from .base import Registry


def get_registry(url: str = settings.database_url) -> Registry:
    scheme = url.split("://", 1)[0].lower()
    if scheme.startswith("mongodb"):
        from .mongo import MongoRegistry
        return MongoRegistry(url)
    raise ValueError(f"Unsupported database scheme '{scheme}'. Use mongodb://")
