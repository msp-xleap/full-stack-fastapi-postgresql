import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import aiohttp
from langchain_core.documents import Document
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
        task_reference: str | None = None,
        ideas_to_generate: int = 1
    ):
        self._agent = agent
        self._api_key = agent.api_key
        self._model = agent.model
        self._temperature = temperature
        self._ideas = ideas
        self.generated_idea: str | list[str | dict[Any, Any]] | None = None
        self.task_reference = task_reference
        self._ideas_to_generate = ideas_to_generate

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
                        task_reference: str | None = None) -> None:
        """
        Post idea to the XLeap
        :param idea (optional), default self.generated_idea
        :param task_reference (optional, default self.task_reference)
          when an idea is created on demand or by a test briefing request
          the result requires a task_reference (secret) to be presented to XLeap inorder to bypass
          Agent.is_active checks
        """
        if idea is None:
            idea = self.generated_idea

        if task_reference is None:
            task_reference = self.task_reference

        # check if we can resolve the server address in DNS
        resolve_server_addr(self._agent.server_address)

        # Maybe alter generated Idea before sending it
        idea_to_post = self._alter_generated_idea(idea)

        data = {"text": idea_to_post, "folder_id": ""}
        if task_reference is not None:
            data['task_reference'] = task_reference

        logging.info(
            f"""
                Agent ({self._agent.id}) is posting new idea to
                XLeap server: {self._agent.server_address}
                XLeap session ID: {self._agent.session_id}
                XLeap workspace ID: {self._agent.workspace_id}
                XLeap task reference: {task_reference}
                """
        )

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
    def maybe_deactivate_agent(err: aiohttp.ClientResponseError,
                                      agent: AIAgent,
                                      session: Session):
        """
        Deactivates the agent is these HTTP status are returned
          402 Payment Required - if the XLeap subscription expired
          409 Conflict - when an agent is not supposed to be active

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

        if must_deactivate_agent:
            # update the agent object before changing it
            session.refresh(agent)
            if agent.is_active:
                agent.is_active = False
                session.merge(agent)
                session.commit()


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
