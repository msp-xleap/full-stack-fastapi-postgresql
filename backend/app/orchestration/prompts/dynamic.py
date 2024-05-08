import logging

from app.core.db import engine
from sqlmodel import Session
from app.models import AIAgent, Briefing2, PromptStrategyType
from app.utils import (
    AgentGenerationLock,
    get_prompt_strategy,
)

from .chaining import generate_idea_and_post as chaining_generate_idea_and_post
from .few_shot import generate_idea_and_post as few_shot_generate_idea_and_post
from .xleap_few_shot import (
    generate_idea_and_post as xleap_generate_idea_and_post,
)


async def generate_idea_and_post(
    agent_id: str,
    lock: AgentGenerationLock,
) -> None:
    """
    Dynamically switches the prompt strategy for the specified agent
    """
    with Session(engine) as session:
        try:
            strategy = get_prompt_strategy(agent_id=agent_id, session=session)

            logging.info(
                f"""Using prompt strategy {strategy.type} (version {strategy.version}) for agent {agent_id}"""
            )

            match strategy.type:
                case PromptStrategyType.CHAINING:
                    await chaining_generate_idea_and_post(
                        agent_id, session
                    )
                case PromptStrategyType.FEW_SHOT:
                    await few_shot_generate_idea_and_post(
                        agent_id, session
                    )
                case PromptStrategyType.XLEAP_ZERO_SHOT:
                    await xleap_generate_idea_and_post(
                        agent_id, session
                    )  # same as few shot deprecated
                case PromptStrategyType.XLEAP_FEW_SHOT:
                    await xleap_generate_idea_and_post(
                        agent_id, session
                    )
                case _:
                    raise ValueError(f"Unhandled strategy type: '{strategy.type}'")
        except Exception as e:
            lock.set_last_idea(None)
            raise e
        finally:
            lock.release()
