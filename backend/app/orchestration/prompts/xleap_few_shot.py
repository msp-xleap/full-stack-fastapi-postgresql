import logging
import re

import aiohttp
from langchain_core.prompts import (
    ChatPromptTemplate,
)
from langchain_openai import ChatOpenAI

from app.api.deps import SessionDep
from app.core.config import settings
from app.crud import get_ai_agent_references
from app.models import AIAgent, Briefing2, Briefing2Reference, Idea
from app.orchestration.prompts import BrainstormBasePrompt, langfuse_handler
from app.utils import get_last_n_ideas
from app.utils.agents import get_agent_by_id
from app.utils.briefings import get_briefing2_by_agent_id
from app.utils.streaming_briefing_test_token_consumer import (
    XLeapStreamingTokenizer,
)

from .xleap_system_prompt_base import GeneratedPrompt, XLeapSystemPromptBase


async def describe_system_prompt(
    agent: AIAgent, briefing: Briefing2, session: SessionDep
) -> GeneratedPrompt:
    references = get_ai_agent_references(session=session, agent=agent)
    xleap_prompt = XLeapBasicPrompt(
        agent=agent, briefing=briefing, ideas=[], references=references
    )
    system_prompt = await xleap_prompt.generate_system_prompt(
        briefing=briefing, references=references
    )
    return system_prompt


async def generate_idea_and_post(
    agent_id: str,
    session: SessionDep,
    ideas_to_generate: int = 1,
    task_reference: str | None = None,
) -> None:
    """
    Generate idea and post it to the XLeap server
    :param agent_id: the ID of the agent
    :param session: the database session
    :param ideas_to_generate: the number of ideas to generate
    :param task_reference: if a task reference is given this is an on-demand generation
      which can ignore the agent active check
    :return:
    """
    attached_agent = get_agent_by_id(agent_id, session)
    attached_briefing = get_briefing2_by_agent_id(agent_id, session)

    ideas_to_select = attached_briefing.frequency * 3
    if attached_briefing.frequency <= 0:
        ideas_to_select = 50

    attached_ideas = get_last_n_ideas(
        session, n=ideas_to_select, agent_id=attached_agent.id
    )
    references = get_ai_agent_references(session=session, agent=attached_agent)

    xleap_prompt = XLeapBasicPrompt(
        agent=attached_agent,
        briefing=attached_briefing,
        ideas=attached_ideas,
        references=references,
        task_reference=task_reference,
        ideas_to_generate=ideas_to_generate,
    )
    # noinspection PyBroadException
    try:
        try:
            await xleap_prompt.generate_idea()
        except (
            aiohttp.ClientResponseError
        ) as err:  # error when generated idea was sent to XLeap
            session.refresh(attached_agent)
            xleap_prompt.maybe_deactivate_agent(err, attached_agent, session)
            raise err
        except Exception:
            await xleap_prompt.generate_idea()
    except (
        aiohttp.ClientResponseError
    ) as err:  # error when generated idea was sent to XLeap
        raise err


class XLeapBasicPrompt(BrainstormBasePrompt, XLeapSystemPromptBase):
    """
    Class using basic XLeap prompting and Langchain API to generate ideas
    """

    _lang_chain_input: dict

    def __init__(
        self,
        agent: AIAgent,
        briefing: Briefing2,
        references: list[Briefing2Reference],
        ideas: list[Idea] | None = None,
        temperature: float = 0.5,
        task_reference: str | None = None,
        ideas_to_generate: int = 1,
    ):
        super().__init__(
            agent=agent,
            ideas=ideas,
            temperature=briefing.temperature / 100.0,
            task_reference=task_reference,
            ideas_to_generate=ideas_to_generate,
        )
        self._briefing = briefing
        self._references = references

    async def generate_idea(self) -> None:  # type: ignore
        """
        Generate ideas

        Returns:
            str: Generated ideas
        """
        final_prompt = await self._generate_prompt()

        llm = ChatOpenAI(
            openai_api_key=self._api_key,  # type: ignore
            model_name=self._model,
            temperature=self._temperature,
            openai_proxy=settings.HTTP_PROXY,
        )

        if self._ideas_to_generate > 1:
            tokenizer = XLeapStreamingTokenizer()
            chain = final_prompt | llm | tokenizer

            try:
                async for chunk in chain.astream(
                    input=self._lang_chain_input,
                    config={"callbacks": [langfuse_handler]},
                ):
                    logging.info(
                        f"""
                    XLeapBasicPrompt.generate_idea
                    chunk is {chunk}
                """
                    )
                    await self.post_idea(
                        idea=chunk, task_reference=self.task_reference
                    )
            except aiohttp.ClientResponseError as err:
                raise err
        else:
            chain = final_prompt | llm

            idea = chain.invoke(
                input=self._lang_chain_input,
                config={"callbacks": [langfuse_handler]},
            )

            self.generated_idea = idea.content
            await self.post_idea(
                idea=idea.content, task_reference=self.task_reference
            )

    async def _generate_prompt(self) -> ChatPromptTemplate:
        """
        Generate prompt for prompt chaining

        Returns:
            str: Generated prompt

        """

        system_prompt = await self.generate_system_prompt(
            briefing=self._briefing, references=self._references
        )

        participant_prompts = await self.generate_idea_prompts(
            ideas=self._ideas
        )

        task_prompt = await self.generate_task_prompt(
            briefing=self._briefing,
            ideas=self._ideas,
            num_contributions=self._ideas_to_generate,
        )

        self._lang_chain_input = {
            **system_prompt.lang_chain_input,
            **task_prompt.lang_chain_input,
        }

        messages = (
            [("system", system_prompt.prompt)]
            + participant_prompts
            + [("human", task_prompt.prompt)]
        )

        final_prompt = ChatPromptTemplate.from_messages(messages)
        return final_prompt

    async def _get_examples(
        self,
    ) -> str:
        """ """
        idea_examples: str = ""
        for example in self._ideas:
            idea_examples += "- " + example.text + "\n"

        return idea_examples

    @staticmethod
    async def _parse_idea(idea: str) -> str:
        """
        Parse the idea generated by the AI

        Args:
            idea (str): Idea generated by the AI

        Returns:
            str: Parsed idea
        """
        logging.info(
            f"""







        Raw idea: {idea}










"""
        )

        # Remove the tags from the idea
        pattern = r"<selected_idea[^>]*>(.*?)<\/selected_idea>"
        content = re.search(pattern, idea, re.DOTALL).group(1).strip()

        # Remove all occurrences of **
        content_without_asterisks = content.replace("**", "")

        return content_without_asterisks
