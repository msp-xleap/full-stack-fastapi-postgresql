
from fastapi import HTTPException

from app.api.deps import SessionDep
from app.models import AIAgent


def get_agent(agent_id: str, session: SessionDep) -> AIAgent:
    """Get agent by ID

    Args:
        agent_id (str): UUID of the agent to be activated
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the agent is not found.

    Returns:
        AIAgent: Agent object
    """
    # Find agent by ID
    agent = session.get(AIAgent, agent_id)
    if agent is None:
        # If agent is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="The agent with this id does not exist in the system",
        )
    return agent


def check_agent_exists_by_instance_id(
        instance_id: str, session: SessionDep
) -> None:
    """Check if an agent with the given an instance ID already exists.

    Args:
        instance_id (str): Instance ID of the agent to be created.
        session (SessionDep): Database session.

    Raises:
        HTTPException - 409: If the agent already exists.

    Returns:
        None
    """
    existing_agent = (
        session.query(AIAgent).filter_by(instance_id=instance_id).first()
    )
    if existing_agent:
        raise HTTPException(
            status_code=409,
            detail={
                "error_message": "An agent with this instance id already "
                                 "exists in the system",
                "agent_id": str(existing_agent.id),
            },
        )
