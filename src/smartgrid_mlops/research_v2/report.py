"""Stage 9D: Cross-candidate comparison and final research report.

This module reads the per-candidate evidence packages produced by
`candidate.py` and writes:

  * `artifacts/v2/forecasting_research/comparisons/summary.json` -
    a flat, machine-readable summary of all candidates.
  * `artifacts/v2/forecasting_research/reports/stage_9_research_report.md` -
    a human-readable research report.

The report lists every candidate with its target, MAE, classification,
and a one-line honest interpretation. The report does NOT promote or
deploy anything. It is evidence for a future governance stage to
consume.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[3]


def _read_candidate_evidence(candidates_dir: Path) -> list[dict]:
    out: list[dict] = []
    if not candidates_dir.exists():
        return out
    for cand_dir in sorted(p for p in candidates_dir.iterdir() if p.is_dir()):
        ej = cand_dir / "experiment.json"
        if not ej.is_file():
            continue
        try:
            out.append(json.loads(ej.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def write_summary(candidates_dir: Path, out_path: Path) -> dict:
    candidates = _read_candidate_evidence(candidates_dir)
    summary = {
        "generated_at": datetime.utcnow().isoformat() + "+00:00",
        "n_candidates": len(candidates),
        "candidates": candidates,
        "by_classification": _count_by(candidates, "classification"),
        "by_target": _count_by_target(candidates),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return summary


def _count_by(candidates: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in candidates:
        v = str(c.get(key, "unknown"))
        out[v] = out.get(v, 0) + 1
    return out


def _count_by_target(candidates: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in candidates:
        v = str(c.get("target", "unknown"))
        out[v] = out.get(v, 0) + 1
    return out


def _format_summary_table_md(summary: dict) -> str:
    lines: list[str] = []
    lines.append("# Stage 9 Research Report")
    lines.append("")
    lines.append(f"Generated: `{summary['generated_at']}`")
    lines.append("")
    lines.append(f"Total candidates evaluated: **{summary['n_candidates']}**")
    lines.append("")
    lines.append("## Classification totals")
    lines.append("")
    if summary["by_classification"]:
        for k, v in sorted(summary["by_classification"].items()):
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Per-candidate results")
    lines.append("")
    lines.append("| candidate_id | target | MAE | RMSE | sMAPE (%) | n | classification | notes |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | --- | --- |")
    for c in summary["candidates"]:
        m = c["metrics"]
        notes = c["comparison"].get("notes", "")
        if c["comparison"].get("frozen_metrics"):
            fm = c["comparison"]["frozen_metrics"]
            notes += f"; frozen finalist MAE={fm['MAE']:.2f}."
        lines.append(
            f"| `{c['candidate_id']}` | {c['target']} | "
            f"{m['MAE']:.3f} | {m['RMSE']:.3f} | {m['sMAPE_pct']:.2f} | "
            f"{m['n']} | **{c['classification']}** | {notes} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_markdown_report(summary: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_format_summary_table_md(summary), encoding="utf-8")
