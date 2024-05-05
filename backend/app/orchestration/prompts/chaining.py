import logging
import re

from langchain.chains.llm import LLMChain
from langchain.chains.sequential import SequentialChain
from langchain_community.document_transformers import LongContextReorder
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import AIAgent, Briefing, Briefing2
from app.orchestration.prompts import BasePrompt, langfuse_handler
from app.utils import get_last_n_ideas

##
# Currently using briefing.additional_info as the only instruction (previously briefing.question)
# briefing.participant_info instead of briefing.topic
##


async def generate_idea_and_post(
    agent: AIAgent, briefing: Briefing2, session: SessionDep
) -> None:
    """
    Generate idea and post it to the XLeap server

    Todo: get question from the agent settings
    """
    attached_agent = session.merge(agent)
    attached_briefing = session.merge(briefing)
    attached_ideas = get_last_n_ideas(
        session, n=attached_briefing.frequency * 3, agent_id=attached_agent.id
    )
    # Reorder the ideas such that they get not lost in the middle
    docs = [Document(idea.text) for idea in attached_ideas]
    reordering = LongContextReorder()
    attached_docs = reordering.transform_documents(documents=docs)

    prompt_chaining = ChainingPrompt(
        agent=attached_agent, briefing=attached_briefing, ideas=attached_docs
    )
    await prompt_chaining.generate_idea()
    await prompt_chaining.post_idea()


class ChainingPrompt(BasePrompt):
    """
    Class using prompt chaining and Langchain API to generate ideas
    """

    async def generate_idea(self) -> None:  # type: ignore
        """
        Generate ideas using prompt chaining

        Returns:
            str: Generated ideas
        """
        # Initialize different LLM configurations for each chain step with
        # different temperatures
        llm_tone = ChatOpenAI(
            openai_api_key=self._api_key,
            model_name=self._model,
            # Lower temperature for more consistent and conservative output
            temperature=0.3,
            openai_proxy=settings.HTTP_PROXY,
        )

        llm_ideas = ChatOpenAI(
            openai_api_key=self._api_key,
            model_name=self._model,
            # Higher temperature for more creative and diverse ideas
            temperature=0.7,
            top_p=0.7,
            frequency_penalty=0.7,
            presence_penalty=0.7,
            openai_proxy=settings.HTTP_PROXY,
        )

        llm_selection = ChatOpenAI(
            openai_api_key=self._api_key,
            model_name=self._model,
            # Moderate temperature for balanced idea selection
            temperature=0.5,
            openai_proxy=settings.HTTP_PROXY,
        )

        # Load examples or any needed data
        examples = await self._get_examples()

        # Define different chains for each process using the respective LLMs
        tone_in_brainstorming = await self._describe_tone(llm_tone)
        idea_generation_chain = await self._generate_multiple_ideas(llm_ideas)
        idea_selection_chain = await self._select_idea(llm_selection)

        # Creating the simple sequential chain
        ss_chain = SequentialChain(
            chains=[
                tone_in_brainstorming,
                idea_generation_chain,
                idea_selection_chain,
            ],
            input_variables=["question", "idea", "persona", "setting", "language", "context"],
            output_variables=["selected_idea"],
        )

        # Invoke the chain with the input
        idea = await ss_chain.ainvoke(
            input={"question": self._briefing.workspace_instruction,
                   "idea": examples,
                   "persona": self._briefing.persona,
                   "setting": self._briefing.participant_info,
                   "context": self._briefing.workspace_info,
                   "language": "German"},
            config={"callbacks": [langfuse_handler]},
        )

        # Parse the output
        self.generated_idea = await self._parse_idea(idea["selected_idea"])

    async def _generate_multiple_ideas(self, llm) -> LLMChain:
        idea_generation_prompt = await self._generate_prompt(
            question="CHAINING_PROMPT_QUESTION"
        )
        idea_generation_chain: LLMChain = LLMChain(
            llm=llm,
            prompt=idea_generation_prompt,
            output_key="generated_ideas",
        )
        return idea_generation_chain

    async def _select_idea(self, llm) -> LLMChain:
        """
        Generate prompt for prompt chaining

        Returns:
            str: Generated prompt

        """
        idea_selection_prompt = await self._generate_prompt(
            question="CHAINING_PROMPT_SELECTION"
        )
        idea_selection_chain: LLMChain = LLMChain(
            llm=llm, prompt=idea_selection_prompt, output_key="selected_idea"
        )
        return idea_selection_chain

    async def _describe_tone(self, llm) -> LLMChain:
        """
        Generate prompt for prompt chaining

        Returns:
            str: Generated prompt

        """
        tone_prompt = await self._generate_prompt(
            question="CHAINING_PROMPT_TONE"
        )
        tone_chain: LLMChain = LLMChain(
            llm=llm, prompt=tone_prompt, output_key="tone"
        )
        return tone_chain

    async def _generate_prompt(self, question: str) -> ChatPromptTemplate:  # type: ignore
        """
        Generate prompt for prompt chaining

        Returns:
            str: Generated prompt
        """
        system_prompt = await self._get_prompt_from_langfuse(
            prompt_name="SYSTEM_PROMPT"
        )
        context_prompt = await self._get_prompt_from_langfuse(
            prompt_name=f"CONTEXT_PROMPT"
        )
        chaining_prompt_examples = await self._get_prompt_from_langfuse(
            prompt_name="CHAINING_PROMPT_EXAMPLES"
        )

        chaining_prompt_question = await self._get_prompt_from_langfuse(
            prompt_name=question
        )

        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt + context_prompt),
                ("human", chaining_prompt_examples + chaining_prompt_question),
            ]
        )
        return final_prompt

    async def _get_examples(
        self,
    ) -> str:
        """ """
        idea_examples: str = ""
        for example in self._ideas:
            idea_examples += "- " + example.page_content + "\n"

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
        # Remove the tags from the idea
        pattern = r"<selected_idea[^>]*>(.*?)<\/selected_idea>"
        content = re.search(pattern, idea, re.DOTALL).group(1).strip()

        # Remove all occurrences of **
        content_without_asterisks = content.replace("**", "")

        # Remove all occurrences of "
        content_without_quotes = content_without_asterisks.replace('"', "")

        return content_without_quotes
