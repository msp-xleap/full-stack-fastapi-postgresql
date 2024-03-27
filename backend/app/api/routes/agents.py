from typing import Any

from fastapi import APIRouter, BackgroundTasks
from sqlmodel import select

from app import crud
from app.api.deps import SessionDep
from app.models import AIAgent, AIAgentCreate, AIAgentIdResponse, AIAgentsOut
from app.utils import check_agent_exists_by_instance_id, get_agent

router = APIRouter()


@router.get("/", response_model=AIAgentsOut, status_code=200)
def read_agents(session: SessionDep) -> Any:
    """
    Retrieve all agents.
    """
    agents = session.exec(select(AIAgent)).all()

    return AIAgentsOut(data=agents)


@router.post(
    "/",
    response_model=AIAgentIdResponse,
    responses={409: {"detail": "Agent already exists"}},
    status_code=202,
)
async def create_agent(
    *,
    session: SessionDep,
    agent_in: AIAgentCreate,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Create new agent.
    """
    # Check if agent already exists
    check_agent_exists_by_instance_id(agent_in.xleap.instance_id, session)

    # Create agent if it does not exist
    agent = crud.create_ai_agent(session=session, ai_agent=agent_in)
    # background_tasks.add_task(get_agent_briefing, agent)

    return AIAgentIdResponse(agent_id=str(agent.id))


@router.post(
    "/{agent_id}/activate/",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=200,
)
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
    crud.activate_ai_agent(session=session, ai_agent=agent)


@router.post(
    "/{agent_id}/deactivate/",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=200,
)
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
    crud.deactivate_ai_agent(session=session, ai_agent=agent)
