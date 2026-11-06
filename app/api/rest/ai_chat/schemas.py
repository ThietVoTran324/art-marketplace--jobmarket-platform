from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    meta: dict = Field(default_factory=dict)
    created_at: datetime | str | None = None


class ChatTurnOut(BaseModel):
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    warning: str | None = None


class ChatHistoryOut(BaseModel):
    messages: list[ChatMessageOut]


class ChatClearOut(BaseModel):
    cleared: bool
    conversation_id: int | None = None
    deleted_messages: int = 0
