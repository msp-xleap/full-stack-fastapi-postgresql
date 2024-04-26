import uuid as uuid_pkg

from sqlmodel import Field, SQLModel

from .briefings import AIBriefing2Base

class XLeapDetailsBase(SQLModel):
    server_address: str
    session_id: str
    workspace_id: str
    instance_id: str = Field(unique=True, index=True)
    secret: str


class AIAgentConfigBase(SQLModel):
    api_type: str
    model: str
    api_url: str | None = None
    api_key: str
    org_id: str | None = None

class AIAgentCreate(SQLModel):
    xleap: XLeapDetailsBase
    config: AIAgentConfigBase
    briefing: AIBriefing2Base


class AIAgentBase(XLeapDetailsBase, AIAgentConfigBase):
    pass


# Database model, database table inferred from class name
class AIAgent(AIAgentBase, table=True):
    __tablename__ = "ai_agent"

    id: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    # hashed_secret: str
    is_active: bool = False


class AIAgentIdResponse(SQLModel):
    agent_id: str


class AIAgentsOut(SQLModel):
    data: list[AIAgent]
