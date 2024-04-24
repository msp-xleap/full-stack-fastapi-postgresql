import logging
import re

from langchain.chains.llm import LLMChain
from langchain.chains.sequential import SequentialChain
from langchain_core.prompts import (
    ChatPromptTemplate,
)
from langchain_openai import ChatOpenAI

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import AIAgent, Briefing, BriefingCategory, BriefingSubCategory
from app.orchestration.prompts import BasePrompt, langfuse_handler
from app.utils import get_last_n_ideas



async def generate_idea_and_post(
        agent: AIAgent, briefing: Briefing, session: SessionDep
) -> None:
    """
    Generate idea and post it to the XLeap server

    Todo: get question from the agent settings
    """
    # attached_agent = session.merge(agent)
    # attached_briefing = session.merge(briefing)
    # attached_ideas = get_last_n_ideas(
    #     session, n=attached_briefing.frequency * 3, agent_id=attached_agent.id
    # )
    # prompt_chaining = ChainingPrompt(
    #     agent=attached_agent, briefing=attached_briefing, ideas=attached_ideas
    # )
    # try:
    #     await prompt_chaining.generate_idea()
    # except Exception:
    #     await prompt_chaining.generate_idea()
    # await prompt_chaining.post_idea()

