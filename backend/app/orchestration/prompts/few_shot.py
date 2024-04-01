from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI

from app.api.deps import SessionDep
from app.models import AIAgent, Briefing
from app.orchestration.prompts import BasePrompt, langfuse_handler
from app.utils import get_last_n_ideas


async def generate_idea_and_post(
    agent: AIAgent, briefing: Briefing, session: SessionDep
) -> None:
    """
    Generate idea and post it to the XLeap server

    Todo: get question from the agent settings
    """
    attached_agent = session.merge(agent)
    attached_briefing = session.merge(briefing)
    attached_ideas = get_last_n_ideas(session, n=attached_briefing.frequency)
    zero_shot_prompt = FewShotPrompt(
        agent=attached_agent, briefing=attached_briefing, ideas=attached_ideas
    )
    await zero_shot_prompt.generate_idea()
    await zero_shot_prompt.post_idea()


class FewShotPrompt(BasePrompt):
    """
    Class to generate few-shot prompts using Langchain API
    """

    async def generate_idea(self) -> None:  # type: ignore
        """
        Generate ideas using few-shot prompting

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
        few_shot_prompt_examples = await self._generate_example_prompt()

        few_shot_prompt_question = await self._get_prompt_from_langfuse(
            prompt_name="FEW_SHOT_PROMPT_QUESTION"
        )

        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt + context_prompt),
                few_shot_prompt_examples,
                ("human", few_shot_prompt_question),
            ]
        )
        return final_prompt

    async def _generate_example_prompt(
        self,
    ) -> FewShotChatMessagePromptTemplate:
        """
        Generate few-shot prompt examples.
        Examples are generated from the attached ideas and help the AI to
        pick up the tone and style of the conversation as well as the context.

        Returns:
            FewShotChatMessagePromptTemplate: Generated few-shot prompt examples
        """
        example_template = await self._get_prompt_from_langfuse(
            prompt_name="FEW_SHOT_PROMPT_EXAMPLES"
        )
        question, answer = example_template.split("\n")
        example_prompt = ChatPromptTemplate.from_messages(
            [("human", question), ("ai", answer)]
        )

        idea_examples: list = []
        for example in self._ideas:
            idea_examples.append(
                {"question": self._briefing.question, "idea": example.text}
            )

        few_shot_prompt_examples = FewShotChatMessagePromptTemplate(
            examples=idea_examples,
            # This is a prompt template used to format each individual example.
            example_prompt=example_prompt,
        )

        return few_shot_prompt_examples
