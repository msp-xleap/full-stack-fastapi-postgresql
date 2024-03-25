import uuid as uuid_pkg

from sqlalchemy import func
from sqlmodel import Field, SQLModel
from datetime import datetime


class IdeaBase(SQLModel):
    id: str
    text: str
    folder_id: str | None = None
    created_by_ai: bool


class Idea(IdeaBase, table=True):
    __tablename__ = "ideas"

    idea_id: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    agent_id: uuid_pkg.UUID = Field(default=None, foreign_key="ai_agent.id",
                          nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow,
                                 nullable=False)
    idea_count: int = Field(default=None)