import uuid as uuid_pkg

from sqlalchemy import Column, Select, func
from sqlmodel import Session, select

from app.models import Idea, IdeaBase


def create_idea(
    *, session: Session, idea: IdeaBase, agent_id: uuid_pkg.uuid4
) -> Idea:
    """Store new AI Agent in the database

    Args:
        session (Session): Database session
        idea (IdeaBase): Idea object
        agent_id (uuid_pkg.uuid4): Agent ID

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


def update_idea(
    *, session: Session, idea_db: Idea, idea_new: IdeaBase
) -> Idea:
    """
    Update an existing idea in the database.

    Args:
        session (Session): Database session
        idea_db (Idea): Existing idea object
        idea_new (IdeaBase): New idea object

    Returns:
        Idea: Updated idea object
    """
    idea_data = idea_new.model_dump(exclude_unset=True)
    idea_db.sqlmodel_update(idea_data)
    session.add(idea_db)
    session.commit()
    session.refresh(idea_db)
    return idea_db
