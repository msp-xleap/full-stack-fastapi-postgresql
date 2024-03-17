from typing import Any

from fastapi import APIRouter

from app import crud
from app.api.deps import SessionDep
from app.models import AIAgentCreate, AgentIdResponse
from app.utils import get_agent, check_agent_exists

router = APIRouter()


@router.post("/",
             response_model=AgentIdResponse,
             responses={409: {"detail": "Agent already exists"}},
             status_code=202)
def create_agent(*, session: SessionDep, agent_in: AIAgentCreate) -> Any:
    """
    Create new agent.
    """
    # Check if agent already exists
    check_agent_exists(agent_in.xleap.instance_id, session)

    # Create agent if it does not exist
    agent = crud.create_ai_agent(session=session, ai_agent=agent_in)

    return AgentIdResponse(agent_id=str(agent.id))


@router.post("/{agent_id}/activate/",
             responses={403: {"detail": "Invalid secret"},
                        404: {"detail": "Agent not found"}}, status_code=200)
async def activate_agent(agent_id: str, session: SessionDep) -> None:
    """
    Activate agent.
    
    To do:
        - Add/validate secret to the request body or in header.
    
    Args:
        agent_id (str): UUID of the agent to be activated
        session (SessionDep): Database session

    Raises:
        HTTPException - 403: If the secret is invalid.
        HTTPException - 404: If the agent is not found.

    Returns:
        None
    """
    # Find agent by ID
    agent = get_agent(agent_id, session)

    # Activate agent
    activated_agent = crud.activate_ai_agent(session=session, ai_agent=agent)
    return


@router.post("/{agent_id}/deactivate/",
             responses={403: {"detail": "Invalid secret"},
                        404: {"detail": "Agent not found"}}, status_code=200)
async def deactivate_agent(agent_id: str, session: SessionDep) -> None:
    """
    Deactivate agent.

    To do:
        - Add/validate secret to the request body or in header.
        - Stop running processes of agent in the background.

    Args:
        agent_id (str): UUID of the agent to be deactivated
        session (SessionDep): Database session

    Raises:
        HTTPException - 403: If the secret is invalid.
        HTTPException - 404: If the agent is not found.

    Returns:
        None
    """
    # Find agent by ID
    agent = get_agent(agent_id, session)

    # Deactivate agent
    deactivated_agent = crud.deactivate_ai_agent(session=session,
                                                 ai_agent=agent)
    return
