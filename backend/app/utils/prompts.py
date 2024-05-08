from sqlmodel import Session, select
from app.models import PromptStrategy, PromptStrategyType


def get_prompt_strategy(*, session: Session, agent_id: str) -> PromptStrategy:
    """
     returns the prompt strategy to use.
     This works as follows:
     1. check if a strategy for the agent was defined
        IF YES return it
        IF NO, then check if a default strategy is defined
            IF YES return it
            OTHERWISE return  XLEAP_FEW_SHOT
    :param session: the sql session
    :param agent_id: the ID of the agent to use.
    :return: the strategy to use for this agent.
    """
    query = select(PromptStrategy).where(PromptStrategy.agent_id == agent_id)
    strategy = session.exec(query).first()

    if strategy is None:
        # ignore, alchemy cannot handle "is None"
        query = select(PromptStrategy).where(PromptStrategy.agent_id == None)  # noqa
        strategy = session.exec(query).first()

    if strategy is not None:
        return strategy

    return PromptStrategy(type=PromptStrategyType.CHAINING, version=0)
