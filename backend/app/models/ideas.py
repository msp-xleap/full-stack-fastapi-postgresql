import uuid as uuid_pkg
from datetime import datetime

from sqlmodel import Field, SQLModel


class IdeaBase(SQLModel):
    id: str
    text: str
    folder_id: str | None = None
    created_by_ai: bool
    created_by_this_ai: bool
    created_by: str | None = None

class Idea(IdeaBase, table=True):
    __tablename__ = "idea"

    idea_id: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    agent_id: uuid_pkg.UUID = Field(
        default=None, foreign_key="ai_agent.id", nullable=False
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False
    )
    idea_count: int = Field(default=None)
    deleted: bool = False
