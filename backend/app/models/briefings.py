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
    TEMPERATURE = "temperature"
    """ The temperature which defined the creativity of the AI """
    RESPONSE_LANGUAGE = "response_language"
    """ The language in which the AI should respond to us """


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


class BriefingSubCategoryDifferentiator(enum.StrEnum):
    NONE = ""
    TASK_ONE_NN = "_1_nn"
    TASK_ONE_PN = "_1_pn"
    TASK_ONE_NA = "_1_na"
    TASK_ONE_PA = "_1_pa"
    TASK_MULTI_NN = "_m_nn"
    TASK_MULTI_PN = "_m_pn"
    TASK_MULTI_NA = "_m_na"
    TASK_MULTI_PA = "_m_pa"


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
    """ reference to the ID in XLeap for the briefing """
    workspace_type: str = ""
    """ The type of workspace this briefing is for
        e.g. 'brainstorm', 'deepdive', 'presentation'
    """
    frequency: int = 7
    """ After who many human contributions the AI should contribute.
        A frequency of 0 means that the agent should only generate a contribution
        when explicitly requested
    """
    temperature: int = 70
    """ A specific temperature (decimal, 1..200) for the AI.
        E.g. this is to be used when generating contributions. Other steps may use other temperatures.
    """
    response_length: int = 3
    """ A number in the range 1 - 3 where
        Where 1 means short, 2 medium, and 3 long.
    """
    response_length_template: str = ""
    """ The template for the prompt element as instruction to the AI
        This template has no variables
    """
    context_intro_template: str = ""
    """ The generic template for the context information of a workspace.
        This template has no variables
    """
    with_additional_info: bool = False
    """ Whether additional info should be provided to the AI """
    additional_info: str = ""
    """ The additional info to be passed to the self.additional_info_template as {{additional_info}} if
        self.with_additional_info is True
    """
    additional_info_template: str = ""
    """ The language template for the AI instruction.
        The template provides the {{additional_info}} variable for self.additional_info
    """
    with_persona: bool = False
    """ Whether the AI should assume a specific Persona """
    persona: str = ""
    """ The persona info to be passed to the self.persona_template as {{persona}} if
         self.with_persona is True
    """
    persona_template: str = ""
    """ The language template for the persona instruction.
        The template provides the {{persona}} variable for self.persona
    """
    with_tone: bool = False
    """ Whether the AI should use a specific tone its responses """
    tone: str = ""
    """ The tone info to be passed to the self.with_session_info as {{tone}} if
        self.with_tone is True
    """
    tone_template: str = ""
    """ The language template for the tone instruction.
        The template provides the {{tone}} variable for self.tone
    """
    with_session_info: bool = False
    """ Whether information about the current session should be provided to the AI """
    session_info: str = ""
    """ The session info to be passed to self.session_info_template as {{session_info}} if
        self.with_session_info is True
    """
    session_info_template: str = ""
    """  The language template for the session info instruction .
         The template provides the {{session_info} variable for self.session_info
    """
    with_host_info: bool = False
    """ Whether information about the host should be provided to the AI """
    host_info: str = ""
    """ The host info to be passed to the self.host_info_template as {{host_info}} if
       self.with_host_info is True
    """
    host_info_template: str = ""
    """ The language template for the host info instruction.
        The template provides the {{host_info}} variable for self.host_info.
        **NOTE:** the host info can be empty, if it is not empty it always ends with '. '
    """
    with_participant_info: bool = False
    """ Whether information about the participants should be provided to the AI """
    participant_info: str = ""
    """ The participants info to be passed to the self.participant_info_template
        as {{participant_info}} if self.with_participant_info is True
    """
    participant_info_template: str = ""
    """ The language template for the participant info instruction.
        The template provides the {{participant_info}} variable for self.participant_info_template.
    """
    with_workspace_info: bool = False
    """ Whether information about the workspace (e.g. Brainstorm) should be provided to the AI """
    workspace_info: str = ""
    """ The workspace information (e.g. the purpose of the brainstorm)
        to be passed to the self.workspace_info_template as {{workspace_info}}
        if self.with_workspace_info is True
    """
    workspace_info_template: str = ""
    """ The language template for the workspace info.
        The template provides one variable {{workspace_info}} variable for self.workspace_info.
    """
    workspace_info_references: list[AIBriefing2ReferenceBase] = Field(None)
    """  A list of references describing the purpose of the workspace.
     Depending on their AIBriefing2ReferenceBase.type their description is composed
     from their own templates AIBriefing2ReferenceBase.template and passed to the
     self.workspace_info_template as {{references}} if self.with_workspace_info is True.
     It is possible that there are no references, in such case {{references}} should be replaced with an empty string.
    """
    with_workspace_instruction: bool = False
    """ Whether the workspace has an instruction """
    workspace_instruction: str = ""
    """ The instruction passed to the self.workspace_instruction_template as {{workspace_instruction}} if
        self.with_workspace_instruction is True
    """
    workspace_instruction_template: str = ""
    """ The language template for the workspace instruction.
        The template provides the {{workspace_instruction}} variable for
        self.workspace_instruction.
    """
    with_num_exemplar: int = 0
    """ The number of provided exemplar """
    exemplar_template: str = ""
    """ The language template for the exemplar
        The template provides one variable, and ends with a colon ':'
        The examples are supposed to follow next.
        It provides the {{num-exemplar}} variable for self.with_num_exemplar
    """
    exemplar_references: list[AIBriefing2ReferenceBase] = Field(None)
    """
        The reference exemplar
    """
    with_response_language: bool = False
    """ Are we asking the AI to respond in a specific language.
        Only used if the requested response language differs from the language
        in the templates
    """
    response_language: str = ""
    """ The language to respond in passed to the self.response_language_template as
        {{response_language}} if self. with_response_language is True.
    """
    response_language_template: str = ""
    """ The template for the response language instruction. It has a variable {{response_language}}
    """
    task_template_nn: str = ""
    """  The task template to be used when the AI is ask to contribution 1 own contribution and
     there are neither participant contributions nor prior AI contributions.
     The template provides no variable
    """
    task_template_pn: str = ""
    """ The task template to be used when the AI is ask to contribution 1 own contribution and there are participant
     contributions but no prior AI contributions.
     The template provides no variable
    """
    task_template_na: str = ""
    """ The task template to be used when the AI is ask to contribution 1 own contribution and
      there are no participant contributions but prior AI contributions.
      The template provides no variable
    """
    task_template_pa: str = ""
    """ The task template to be used when the AI is ask to contribution <b>one</b> own contribution and
    there are participant and prior AI contributions.
    The template provides no variable
    """
    task_template_multi_nn: str = ""
    """ The task template to be used when the AI is ask to contribution multiple own contributions and
    there are neither participant contributions nor prior AI contributions.
    The template provides the variable {{num_contributions}} to the number of contributions to generate
    The value for the variable is provided as part of an on-demand request
    """
    task_template_multi_pn: str = ""
    """ The task template to be used when the AI is ask to contribution multiple own contributions and
     there are participant contributions but no prior AI contributions.
     The template provides the variable {{num_contributions}} to the number of contributions to generate
     The value for the variable is provided as part of an on-demand request
    """
    task_template_multi_na: str = ""
    """ The task template to be used when the AI is ask to contribution multiple own contributions and
    there are no participant contributions but prior AI contributions.
    The template provides the variable {{num_contributions}} to the number of contributions to generate
    The value for the variable is provided as part of an on-demand request
    """
    task_template_multi_pa: str = ""
    """ The task template to be used when the AI is ask to contribution multiple own contributions and
    there are participant and prior AI contributions.
    The template provides the variable {{num_contributions}} to the number of contributions to generate
    The value for the variable is provided as part of an on-demand request
    """
    test_briefing_template: str = ""
    """  The test briefing template is used when the host clicks on the test briefing
      button of an AI tab. The template provides a single variable {{num-generate}}
      for the number of ideas the Agent shall generate, if the number is 0 there the
      variable is not present. This number is provided in a separate test request.
    """


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
    contribution_langfuse_name: str = ""
    task_nn_langfuse_name: str = ""
    task_pn_langfuse_name: str = ""
    task_na_langfuse_name: str = ""
    task_pa_langfuse_name: str = ""
    task_multi_nn_langfuse_name: str = ""
    task_multi_pn_langfuse_name: str = ""
    task_multi_na_langfuse_name: str = ""
    task_multi_pa_langfuse_name: str = ""
    test_briefing_langfuse_name: str = ""
    response_language_langfuse_name: str = ""


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
    temperature: int = 70
    response_length: int = 3
    response_length_langfuse_name: str = ""
    with_response_language: bool = False
    response_language: str = ""
    response_language_langfuse_name: str = ""
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
    task_nn_langfuse_name: str = ""
    task_pn_langfuse_name: str = ""
    task_na_langfuse_name: str = ""
    task_pa_langfuse_name: str = ""
    task_multi_nn_langfuse_name: str = ""
    task_multi_pn_langfuse_name: str = ""
    task_multi_na_langfuse_name: str = ""
    task_multi_pa_langfuse_name: str = ""
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
