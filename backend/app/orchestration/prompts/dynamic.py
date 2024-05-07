import logging

from app.api.deps import SessionDep
from app.models import AIAgent, Briefing2, PromptStrategyType
from app.utils import (
    AgentGenerationLock,
    get_briefing_by_agent_id,
    get_prompt_strategy,
)

from .chaining import generate_idea_and_post as chaining_generate_idea_and_post
from .few_shot import generate_idea_and_post as few_shot_generate_idea_and_post
from .xleap_few_shot import (
    generate_idea_and_post as xleap_generate_idea_and_post,
)


async def generate_idea_and_post(
    agent: AIAgent,
    briefing: Briefing2,
    lock: AgentGenerationLock,
    session: SessionDep,
) -> None:
    """
    Dynamically switches the prompt strategy for the specified agent
    """

    try:
        strategy = get_prompt_strategy(agent=agent, session=session)

        logging.info(
            f"""Using prompt strategy {strategy.type} (version {strategy.version}) for agent {agent.id}"""
        )

        match strategy.type:
            case PromptStrategyType.CHAINING:
                briefing1 = get_briefing_by_agent_id(str(agent.id), session)
                await chaining_generate_idea_and_post(
                    agent, briefing1, session
                )
            case PromptStrategyType.FEW_SHOT:
                briefing1 = get_briefing_by_agent_id(str(agent.id), session)
                await few_shot_generate_idea_and_post(
                    agent, briefing1, session
                )
            case PromptStrategyType.XLEAP_ZERO_SHOT:
                await xleap_generate_idea_and_post(
                    agent, briefing, session
                )  # same as few shot deprecated
            case PromptStrategyType.XLEAP_FEW_SHOT:
                await xleap_generate_idea_and_post(agent, briefing, session)
            case _:
                raise ValueError(f"Unhandled strategy type: '{strategy.type}'")
    except Exception as e:
        lock.set_last_idea(None)
        raise e
    finally:
        lock.release()
