import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import aiohttp
from langchain_core.prompts import ChatPromptTemplate

from app.models import AIAgent, Idea
from app.orchestration.data import resolve_server_addr
from app.orchestration.prompts import langfuse_client, langfuse_handler

from sqlmodel import Session


class BrainstormBasePrompt(ABC):
    """
    Abstract class for generating prompts
    """

    _langfuse_client = langfuse_client
    _langfuse_handler = langfuse_handler

    _agent: AIAgent
    _ideas: list[Idea] | None

    def __init__(
        self,
        agent: AIAgent,
        ideas: list[Idea] | None = None,
        temperature: float = 0.5,
    ):
        self._agent = agent
        self._api_key = agent.api_key
        self._model = agent.model
        self._temperature = temperature
        self._ideas = ideas
        self.generated_idea: str | list[str | dict[Any, Any]] | None = None

    def _alter_generated_idea(self, idea_to_post: str) -> str:
        """
        Allows subclasses to alter the idea generated by the AI before sending it.
        The default implementation returns the input text.

        :param idea_to_post: the idea to send
        :return: the idea to send
        """
        return idea_to_post

    async def post_idea(self,
                        idea: str | None = None,
                        test_secret: str | None = None) -> None:
        """
        Post idea to the XLeap
        :param idea (optional), default self.generated_idea
        :param test_secret (optional, default None) when an idea is created by the test briefing request,
         the result required a secret to be presented to XLeap inorder to bypass Agent.is_active checks
        """
        logging.getLogger().setLevel(logging.DEBUG)

        if idea is None:
            idea = self.generated_idea

        logging.info(
            f"""
        Agent ({self._agent.id}) is posting new idea to
        XLeap server: {self._agent.server_address}
        XLeap session ID: {self._agent.session_id}
        XLeap workspace ID: {self._agent.workspace_id}
        """
        )

        # check if we can resolve the server address in DNS
        resolve_server_addr(self._agent.server_address)

        # Maybe alter generated Idea before sending it
        idea_to_post = self._alter_generated_idea(idea)

        data = {"text": idea_to_post, "folder_id": ""}
        if test_secret is not None:  # only include for test generations, as this can bypass active agent checks
            data.test_secret = test_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=f"{self._agent.server_address}/services/api/sessions"
                f"/{self._agent.session_id}/brainstorms/"
                f"{self._agent.workspace_id}/ideas",
                data=json.dumps(data),
                headers={
                    "Authorization": f"Bearer {self._agent.secret}",
                    "content-type": "application/json",
                },
            ) as response:
                response.raise_for_status()

    @staticmethod
    def handle_client_response_errors(err: aiohttp.ClientResponseError,
                                      agent: AIAgent,
                                      session: Session) -> AIAgent:
        """
        Handles some common HTTP status like
          402 Payment Required - if the XLeap subscription expired
          409 Conflict - when an agent is not supposed to be active
        other errors will be reraised

        Both lead to the agent being deactivated if it is not already the case.

        :param err: a  ClientResponseError
        :param agent: the current agent
        :param session: the DB session
        :return: the updated agent object
        """
        must_deactivate_agent = False
        # 402 payment required => XLeap license expired
        if 402 == err.status:
            logging.info('XLeap subscription expired, agent is being deactivated')
            must_deactivate_agent = True
        # 409 conflict => The agent should not be generating content since it was deactivated
        elif 409 == err.status:
            logging.info('Agent should not have been active, deactivating')
            must_deactivate_agent = True
        else:
            raise err

        if must_deactivate_agent:
            # update the agent object before changing it
            session.refresh(agent)
            if agent.is_active:
                agent.is_active = False
                session.merge(agent)

        return agent

    @abstractmethod
    async def generate_idea(self) -> str:
        """
        Generates an idea using prompt and stores it in self.generated_idea

        Returns:
            str: Generated idea
        """
        raise NotImplementedError

    @abstractmethod
    def _generate_prompt(self) -> ChatPromptTemplate:
        """
        Generate prompt
        """
        raise NotImplementedError

    async def _get_prompt_from_langfuse(self, prompt_name: str) -> str:
        """
        Get prompt from langfuse
        """
        prompt_obj = self._langfuse_client.get_prompt(prompt_name)
        prompt = prompt_obj.get_langchain_prompt()
        return prompt
