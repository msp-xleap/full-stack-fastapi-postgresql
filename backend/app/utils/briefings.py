from fastapi import HTTPException
from sqlmodel import Session, select

from typing import Sequence

from app.models import Briefing, Briefing2, Briefing2Reference


def get_briefing_by_agent_id(agent_id: str, session: Session) -> Briefing:
    """Get briefing by agent ID

    Args:
        agent_id (str): UUID of the agent to be activated
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing: Briefing object
    """
    # Find briefing by agent ID
    query = select(Briefing).where(Briefing.agent_id == agent_id)
    briefing = session.exec(query).first()

    if briefing is None:
        # If briefing is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="Briefing for this agent does not exist in the system",
        )
    return briefing


def get_briefing2_by_agent(agent_id: str, session: Session) -> Briefing2:
    """Get briefing by agent

    Args:
        agent_id (str): UUID of the agent
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing2: Briefing2 object
    """
    # Find briefing by agent ID
    query = select(Briefing2).where(Briefing2.agent_id == agent_id)
    briefing = session.exec(query).first()

    if briefing is None:
        # If briefing is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="Briefing for this agent does not exist in the system",
        )
    return briefing


def get_briefing2_references_by_agent(agent_id: str, session: Session) -> Sequence[Briefing2Reference]:
    """Returns the references of a briefing

    Args:
        agent_id (stc): UUID of agent
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing2: Briefing2 object
    """

    # Find references by briefing ID
    query = select(Briefing2Reference).where(Briefing2Reference.agent_id == agent_id)
    return session.exec(query).all()
