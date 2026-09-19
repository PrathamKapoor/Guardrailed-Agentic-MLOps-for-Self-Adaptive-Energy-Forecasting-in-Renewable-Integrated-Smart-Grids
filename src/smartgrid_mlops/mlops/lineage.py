from __future__ import annotations

import json
from collections import deque
from pathlib import Path


class LineageGraph:
    NODE_TYPES = {"dataset", "processed_dataset", "feature_dataset", "protocol", "model_spec", "experiment_run", "evaluation", "evidence", "registry_entry", "deviation"}
    EDGE_TYPES = {"DERIVED_FROM", "USES", "EVALUATED_BY", "GOVERNED_BY", "PRODUCED", "INVALIDATED_BY", "REGISTERED_AS", "COMPARED_WITH"}

    def __init__(self, document: dict | None = None):
        document = document or {"schema_version": "phase12-lineage-v1", "nodes": [], "edges": []}
        self.document = document
        self.nodes = {x["id"]: x for x in document.get("nodes", [])}
        self.edges = document.get("edges", [])

    @classmethod
    def load(cls, path: Path):
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def add_node(self, node_id: str, node_type: str, **metadata):
        if node_type not in self.NODE_TYPES:
            raise ValueError(f"Unsupported node type {node_type}")
        self.nodes[node_id] = {"id": node_id, "type": node_type, **metadata}

    def add_edge(self, source: str, target: str, relationship: str):
        if relationship not in self.EDGE_TYPES or source not in self.nodes or target not in self.nodes:
            raise ValueError("Invalid lineage edge or missing node")
        edge = {"source": source, "target": target, "relationship": relationship}
        if edge not in self.edges:
            self.edges.append(edge)

    def validate(self):
        for edge in self.edges:
            if edge["source"] not in self.nodes or edge["target"] not in self.nodes:
                raise ValueError(f"Missing lineage node for edge {edge}")
        return True

    def trace(self, node_id: str) -> list[dict]:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        adjacent: dict[str, set[str]] = {}
        for edge in self.edges:
            adjacent.setdefault(edge["source"], set()).add(edge["target"])
            adjacent.setdefault(edge["target"], set()).add(edge["source"])
        seen, queue = set(), deque([node_id])
        while queue:
            current = queue.popleft()
            if current in seen: continue
            seen.add(current); queue.extend(sorted(adjacent.get(current, set()) - seen))
        return [self.nodes[key] for key in sorted(seen)]

    def dump(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.document["nodes"] = [self.nodes[k] for k in sorted(self.nodes)]
        self.document["edges"] = sorted(self.edges, key=lambda e: (e["source"], e["target"], e["relationship"]))
        path.write_text(json.dumps(self.document, indent=2) + "\n", encoding="utf-8")
