import uuid as uuid_pkg
from datetime import datetime

from sqlmodel import Field, SQLModel


class IdeaBase(SQLModel):
    id: str
    text: str
    folder_id: str | None = None
    created_by_ai: bool
    """ did this AI create this idea? """
    created_by_an_ai: bool = Field(default=False, nullable=False)
    """ did an AI (this or another) create this idea? """
    created_by: str | None = None
    """ ID of the user or AI who created the idea (may depend on anonymity settings) """
    visible: bool = True
    """ The microservice may receive ideas that are not visible to it. Invisible ideas should
        only be used for counting purposes. E.g. act after n-human contributions.
    """


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


class IdeaGenerationData(SQLModel):
    """Generate number of examples based on a briefing"""

    reference: str
    """ the secret to be presented to XLeap with every generated example idea
        This is required to bypass Agent.is_active check in XLeap
    """
    num_items: int
    """ the number of items to generate """
