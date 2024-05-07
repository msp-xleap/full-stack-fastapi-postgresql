import uuid as uuid_pkg

from sqlalchemy import Column, Select, func
from sqlmodel import Session, select

from app.models import Idea, IdeaBase
from app.utils import agent_manager, check_if_idea_exists


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

    # acquire a lock to avoid two ideas getting the same count
    lock = agent_manager.acquire_contribution_lock(agent_id=agent_id)
    try:
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
    finally:
        lock.release()


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
    do_not_update_creator: set[str] = set('created_by')
    idea_data = idea_new.model_dump(exclude_unset=True, exclude=do_not_update_creator)
    idea_db.sqlmodel_update(idea_data)
    idea_db.deleted = False  # Idea was restored
    session.add(idea_db)
    session.commit()
    session.refresh(idea_db)
    return idea_db


class CreateOrUpdateResult:
    def __init__(self, idea: Idea, is_new: bool):
        self.idea: Idea = idea
        self.is_new: bool = is_new


def create_or_update_idea(session: Session, agent_id: uuid_pkg.uuid4, idea: IdeaBase) -> CreateOrUpdateResult:
    # Check if idea already exists
    idea_old = check_if_idea_exists(
        session=session, idea_id=idea.id, agent_id=agent_id
    )

    if not idea_old:
        # Create idea if it does not exist
        return CreateOrUpdateResult(idea=create_idea(session=session, idea=idea, agent_id=agent_id), is_new=True)
    else:
        # deleted = idea_old.deleted
        # Update idea if it exists
        return CreateOrUpdateResult(idea=update_idea(session=session, idea_db=idea_old, idea_new=idea), is_new=False)
