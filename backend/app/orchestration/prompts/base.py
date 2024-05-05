from abc import abstractmethod

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from app.models import AIAgent, Briefing, Idea, Briefing2
from app.orchestration.prompts import BrainstormBasePrompt
from app.utils import TextTypeSwapper


class BasePrompt(BrainstormBasePrompt):
    """
    Abstract class for generating prompts
    """

    _briefing: Briefing2

    def __init__(
        self,
        agent: AIAgent,
        briefing: Briefing2,
        ideas: list[Idea] | None = None,
        temperature: float = 0.5,
    ):
        super().__init__(agent, ideas, temperature)
        self._briefing = briefing

    def _alter_generated_idea(self, idea_to_post: str) -> str:
        # Add typos to the generated idea
        swapper = TextTypeSwapper(text=idea_to_post, typo_prob=0.01)
        return swapper.add_typos().get_text()

    @abstractmethod
    async def generate_idea(self) -> str:
        """
        Generates an idea using prompt and stores it in self.generated_idea

        Returns:
            str: Generated idea
        """
        raise NotImplementedError

    @abstractmethod
    def _generate_prompt(self, question: str = None) -> ChatPromptTemplate:
        """
        Generate prompt
        """
        raise NotImplementedError

    # async def add_evaluations(self, trace_id: str | None) -> None:
    #     """
    #     Add model based evaluations to the generated idea
    #
    #     Args:
    #         trace_id: Trace ID for the request
    #
    #     Returns:
    #
    #     """
    #     pass
