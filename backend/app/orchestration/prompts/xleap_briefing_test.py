import logging

import aiohttp
from langchain_core.prompts import (
    ChatPromptTemplate,
)
from langchain_openai import ChatOpenAI
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.crud import get_ai_agent_references
from app.models import AIAgent, Briefing2, Briefing2Reference
from app.orchestration.prompts import BrainstormBasePrompt, langfuse_handler
from app.utils.agents import get_agent_by_id
from app.utils.briefings import get_briefing2_by_agent_id
from app.utils.streaming_briefing_test_token_consumer import (
    XLeapStreamingTokenizer,
)

from .xleap_system_prompt_base import GeneratedPrompt, XLeapSystemPromptBase


async def generate_ideas_and_post(
        agent_id: str,
        test_secret: str,
        num_ideas_to_generate: int,
        ) -> None:
    """
    Generate idea and post it to the XLeap server
    """

    with Session(engine) as session:
        attached_agent = get_agent_by_id(agent_id, session)
        attached_briefing = get_briefing2_by_agent_id(agent_id, session)

        references = get_ai_agent_references(session=session, agent=attached_agent)
        xleap_test = XLeapBriefingTest(
            agent=attached_agent,
            briefing=attached_briefing,
            references=references,
            test_secret=test_secret,
            session=session,
            num_ideas_to_generate=num_ideas_to_generate,
        )

        await xleap_test.generate_and_post_ideas()

        logging.info(""" 
        ################ 
        XLeapBriefingTest completed
        ################
        """)


class XLeapBriefingTest(BrainstormBasePrompt, XLeapSystemPromptBase):
    """
        Class using basic XLeap prompting and Langchain API to generate ideas
    """

    _lang_chain_input: dict

    def __init__(self,
                 agent: AIAgent,
                 briefing: Briefing2,
                 references: list[Briefing2Reference],
                 test_secret: str,
                 session: Session,
                 num_ideas_to_generate: int = 12,
                 temperature: float = 0.5):
        super().__init__(agent=agent, ideas=None, temperature=temperature)
        self._briefing = briefing
        self._references = references
        self._test_secret = test_secret
        self._db_session = session
        self._num_ideas_to_generate = num_ideas_to_generate

    async def generate_and_post_ideas(self) -> None:  # type: ignore
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

        tokenizer = XLeapStreamingTokenizer()

        chain = final_prompt | llm | tokenizer

        try:
            async for chunk in chain.astream(
                    input=self._lang_chain_input,
                    config={"callbacks": [langfuse_handler]}):
                logging.info(f"""
                    XLeapBriefingTest.generate_and_post_ideas
                    chunk is {chunk}
                """)
                await self.post_idea(idea=chunk, task_reference=self._test_secret)
        except aiohttp.ClientResponseError as err:
            raise err

    async def generate_test_prompt(self) -> GeneratedPrompt:
        """
        Generates the task for the agent to generate some ideas
        :return: the prompt for the AI
        """
        prompt = await self._get_prompt_from_langfuse(
            prompt_name=self._briefing.test_briefing_langfuse_name
        )

        lang_chain_input: dict= {"num_generate": self._num_ideas_to_generate}

        return GeneratedPrompt(prompt=prompt, lang_chain_input=lang_chain_input)

    async def _generate_prompt(self) -> ChatPromptTemplate:
        """
        Generate prompt for prompt chaining

        Returns:
            str: Generated prompt

        """
        system_prompt = await self.generate_system_prompt(briefing=self._briefing, references=self._references)

        test_task_prompt = await self.generate_test_prompt()

        self._lang_chain_input = {
            **system_prompt.lang_chain_input,
            **test_task_prompt.lang_chain_input
        }

        final_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt.prompt),
            ("human", test_task_prompt.prompt)
        ])
        return final_prompt

    async def generate_idea(self) -> str:
        """
        Generates an idea using prompt and stores it in self.generated_idea

        Returns:
            str: Generated idea
        """
        raise NotImplementedError  # not used


