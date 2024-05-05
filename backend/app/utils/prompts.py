from sqlmodel import Session, select

from app.models import AIAgent, PromptStrategy, PromptStrategyType


def get_prompt_strategy(*, session: Session, agent: AIAgent) -> PromptStrategy:
    """
     returns the prompt strategy to use.
     This works as follows:
     1. check if a strategy for the agent was defined
        IF YES return it
        IF NO check if a default strategy is defined
            IF YES return it
            OTHERWISE return  XLEAP_FEW_SHOT
    :param session: the sql session
    :param agent: the agent to use.
    :return: the strategy to use for this agent.
    """
    agent_id = agent.id
    query = select(PromptStrategy).where(PromptStrategy.agent_id == agent_id)
    strategy = session.exec(query).first()

    if strategy is None:
        query = select(PromptStrategy).where(PromptStrategy.agent_id is None)
        # ignore, alchemy cannot handle "is None"
        strategy = session.exec(query).first()

    if strategy is not None:
        return strategy

    return PromptStrategy(type=PromptStrategyType.CHAINING, version=0)
