import json
import logging
from random import random

from fastapi import APIRouter, BackgroundTasks, Depends

from app import crud
from app.api.deps import SessionDep, get_db
from app.models import Idea, IdeaBase, BulkIdeaDeletionRequestData

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


def _maybe_kick_idea_generation(agent,
                                agent_id: str,
                                new_idea: IdeaBase,
                                session: SessionDep,
                                background_tasks: BackgroundTasks):
    """
    To be called when we receive an Idea from XLeap. Check if the specified Agent should generate
    its next own idea.
    :param agent: the agent object
    :param agent_id: the agent ID
    :param new_idea: the last new idea received from XLeap
    :param session: the database session
    :param background_tasks: the background tasks
    """

    # no need to check anything when the agent is not active
    if not agent.is_active:
        logging.info(f"Agent {agent.id} is not active")
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

            random_number = random()

            debug_info = {
                'agent.is_active': agent.is_active,
                'previous_id': previous_id,
                'last_ai_idea.id': last_ai_idea.id,
                'frequency': frequency,
                'random_number': random_number,
                '1/frequency': 1 / frequency,
                'frequency//2': frequency // 2,
                'new_idea.idea_count': new_idea.idea_count,
                'new_idea.idea_count - last_ai_idea_count': new_idea.idea_count - last_ai_idea_count
            }

            logging.info(json.dumps(debug_info, indent=2))

            # Generate idea and post if agent is active
            if (
                    (previous_id is None
                     or previous_id != last_ai_idea.id)
                    and new_idea.idea_count >= frequency // 2
                    and (random_number < 1 / frequency
                         or (frequency // 2 <= new_idea.idea_count - last_ai_idea_count >=
                             frequency))
                    # and idea.idea_count % frequency == 0  # as an alternative to the
                    # line above
            ):
                was_tasked = True
                lock.set_last_idea(last_ai_idea)
                background_tasks.add_task(
                    generate_idea_and_post, agent, briefing, lock
                )
            else:
                logging.info(f"Agent {agent.id} does not need to create an idea")
        finally:
            if not was_tasked:
                lock.release()
    else:
        logging.info(f"Agent {agent.id} lock was already held")


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

    cou_result = crud.create_or_update_idea(session=session, idea=new_idea, agent_id=agent_id)
    new_idea = cou_result.idea

    if cou_result.is_new:
        _maybe_kick_idea_generation(agent=agent,
                                    agent_id=agent_id,
                                    new_idea=new_idea,
                                    session=session,
                                    background_tasks=background_tasks)


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
    agent = get_agent_by_id(agent_id, session)

    last_new_idea: Idea | None = None
    for idea in ideas:
        cou_result = crud.create_or_update_idea(session=session, idea=idea, agent_id=agent_id)

        if cou_result.is_new:
            last_new_idea = cou_result.idea

    if last_new_idea is not None:
        _maybe_kick_idea_generation(agent=agent,
                                    agent_id=agent_id,
                                    new_idea=last_new_idea,
                                    session=session,
                                    background_tasks=background_tasks)


MARK_IDEAS_DELETED_ONLY = True
""" if true Idea's are only marked as deleted, otherwise they are actually deleted """


@router.delete(
    "/agents/{agent_id}/ideas/bulk",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=200,
)
async def delete_ideas(
        agent_id: str,
        idea_ids: list[str],
        session: SessionDep,
        ) -> None:
    """
    Deletes multiple Ideas for an agent
    :param agent_id: ID of Agent
    :param idea_ids: the body of the request with a list of IDs (either the UUID of an idea or the XLeap ID for an idea)
    :param session: the database session
    """
    # Check if agent exists
    get_agent_by_id(agent_id, session)  # throws 404 error is agent was not found

    for idea_id in idea_ids:
        delete_idea_by_agent_and_id(agent_id, idea_id, MARK_IDEAS_DELETED_ONLY, session, True)


@router.delete(
    "/agents/{agent_id}/ideas/{idea_id}",
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

