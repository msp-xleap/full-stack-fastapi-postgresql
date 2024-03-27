from sqlalchemy import Column, Select, func
from sqlmodel import Session, select

from app.models import Idea, IdeaBase


def create_idea(*, session: Session, idea: IdeaBase, agent_id: str) -> Idea:
    """Store new AI Agent in the database

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object

    Returns:
        AIAgent: Created AI Agent object
    """
    # Calculate the next idea_count for the given agent_id
    stmt: Select[Column] = select(  # type: ignore
        func.coalesce(func.max(Idea.idea_count), 0) + 1
    ).filter(Idea.agent_id == agent_id)  # type: ignore
    next_idea_count = session.exec(stmt).first()  # type: ignore

    if next_idea_count is None:
        next_idea_count = 1

    # Validate idea object and create new idea
    db_obj = Idea.model_validate(
        idea.model_dump(),
        update={"agent_id": agent_id, "idea_count": next_idea_count},
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj
