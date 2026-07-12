from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class ZoneRename(BaseModel):
    name: str


class ZoneMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: str
    name: str
    role: str
    joined_at: datetime


class ZoneInvitationCreate(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _normalize(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("not a valid email address")
        return value


class ZoneInvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    status: str
    created_at: datetime
