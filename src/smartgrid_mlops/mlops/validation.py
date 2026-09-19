from __future__ import annotations

from pathlib import Path, PurePosixPath


def portable_path(path: str | Path) -> str:
    raw = str(path).replace("\\", "/")
    p = PurePosixPath(raw)
    if p.is_absolute() or (len(raw) > 1 and raw[1] == ":"):
        raise ValueError("Canonical research paths must be repository-relative")
    if ".." in p.parts:
        raise ValueError("Research paths may not escape the repository")
    return p.as_posix()


def resolve_portable_path(project_root: Path, relative_path: str) -> Path:
    rel = portable_path(relative_path)
    candidate = (project_root / Path(rel)).resolve()
    root = project_root.resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("Resolved path escapes project root")
    return candidate


def require_complete_lineage(graph, registry_id: str) -> None:
    required = {"dataset", "processed_dataset", "feature_dataset", "protocol", "model_spec", "evaluation", "evidence", "registry_entry"}
    present = {node["type"] for node in graph.trace(registry_id)}
    missing = required - present
    if missing:
        raise ValueError(f"Incomplete lineage: {sorted(missing)}")
