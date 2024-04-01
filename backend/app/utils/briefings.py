from fastapi import HTTPException
from sqlmodel import select

from app.api.deps import SessionDep
from app.models import Briefing


def get_briefing_by_agent_id(agent_id: str, session: SessionDep) -> Briefing:
    """Get briefing by agent ID

    Args:
        agent_id (str): UUID of the agent to be activated
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the agent is not found.

    Returns:
        AIAgent: Agent object
    """
    # Find briefing by agent ID
    query = select(Briefing).where(Briefing.agent_id == agent_id)
    briefing = session.exec(query).first()

    if briefing is None:
        # If agent is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="Briefing for this agent does not exist in the system",
        )
    return briefing
