"""Assembles the Catalog a builder chooses from."""
from ..core.schemas import Catalog
from .skills import load_skills
from .tools import load_tools


async def load_catalog() -> Catalog:
    return Catalog(tools=await load_tools(), skills=load_skills())
