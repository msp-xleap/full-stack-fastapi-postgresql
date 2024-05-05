
import uuid as uuid_pkg
from random import random

from sqlalchemy import func
from sqlmodel import Session, desc, select

from app.models import Idea, AIAgent
from app.utils import AgentGenerationLock


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
        .order_by(desc(Idea.idea_count))
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
        idea: Idea,
        frequency: int,
        ai_idea_share: float,
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
        idea (Idea): The current idea under consideration.
        frequency (int): The expected frequency of idea posting.
        ai_idea_share (float): The percentage of ideas created by AI.

    Returns:
        bool: True if a new AI idea should be posted, False otherwise.
    """
    # Defines the "ideal" share of AI ideas.
    target_share = 1 / frequency
    # 25% buffer around the target share for flexibility.
    buffer = 0.25 * target_share
    # Get the idea count of the last AI idea.
    last_ai_idea_count = last_ai_idea.idea_count if last_ai_idea else 0

    # Basic conditions to check if the agent is active and the idea
    # is not locked.
    if not agent.is_active:
        return False
    if lock.last_id is not None and lock.last_id == idea.id:
        return False

    # Checking idea count relative to frequency
    if idea.idea_count < frequency // 2:
        return False

    # Dynamic condition based on AI idea share:
    # Using a buffer to add flexibility to the decision to post.
    if ai_idea_share < target_share - buffer:
        # Post more if the share of AI ideas is significantly below the target.
        return True
    elif ai_idea_share > target_share + buffer:
        # Do not post if AI ideas are significantly overrepresented.
        return False

    # Fallback conditions for additional posting checks:
    # Random chance to post based on the defined frequency.
    random_chance_to_post = random() < 1 / frequency
    # Significant change in idea count, suggesting a burst of new ideas.
    significant_idea_increase = (idea.idea_count - last_ai_idea_count >= frequency)

    # Evaluate fallback conditions
    return random_chance_to_post or significant_idea_increase
