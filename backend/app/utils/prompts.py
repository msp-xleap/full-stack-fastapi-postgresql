from sqlmodel import Session, select
from app.models import PromptStrategy, PromptStrategyType


def get_prompt_strategy(*, session: Session, agent_id: str, host_id: str) -> PromptStrategy:
    """
     returns the prompt strategy to use.
     This works as follows:
     1. Check if a strategy for the agent was defined
        IF YES return it
        IF NO goto 2
     2. Check if we have a host_id and check if the host or the session has
            a preferred strategy
        IF NO goto 3
     3. Check if a default strategy is defined
            IF YES return it
            OTHERWISE return XLEAP_FEW_SHOT
    :param session: the sql session
    :param agent_id: the ID of the agent to use.
    :param host_id: the ID of the host of the session where the agent was defined
    :return: the strategy to use for this agent.
    """
    query = select(PromptStrategy).where(PromptStrategy.agent_id == agent_id)
    strategy = session.exec(query).first()

    if strategy is None:
        # ignore, alchemy cannot handle "is None"
        query = select(PromptStrategy).where(PromptStrategy.host_id == None)  # noqa
        strategy = session.exec(query).first()

    if strategy is None and host_id is not None and host_id != "":
        # ignore, alchemy cannot handle "is None"
        query = select(PromptStrategy).where(PromptStrategy.host_id == host_id)  # noqa
        strategy = session.exec(query).first()

    if strategy is not None:
        return strategy

    return PromptStrategy(type=PromptStrategyType.CHAINING, version=0)
