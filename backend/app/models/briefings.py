import uuid as uuid_pkg

from sqlmodel import Field, SQLModel

# ToDo: Change JSON object of Briefing. Currently, it is unncessarily nested
#  and can be simplified.
#  Example for future JSON object:
#  {
#       'briefing': {
#           'response_length':  2,
#           'workspace_purpose_info':  'MY QUESTION',
#           'frequency': 5,
#           // other fields
#           }
#  }


class Briefing(SQLModel, table=True):
    __tablename__ = "briefing"

    briefing_id: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )

    frequency: int = 7
    question: str = "MY QUESTION"
    topic: str = "MY TOPIC"

    agent_id: uuid_pkg.UUID = (
        Field(default=None, foreign_key="ai_agent.id", nullable=False),
    )
