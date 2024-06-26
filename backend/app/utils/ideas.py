import logging
import uuid as uuid_pkg
from random import random

from fastapi import HTTPException
from sqlmodel import Session, desc, func, select

from app.models import AIAgent, Idea
from app.utils import AgentGenerationLock, get_briefing2_by_agent_id


def check_if_idea_exists(
    session: Session, idea_id: str, agent_id: uuid_pkg.uuid4
) -> Idea | None:
    """
    Given an idea ID and an agent ID, check if the idea exists in the database.

    Args:
        session (Session): Database session.
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
        n (int): Number of last ideas to retrieve. These are only the ideas of others.
        agent_id (uuid_pkg.uuid4): Agent ID.


    Returns:
        List[Idea]: List of last n ideas.
    """
    # Define your subquery to reverse the order
    subquery = (
        select(Idea)
        .where(
            Idea.agent_id == agent_id,
            Idea.created_by_ai == False,
            Idea.deleted == False,
        )  # noqa
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
        .where(
            Idea.agent_id == agent_id,
            Idea.created_by_ai == True,
            Idea.deleted == False,
        )
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
        .where(Idea.agent_id == agent_id, Idea.created_by_ai == True)
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
    total_ideas_query = select(func.count()).where(
        Idea.agent_id == agent_id, Idea.deleted == False
    )
    total_ideas = session.execute(total_ideas_query).scalar_one()

    # Number of ideas created by AI by the same agent
    ai_ideas_query = select(func.count()).where(
        Idea.agent_id == agent_id,
        Idea.deleted == False,
        Idea.created_by_ai == True,
    )
    ai_ideas = session.execute(ai_ideas_query).scalar_one()

    # Calculating the percentage of AI-created ideas
    if total_ideas == 0:
        return 0.0  # To handle division by zero if there are no ideas
    ai_idea_share = ai_ideas / total_ideas

    return ai_idea_share


def should_ai_post_new_idea(
    agent: AIAgent,
    lock: AgentGenerationLock,
    session: Session,
    # frequency: int,
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
        session (Session): the database session

    Returns:
        bool: True if a new AI idea should be posted, False otherwise.
    """
    debug = True
    if debug:
        logging.info(
            f"should_ai_post_new_idea: Computing share for agent {agent.id}"
        )

    # Primary rule: If the agent is triggered manually
    briefing = get_briefing2_by_agent_id(str(agent.id), session)
    # A frequency of 0 (or below) means the Agent will be triggered manually
    # However, we should not get here, since an on demand agent stay inactive.
    if briefing.frequency <= 0:
        logging.info(f"Agent {agent.id} is in on-demand mode")
        return False
    frequency = briefing.frequency + 1

    # Secondary rule: If the agent is not active there is no need to check
    # anything else
    if not agent.is_active:
        if debug:
            logging.info(
                "should_ai_post_new_idea: No, the agent is not active"
            )
        return False

    # Define various metrics related to idea generation for the agent. These
    # metrics are used as conditions for the AI contributions

    # Fetch the total number of human ideas
    total_human_ideas = get_total_human_ideas(session, agent.id)
    # Fetch the most recent AI-generated idea to establish a reference point
    last_ai_idea = get_last_ai_idea(session, agent.id)
    # Count the number of human-generated ideas that have been created since
    # the last AI-generated idea.
    human_ideas_since_ai = get_human_ideas_since(
        session, agent.id, last_ai_idea
    )
    # Calculate the proportion of ideas generated by AI compared to
    # total ideas, providing insight into AI versus human contribution.
    ai_ideas_share = get_ai_idea_share(session, agent.id)

    # Tertiary rule: If the idea is still locked, we will not generate a new
    # idea
    previous_id = lock.get_last_id()

    if previous_id is not None and previous_id == last_ai_idea.id:
        if debug:
            logging.info(
                "should_ai_post_new_idea: base idea is still the same, not "
                "continuing"
            )
        return False

    # Defines the "ideal" share of AI ideas.
    target_share = 1 / frequency
    # 25% buffer around the target share for flexibility.
    buffer = 0.25 * target_share

    # Ensuring that AI ideas are not posted to early in the process
    if total_human_ideas < frequency // 2:
        if debug:
            logging.info(
                f"should_ai_post_new_idea: No, because there are not enough"
                f"human ideas: {human_ideas_since_ai} < {frequency // 2}"
            )
        return False

    # Dynamic condition based on AI idea share:
    # Using a buffer to add flexibility to the decision to post.
    if ai_ideas_share < target_share - buffer:
        # Post more if the share of AI ideas is significantly below the target.
        if debug:
            logging.info(
                f"should_ai_post_new_idea: Yes, because AI share is to low: "
                f"{ai_ideas_share} < {target_share - buffer}"
            )
        return True
    elif ai_ideas_share > target_share + buffer:
        # Do not post if AI ideas are significantly overrepresented.
        if debug:
            logging.info(
                f"should_ai_post_new_idea: No, because AI share is to high: "
                f"{ai_ideas_share} > {target_share + buffer}"
            )
        return False

    # Fallback conditions for additional posting checks:
    # Random chance to post based on the defined frequency.
    random_chance_to_post = random() < 1 / frequency
    # Significant change in idea count, suggesting a burst of new ideas.
    significant_idea_increase = human_ideas_since_ai >= frequency

    # Evaluate fallback conditions
    if random_chance_to_post:
        if debug:
            logging.info("should_ai_post_new_idea: Yes, because of randomness")
        return True

    if significant_idea_increase:
        if debug:
            logging.info(
                f"should_ai_post_new_idea: Yes, significant increase in idea "
                f"count: {human_ideas_since_ai} >= {frequency}"
            )
        return True

    if debug:
        logging.info("should_ai_post_new_idea: No finally")
    return False


def get_total_human_ideas(session: Session, agent_id: uuid_pkg.UUID) -> int:
    """
    Counts the total number of human-created ideas for a given agent.

    Args:
        session (Session): Active database session.
        agent_id (UUID): The unique identifier for the agent.

    Returns:
        int: Total number of human-generated ideas.
    """
    # Base query for counting all human ideas
    query = (
        select(func.count())
        .select_from(Idea)
        .where(
            Idea.agent_id == agent_id,
            Idea.created_by_ai == False,  # Exclude AI-generated ideas
            Idea.deleted == False,  # Exclude deleted ideas
        )
    )

    # Execute the query and return the count, defaulting to 0 if none found
    count = session.execute(query).scalar_one_or_none()
    return count if count is not None else 0


def get_human_ideas_since(
    session: Session,
    agent_id: uuid_pkg.UUID,
    reference_idea: Idea | None = None,
) -> int:
    """
    Counts the number of human-created ideas since the last AI-generated idea, or all human ideas if no reference is given.

    Args:
        session (Session): Active database session.
        agent_id (UUID): The unique identifier for the agent.
        reference_idea (Optional[Idea]): The last AI-generated idea to use as a starting reference point, if available.

    Returns:
        int: Number of human-generated ideas since the specified reference idea, or total if no reference provided.
    """
    # Base query for counting ideas
    query = (
        select(func.count())
        .select_from(Idea)
        .where(
            Idea.agent_id == agent_id,
            Idea.created_by_ai == False,  # Exclude AI-generated ideas
            Idea.deleted == False,  # Exclude deleted ideas
        )
    )

    # Add condition to compare dates if a reference idea is provided
    if reference_idea:
        query = query.where(Idea.created_at > reference_idea.created_at)

    # Execute the query and return the count, defaulting to 0 if none found
    count = session.execute(query).scalar_one_or_none()
    return count if count is not None else 0


def delete_idea_by_agent_and_id(
    agent_id: str,
    xleap_idea_id_or_uuid: str,
    mark_only: bool,
    session: Session,
    silent: bool = False,
):
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
    if xleap_idea_id_or_uuid.startswith("bsi_"):
        query = select(Idea).where(
            Idea.agent_id == agent_id, Idea.id == xleap_idea_id_or_uuid
        )
    else:
        query = select(Idea).where(
            Idea.agent_id == agent_id, Idea.idea_id == xleap_idea_id_or_uuid
        )

    idea = session.exec(query).first()

    if idea is None:
        if silent:
            return

        logging.info(
            f"The requested idea does not exist {xleap_idea_id_or_uuid} for {agent_id}"
        )
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
