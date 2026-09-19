from __future__ import annotations
from .schemas import LIFECYCLE_STATES

class LifecycleStateMachine:
    def __init__(self,transition_rules:dict[str,list[str]]):
        self.rules={key:set(value) for key,value in transition_rules.items()}
        if set(self.rules)-LIFECYCLE_STATES: raise ValueError("Unknown lifecycle state in policy")
    def is_allowed(self,current:str,proposed:str)->bool:
        if current not in LIFECYCLE_STATES or proposed not in LIFECYCLE_STATES:return False
        return proposed in self.rules.get(current,set())
    def legal_transitions(self,current:str)->set[str]:return set(self.rules.get(current,set()))
    def is_terminal(self,state:str)->bool:return state in {"INVALIDATED","ARCHIVED"}
    def validate_baseline(self,research_role:str,current:str,proposed:str)->bool:
        return research_role!="BASELINE_COMPARATOR"
