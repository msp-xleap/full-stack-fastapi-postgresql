from app.models import AIAgent, Briefing, BriefingCategory, BriefingSubCategory

from abc import ABC
from sqlmodel import Session
from app.orchestration.prompts import langfuse_client, langfuse_handler

class XLeapPromptManagement(ABC):

    _langfuse_client = langfuse_client
    _langfuse_handler = langfuse_handler

    async def _get_langfuse_prompt_name(self,
                                        session: Session,
                                        cat:BriefingCategory,
                                        sub_category:BriefingSubCategory,
                                        template: str) -> str:
        """
        Gets the name of a Prompt from an XLeap template string
        """



        prompt_obj = self._langfuse_client.get_prompt(prompt_name)
        prompt = prompt_obj.get_langchain_prompt()
        return prompt