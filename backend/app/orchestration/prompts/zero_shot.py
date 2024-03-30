from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.api.deps import SessionDep
from app.models import AIAgent
from app.orchestration.prompts import BasePrompt, langfuse_handler


async def generate_idea_and_post(agent: AIAgent, session: SessionDep) -> None:
    """
    Generate idea and post it to the XLeap server

    Todo: get question from the agent settings
    """
    attached_agent = session.merge(agent)

    zero_shot_prompt = ZeroShotPrompt(agent=attached_agent)
    await zero_shot_prompt.generate_idea(
        question=(
            "As a student at UZH, what new services, initiatives or "
            "offerings would you find most valuable and appealing "
            "from the ICU?"
        )
    )
    await zero_shot_prompt.post_idea()


class ZeroShotPrompt(BasePrompt):
    """
    Class to generate zero-shot prompts using Langchain API
    """

    async def generate_idea(self, question: str) -> None:  # type: ignore
        """
        Generate ideas using zero-shot prompt

        Args:
            question (str): Question to be injected into the prompt

        Returns:
            str: Generated ideas
        """
        final_prompt = await self._generate_prompt()

        llm = ChatOpenAI(
            openai_api_key=self._api_key,  # type: ignore
            model_name=self._model,
            temperature=self._temperature,
        )

        chain = final_prompt | llm

        idea = chain.invoke(
            input={"question": question},
            config={"callbacks": [langfuse_handler]},
        )
        self.idea = idea.content

    async def _generate_prompt(self) -> ChatPromptTemplate:  # type: ignore
        """
        Generate prompt for zero-shot

        Returns:
            str: Generated prompt

        """
        system_prompt = await self._get_prompt_from_langfuse(
            prompt_name="SYSTEM_PROMPT"
        )
        context_prompt = await self._get_prompt_from_langfuse(
            prompt_name="CONTEXT_ICU"
        )
        zero_shot_prompt = await self._get_prompt_from_langfuse(
            prompt_name="ZERO_SHOT_PROMPT"
        )

        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt + context_prompt),
                ("human", zero_shot_prompt),
            ]
        )
        return final_prompt
