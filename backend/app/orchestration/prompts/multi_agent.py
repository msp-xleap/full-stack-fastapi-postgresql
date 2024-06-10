import copy
import re

import aiohttp
from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent
from langchain_community.document_transformers import LongContextReorder
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import AIAgent
from app.orchestration.prompts import BasePrompt, langfuse_handler
from app.utils import get_last_n_ideas
from app.utils.agents import get_agent_by_id
from app.utils.briefings import get_briefing2_by_agent_id


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
    """
    attached_agent = get_agent_by_id(agent_id, session)
    attached_briefing = get_briefing2_by_agent_id(agent_id, session)
    ideas_to_select = attached_briefing.frequency * 3
    if attached_briefing.frequency <= 0:
        ideas_to_select = 50

    attached_ideas = get_last_n_ideas(
        session, n=ideas_to_select, agent_id=attached_agent.id
    )

    multi_agent = MultiAgent(
        agent=attached_agent,
        briefing=attached_briefing,
        ideas=attached_ideas,
        task_reference=task_reference,
    )
    await multi_agent.generate_idea()

    # refresh agent object again, then check if our agent is still active,
    # before posting the Idea to XLeap
    attached_agent = session.get(AIAgent, attached_agent.id)
    if attached_agent.is_active or task_reference is not None:
        try:
            await multi_agent.post_idea()
        except aiohttp.ClientResponseError as err:
            multi_agent.maybe_deactivate_agent(err, attached_agent, session)
            raise err


class MultiAgent(BasePrompt):
    """
    Class using Langchain and Autogen to facilitate collaborative
    idea generation through multiple agent interaction.

    Sources:
    - https://microsoft.github.io/autogen/
    - https://github.com/microsoft/autogen
    - https://arxiv.org/abs/2308.08155

    Future Work:
    - Use AutoBuild to create agents. We did not use AutoBuild because it
      was too slow. Future models with faster response times may use AutoBuild.
    - In our use case, two agents were sufficient. Depending on the
      brainstorming question, more agents might produce a better result.
    """

    async def generate_idea(self) -> None:  # type: ignore
        """
        Method to generate ideas using prompt chaining with multiple agents.

        Returns:
            str: The final generated idea after interaction between agents.
        """
        # Load ideas as example ideas in the prompt
        examples = await self._load_ideas_as_examples()
        # Extract tone from examples
        tone = await self._determine_tone(examples)
        # Generate prompt for multi-agent collaboration task
        task_prompt = await self._generate_multi_agent_task_prompt(examples)

        agents = await self._initialize_agents(tone)
        messages = await self._conduct_group_discussion(agents, task_prompt)

        # Parse the output
        self.generated_idea = await self._parse_idea(messages)

    def _generate_prompt(self):
        """
        Placeholder meethod that is required by the superclass. However, this
        prompt strategy follows a different approach to construct the prompts.
        """
        raise NotImplementedError

    async def _determine_tone(self, examples) -> str | list[str | dict]:
        """
        Analyzes and extracts the tone from the given examples.

        Args:
            examples (str): Idea examples.

        Returns:
            str: Extracted tone description.
        """
        # Get prompt to extract tone
        tone_prompt = await self._generate_tone_analyis_prompt()

        # Initialize LLM to perform tone analysis
        llm_tone = ChatOpenAI(
            openai_api_key=self._api_key,
            model_name=self._model,
            # Lower temperature for more consistent and conservative output
            temperature=0.3,
            openai_proxy=settings.HTTP_PROXY,
        )
        chain = tone_prompt | llm_tone

        # Invoke chain
        tone = chain.invoke(
            input={
                "question": self._briefing.workspace_instruction,
                "idea": examples,
            },
            config={"callbacks": [langfuse_handler]},
        )

        # Storing trace id. Trace id will be required to upload multi-agent
        # conversation
        self._trace_id = langfuse_handler.trace.id

        return tone.content

    async def _initialize_agents(self, tone: str) -> list[AssistantAgent]:
        """
        Initializes and returns a list of agents based on the given tone.

        Args:
            tone (str): The tone extracted from the idea examples.

        Returns:
            List[AssistantAgent]: List of initialized agents.

        Note / To do:
            In this code, the role of the first agent is hard coded in the
            code as 'Mayor'. If the user interface allowed for multiple
            personas, we could make this part of the code dynamic to create
            as many agents as there are personas.
        """
        # user_proxy = UserProxyAgent(
        #     name="user_proxy",
        #     system_message="Admin",
        #     code_execution_config=False,
        #     human_input_mode="TERMINATE",
        # )

        # Initialize first agent `Mayor`
        mayor = await self._generate_autogen_agent("MAYOR", "Mayor", tone)
        # Initiliaze second agent
        second_agent = await self._generate_autogen_agent(
            "OTHER", self._briefing.persona, tone
        )

        #agent_list = [user_proxy, mayor, second_agent]
        agent_list = [mayor, second_agent]

        return agent_list

    async def _conduct_group_discussion(
        self,
        agents: list[AssistantAgent],
        task: str,
        max_rounds: int = 6,
        allow_repeat_speaker: bool = True,
    ) -> str:
        """
        Sets up a group chat environment for the agents with specified
        configurations.
        Manages the interaction between agents in a group chat to generate
        ideas based on the initial task prompt.

        Args:
            agents (List[AssistantAgent]): List of participating agents.
            task (str): The initial task message to start the conversation.
            max_rounds (int, optional): Maximum number of rounds the agents
                are allowed to interact. Default is 6.
            allow_repeat_speaker (bool, optional): Flag to allow or disallow
                the same agent to speak consecutively. Default is True.

        Returns:
            str: Concatenated string of all messages from the group chat.
        """
        # Get configs for discussion
        llm_configs = await self._get_agent_configs()

        # Initializes a GroupChat object with a list of agents.
        group_chat = GroupChat(
            agents=agents,
            messages=[],
            max_round=max_rounds,
            allow_repeat_speaker=allow_repeat_speaker,
        )
        # This manager will handle the operation and progression of the
        # group chat.
        manager = GroupChatManager(
            groupchat=group_chat, llm_config=llm_configs
        )
        # The first agent in the list starts the chat by sending an initial
        # message (task) which sets the context or the topic for the group
        # discussion.
        agents[0].initiate_chat(manager, message=task)

        # Add conversation to trace
        await self.add_conversation_to_trace(task, group_chat, agents)

        return manager.messages_to_string(group_chat.messages)

    async def _generate_tone_analyis_prompt(self) -> ChatPromptTemplate:  # type: ignore
        """
        Retrieves a prompt template for analyzing the tone of examples.

        Returns:
            ChatPromptTemplate: A template for tone analysis.
        """
        # Template for examples
        examples_prompt_template = await self._get_prompt_from_langfuse(
            prompt_name="CHAINING_PROMPT_EXAMPLES"
        )

        # Template for tone analysis (includes aspects to consider in analysis)
        tone_char_prompt_template = await self._get_prompt_from_langfuse(
            prompt_name="CHAINING_PROMPT_TONE"
        )

        # Generate chat prompt template
        tone_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "human",
                    examples_prompt_template + tone_char_prompt_template,
                ),
            ]
        )
        return tone_prompt

    async def _generate_multi_agent_task_prompt(self, examples: str) -> str:
        """
        Retrieves the task prompt for the multi-agent group discussion
        from Langfuse.

        The task includes the

        Args:
            examples (str): Preprocessed examples to be included in the task prompt.

        Returns:
            str: The final composed task prompt.
        """
        # Template for task description
        task_prompt_template = self._langfuse_client.get_prompt(
            "MULTI_AGENT_TASK_PROMPT"
        )

        # Fill variables into prompt template
        task_prompt = task_prompt_template.compile(
            question=self._briefing.workspace_instruction, ideas=examples
        )

        return task_prompt

    async def _generate_agent_prompt(
        self, type: str, role: str, tone: str
    ) -> str:
        """
        Generates a customized prompt for an agent based on the specified
        ype, role, and tone.

        This method retrieves a system prompt template from Langfuse,
        then fills it with the given parameters to create a context-specific
        message for the agent. The prompt is used to guide the agent's
        contributions in a group chat scenario, ensuring it aligns with the
        intended tone and role.

        Args:
            type (str): The type of the agent, which dictates the template
                used for the prompt.
            role (str): The role of the agent within the interaction,
                influencing the nature of the prompt.
            tone (str): The desired tone of the agent's contributions,
                affecting the style and approach of the generated content.

        Returns:
            str: The fully compiled prompt ready to be insert as system
            message by an agent.
        """
        # Template for system message of agent
        agent_system_prompt_template = self._langfuse_client.get_prompt(
            f"SYSTEM_PROMPT_{type}_AGENTS"
        )

        # Fill variables into prompt template
        agent_system_message = agent_system_prompt_template.compile(
            role=role, question=self._briefing.workspace_instruction, tone=tone
        )

        return agent_system_message

    async def _generate_autogen_agent(
        self, type: str, role: str, tone: str
    ) -> AssistantAgent:
        """
        Generates an autonomous agent with specified parameters.

        Args:
            type (str): Type of the agent.
            role (str): Role of the agent.
            tone (str): Tone for the agent's interaction.

        Returns:
            AssistantAgent: Configured autonomous agent.
        """
        agent_config = await self._get_agent_configs()

        agent_prompt = await self._generate_agent_prompt(
            type=type, role=role, tone=tone
        )

        autogen_agent = AssistantAgent(
            name=role,
            system_message=agent_prompt,
            llm_config=agent_config,
        )

        return autogen_agent

    async def add_conversation_to_trace(
        self, task: str, group_chat: GroupChat, agents: list
    ):
        """
        Adds a conversation to the trace in Langfuse by creating a span with
        conversation metadata.

        This method retrieves configuration data, modifies it by removing
        sensitive information, and uses it in the tracing span.

        Args:
            task: The task associated with the conversation.
            group_chat: The group chat object containing the messages of the
                conversation.
            agents: List of agents

        Returns:
            None. The function's purpose is to perform side effects by
                interacting with the langfuse handler.
        """
        # Get configs for discussion
        llm_configs = await self._get_agent_configs()

        # Create a deep copy of the dictionary to modify
        config_copy = copy.deepcopy(llm_configs)

        # Remove 'api_key' from the copy
        if "api_key" in config_copy["config_list"][0]:
            del config_copy["config_list"][0]["api_key"]

        # Document all input messages
        inputs = {agent.name: agent.system_message for agent in agents}
        inputs["task"] = task

        # Create new nested span
        langfuse_handler.langfuse.span(
            trace_id=self._trace_id,
            name="Multi-Agent Conversation",
            metadata=config_copy,
            input=inputs,
            output=group_chat.messages,
        )

    async def _load_ideas_as_examples(self) -> str:
        """
        Loads and reorders idea examples for use in generating tasks. When
        reordering, we account for the lost in the middle problem.

        Returns:
            str: A formatted string of reordered idea examples.
        """
        # Reorder the ideas such that they get not lost in the middle
        docs = [Document(idea.text) for idea in self._ideas]
        reordered_docs = LongContextReorder().transform_documents(docs)
        return "\n".join(f"- {doc.page_content}" for doc in reordered_docs)

    async def _get_agent_configs(self):
        """
        Retrieves the configuration settings for language model agents.

        This method compiles and returns a configuration dictionary tailored
        for agents' interaction with the language model specified. The
        configuration includes model specifications such as API key and
        model name, as well as operational parameters like temperature
        and penalty settings which influence the behavior and responses of
        the language model.

        Note:
            Some models do not allow to adjust operational parameters such as
            top_p, frequency_penalty or presence_penalty.

        Returns:
            Dict: A dictionary containing language model configurations
                required by Autogen funcitons.
        """
        # Define the configuration settings for the language model interaction
        llm_config = {
            "config_list": [
                {"model": self._agent.model, "api_key": self._agent.api_key}
            ],
            "temperature": 0.7,
            # Adjusts the randomness of the model's responses
            "top_p": 0.7,  # Controls the diversity of the model's responses
            "frequency_penalty": 0.7,  # Discourages repetitive responses
            "presence_penalty": 0.7,  # Encourages novel topic introduction
        }
        return llm_config

    @staticmethod
    async def _parse_idea(text: str) -> str:
        """
        Extracts and processes the final idea from the agents' conversation
        text.

        Args:
            text (str): The conversation text containing multiple agent
                interactions.

        Returns:
            str: The final parsed idea, cleaned and formatted.
        """
        # Get all generated ideas without tags
        pattern = r"<selected_idea.*?>(.*?)<\/selected_idea>"
        matches = re.findall(pattern, text)

        # Return the content of the last match
        content = matches[-1]
        # Transform special characters
        content = content.strip().encode("utf-8").decode("unicode_escape")
        # Remove all occurrences of **
        content = content.replace("**", "")
        # Remove all occurrences of "
        content = content.replace('"', "")

        return content
