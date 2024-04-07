import logging
import uuid as uuid_pkg

from sqlmodel import Session, desc, select

from app.models import Idea


def check_if_idea_exists(
        session: Session, idea_id: str, agent_id: uuid_pkg.uuid4
) -> Idea | None:
    """
    Given an idea ID and an agent ID, check if the idea exists in the database.

    Args:
        session (SessionDep): Database session.
        idea_id (str): Idea ID of XLeap.
        agent_id (uuid_pkg.uuid4): Agent ID.

    Returns:
        bool: True if the idea exists, False otherwise.
    """
    query = select(Idea).where(Idea.id == idea_id, Idea.agent_id == agent_id)
    idea = session.exec(query).first()
    return idea


def get_last_n_ideas(session: Session, n: int, agent_id: uuid_pkg.uuid4) -> \
        list[Idea] | None:
    """
    Retrieve the last n ideas from the database.

    Args:
        session (Session): Database session.
        n (int): Number of last ideas to retrieve.
        agent_id (uuid_pkg.uuid4): Agent ID.


    Returns:
        List[Idea]: List of last n ideas.
    """
    # Define your subquery to reverse the order
    subquery = (
        select(Idea)
        .where(Idea.agent_id == agent_id,
               Idea.created_by_ai == False)
        .order_by(desc(Idea.idea_count))
        .limit(n)
        .subquery()
    )

    # Use the subquery to fetch the reversed results
    query = session.query(subquery).order_by(subquery.c.idea_count)

    # Fetch the ideas
    ideas = query.all()

    ai_query = (
        select(Idea)
        .where(Idea.agent_id == agent_id,
               Idea.created_by_ai == True)
        .order_by(desc(Idea.idea_count))
    )
    ai_ideas = list(session.exec(ai_query))

    return ideas + ai_ideas


def get_last_ai_idea(session: Session,
                     agent_id: uuid_pkg.uuid4) -> Idea | None:
    """
    Retrieve the last AI idea from the database.

    Args:
        session (Session): Database session.
        agent_id (str): Agent ID.

    Returns:
        List[Idea]: List of last n ideas.
    """
    query = (
        select(Idea)
        .where(Idea.agent_id == agent_id,
               Idea.created_by_ai == True)
        .order_by(desc(Idea.idea_count))
    )
    idea = session.exec(query).first()
    return idea
