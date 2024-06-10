import logging

from fastapi import APIRouter, BackgroundTasks

from app import crud
from app.api.deps import SessionDep
from app.models import Idea, IdeaBase, IdeaGenerationData
from app.orchestration.prompts.dynamic import generate_idea_and_post
from app.utils import (
    agent_manager,
    check_if_idea_exists,
    delete_idea_by_agent_and_id,
    get_agent_by_id,
    get_last_ai_idea,
    should_ai_post_new_idea,
)

router = APIRouter()


def _maybe_kick_idea_generation(
    agent,
    agent_id: str,
    session: SessionDep,
    background_tasks: BackgroundTasks,
):
    """
    To be called when we receive an Idea from XLeap. Check if the specified Agent should generate
    its next own idea.
    :param agent: the agent object
    :param agent_id: the agent ID
    :param session: the database session
    :param background_tasks: the background tasks
    """

    logging.getLogger().setLevel(logging.INFO)

    # no need to check anything when the agent is not active
    if not agent.is_active:
        logging.info(f"Agent {agent.id} is not active")
        return

    lock = agent_manager.try_acquire_generation_lock(agent.id)
    if lock.acquired:
        was_tasked = False
        try:
            # Post the idea if specific conditions are met. These include:
            # the agent being active, no current lock preventing posting,
            # and criteria indicating the need for more visibility of
            # AI-generated ideas—such as AI ideas being underrepresented,
            # a favorable random chance outcome, or a significant increase
            # in idea count.
            should_post = should_ai_post_new_idea(
                agent=agent,
                lock=lock,
                session=session,
            )

            # Generate idea and post if agent is active
            if should_post:
                last_ai_idea = get_last_ai_idea(session, agent.id)
                lock.set_last_idea(last_ai_idea)
                background_tasks.add_task(
                    generate_idea_and_post,
                    str(agent.id),
                    agent.host_id,
                    lock,
                    1,
                    None,
                )
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
    idea: IdeaBase,
    background_tasks: BackgroundTasks,
) -> None:
    """
    Create a new idea. If idea for a given agent already exists, update the
    idea.
    """
    # Check if agent exists
    agent = get_agent_by_id(agent_id, session)

    cou_result = crud.create_or_update_idea(
        session=session, idea=idea, agent_id=agent_id
    )
    new_idea = cou_result.idea  # noqa

    if cou_result.is_new:
        _maybe_kick_idea_generation(
            agent=agent,
            agent_id=agent_id,
            session=session,
            background_tasks=background_tasks,
        )


@router.post(
    "/agents/{agent_id}/ideas",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=202,
)
async def create_idea(  # noqa
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
    check_if_idea_exists(
        session=session, idea_id=new_idea.id, agent_id=agent_id
    )

    cou_result = crud.create_or_update_idea(
        session=session, idea=new_idea, agent_id=agent_id
    )

    if cou_result.is_new:
        _maybe_kick_idea_generation(
            agent=agent,
            agent_id=agent_id,
            session=session,
            background_tasks=background_tasks,
        )


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
        cou_result = crud.create_or_update_idea(
            session=session, idea=idea, agent_id=agent_id
        )

        if cou_result.is_new:
            last_new_idea = cou_result.idea

    if last_new_idea is not None:
        _maybe_kick_idea_generation(
            agent=agent,
            agent_id=agent_id,
            session=session,
            background_tasks=background_tasks,
        )


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
    get_agent_by_id(
        agent_id, session
    )  # throws 404 error is agent was not found

    for idea_id in idea_ids:
        delete_idea_by_agent_and_id(
            agent_id, idea_id, MARK_IDEAS_DELETED_ONLY, session, True
        )


@router.delete(
    "/agents/{agent_id}/ideas/{idea_id}",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found or Idea not found"},
    },
    status_code=200,
)
async def delete_idea(
    agent_id: str, idea_id: str, session: SessionDep
) -> None:
    """
    Deletes an Idea for the specified agent
    :param agent_id: ID of Agent
    :param idea_id: either the UUID of an idea or the XLeap ID for an idea
    :param session: the database session
    """
    # Check if agent exists
    get_agent_by_id(
        agent_id, session
    )  # throws 404 error is agent was not found

    delete_idea_by_agent_and_id(
        agent_id, idea_id, MARK_IDEAS_DELETED_ONLY, session
    )


@router.post(
    "/agents/{agent_id}/ideas/generate",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=202,
)
async def generate_idea_(
    agent_id: str,
    session: SessionDep,
    config: IdeaGenerationData,
    background_tasks: BackgroundTasks,
) -> None:
    """
    On demand request to generate one or multiple ideas.
    The created ideas must pass the reference mentioned in the config to XLeap
    """
    # Check if agent exists
    agent = get_agent_by_id(agent_id, session)

    lock = agent_manager.acquire_generation_lock(agent.id)
    background_tasks.add_task(
        generate_idea_and_post,
        str(agent.id),
        lock,
        config.num_items,
        config.reference,
    )
