from random import random

from fastapi import APIRouter, BackgroundTasks

from app import crud
from app.api.deps import SessionDep
from app.models import Idea, IdeaBase

# from app.orchestration.prompts.zero_shot import generate_idea_and_post
# from app.orchestration.prompts.few_shot import generate_idea_and_post
# from app.orchestration.prompts.chaining import generate_idea_and_post
from app.orchestration.prompts.dynamic import generate_idea_and_post
from app.utils import (
    check_if_idea_exists,
    get_agent_by_id,
    get_briefing2_by_agent_id,
    get_last_ai_idea,
    get_human_ideas_since,
    delete_idea_by_agent_and_id,
    agent_manager
)

router = APIRouter()

MARK_IDEAS_DELETED_ONLY = True
""" if true Idea's are only marked as deleted, otherwise they are actually deleted """


@router.delete(
    "/agents/{agent_id}/ideas/{idea_id}/",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found or Idea not found"},
    },
    status_code=200,
)
async def delete_idea(
     agent_id: str,
     idea_id: str,
     session: SessionDep) -> None:
    """
    Deletes an Idea for the specified agent
    :param agent_id: ID of Agent
    :param idea_id: either the UUID of an idea or the XLeap ID for an idea
    :param session: the database session
    """
    # Check if agent exists
    get_agent_by_id(agent_id, session)  # throws 404 error is agent was not found

    delete_idea_by_agent_and_id(agent_id, idea_id, MARK_IDEAS_DELETED_ONLY, session)


@router.post(
    "/agents/{agent_id}/ideas",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=202,
)
async def create_idea(
        agent_id: str,
        session: SessionDep,
        new_idea: IdeaBase,
        background_tasks: BackgroundTasks,
) -> None:
    """
    Create a new idea. If idea for a given agent already exists, update the
    idea.
    """
    # Check if agent exists
    agent = get_agent_by_id(agent_id, session)
    # Check if idea already exists
    idea_old = check_if_idea_exists(
        session=session, idea_id=new_idea.id, agent_id=agent_id
    )

    if not idea_old:
        # Create idea if it does not exist
        new_idea = crud.create_idea(session=session, idea=new_idea, agent_id=agent_id)
    else:
        # Update idea if it exists
        crud.update_idea(
            session=session, idea_db=idea_old, idea_new=new_idea
        )
        # don't react of edits
        return

    lock = agent_manager.try_acquire_generation_lock(agent.id)
    if lock.acquired:
        was_tasked = False
        try:
            briefing = get_briefing2_by_agent_id(agent_id, session)
            frequency = briefing.frequency + 1
            last_ai_idea = lock.get_last_idea()
            if last_ai_idea is None:
                last_ai_idea = get_last_ai_idea(session, agent_id)

            last_ai_idea_count = 0

            if last_ai_idea is not None:
                last_ai_idea_count = get_human_ideas_since(session, agent.id, last_ai_idea)

            previous_id = lock.get_last_id()

            # Generate idea and post if agent is active
            # Todo: determine threshold out of agent settings
            if (
                    agent.is_active
                    and (previous_id is None
                         or previous_id != last_ai_idea.id)
                    and new_idea.idea_count >= frequency // 2
                    and (random() < 1 / frequency
                         or (frequency // 2 <= new_idea.idea_count - last_ai_idea_count >=
                             frequency))
                    # and idea.idea_count % frequency == 0  # as an alternative to the
                    # line above
            ):
                was_tasked = True
                lock.set_last_idea(last_ai_idea)
                background_tasks.add_task(
                    generate_idea_and_post, agent, briefing, session, lock
                )
        finally:
            if not was_tasked:
                lock.release()

    return


@router.post("/agents/{agent_id}/ideas/bulk", status_code=202)
async def create_ideas(
        agent_id: str,
        ideas: list[IdeaBase],
        session: SessionDep,
        background_tasks: BackgroundTasks,
) -> None:
    """
    Create multiple new ideas for an agent.
    """
    # Check if agent already exists
    get_agent_by_id(agent_id, session)

    # Create ideas
    created_ideas: list[Idea] = []
    for idea in ideas:
        created_ideas.append(
            crud.create_idea(session=session, idea=idea, agent_id=agent_id)
        )
