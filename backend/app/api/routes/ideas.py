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
)
from app.utils.task_broker import broker

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

    briefing = get_briefing2_by_agent_id(agent_id, session)
    frequency = briefing.frequency + 1
    last_ai_idea = get_last_ai_idea(session, agent_id)
    last_ai_idea_count = last_ai_idea.idea_count if last_ai_idea else 0

    # Generate idea and post if agent is active
    # Todo: determine threshold out of agent settings
    if (
        agent.is_active
        # and not agent.is_generating
        and idea.idea_count >= frequency // 2
        and (
            random() < 1 / frequency
            or (
                frequency // 2
                <= idea.idea_count - last_ai_idea_count
                >= frequency
            )
        )
        # and idea.idea_count % frequency == 0  # as an alternative to the
        # line above
    ):
        # background_tasks.add_task(
        #     generate_idea_and_post, agent, briefing, session
        # )

        print(f"""
s
        BROKER TASKS:
        {broker.get_all_tasks()}


""")


        await generate_idea_and_post.kicker().with_broker(broker).kiq(agent,
                                                                 briefing)

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
