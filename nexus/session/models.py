"""Pydantic models for session storage."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Turn(BaseModel):
    """Individual conversation turn."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    role: Literal["user", "assistant"]
    content: str
    model: str
    tokens: Dict[str, int] = Field(default_factory=dict)  # prompt, completion, total
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)  # files, system_prompt


class Session(BaseModel):
    """Complete session with all turns."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    model: str
    provider: str
    total_tokens: int = 0
    turns: List[Turn] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Search result with match details."""

    session_name: str
    match_type: Literal["name", "content"]
    matched_text: str  # Actual matched text, not snippet
    turn_count: int
    updated_at: datetime
