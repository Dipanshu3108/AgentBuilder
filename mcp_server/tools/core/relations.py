"""Relation parsing tools."""
import json
import re

RELATION_RE = re.compile(r"^\s*-?\s*(.+?)\s*-\[(.+?)\]->\s*(.+?)\s*$")


def parse_relations(text: str) -> str:
    """Parse lines like 'A -[relation]-> B' into a JSON graph with nodes and edges.
    Use when: the input is a list of entity relations that must become structured data."""
    nodes: dict[str, dict] = {}
    edges = []
    for line in text.splitlines():
        match = RELATION_RE.match(line)
        if not match:
            continue
        source, relation, target = (value.strip() for value in match.groups())
        for node in (source, target):
            nodes.setdefault(node, {"id": node, "label": node})
        edges.append({"source": source, "target": target, "relation": relation})
    return json.dumps({"nodes": list(nodes.values()), "edges": edges}, indent=2)
