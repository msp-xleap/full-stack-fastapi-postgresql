from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select
from app import crud

from app.api.deps import CurrentUser, SessionDep
from app.models import Item, ItemCreate, ItemOut, ItemsOut, ItemUpdate, Message, AIAgentBase

router = APIRouter()


# @router.post("/", response_model=ItemOut, status_code=202)
# def create_agent(
#         *, session: SessionDep, agent_in: AIAgentBase
# ) -> Any:
#     """
#     Create new agent.
#     """
#     agent = crud.create_ai_agent(session=session, ai_agent=agent_in)
#
#     return agent.id