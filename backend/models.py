from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

Route = Literal['auto_apply', 'faculty_review', 'no_change']

class Edit(BaseModel):
    field: str
    find: Any = None
    replace: Any

class Result(BaseModel):
    reportId: str
    questionId: str
    verdict: str
    repair: str | None = None
    edit: Edit | dict = Field(default_factory=dict)
    route: Route
    confidence: float = Field(ge=0, le=1)
    evidence: str
    student_reply: str

    @field_validator('reportId', 'questionId', 'verdict')
    @classmethod
    def non_empty(cls, v):
        if not v: raise ValueError('required')
        return v
