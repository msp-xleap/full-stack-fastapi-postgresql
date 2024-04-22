import uuid as uuid_pkg

from sqlmodel import Field, SQLModel, PrimaryKeyConstraint

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


class AIBriefing2ReferenceBase(SQLModel):
    ref_id: str = Field(unique=True, index=True)
    type: str
    text: str
    template: str
    url: str
    url_expires_at: str
    filename: str


class AIBriefing2Base(SQLModel):
    instance_id: str = Field(unique=True, index=True)
    frequency: int = 7
    response_length: int = 3
    response_length_template: str = ""
    with_additional_info: bool = False
    additional_info_text: str = ""
    additional_info_template: str = ""
    with_persona: bool = False
    persona_text: str = ""
    persona_template: str = ""
    with_tone: bool = False
    tone_text: str = ""
    tone_template: str = ""
    with_session_info: bool = False
    session_info_text: str = ""
    session_info_template: str = ""
    with_host_info: bool = False
    host_info_text: str = ""
    host_info_template: str = ""
    with_participant_info: bool = False
    participant_info_text: str = ""
    participant_info_template: str = ""
    with_workspace_info: bool = False
    workspace_info_text: str = ""
    workspace_info_template: str = ""
    workspace_info_references: list[AIBriefing2ReferenceBase]


class Briefing(SQLModel, table=True):
    __tablename__ = "briefing"

    briefing_id: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
        unique=True,
        index=True,
        nullable=False,
    )

    frequency: int = 7
    question: str = "MY QUESTION"
    topic: str = "MY TOPIC"

    agent_id: uuid_pkg.UUID = (
        Field(default=None,
              foreign_key="ai_agent.id",
              nullable=False,
              unique=True,
              index=True,
       ),
    )


class Briefing2(SQLModel, table=True):
    __tablename__ = "briefing2"
    __table_args__ = (
        PrimaryKeyConstraint("agent_id", name="briefing_pk"),
    )

    agent_id: uuid_pkg.UUID = (
        Field(default=None,
              foreign_key="ai_agent.id",
              primary_key=True,
              unique=True,
              index=True,
              nullable=False),
    )

    instance_id: str
    frequency: int = 7
    response_length: int = 3
    response_length_template: str = ""
    with_additional_info: bool = False
    additional_info_text: str = ""
    additional_info_template: str = ""
    with_persona: bool = False
    persona_text: str = ""
    persona_template: str = ""
    with_tone: bool = False
    tone_text: str = ""
    tone_template: str = ""
    with_session_info: bool = False
    session_info_text: str = ""
    session_info_template: str = ""
    with_host_info: bool = False
    host_info_text: str = ""
    host_info_template: str = ""
    with_participant_info: bool = False
    participant_info_text: str = ""
    participant_info_template: str = ""
    with_workspace_info: bool = False
    workspace_info_text: str = ""
    workspace_info_template: str = ""


class Briefing2Reference(SQLModel, table=True):
    __tablename__ = "briefing2_reference"
    __table_args__ = (
        PrimaryKeyConstraint("agent_id", "ref_id", name="briefing_ref_pk"),
    )

    agent_id: uuid_pkg.UUID = (
        Field(default=None,
              foreign_key="ai_agent.id",
              unique=True,
              nullable=False),
    )

    ref_id: str = Field (
        index=True,
        nullable=False,
    )
    type: str
    text: str
    template: str
    url: str
    url_expires_at: str
    filename: str
