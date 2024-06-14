from sqlmodel import Session, select

from app.models import ThresholdStrategy


def get_threshold_strategy_type(
        *, session: Session, agent_id: str, host_id: str
) -> str:
    """
     returns the threshold strategy type to use.
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

    The strategy string contains multiple instructions separated with '+'
    The following instructions are supported:
    1) +dynamic: Dynamic condition based on AI idea share:
                Using a buffer to add flexibility to the decision to post.

    2) +random: Random chance to post based on the defined frequency.

    3) +1: Increases the frequency defined in XLeap by 1 (AS: why)

    4) (default) empty only uses the frequency defined by XLeap

    example: '+dynamic+random+1'
    The example is the strategy used during experiments

    :param session: the sql session
    :param agent_id: the ID of the agent to use.
    :param host_id: the ID of the host of the session where the agent was defined
    :return: the strategy to use for this agent.
    """
    query = select(ThresholdStrategy).where(ThresholdStrategy.agent_id == agent_id)
    strategy = session.exec(query).first()

    if strategy is None and host_id is not None and host_id != "":
        # ignore, alchemy cannot handle "is None"
        query = select(ThresholdStrategy).where(ThresholdStrategy.host_id == host_id)  # noqa
        strategy = session.exec(query).first()

    if strategy is None:
        # ignore, alchemy cannot handle "is None"
        query = select(ThresholdStrategy).where(
            ThresholdStrategy.agent_id == None, ThresholdStrategy.host_id == ""
        )  # noqa
        strategy = session.exec(query).first()

    if strategy is not None:
        return strategy.type

    return ''
