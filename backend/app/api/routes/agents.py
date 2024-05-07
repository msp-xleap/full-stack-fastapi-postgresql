import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks
from sqlmodel import select

from app import crud
from app.api.deps import SessionDep
from app.models import (
    AIAgent,
    AIAgentCreate,
    AIAgentIdResponse,
    AIAgentsOut,
    AIBriefing2Base,
    BriefingTextResponse,
    AIBriefingTest,
)
from app.utils import check_agent_exists_by_instance_id, get_agent_by_id, get_briefing2_by_agent_id

router = APIRouter()


@router.get("/", response_model=AIAgentsOut, status_code=200)
def read_agents(session: SessionDep) -> Any:
    """
    Retrieve all agents.
    """
    agents = session.exec(select(AIAgent)).all()

    return AIAgentsOut(data=agents)


@router.post(
    "/",
    response_model=AIAgentIdResponse,
    responses={409: {"detail": "Agent already exists"}},
    status_code=202,
)
async def create_agent(
    *,
    session: SessionDep,
    agent_in: AIAgentCreate,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Create new agent.

    To do: Serialize briefings. currently, default values are stored in the
        database.
    """
    # Check if agent already exists
    check_agent_exists_by_instance_id(agent_in.xleap.instance_id, session)

    # Create agent if it does not exist
    agent = crud.create_ai_agent(session=session, ai_agent=agent_in)
    briefing = crud.create_ai_agent_briefing2(session=session, ai_agent=agent, briefing_base=agent_in.briefing)

    for brie_ref in agent_in.briefing.workspace_info_references:
        crud.create_ai_agent_briefing2_reference(session=session, briefing=briefing, briefing_ref_base=brie_ref)

    for exemplar in agent_in.briefing.exemplar_references:
        crud.create_ai_agent_briefing2_reference(session=session, briefing=briefing, briefing_ref_base=exemplar)

    # background_tasks.add_task(get_agent_briefing, agent)

    return AIAgentIdResponse(agent_id=str(agent.id))


@router.post(
    "/{agent_id}/activate/",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=200,
)
async def activate_agent(agent_id: str, session: SessionDep) -> None:
    """
    Activate agent.

    To do:
        - Add/validate secret to the request body or in header.

    Args:
        agent_id (str): UUID of the agent to be activated
        session (SessionDep): Database session

    Raises:
        HTTPException - 403: If the secret is invalid.
        HTTPException - 404: If the agent is not found.

    Returns:
        None
    """
    # Find agent by ID
    agent = get_agent_by_id(agent_id, session)

    # Activate agent
    crud.activate_ai_agent(session=session, ai_agent=agent)


@router.post(
    "/{agent_id}/deactivate/",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=200,
)
async def deactivate_agent(agent_id: str, session: SessionDep) -> None:
    """
    Deactivate agent.

    To do:
        - Add/validate secret to the request body or in header.
        - Stop running processes of agent in the background.

    Args:
        agent_id (str): UUID of the agent to be deactivated
        session (SessionDep): Database session

    Raises:
        HTTPException - 403: If the secret is invalid.
        HTTPException - 404: If the agent is not found.

    Returns:
        None
    """
    # Find agent by ID
    agent = get_agent_by_id(agent_id, session)

    # Deactivate agent
    crud.deactivate_ai_agent(session=session, ai_agent=agent)


@router.put(
    "/{agent_id}/briefing/",
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=200,
)
async def update_agent_briefing(
        *,
        agent_id: str,
        briefing_in: AIBriefing2Base,
        session: SessionDep) -> Any:
    """
    Updates the briefing of an existing agent.

    To do:
        - Add/validate secret to the request body or in header.

    Args:
        agent_id (str): UUID of the agent to be activated
        briefing_in (AIBriefing2Base) the latest briefing
        session (SessionDep): Database session

    Raises:
        HTTPException - 403: If the secret is invalid.
        HTTPException - 404: If the agent is not found.

    Returns:
        None
    """
    # Find agent by ID
    agent = get_agent_by_id(agent_id, session)

    crud.create_or_update_ai_agent_briefing2(session=session, ai_agent=agent, briefing_base=briefing_in)

    crud.replace_briefing2_references(
        session=session,
        agent_id=str(agent.id),
        briefing_refs=briefing_in.workspace_info_references
    )
    return None


@router.get(
    "/{agent_id}/briefing/",
    response_model=BriefingTextResponse,
    responses={
        403: {"detail": "Invalid secret"},
        404: {"detail": "Agent not found"},
    },
    status_code=200,
)
async def get_briefing_as_text(
        *,
        agent_id: str,
        session: SessionDep) -> Any:
    from app.orchestration.prompts.xleap_few_shot import describe_system_prompt
    # Check if agent exists
    agent = get_agent_by_id(agent_id, session)
    briefing = get_briefing2_by_agent_id(agent_id, session)
    prompt = await describe_system_prompt(agent, briefing, session)

    logging.info(json.dumps({"text": prompt.prompt, "vars": prompt.lang_chain_input}, indent=4))

    return BriefingTextResponse(
        text=prompt.prompt.format(**prompt.lang_chain_input)
    )


@router.post("/{agent_id}/test",
             responses={
                 403: {"detail": "Invalid secret"},
                 404: {"detail": "Agent not found"},
             },
             status_code=202)
async def test_briefing(
        agent_id: str,
        config: AIBriefingTest,
        session: SessionDep,
        background_tasks: BackgroundTasks) -> None:
    """
    Tests the briefing for an agent.
    This test can be run at any time meaning, unlike create_idea
      1. the agent does not need to be active
      2. the agent might already be creating ideas with 'create_idea'
      3. this method does not account existing ideas it just feeds
         the briefing to the AI and directly asks it to generate one or more ideas

    :param agent_id:
    :param config:
    :param session:
    :return:
    """
    from app.orchestration.prompts.xleap_briefing_test import generate_ideas_and_post
    # Check if agent already exists
    agent = get_agent_by_id(agent_id, session)

    briefing = get_briefing2_by_agent_id(agent_id, session)

    background_tasks.add_task(
        generate_ideas_and_post, agent, briefing, config.secret, config.num_samples, session,
    )
