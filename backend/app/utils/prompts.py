from sqlmodel import Session, select

from app.models import PromptStrategy, PromptStrategyType, AIAgent


def get_prompt_strategy(*, session: Session, agent: AIAgent) -> PromptStrategy:
    """ returns the prompt strategy to use """
    agent_id = agent.id
    query = select(PromptStrategy).where(PromptStrategy.agent_id == agent_id)
    strategy = session.exec(query).first()

    if strategy is None:
        query = select(PromptStrategy).where(PromptStrategy.agent_id is None)
        strategy = session.exec(query).first()

    if strategy is not None:
        return strategy

    return PromptStrategy(strategy=PromptStrategyType.XLEAP_ZERO_SHOT, version=0)
