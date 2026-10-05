import json
from pathlib import Path

from mcp_server.tools.core.relations import parse_relations

ROOT = Path(__file__).resolve().parents[3]


def test_parse_relations_example():
    text = (ROOT / "examples" / "mash_relations.txt").read_text()
    graph = json.loads(parse_relations(text))
    assert len(graph["edges"]) == 10
    assert {"MASH treatment", "Drug", "Homecare"} <= {n["id"] for n in graph["nodes"]}
    assert graph["edges"][0]["relation"] == "composed_of"
