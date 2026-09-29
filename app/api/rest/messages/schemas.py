from datetime import datetime

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    content: str | None = None
    to_user_id: int | None = None
    chat_id: int | None = None
    pin_id: int | None = None


class MessageOut(BaseModel):
    id: int
    chat_id: int
    user_id_: int
    content: str | None = None
    created_at: datetime
    image: str | None = None
    is_read: bool | None = None
    pin_id: int | None = None
    message_kind: str = "text"


class ChatOut(BaseModel):
    id: int
    user_1_id: int | None = None
    user_2_id: int | None = None
    kind: str = "dm"
    title: str | None = None
    invite_code: str | None = None
    created_by: int | None = None


class ShareTargetOut(BaseModel):
    user_id: int
    username: str
    chat_id: int | None = None
    source: str  # chat | following


class SharePinIn(BaseModel):
    pin_id: int
    to_user_id: int | None = None
    chat_id: int | None = None


class CreateGroupIn(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    member_ids: list[int] = Field(default_factory=list)


class JoinGroupIn(BaseModel):
    code: str = Field(..., min_length=10, max_length=10)


class GroupCreatedOut(BaseModel):
    id: int
    title: str | None = None
    invite_code: str
    kind: str = "group"
