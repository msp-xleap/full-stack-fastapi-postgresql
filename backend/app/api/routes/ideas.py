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
    agent_manager,
    check_if_idea_exists,
    get_agent_by_id,
    get_briefing2_by_agent_id,
    get_last_ai_idea, get_ai_idea_share, should_ai_post_new_idea,
)

router = APIRouter()


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
    # Check if idea already exists
    idea_old = check_if_idea_exists(
        session=session, idea_id=idea.id, agent_id=agent_id
    )

    if not idea_old:
        # Create idea if it does not exist
        idea = crud.create_idea(session=session, idea=idea, agent_id=agent_id)
    else:
        # Update idea if it exists
        idea = crud.update_idea(
            session=session, idea_db=idea_old, idea_new=idea
        )

    lock = agent_manager.try_acquire_generation_lock(agent.id)
    if lock.acquired:
        was_tasked = False
        try:
            briefing = get_briefing2_by_agent_id(agent_id, session)
            frequency = briefing.frequency + 1
            last_ai_idea = get_last_ai_idea(session, agent_id)
            ai_share = get_ai_idea_share(session, agent_id)

            # Post the idea if specific conditions are met. These include:
            # the agent being active, no current lock preventing posting,
            # and criteria indicating the need for more visibility of
            # AI-generated ideas—such as AI ideas being underrepresented,
            # a favorable random chance outcome, or a significant increase
            # in idea count.
            should_post = should_ai_post_new_idea(
                agent=agent, lock=lock, last_ai_idea=last_ai_idea,
                idea=idea, frequency=frequency, ai_idea_share=ai_share
            )
            # Generate idea and post if agent is active
            if should_post:
                was_tasked = True
                lock.last_id = idea.id
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
