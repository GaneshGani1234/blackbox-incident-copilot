from typing import Optional
from pydantic import BaseModel, Field


class IncidentIn(BaseModel):
    id: Optional[str] = None
    date: Optional[str] = None  # ISO 8601, defaults to now
    service: str
    title: str
    severity: str = "SEV2"
    symptoms: str = ""
    error_signature: str = ""


class AnalyzeRequest(BaseModel):
    incident: IncidentIn
    use_memory: bool = True


class DiagnosticStep(BaseModel):
    action: str
    result: str


class ResolveRequest(BaseModel):
    incident: IncidentIn
    root_cause: str
    fix: str
    owner: str = "unassigned"
    minutes_to_resolve: Optional[int] = None
    diagnostic_steps: list[DiagnosticStep] = Field(default_factory=list)
    deploy_related: Optional[str] = None


class ReflectRequest(BaseModel):
    question: str


class SeedRequest(BaseModel):
    reset: bool = False
