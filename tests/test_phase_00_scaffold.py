from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_phase_zero_paths_exist() -> None:
    required_paths = [
        "AGENTS.md",
        "README.md",
        "pyproject.toml",
        ".gitignore",
        ".env.example",
        "docs/research_basis.md",
        "docs/architecture_overview.md",
        "reports/phase_00_completion.md",
        "src/smartgrid_mlops/__init__.py",
    ]
    assert all((ROOT / path).is_file() for path in required_paths)


def test_governance_non_negotiables_are_documented() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    required_statements = [
        "Never fabricate experimental results, accuracy values, dataset characteristics or model improvements.",
        "No LLM or autonomous agent may bypass the deterministic model-governance policy engine.",
        "Agent recommendations are advisory until they satisfy deterministic validation gates.",
        "Production-style champion replacement requires explicit approval unless the system is running in an explicitly configured simulation/demo environment.",
        "Never use random train/test splitting for time-series forecasting.",
    ]
    assert all(statement in agents for statement in required_statements)


def test_research_sources_are_labeled_as_inspiration_only() -> None:
    basis = (ROOT / "docs/research_basis.md").read_text(encoding="utf-8")
    assert "10.32996/jcsts.2025.7.4.55" in basis
    assert "10.1049/gtd2.12603" in basis
    assert "research inspiration only" in basis
