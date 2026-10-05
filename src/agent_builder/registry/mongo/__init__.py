"""MongoDB registry: one store per collection behind a single Registry object."""
from .agents import MongoAgentStore
from .client import connect
from .models import MongoModelStore
from .orchestrators import MongoOrchestratorStore
from .runs import MongoRunStore
from .tools import MongoToolStore


class MongoRegistry(
    MongoAgentStore, MongoModelStore, MongoRunStore, MongoOrchestratorStore, MongoToolStore
):
    def __init__(self, url: str):
        db = connect(url)
        MongoAgentStore.__init__(self, db)
        MongoModelStore.__init__(self, db)
        MongoRunStore.__init__(self, db)
        MongoOrchestratorStore.__init__(self, db)
        MongoToolStore.__init__(self, db)


__all__ = ["MongoRegistry"]
