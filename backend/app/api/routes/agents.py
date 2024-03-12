from typing import Any

from fastapi import APIRouter
from app import crud

from app.api.deps import SessionDep
from app.models import AIAgentCreate

router = APIRouter()


@router.post("/", response_model=dict, status_code=202)
def create_agent(
        *, session: SessionDep, agent_in: AIAgentCreate
) -> Any:
    """
    Create new agent.
    """
    agent = crud.create_ai_agent(session=session, ai_agent=agent_in)

    return {"agent_id": agent.id}
