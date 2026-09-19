from __future__ import annotations
from pathlib import Path
from .lineage import LineageGraph
from .registry import ResearchRegistry

class RegistryQueries:
    def __init__(self, root: Path):
        self.registry=ResearchRegistry.load(root/"artifacts/model_registry/mlops_research_registry.yaml")
        self.lineage=LineageGraph.load(root/"artifacts/mlops/lineage/lineage_index.yaml")
    def get_reference_model(self,target): return next(x for x in self.registry.entries if x["target"]==target.lower() and x["research_role"]=="REFERENCE")
    def get_challengers(self,target): return [x for x in self.registry.entries if x["target"]==target.lower() and x["research_role"]=="CHALLENGER"]
    def get_lineage(self,registry_id): return self.lineage.trace(registry_id)
    def get_benchmark_gate(self,registry_id): return next(x["development_benchmark_gate"] for x in self.registry.entries if x["registry_id"]==registry_id)
    def get_evidence(self,registry_id): return next(x["selection_evidence"] for x in self.registry.entries if x["registry_id"]==registry_id)
    def get_protocol_hash(self,registry_id): return next(x["protocol_hash"] for x in self.registry.entries if x["registry_id"]==registry_id)
