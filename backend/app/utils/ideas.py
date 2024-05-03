import logging
import uuid as uuid_pkg

from sqlmodel import Session, desc, select, func

from app.models import Idea
from fastapi import HTTPException


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
               Idea.created_by_ai == False,
               Idea.deleted == False)  # noqa
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
               Idea.created_by_ai == True,
               Idea.deleted == False)
        .order_by(desc(Idea.idea_count))  # noqa
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
        .order_by(desc(Idea.idea_count))  # noqa
    )
    idea = session.exec(query).first()
    return idea


def get_human_ideas_since(session: Session,
                          agent_id: uuid_pkg.uuid4,
                          reference_idea: Idea) -> int:
    """
        Count the number of ideas created by a human since the last AI contribution
        indicated by the specified idea

    :param session: Database session.
    :param agent_id: Agent ID
    :param reference_idea: a reference Idea
    :return: number of human ideas since the specified Idea was generated
    """

    query = (
        select(func.count())
        .select_from(Idea)
        .where(Idea.agent_id == agent_id,
               Idea.created_by_ai == False,  # noqa
               Idea.created_at > reference_idea.created_at)
    )

    count = (session.execute(query).scalar_one())
    return count


def delete_idea_by_agent_and_id(agent_id: str, xleap_idea_id_or_uuid: str, mark_only: bool, session: Session):
    """Deletes an idea

    Args:
        agent_id (str): UUID of the agent to be activated
        xleap_idea_id_or_uuid (str): The ID of the Idea either the UUID of the Idea (Idea.idea_id) or the
            XLeap's system (Idea.id)
        mark_only (bool): when True the idea's deleted flag is set to True, otherwise
            the entity actually deleted from the database
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the idea was not found
    """
    if xleap_idea_id_or_uuid.startswith('bsi_'):
        query = (
            select(Idea)
            .where(Idea.agent_id == agent_id, Idea.id == xleap_idea_id_or_uuid)
        )
    else:
        query = (
            select(Idea)
            .where(Idea.agent_id == agent_id, Idea.idea_id == xleap_idea_id_or_uuid)
        )

    idea = session.exec(query).first()

    if idea is None:
        logging.info(f"The requested idea does not exist {xleap_idea_id_or_uuid} for {agent_id}")
        # If agent is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="The idea with this id does not exist in the system",
        )
    else:
        if mark_only:
            idea.deleted = True
            session.merge(idea)
        else:
            session.delete(idea)
        session.commit()
