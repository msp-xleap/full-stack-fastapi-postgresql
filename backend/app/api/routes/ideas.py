from fastapi import APIRouter, BackgroundTasks

from app import crud
from app.api.deps import SessionDep
from app.models import IdeaBase
from app.utils import get_agent

router = APIRouter()


@router.post("/agents/{agent_id}/ideas",
             responses={403: {"detail": "Invalid secret"},
                        404: {"detail": "Agent not found"}}, status_code=202)
async def create_idea(agent_id: str, session: SessionDep, idea: IdeaBase,
                      background_tasks: BackgroundTasks) -> None:
    """
    Create a new idea.
    """
    # Check if agent already exists
    agent = get_agent(agent_id, session)

    # Create agent if it does not exist
    idea = crud.create_idea(session=session, idea=idea, agent_id=agent_id)

    return


@router.post("/agents/{agent_id}/ideas/bulk", status_code=202)
async def create_ideas(agent_id: str, ideas: list[IdeaBase],
                       session: SessionDep,
                       background_tasks: BackgroundTasks, ):
    """
    Create multiple new ideas for an agent.
    """
    # Check if agent already exists
    agent = get_agent(agent_id, session)

    # Create ideas
    created_ideas: list = []
    for idea in ideas:
        created_idea = crud.create_idea(session=session, idea=idea,
                                        agent_id=agent_id)

    return
