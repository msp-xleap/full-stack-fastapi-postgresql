
import uuid as uuid_pkg
from random import random

from sqlmodel import Session, desc, select, func

from app.models import Idea, AIAgent
from app.utils import AgentGenerationLock
from fastapi import HTTPException

import logging


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


def get_last_n_ideas(
    session: Session, n: int, agent_id: uuid_pkg.uuid4
) -> list[Idea] | None:
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


def get_last_ai_idea(
    session: Session, agent_id: uuid_pkg.uuid4
) -> Idea | None:
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

def get_ai_idea_share(session: Session, agent_id: uuid_pkg.uuid4) -> float:
    """
    Calculate the percentage share of ideas created by AI for a given agent.

    Args:
        session (Session): Database session.
        agent_id (uuid.UUID): Agent ID.

    Returns:
        float: Percentage of ideas created by AI. Between 0 and 1.
    """
    # Total number of ideas created by the agent
    total_ideas_query = (
        select(func.count())
        .where(Idea.agent_id == agent_id)
    )
    total_ideas = session.execute(total_ideas_query).scalar_one()

    # Number of ideas created by AI by the same agent
    ai_ideas_query = (
        select(func.count())
        .where(Idea.agent_id == agent_id, Idea.created_by_ai == True)
    )
    ai_ideas = session.execute(ai_ideas_query).scalar_one()

    # Calculating the percentage of AI-created ideas
    if total_ideas == 0:
        return 0.0  # To handle division by zero if there are no ideas
    ai_idea_share = (ai_ideas / total_ideas)

    return ai_idea_share


def should_ai_post_new_idea(
        agent: AIAgent,
        lock: AgentGenerationLock,
        last_ai_idea: Idea,
        frequency: int,
        ai_idea_share: float,
        last_ai_idea_count: int
) -> bool:
    """
    Determine whether a new AI-generated idea should be posted based on
    various factors, such as
    - whether the agent is active
    - whether agent is currently generating an idea
    - the share of AI ideas relative to the target share


    Args:
        agent (AIAgent): Agent instance, must have an 'is_active' attribute.
        lock (AgentGenerationLock): Lock instance, must have a 'last_id' attribute.
        last_ai_idea (Idea): The last AI idea fetched.
        frequency (int): The expected frequency of idea posting.
        ai_idea_share (float): The percentage of ideas created by AI.
        last_ai_idea_count (int): The number of Ideas generated since last_ai_idea was created
    Returns:
        bool: True if a new AI idea should be posted, False otherwise.
    """
    debug = True
    # Primary rule: If the agent is not active there is no need to check anything else
    if not agent.is_active:
        if debug:
            logging.info('should_ai_post_new_idea: No, the agent is not active')
        return False

    previous_id = lock.get_last_id()
    # We base our calculations on the number of ideas generated since
    # our agent created its last idea. However, if this is still the same
    # we should not continue.
    if previous_id is not None and previous_id == last_ai_idea.id:
        return False

    # Defines the "ideal" share of AI ideas.
    target_share = 1 / frequency
    # 25% buffer around the target share for flexibility.
    buffer = 0.25 * target_share

    # Checking idea count relative to frequency
    if last_ai_idea_count < frequency // 2:
        if debug:
            logging.info(f"should_ai_post_new_idea: No, because: {last_ai_idea_count} < {frequency // 2}")
        return False

    # Dynamic condition based on AI idea share:
    # Using a buffer to add flexibility to the decision to post.
    if ai_idea_share < target_share - buffer:
        # Post more if the share of AI ideas is significantly below the target.
        if debug:
            logging.info(f"should_ai_post_new_idea: Yes, because AI share is to low: {ai_idea_share} < {target_share - buffer}")
        return True
    elif ai_idea_share > target_share + buffer:
        # Do not post if AI ideas are significantly overrepresented.
        if debug:
            logging.info(f"should_ai_post_new_idea: No, because AI share is to high: {ai_idea_share} > {target_share + buffer}")
        return False

    # Fallback conditions for additional posting checks:
    # Random chance to post based on the defined frequency.
    random_chance_to_post = random() < 1 / frequency
    # Significant change in idea count, suggesting a burst of new ideas.
    significant_idea_increase = (last_ai_idea_count >= frequency)

    # Evaluate fallback conditions
    if random_chance_to_post:
        if debug:
            logging.info(f"should_ai_post_new_idea: Yes, because of randomness")
        return True

    if significant_idea_increase:
        if debug:
            logging.info(f"should_ai_post_new_idea: Yes, significant increase in idea count: {last_ai_idea_count} >= {frequency}")
        return True
    return False


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


def delete_idea_by_agent_and_id(agent_id: str,
                                xleap_idea_id_or_uuid: str,
                                mark_only: bool,
                                session: Session,
                                silent: bool = False):
    """Deletes an idea

    Args:
        agent_id (str): UUID of the agent to be activated
        xleap_idea_id_or_uuid (str): The ID of the Idea either the UUID of the Idea (Idea.idea_id) or the
            XLeap's system (Idea.id)
        mark_only (bool): when True the idea's deleted flag is set to True, otherwise
            the entity actually deleted from the database
        session (SessionDep): Database session
        silent (bool): Default False in which case a HTTPException is raised when the specified ID does
            not exist, if True no exception is raised

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
        if silent:
            return

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
