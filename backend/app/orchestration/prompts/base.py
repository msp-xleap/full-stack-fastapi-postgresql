import logging
from abc import ABC, abstractmethod

import aiohttp

from app.models import AIAgent
from app.orchestration.prompts import langfuse_client, langfuse_handler


class BasePrompt(ABC):
    """
    Abstract class for generating prompts
    """
    _langfuse_client = langfuse_client
    _langfuse_handler = langfuse_handler

    def __init__(self, agent: AIAgent, temperature: float = 0.5):
        logging.info(f"""
    
        {agent}
        
        """)

        self._agent = agent
        self._api_key = agent.api_key
        self._model = agent.model
        self._temperature = temperature
        self.idea = None

    async def post_idea(self) -> None:
        """
        Post idea to the XLeap
        """
        logging.info(f"""
        Agent ({self._agent.id}) is posting new idea to
        XLeap server: {self._agent.server_address}
        XLeap session ID: {self._agent.session_id}
        XLeap workspace ID: {self._agent.workspace_id}
        """)

        async with (aiohttp.ClientSession() as session):
            session_post = session.post(
                url=f"{self._agent.server_address}/services/api/sessions"
                    f"/{self._agent.session_id}/brainstorms/"
                    f"{self._agent.workspace_id}/ideas",
                data={"text": self.idea, "folder_id": ""},
                headers={"Authorization": f"Bearer {self._agent.secret}"}
            )
            # Don't await the response
            response = await session_post

    @abstractmethod
    async def generate_idea(self) -> str:
        """
        Generates an idea using prompt and stores it in self.idea
        """
        raise NotImplementedError

    @abstractmethod
    def _generate_prompt(self) -> str:
        """
        Generate prompt
        """
        raise NotImplementedError

    async def _get_prompt_from_langfuse(self, prompt_name: str) -> str:
        """
        Get prompt from langfuse
        """
        prompt_obj = self._langfuse_client.get_prompt(prompt_name)
        return prompt_obj.prompt
