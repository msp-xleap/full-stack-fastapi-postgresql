import logging

from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.api.deps import SessionDep
from app.orchestration.prompts import (
    BasePrompt,
    langfuse_handler
)
from app.models import AIAgent


async def generate_idea_and_post(agent: AIAgent, session: SessionDep) -> None:
    """
    Generate idea and post it to the XLeap server
    """
    attached_agent = session.merge(agent)

    zero_shot_prompt = ZeroShotPrompt(agent=attached_agent)
    await zero_shot_prompt.generate_idea()
    await zero_shot_prompt.post_idea()


class ZeroShotPrompt(BasePrompt):
    """
    Class to generate zero-shot prompts using Langchain API
    """

    async def generate_idea(self) -> None:
        """
        Generate ideas using zero-shot prompt

        Returns:
            str: Generated ideas
        """
        final_prompt = await self._generate_prompt()

        llm = ChatOpenAI(openai_api_key=self._api_key,
                         model_name=self._model,
                         temperature=self._temperature)

        self.idea = llm.invoke(
            final_prompt,
            config={"callbacks": [langfuse_handler]}
        ).content

    async def _generate_prompt(self) -> PromptValue:
        """
        Generate prompt for zero-shot

        Returns:
            str: Generated prompt

        """
        system_prompt = await self._get_prompt_from_langfuse(
            prompt_name="SYSTEM_PROMPT")
        context_prompt = await self._get_prompt_from_langfuse(
            prompt_name="CONTEXT_ICU")
        brainstorm_prompt = await self._get_prompt_from_langfuse(
            prompt_name="BRAINSTORM_ICU")
        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt + context_prompt),
                ("human", brainstorm_prompt),
            ]
        )
        return final_prompt.format_prompt()
