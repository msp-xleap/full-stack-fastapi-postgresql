from abc import ABC, abstractmethod
from html import escape

from app.models import Briefing2, Briefing2Reference, Idea


class GeneratedPrompt:
    """
    Describes the prompt and variables of the XLeap prompt
    """

    prompt: str
    lang_chain_input: dict

    def __init__(self, prompt: str, lang_chain_input: dict):
        self.prompt = prompt
        self.lang_chain_input = lang_chain_input


class XLeapSystemPromptBase(ABC):
    """
    Abstract class for generating a system prompt from an XLeap Briefing
    """

    @abstractmethod
    async def _get_prompt_from_langfuse(self, prompt_name: str) -> str:
        raise NotImplementedError

    @staticmethod
    def _get_file_references(
        references: list[Briefing2Reference],
    ) -> list[Briefing2Reference]:
        """
        Returns all files for retrieval
        :param references: the list of all references (e.g. links, files, xleap content and exemplar)
        :return: the list of all file references
        """
        return filter(lambda ref: ref.type == "file", references)

    async def _append_reference_templates(
        self,
        ref_type: str,
        references: list[Briefing2Reference],
        prompt_parts: list[str],
        lang_chain_input: dict,
    ) -> None:
        """
        Collects all templates for the given type to prompt_parts and
        put the corresponding variables to lang_chain_input
        :param ref_type: the reference type (link, file, xleap, exemplar)
        :param prompt_parts: the list of prompt parts
        :param lang_chain_input: the dictionary of variable
        """
        for ref in references:
            if ref.type == ref_type:
                prompt = await self._get_prompt_from_langfuse(
                    prompt_name=ref.langfuse_name
                )
                prompt_parts.append(prompt)

                match ref_type:
                    case "link":
                        lang_chain_input[
                            f"link_info_{ref.ref_number}"
                        ] = ref.text
                        lang_chain_input[
                            f"link_url_{ref.ref_number}"
                        ] = ref.url
                    case "file":
                        lang_chain_input[
                            f"file_info_{ref.ref_number}"
                        ] = ref.text
                        lang_chain_input[
                            f"filename_{ref.ref_number}"
                        ] = ref.filename
                        lang_chain_input[
                            f"file_url_{ref.ref_number}"
                        ] = ref.url
                    case "xleap":
                        lang_chain_input[
                            f"xleap_info_{ref.ref_number}"
                        ] = ref.text
                        lang_chain_input[
                            f"xleap_url_{ref.ref_number}"
                        ] = ref.url
                    case "exemplar":
                        lang_chain_input[
                            f"exemplar_{ref.ref_number}"
                        ] = ref.text

    # noinspection DuplicatedCode
    async def generate_system_prompt(
        self, briefing: Briefing2, references: list[Briefing2Reference]
    ) -> GeneratedPrompt:
        """
        Generate prompt for prompt chaining

        Returns:
            str: Generated prompt

        """

        # NOTE: currently only for brainstorming

        # The general XLeap structure based on the inputs on XLeap's AI settings are
        # 1. Introduction to brainstorm
        #      - Hi, {{host_info}}I run a brainstorming session with XLeap facilitation software.
        #    * The host info can be the empty string, if it is not empty if always ends with ". ", meaning
        #      we either have one sentence (no host info) or two sentences
        #      - Hi, I run a brainstorming session with XLeap facilitation software.
        #      OR
        #      - Hi, My name is Joe. I am Product Manager for product X in the marketing department of Example Corp.
        #        I run a brainstorming session with XLeap facilitation software.
        # 2. Context info via the context template
        #      - Before I ask you to participate in a brainstorming session, let me give you some context:
        # 3. Session purpose (optional):
        #      - The brainstorming session is part of a facilitated meeting whose purpose is given as,
        #        “{{session_info}}”.
        # 4. Participant info (optional):
        #      - The participants are described as, “{{participant_info}}”.
        # 5. Workspace purpose (optional). Potentially with links and files
        #    * If references the {{references}} variable is present otherwise not.
        #      - The purpose of the brainstorming session that you are asked to participate in is stated as,
        #        “{{workspace_info}}”.
        #      OR
        #      - The purpose of the brainstorming session that you are asked to participate in is stated as,
        #        “{{workspace_info}}”.
        #    * The information should follow listings of link, file and xleap references:
        #
        #   5.1 Link references have the following pattern where N is the ref_number of the reference
        #      - This webpage explains {{link_info_N}}: {{link_url_N}}
        #   5.2 File references (links back to the XLeap server which may expire)
        #      - The content of this file explains {{file_info_N}}: {{filename_N}} ({{file_url_N}})
        #      TODO may depend how we deal with this
        #   5.3 XLeap references (links back to the XLeap server to retrieve the content of that workspace, may expire)
        #      - These results of a previous XLeap brainstorming explain {{xleap_info_N}}: {{xleap_url_N}}
        #      TODO currently there is no info
        # 6. The instruction of the workspace (optional)
        #      - The brainstorm instruction reads: “{{workspace_instruction}}”
        # 7. Additional info (optional)
        #      - An additional, specific instruction for you reads "{{additional_info}}."
        # 8. Persona instruction (optional)
        #     - Adopt the persona of “{{persona}}”.
        # 9. Tone instruction (optional)
        #     - Your tone should be {{tone}}.
        # 10. Exemplar (optional)
        #    * the 'header' for examples of good contributions
        #     - Here {{num_exemplar}} for good brainstorming contributions:
        #    * The information should follow listings of exemplar references:
        #   10.1 for 1st to 3rd example
        #     - 1. exemplar: "{{exemplar_1}}"
        #     - 2. exemplar: "{{exemplar_2}}"
        #     - 3. exemplar: "{{exemplar_3}}"
        # 11. Response length (required)
        #    * one of:
        #    - Please limit your contributions to one sentence without detail.
        #    - Include necessary detail in no more than 3 sentences.
        #    - Give some detail or an example in no more than 5 sentences.

        prompt_parts = []
        lang_chain_input = {}

        # 1. host info
        # actually always true
        if briefing.with_host_info:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.host_info_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input["host_info"] = briefing.host_info

        # 2. context
        prompt = await self._get_prompt_from_langfuse(
            prompt_name=briefing.context_intro_langfuse_name
        )
        prompt_parts.append(prompt)

        # 3. session purpose
        if briefing.with_session_info:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.session_info_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input["session_info"] = briefing.session_info

        # 4. participants
        if briefing.with_participant_info:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.participant_info_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input["participant_info"] = briefing.participant_info

        # 5. workspace info
        if briefing.with_workspace_info:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.workspace_info_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input["workspace_info"] = briefing.workspace_info

            await self._append_reference_templates(
                "link", references, prompt_parts, lang_chain_input
            )

            # TODO handle file content
            # await self._append_reference_templates('file', references, prompt_parts, lang_chain_input)

            # TODO implement XLeap content on XLeap site
            # await self._append_reference_templates('xleap', references, prompt_parts, lang_chain_input)

        # 6. workspace instruction
        if briefing.with_workspace_instruction:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.workspace_instruction_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input[
                "workspace_instruction"
            ] = briefing.workspace_instruction

        # 7. additional info
        if briefing.with_additional_info:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.additional_info_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input["additional_info"] = briefing.additional_info

        # 8. persona
        if briefing.with_persona:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.persona_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input["persona"] = briefing.persona

        # 9. tone
        if briefing.with_tone:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.tone_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input["tone"] = briefing.tone

        # 10. exemplar
        if briefing.with_num_exemplar > 0:
            prompt = await self._get_prompt_from_langfuse(
                prompt_name=briefing.exemplar_langfuse_name
            )
            prompt_parts.append(prompt)
            lang_chain_input["num_exemplar"] = briefing.with_num_exemplar

            await self._append_reference_templates(
                "exemplar", references, prompt_parts, lang_chain_input
            )

        # 11. response length
        prompt = await self._get_prompt_from_langfuse(
            prompt_name=briefing.response_length_langfuse_name
        )
        prompt_parts.append(prompt)

        system_prompt = "\n".join(prompt_parts)

        return GeneratedPrompt(
            prompt=system_prompt, lang_chain_input=lang_chain_input
        )

    async def generate_idea_prompts(
        self, ideas: list[Idea] | None
    ) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for idea in ideas:
            if idea.created_by_ai:
                result.append(("assistant", idea.text))
            else:
                result.append(("human", idea.text))
        return result

    async def generate_task_prompt(
        self, briefing: Briefing2, ideas: list[Idea] | None
    ) -> GeneratedPrompt:
        """
        Generates the task for the agent to generate an own idea
        :param briefing: the briefing
        :param ideas: the participant ideas
        :return: the prompt for the AI
        """
        prompt = await self._get_prompt_from_langfuse(
            prompt_name=briefing.task_langfuse_name
        )
        list_elements: list = []
        for idea in ideas:
            list_elements.append(f"\n<li>{escape(idea.text)}</li>")

        lang_chain_input: dict = {"idea-list-items": ""}

        return GeneratedPrompt(
            prompt=prompt, lang_chain_input=lang_chain_input
        )
