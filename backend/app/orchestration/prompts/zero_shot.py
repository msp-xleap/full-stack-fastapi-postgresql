from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.orchestration.prompts import BasePrompt, langfuse_handler

# async def generate_idea_and_post(agent: AIAgent, briefing: Briefing, session:
# SessionDep) -> None:
#     """
#     Generate idea and post it to the XLeap server
#
#     Todo: get question from the agent settings
#     """
#     attached_agent = session.merge(agent)
#     attached_briefing = session.merge(briefing)
#     attached_ideas = get_last_n_ideas(session, 5)
#     zero_shot_prompt = ZeroShotPrompt(agent=attached_agent, briefing=attached_briefing)
#     await zero_shot_prompt.generate_idea()
#     await zero_shot_prompt.post_idea()


class ZeroShotPrompt(BasePrompt):
    """
    Class to generate zero-shot prompts using Langchain API
    """

    async def generate_idea(self) -> None:  # type: ignore
        """
        Generate ideas using zero-shot prompt

        Returns:
            str: Generated ideas
        """
        final_prompt = await self._generate_prompt()

        llm = ChatOpenAI(
            openai_api_key=self._api_key,  # type: ignore
            model_name=self._model,
            temperature=self._temperature,
            openai_proxy=settings.HTTP_PROXY
        )

        chain = final_prompt | llm

        idea = chain.invoke(
            input={"question": self._briefing.question},
            config={"callbacks": [langfuse_handler]},
        )
        self.generated_idea = idea.content

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
            prompt_name=f"CONTEXT_PROMPT_{self._briefing.topic.upper()}"
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
