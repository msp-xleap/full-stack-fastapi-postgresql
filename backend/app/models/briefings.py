import enum
import uuid as uuid_pkg

from sqlmodel import Field, SQLModel, PrimaryKeyConstraint, Column, ForeignKeyConstraint, String, Text, Index



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
        PrimaryKeyConstraint("category", "sub_category", "template", name="xleap_briefing_prompt_pk"),
    )

    category: BriefingCategory = Column(String(50))
    sub_category: BriefingSubCategory = Column(String(50))
    template: str = Column(Text)
    """ The prompt template """
    langfuse_prompt: str
    """ The name of the prompt in langfuse """


class AIBriefing3ReferenceBase(SQLModel):
    ref_id: str
    type: str
    workspace_type: str = Field(None)
    text: str
    template: str
    url: str
    url_expires_at: str
    filename: str

class AIBriefing3Base(SQLModel):
    instance_id: str
    frequency: int = 7
    workspace_type: str = ""
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
    workspace_info_references: list[AIBriefing3ReferenceBase] = Field(None)
    with_num_exemplar: int = 0
    exemplar_template: str = ""
    exemplar_references: list[AIBriefing3ReferenceBase] = Field(None)

class AIBriefing3LangfuseBase(SQLModel):
    response_length_langfuse: str = ""
    additional_info_langfuse: str = ""
    persona_langfuse: str = ""
    tone_langfuse: str = ""
    session_info_langfuse: str = ""
    host_info_langfuse: str = ""
    participant_info_langfuse: str = ""
    workspace_info_langfuse: str = ""
    exemplar_langfuse: str = ""

class AIBriefing3ReferenceLangfuseBase(SQLModel):
    template_langfuse: str = ""


class Briefing3(SQLModel, table=True):
    __tablename__ = "briefing3"
    __table_args__ = (
        PrimaryKeyConstraint("agent_id", name="briefing3_pk"),
        ForeignKeyConstraint(["agent_id"], ["ai_agent.id"])
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
    response_length_langfuse_name: str = ""
    with_additional_info: bool = False
    additional_info_text: str = ""
    additional_info_langfuse_name: str = ""
    with_persona: bool = False
    persona_text: str = ""
    persona_langfuse_name: str = ""
    workspace_type: str = ""
    with_tone: bool = False
    tone_text: str = ""
    tone_langfuse: str = ""
    with_session_info: bool = False
    session_info_text: str = ""
    session_info_langfuse_name: str = ""
    with_host_info: bool = False
    host_info_text: str = ""
    host_info_langfuse_name: str = ""
    with_participant_info: bool = False
    participant_info_text: str = ""
    participant_info_langfuse_name: str = ""
    with_workspace_info: bool = False
    workspace_info_text: str = ""
    workspace_info_langfuse_name: str = ""
    with_exemplar: bool = False
    exemplar_text: str = ""
    exemplar_langfuse: str = ""


class Briefing3Reference(SQLModel, table=True):
    __tablename__ = "briefing3_reference"
    __table_args__ = (
        PrimaryKeyConstraint("agent_id", "ref_id", name="briefing3_ref_pk"),
        ForeignKeyConstraint(["agent_id"], ["ai_agent.id"])
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
    workspace_type: str = ""
    text: str
    langfuse_name: str
    url: str
    url_expires_at: str
    filename: str


class Briefing(SQLModel, table=True):
    """ Deprecated """
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