"""The `models` collection: LiteLLM configurations, including the API key."""
from __future__ import annotations

from pymongo.database import Database

from ...core.schemas import ModelConfig


class MongoModelStore:
    def __init__(self, db: Database, collection: str = "models"):
        self.models = db[collection]
        self.models.create_index("id", unique=True)

    def save_model(self, model: ModelConfig) -> ModelConfig:
        document = model.model_dump(mode="json", exclude={"api_key"})
        document["api_key"] = model.api_key.get_secret_value()
        self.models.replace_one({"id": model.id}, document, upsert=True)
        return model

    def get_model(self, model_id: str) -> ModelConfig | None:
        doc = self.models.find_one({"id": model_id}, projection={"_id": False})
        return ModelConfig.model_validate(doc) if doc else None

    def list_models(self) -> list[ModelConfig]:
        docs = self.models.find({}, projection={"_id": False}).sort("id", 1)
        return [ModelConfig.model_validate(doc) for doc in docs]
