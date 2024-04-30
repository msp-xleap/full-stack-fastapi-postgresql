import enum
import uuid as uuid_pkg

from sqlmodel import Column, Field, SQLModel, String


class PromptStrategyType(enum.StrEnum):
    """
    Defines the primary prompt strategy to use.

    New names should not be longer than 50 characters!
    """

    CHAINING = "chaining"
    FEW_SHOT = "few_shot"
    # ZERO_SHOT = "zero_shot"
    XLEAP_ZERO_SHOT = "xleap_zero_shot"
    XLEAP_FEW_SHOT = "xleap_few_shot"


class PromptStrategy(SQLModel, table=True):
    """
    Defines the prompt strategy to use.

    If the table s empty the strategy used will be XLEAP.
    Otherwise, the first record without an agent_id is the default (there should only be one)
    """

    __tablename__ = "prompt_strategy"

    id: int | None = Field(default=None, primary_key=True)
    type: str = Column(
        String(50)
    )  # explicitly a string to make it easier changing this in DB
    version: int = 0
    """ a version field in case we ever want different variants """
    agent_id: uuid_pkg.UUID = Field(None, nullable=True)
    """ optional default None, if specified the agent with the given UID will use this strategy """
