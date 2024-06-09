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
from .multi_agent import (generate_idea_and_post as
                          multi_agent_generate_idea_and_post)


async def generate_idea_and_post(
    agent_id: str,
    host_id: str | None,
    lock: AgentGenerationLock,
    ideas_to_generate: int = 1,
    task_reference: str | None = None,
) -> None:
    """
    Dynamically switches the prompt strategy for the specified agent then generates the specified number
    of ideas
    :param agent_id: the ID of the agent
    :param host_id: the ID of the XLeap session's host (used to select the prompt strategy by host ID)
    :param lock: the lock for generating ideas
    :param ideas_to_generate: (optional, default=1) the number of ideas to generate
    :param task_reference: (optional, default=None) if specified the task_reference must be passed with
           every generated idea to XLeap
    :return:
    """
    with Session(engine) as session:
        try:
            strategy = get_prompt_strategy(agent_id=agent_id, host_id=host_id, session=session)

            logging.info(
                f"""Using prompt strategy {strategy.type} (version {strategy.version}) for agent {agent_id}"""
            )

            if task_reference is not None:
                logging.info(f"On-Demand generation requested ${task_reference}")

            match strategy.type:
                case PromptStrategyType.CHAINING:
                    await chaining_generate_idea_and_post(
                        agent_id, session, ideas_to_generate, task_reference
                    )
                case PromptStrategyType.FEW_SHOT:
                    await few_shot_generate_idea_and_post(
                        agent_id, session, ideas_to_generate, task_reference
                    )
                case PromptStrategyType.MULTI_AGENT:
                    await multi_agent_generate_idea_and_post(
                        agent_id, session, ideas_to_generate, task_reference
                    )
                case PromptStrategyType.XLEAP_ZERO_SHOT:
                    await xleap_generate_idea_and_post(
                        agent_id, session, ideas_to_generate, task_reference
                    )  # same as few shot deprecated
                case PromptStrategyType.XLEAP_FEW_SHOT:
                    await xleap_generate_idea_and_post(
                        agent_id, session, ideas_to_generate, task_reference
                    )
                case _:
                    raise ValueError(f"Unhandled strategy type: '{strategy.type}'")
        except Exception as e:
            lock.set_last_idea(None)
            raise e
        finally:
            lock.release()
