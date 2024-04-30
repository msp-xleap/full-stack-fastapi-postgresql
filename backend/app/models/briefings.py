import enum
import uuid as uuid_pkg

from sqlmodel import (
    Column,
    Field,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    SQLModel,
    String,
    Text,
)


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


class BriefingCategory(enum.StrEnum):
    """
    Defines the primary information conveyed by a briefing item.
    A briefing categories transport target specific information.

    The string value of this type corresponds to the Java enum type
    com.meetingsphere.util.constants.AIBriefingCategory
    """

    RESPONSE_LENGTH = "response_length"
    """ Prompts the AI about the expected lengthiness of it answers.
        This type uses the subtypes SHORT, MEDIUM and LONG.
    """
    ADDITIONAL_INFO = "additional_info"
    """ An additional specific instruction to the AI. """
    PERSONA = "persona"
    """ Tells the AI about the persona it should assume. """
    TONE = "tone"
    """ Tells the AI about the tone it should be using it its messages. """
    HOST_INFO = "host_info"
    """ Tells the AI about who the host is. """
    PARTICIPANT_INFO = "participant_info"
    """ Tells the AI about who the participants are. """
    SESSION_INFO = "session_info"
    """ Give the AI context about the XLeap session
        This type uses the workspace subtypes WS_*
    """
    WORKSPACE_PURPOSE_INFO = "workspace_purpose_info"
    """ Give the AI context about the particular workspace it is about
        to contribute to.
        This type uses the workspace subtypes WS_*
    """
    EXEMPLAR = "exemplar"
    """ Gives the AI examples of good contributions """
    LINK = "link"
    """ Provides the AI additional info in form of a web links. """
    FILE = "file"
    """ Provides the AI additional info in form of a file. """
    WORKSPACE_CONTENT = "workspace_content"
    """ Provides the AI additional inform of content from other XLeap
        workspaces.
        This type uses the workspace subtypes WS_*
    """
    CONTEXT_INTRO = "context_intro"
    """ The generic info for the following context prompt parts
        This type uses the workspace subtypes WS_*
    """
    WORKSPACE_INSTRUCTION = "workspace_instruction"
    """ The instruction for the workspace
        This type uses the workspace subtypes WS_*
    """
    TASK_TEMPLATE = "task_template"
    """ The template used to instruct the agent to contribute more ideas
    based on participants contributions
    """
    TEST_BRIEFING_TEMPLATE = "test_briefing_template"
    """ The template used to generate N-ideas only based on the briefing
    """


class BriefingSubCategory(enum.StrEnum):
    """
    Defines a sub category of a category
    E.g. a WORKSPACE_PURPOSE_INFO can be specific to a workspace.

    The string value of this type corresponds to the Java enum type
    net.xleap.ai.services.micro.constants.PromptSubtype
    """

    NONE = "none"
    """ For PromptTypes without a subtype """
    BRIEF = "brief"
    """ Used as subtype of
      PromptType.RESPONSE_LENGTH
      (not called SHORT = 'shot' because shot is a reserved keyword in java)
    """
    MEDIUM = "medium"
    """ Used as subtype of
      PromptType.RESPONSE_LENGTH
    """
    DETAILED = "detailed"
    """ Used as subtype of
      PromptType.RESPONSE_LENGTH
      (not called LONG = 'long' because long is a reserved keyword in java)
    """
    EXEMPLAR = "exemplar"
    """ Used as subtype for concreate an exemplar """
    WS_BRAINSTORM = "ws_brainstorm"
    """ Used as subtype of
     PromptType.SESSION_INFO,
     PromptType.WORKSPACE_PURPOSE_INFO,
     PromptType.WORKSPACE_CONTENT
    """
    WS_DEEPDIVE = "ws_deepdive"
    """ Used as subtype of
      PromptType.SESSION_INFO,
      PromptType.WORKSPACE_PURPOSE_INFO ,
      PromptType.WORKSPACE_CONTENT
    """
    WS_PRESENTATION = "ws_presentation"
    """ Used as subtype of
     PromptType.SESSION_INFO,
     PromptType.WORKSPACE_PURPOSE_INFO,
     PromptType.WORKSPACE_CONTENT
    """
    WS_RESULTS = "ws_results"
    """ Used as subtype of
     PromptType.SESSION_INFO,
     PromptType.WORKSPACE_PURPOSE_INFO,
     PromptType.WORKSPACE_CONTENT
    """
    WS_MULTI_RESULTS = "ws_multi_results"
    """ Used as subtype of
     PromptType.SESSION_INFO,
     PromptType.WORKSPACE_PURPOSE_INFO,
     PromptType.WORKSPACE_CONTENT
    """


class XLeapBriefingPrompt(SQLModel, table=True):
    """
    The XLeapPrompt table provides a mapping between an
    XLeap's language keys, its usage and the prompt created
    in Langfuse.
    Because a language key may change over time and the microservice
    can potentially be used by multiple XLeap applications the mapping
    occurs purly on the text
    """

    __tablename__ = "xleap_briefing_prompt"
    __table_args__ = (
        PrimaryKeyConstraint(
            "category",
            "sub_category",
            "template",
            name="xleap_briefing_prompt_pk",
        ),
    )
    # store BriefingCategory and BriefingSubCategory as string because alembic
    # does not update these correctly when we add or remove types
    category: str = Column(String(50))
    sub_category: str = Column(String(50))
    template: str = Column(Text)
    """ The prompt template """
    langfuse_prompt: str
    """ The name of the prompt in langfuse """


class AIBriefing2ReferenceBase(SQLModel):
    ref_id: str
    ref_number: int
    type: str
    workspace_type: str = Field(None, nullable=True)
    text: str
    template: str
    url: str
    url_expires_at: str
    filename: str


class AIBriefing2Base(SQLModel):
    instance_id: str
    frequency: int = 7
    workspace_type: str = ""
    response_length: int = 3
    response_length_template: str = ""
    context_intro_template: str = ""
    with_additional_info: bool = False
    additional_info: str = ""
    additional_info_template: str = ""
    with_persona: bool = False
    persona: str = ""
    persona_template: str = ""
    with_tone: bool = False
    tone: str = ""
    tone_template: str = ""
    with_session_info: bool = False
    session_info: str = ""
    session_info_template: str = ""
    with_host_info: bool = False
    host_info: str = ""
    host_info_template: str = ""
    with_participant_info: bool = False
    participant_info: str = ""
    participant_info_template: str = ""
    with_workspace_info: bool = False
    workspace_info: str = ""
    workspace_info_template: str = ""
    workspace_info_references: list[AIBriefing2ReferenceBase] = Field(None)
    with_workspace_instruction: bool = False
    workspace_instruction: str = ""
    workspace_instruction_template: str = ""
    with_num_exemplar: int = 0
    exemplar_template: str = ""
    exemplar_references: list[AIBriefing2ReferenceBase] = Field(None)
    task_template: str = ""
    test_briefing_template: str = ""


class AIBriefing2LangfuseBase(SQLModel):
    response_length_langfuse_name: str = ""
    context_intro_langfuse_name: str = ""
    additional_info_langfuse_name: str = ""
    persona_langfuse_name: str = ""
    tone_langfuse_name: str = ""
    session_info_langfuse_name: str = ""
    host_info_langfuse_name: str = ""
    participant_info_langfuse_name: str = ""
    workspace_info_langfuse_name: str = ""
    workspace_instruction_langfuse_name: str = ""
    exemplar_langfuse_name: str = ""
    task_langfuse_name: str = ""
    test_briefing_langfuse_name: str = ""


class AIBriefing2ReferenceLangfuseBase(SQLModel):
    langfuse_name: str = ""


class Briefing2(SQLModel, table=True):
    __tablename__ = "briefing2"
    __table_args__ = (
        PrimaryKeyConstraint("agent_id", name="briefing2_pk"),
        ForeignKeyConstraint(["agent_id"], ["ai_agent.id"]),
    )

    agent_id: uuid_pkg.UUID = (
        Field(
            default=None,
            foreign_key="ai_agent.id",
            primary_key=True,
            unique=True,
            index=True,
            nullable=False,
        ),
    )

    instance_id: str
    frequency: int = 7
    response_length: int = 3
    response_length_langfuse_name: str = ""
    context_intro_langfuse_name: str = ""
    with_additional_info: bool = False
    additional_info: str = ""
    additional_info_langfuse_name: str = ""
    with_persona: bool = False
    persona: str = ""
    persona_langfuse_name: str = ""
    workspace_type: str = ""
    with_tone: bool = False
    tone: str = ""
    tone_langfuse_name: str = ""
    with_session_info: bool = False
    session_info: str = ""
    session_info_langfuse_name: str = ""
    with_host_info: bool = False
    host_info: str = ""
    host_info_langfuse_name: str = ""
    with_participant_info: bool = False
    participant_info: str = ""
    participant_info_langfuse_name: str = ""
    with_workspace_info: bool = False
    workspace_info: str = ""
    workspace_info_langfuse_name: str = ""
    with_workspace_instruction: bool = False
    workspace_instruction: str = ""
    workspace_instruction_langfuse_name: str = ""
    with_num_exemplar: int = 0
    exemplar: str = ""
    exemplar_langfuse_name: str = ""
    task_langfuse_name: str = ""
    test_briefing_langfuse_name: str = ""


class Briefing2Reference(SQLModel, table=True):
    __tablename__ = "briefing2_reference"
    __table_args__ = (
        PrimaryKeyConstraint("agent_id", "ref_id", name="briefing2_ref_pk"),
        ForeignKeyConstraint(["agent_id"], ["ai_agent.id"]),
    )

    agent_id: uuid_pkg.UUID = (
        Field(
            default=None,
            foreign_key="ai_agent.id",
            unique=True,
            nullable=False,
        ),
    )

    ref_id: str = Field(
        index=True,
        nullable=False,
    )
    ref_number: int = 0
    type: str
    workspace_type: str = Field(None, nullable=True)
    text: str
    langfuse_name: str
    url: str
    url_expires_at: str
    filename: str


class BriefingTextResponse(SQLModel):
    text: str
