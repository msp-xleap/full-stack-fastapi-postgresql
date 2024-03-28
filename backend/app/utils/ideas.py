from sqlmodel import Session, select

from app.models import Idea


def check_if_idea_exists(
    session: Session, idea_id: str, agent_id: str
) -> Idea | None:
    """
    Given an idea ID and an agent ID, check if the idea exists in the database.

    Args:
        session (SessionDep): Database session.
        idea_id (str): Idea ID of XLeap.
        agent_id (str): Agent ID.

    Returns:
        bool: True if the idea exists, False otherwise.
    """
    query = select(Idea).where(Idea.id == idea_id, Idea.agent_id == agent_id)
    idea = session.exec(query).first()
    return idea
