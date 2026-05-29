from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


StepStatus = Literal["pending", "running", "completed", "failed", "blocked", "denied"]


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class PlanStep(BaseModel):
    id: str = Field(default_factory=lambda: new_id("step"))
    title: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    status: StepStatus = "pending"


class Plan(BaseModel):
    id: str = Field(default_factory=lambda: new_id("plan"))
    summary: str
    steps: list[PlanStep]


class ChatRequest(BaseModel):
    message: str
    safe_mode: bool = True


class ChatResponse(BaseModel):
    assistant_message: str
    plan: Plan
    execution_results: list["ToolExecuteResponse"] = Field(default_factory=list)
    memories: list["MemoryRecord"] = Field(default_factory=list)


class ToolExecuteRequest(BaseModel):
    step_id: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


class ToolExecuteResponse(BaseModel):
    step_id: str
    tool: str
    status: StepStatus
    output: str


class MemoryRecord(BaseModel):
    id: int
    kind: str
    content: str
    created_at: str


class ExecutionRecord(BaseModel):
    id: int
    step_id: str
    tool: str
    status: str
    output: str
    created_at: str


class EventRecord(BaseModel):
    type: str
    message: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    payload: dict[str, Any] = Field(default_factory=dict)


class TranscriptionResponse(BaseModel):
    transcript: str


ChatResponse.model_rebuild()
