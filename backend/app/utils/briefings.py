import logging
from collections.abc import Sequence
from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import (
    AIBriefing2Base,
    AIBriefing2LangfuseBase,
    AIBriefing2ReferenceBase,
    AIBriefing2ReferenceLangfuseBase,
    Briefing,
    Briefing2,
    Briefing2Reference,
    BriefingCategory,
    BriefingSubCategory,
    BriefingSubCategoryDifferentiator,
    XLeapBriefingPrompt,
)
from app.orchestration.prompts import langfuse_client


def get_briefing_by_agent_id(agent_id: str, session: Session) -> Briefing:
    """Get briefing by agent ID

    Args:
        agent_id (str): UUID of the agent to be activated
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing: Briefing object
    """
    # Find briefing by agent ID
    query = select(Briefing).where(Briefing.agent_id == agent_id)
    briefing = session.exec(query).first()

    if briefing is None:
        # If briefing is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="Briefing for this agent does not exist in the system",
        )
    return briefing


def get_briefing2_by_agent_id(agent_id: str, session: Session) -> Briefing2:
    """Get briefing by agent ID

    Args:
        agent_id (str): UUID of the agent to be activated
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing: Briefing object
    """
    # Find briefing by agent ID
    query = select(Briefing2).where(Briefing2.agent_id == agent_id)
    briefing = session.exec(query).first()

    if briefing is None:
        # If briefing is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="Briefing for this agent does not exist in the system",
        )
    return briefing


def get_briefing2_by_agent(agent_id: str, session: Session) -> Briefing2:
    """Get briefing by agent

    Args:
        agent_id (str): UUID of the agent
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing2: Briefing2 object
    """
    # Find briefing by agent ID
    query = select(Briefing2).where(Briefing2.agent_id == agent_id)
    briefing = session.exec(query).first()

    if briefing is None:
        # If briefing is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="Briefing for this agent does not exist in the system",
        )
    return briefing


def get_briefing2_references_by_agent(
    agent_id: str, session: Session
) -> Sequence[Briefing2Reference]:
    """Returns the references of a briefing

    Args:
        agent_id (stc): UUID of agent
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing2: Briefing2 object
    """

    # Find references by briefing ID
    query = select(Briefing2Reference).where(
        Briefing2Reference.agent_id == agent_id
    )
    return session.exec(query).all()


def _create_xleap_prompt(
    *,
    session: Session,
    cat: BriefingCategory,
    db_sub_cat: str,
    template: str,
    langfuse_prompt: str,
) -> None:
    db_prompt = XLeapBriefingPrompt(
        category=cat,
        sub_category=db_sub_cat,
        template=template,
        langfuse_prompt=langfuse_prompt,
    )
    session.add(db_prompt)
    session.commit()
    session.refresh(db_prompt)


def _workspace_name_2_sub_category(name: str) -> BriefingSubCategory:
    """
    Maps an XLeap WorkspaceType to a BriefingSubCategory
    :param name: an WorkspaceType constant from Java com.smartspeed.util.constants.WorkspaceType
    :return: the corresponding BriefingSubCategory
    :raise ValueError if the workspace type is unknown
    """
    match name:
        case "brainstorm":
            return BriefingSubCategory.WS_BRAINSTORM
        case "deepdive":
            return BriefingSubCategory.WS_DEEPDIVE
        case "presentation":
            return BriefingSubCategory.WS_PRESENTATION
        case "resulttable":
            return BriefingSubCategory.WS_RESULTS
        case "resultmultitable":
            return BriefingSubCategory.WS_MULTI_RESULTS

    if name is None:
        return BriefingSubCategory.WS_BRAINSTORM

    raise ValueError("Unhandled workspace name: '" + str(name) + "'")


def _get_langfuse_prompt_name(
    *,
    session: Session,
    cat: BriefingCategory,
    sub_category: BriefingSubCategory,
    template: str,
    ref_number: int = 0,
    differentiator: BriefingSubCategoryDifferentiator = BriefingSubCategoryDifferentiator.NONE,
) -> str:
    """
    Gets the name of a Prompt from an XLeap template string
    :param session: the SQL session
    :param cat: the category for the prompt
    :param sub_category:  the sub category of the prompt
    :param template: the language template
    :param ref_number: required for references
    :param differentiator: default NONE="", used TASK_TEMPLATES
    :return: the name of the corresponding prompt in Langfuse
    """
    db_sub_cat = sub_category + differentiator
    if ref_number > 0:
        db_sub_cat = db_sub_cat + "@" + str(ref_number)
    query = select(XLeapBriefingPrompt).where(
        XLeapBriefingPrompt.category == cat,
        XLeapBriefingPrompt.sub_category == db_sub_cat,
        XLeapBriefingPrompt.template == template,
    )
    briefing_prompt = session.exec(query).first()

    if briefing_prompt is not None:
        return briefing_prompt.langfuse_prompt

    date_str = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")

    if BriefingSubCategory.NONE == sub_category:
        if ref_number == 0:
            name = f"xleap-{cat}-{date_str}"
        else:
            name = f"xleap-{cat}-{ref_number}-{date_str}"
    elif ref_number == 0:
        name = f"xleap-{cat}-{sub_category}{differentiator}-{date_str}"
    else:
        name = f"xleap-{cat}-{sub_category}{differentiator}-{ref_number}-{date_str}"

    langfuse_prompt = langfuse_client.create_prompt(
        name=name, prompt=template, is_active=True
    )

    logging.info(f"new prompt name is: {name}")

    _create_xleap_prompt(
        session=session,
        cat=cat,
        db_sub_cat=db_sub_cat,
        template=template,
        langfuse_prompt=langfuse_prompt.name,
    )

    return langfuse_prompt.name


def langfuse_base_from_briefing_base(
    session: Session, briefing_base: AIBriefing2Base
) -> AIBriefing2LangfuseBase:
    """Converts templates from AIBriefing2Base to prompts in Langfuse and returns an object
       with all Langfuse prompt names that are used in the briefing

    Args:
        session (Session): Database session
        briefing_base (AIBriefing2Base): The briefing data

    Returns:
        AIBriefing2LangfuseBase: the result of the conversion
    """
    langfuse_base: AIBriefing2LangfuseBase = AIBriefing2LangfuseBase()
    sub_category = BriefingSubCategory.MEDIUM
    if briefing_base.response_length == 1:
        sub_category = BriefingSubCategory.BRIEF
    elif briefing_base == 3:
        sub_category = BriefingSubCategory.DETAILED

    workspace_sub_category = _workspace_name_2_sub_category(
        briefing_base.workspace_type
    )

    langfuse_base.response_length_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.RESPONSE_LENGTH,
        sub_category=sub_category,
        template=briefing_base.response_length_template,
    )

    langfuse_base.response_language_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.RESPONSE_LANGUAGE,
        sub_category=BriefingSubCategory.NONE,
        template=briefing_base.response_language_template,
    )

    langfuse_base.context_intro_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.CONTEXT_INTRO,
        sub_category=workspace_sub_category,
        template=briefing_base.context_intro_template,
    )

    if briefing_base.with_additional_info:
        langfuse_base.additional_info_langfuse_name = (
            _get_langfuse_prompt_name(
                session=session,
                cat=BriefingCategory.ADDITIONAL_INFO,
                sub_category=BriefingSubCategory.NONE,
                template=briefing_base.additional_info_template,
            )
        )

    if briefing_base.with_persona:
        langfuse_base.persona_langfuse_name = _get_langfuse_prompt_name(
            session=session,
            cat=BriefingCategory.PERSONA,
            sub_category=BriefingSubCategory.NONE,
            template=briefing_base.persona_template,
        )

    if briefing_base.with_tone:
        langfuse_base.tone_langfuse_name = _get_langfuse_prompt_name(
            session=session,
            cat=BriefingCategory.TONE,
            sub_category=BriefingSubCategory.NONE,
            template=briefing_base.tone_template,
        )

    if briefing_base.with_host_info:
        langfuse_base.host_info_langfuse_name = _get_langfuse_prompt_name(
            session=session,
            cat=BriefingCategory.HOST_INFO,
            sub_category=workspace_sub_category,
            template=briefing_base.host_info_template,
        )

    if briefing_base.with_participant_info:
        langfuse_base.participant_info_langfuse_name = (
            _get_langfuse_prompt_name(
                session=session,
                cat=BriefingCategory.PARTICIPANT_INFO,
                sub_category=BriefingSubCategory.NONE,
                template=briefing_base.participant_info_template,
            )
        )

    if briefing_base.with_session_info:
        langfuse_base.session_info_langfuse_name = _get_langfuse_prompt_name(
            session=session,
            cat=BriefingCategory.SESSION_INFO,
            sub_category=workspace_sub_category,
            template=briefing_base.session_info_template,
        )

    if briefing_base.with_workspace_info:
        langfuse_base.workspace_info_langfuse_name = _get_langfuse_prompt_name(
            session=session,
            cat=BriefingCategory.WORKSPACE_PURPOSE_INFO,
            sub_category=workspace_sub_category,
            template=briefing_base.workspace_info_template,
        )

    if briefing_base.with_workspace_instruction:
        langfuse_base.workspace_instruction_langfuse_name = (
            _get_langfuse_prompt_name(
                session=session,
                cat=BriefingCategory.WORKSPACE_INSTRUCTION,
                sub_category=workspace_sub_category,
                template=briefing_base.workspace_instruction_template,
            )
        )

    if briefing_base.with_num_exemplar > 0:
        langfuse_base.exemplar_langfuse_name = _get_langfuse_prompt_name(
            session=session,
            cat=BriefingCategory.EXEMPLAR,
            sub_category=workspace_sub_category,
            template=briefing_base.exemplar_template,
        )

    langfuse_base.task_nn_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TASK_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.task_template_nn,
        differentiator=BriefingSubCategoryDifferentiator.TASK_ONE_NN,
    )

    langfuse_base.task_pn_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TASK_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.task_template_pn,
        differentiator=BriefingSubCategoryDifferentiator.TASK_ONE_PN,
    )

    langfuse_base.task_na_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TASK_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.task_template_na,
        differentiator=BriefingSubCategoryDifferentiator.TASK_ONE_NA,
    )

    langfuse_base.task_pa_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TASK_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.task_template_pn,
        differentiator=BriefingSubCategoryDifferentiator.TASK_ONE_PA,
    )

    langfuse_base.task_multi_nn_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TASK_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.task_template_multi_nn,
        differentiator=BriefingSubCategoryDifferentiator.TASK_MULTI_NN,
    )

    langfuse_base.task_multi_pn_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TASK_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.task_template_multi_pn,
        differentiator=BriefingSubCategoryDifferentiator.TASK_MULTI_PN,
    )

    langfuse_base.task_multi_na_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TASK_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.task_template_multi_na,
        differentiator=BriefingSubCategoryDifferentiator.TASK_MULTI_NA,
    )

    langfuse_base.task_multi_pa_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TASK_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.task_template_multi_pa,
        differentiator=BriefingSubCategoryDifferentiator.TASK_MULTI_PA,
    )

    langfuse_base.test_briefing_langfuse_name = _get_langfuse_prompt_name(
        session=session,
        cat=BriefingCategory.TEST_BRIEFING_TEMPLATE,
        sub_category=workspace_sub_category,
        template=briefing_base.test_briefing_template,
    )

    return langfuse_base


def langfuse_base_from_briefing_reference_base(
    session: Session, briefing_ref_base: AIBriefing2ReferenceBase
) -> AIBriefing2ReferenceLangfuseBase:
    """Converts the template of a AIBriefing2ReferenceBase to a prompt in Langfuse and returns an object
       with the name of that prompt

    :param session: the database session
    :param briefing_ref_base: the reference definition
    :return: the AIBriefing2ReferenceLangfuseBase
    """
    langfuse_base = AIBriefing2ReferenceLangfuseBase()

    match briefing_ref_base.type:
        case "link":
            langfuse_base.langfuse_name = _get_langfuse_prompt_name(
                session=session,
                cat=BriefingCategory.LINK,
                sub_category=BriefingSubCategory.NONE,
                template=briefing_ref_base.template,
                ref_number=briefing_ref_base.ref_number,
            )
        case "file":
            langfuse_base.langfuse_name = _get_langfuse_prompt_name(
                session=session,
                cat=BriefingCategory.FILE,
                sub_category=BriefingSubCategory.NONE,
                template=briefing_ref_base.template,
                ref_number=briefing_ref_base.ref_number,
            )
        case "xleap":
            workspace_sub_category = _workspace_name_2_sub_category(
                briefing_ref_base.workspace_type
            )
            langfuse_base.langfuse_name = _get_langfuse_prompt_name(
                session=session,
                cat=BriefingCategory.WORKSPACE_CONTENT,
                sub_category=workspace_sub_category,
                template=briefing_ref_base.template,
                ref_number=briefing_ref_base.ref_number,
            )
        case "exemplar":
            langfuse_base.langfuse_name = _get_langfuse_prompt_name(
                session=session,
                cat=BriefingCategory.EXEMPLAR,
                sub_category=BriefingSubCategory.EXEMPLAR,
                template=briefing_ref_base.template,
                ref_number=briefing_ref_base.ref_number,
            )
        case _:
            raise ValueError(
                f"Unhandled reference type: '{briefing_ref_base.type}'"
            )

    return langfuse_base
