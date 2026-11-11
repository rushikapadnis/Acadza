"""LangGraph pipeline with optional Groq observations and deterministic safety decisions."""
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from .services import make_result, validate, BY_ID, TAX
from .llm import get_llm

class TriageState(TypedDict):
    report: dict[str, Any]
    proposal: dict[str, Any]
    observations: list[str]

def _observe(state: TriageState, stage: str):
    report=state['report']; observation=get_llm().observe(stage,report,BY_ID[report['questionId']],TAX)
    return {'observations': state.get('observations', []) + ([observation.summary] if observation else [])}
def classification(state: TriageState): return _observe(state,'classification')
def verification(state: TriageState): return _observe(state,'verification')
def repair_proposal(state: TriageState):
    update=_observe(state,'repair proposal')
    # Deterministic rules remain the sole authority for taxonomy-safe persisted proposals.
    update['proposal']=make_result(state['report'])
    return update
def safety_gate(state: TriageState):
    validate(state['proposal'])
    return state

graph=StateGraph(TriageState)
graph.add_node('classification',classification)
graph.add_node('verification',verification)
graph.add_node('repair_proposal',repair_proposal)
graph.add_node('taxonomy_safety_gate',safety_gate)
graph.set_entry_point('classification')
graph.add_edge('classification','verification')
graph.add_edge('verification','repair_proposal')
graph.add_edge('repair_proposal','taxonomy_safety_gate')
graph.add_edge('taxonomy_safety_gate',END)
triage_workflow=graph.compile()
