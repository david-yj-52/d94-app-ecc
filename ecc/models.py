from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class TicketStatus(StrEnum):
    CREATED = "CREATED"
    AWAITING_CONFIRM = "AWAITING_CONFIRM"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class CreateTicket(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    workspace: str = Field(min_length=1, max_length=500)


class IntentPlan(BaseModel):
    intent: str = "code_generation"
    target_cli: str = "claude"
    summary: str
    action_plan: list[str] = Field(default_factory=list)


class Ticket(BaseModel):
    ticket_id: str = Field(default_factory=lambda: f"TCK-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8]}")
    prompt: str
    workspace: str
    status: TicketStatus = TicketStatus.CREATED
    intent: str = "code_generation"
    target_cli: str = "claude"
    summary: str = ""
    action_plan: list[str] = Field(default_factory=list)
    result: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

