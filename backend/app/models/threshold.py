import uuid as uuid_pkg

from sqlmodel import Column, Field, SQLModel, String


class ThresholdStrategy(SQLModel, table=True):
    """
    Defines the threshold strategy to use.

    A Threshold strategy defines when an agent contributes the next idea

    The strategy string contains multiple instructions separated with '+' to enable strategy features
    The following instructions are supported:
    1) +dynamic: Dynamic condition based on AI idea share:
                Using a buffer to add flexibility to the decision to post.

    2) +random: Random chance to post based on the defined frequency.

    3) +1: Increases the frequency defined in XLeap by 1 (AS: why)

    4) (default) empty only uses the frequency defined by XLeap

    example: '+dynamic+random+1'
    The example is the strategy used during experiments
    """
    __tablename__ = "threshold_strategy"

    id: int | None = Field(default=None, primary_key=True)
    type: str = Column(
        String(50)
    )  # explicitly a string to make it easier changing this in DB
    agent_id: uuid_pkg.UUID = Field(None, nullable=True)
    """ optional default None, if specified the agent with the given UID will use this strategy """
    host_id: str = Field(None, nullable=True)
    """ optional default None, if specified and a host created an agent it will be using this strategy """
