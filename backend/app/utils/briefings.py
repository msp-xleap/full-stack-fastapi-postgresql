import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from typing import Sequence
from app.models import (
    Briefing,
    Briefing3,
    Briefing3Reference,
    BriefingCategory,
    BriefingSubCategory,
    AIBriefing3Base,
    AIBriefing3LangfuseBase,
    AIBriefing3ReferenceLangfuseBase,
    XLeapBriefingPrompt,
    AIBriefing3ReferenceBase,
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


def get_briefing3_by_agent(agent_id: str, session: Session) -> Briefing3:
    """Get briefing by agent

    Args:
        agent_id (str): UUID of the agent
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing3: Briefing3 object
    """
    # Find briefing by agent ID
    query = select(Briefing3).where(Briefing3.agent_id == agent_id)
    briefing = session.exec(query).first()

    if briefing is None:
        # If briefing is not found, raise HTTPException
        raise HTTPException(
            status_code=404,
            detail="Briefing for this agent does not exist in the system",
        )
    return briefing


def get_briefing3_references_by_agent(agent_id: str, session: Session) -> Sequence[Briefing3Reference]:
    """Returns the references of a briefing

    Args:
        agent_id (stc): UUID of agent
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the briefing for the agent is not found.

    Returns:
        Briefing3: Briefing3 object
    """

    # Find references by briefing ID
    query = select(Briefing3Reference).where(Briefing3Reference.agent_id == agent_id)
    return session.exec(query).all()

def _create_xleap_prompt(*,
                         session:Session,
                         cat:BriefingCategory,
                         sub_category:BriefingSubCategory,
                         template: str,
                         langfuse_prompt: str) -> None:
    db_prompt = XLeapBriefingPrompt(
        category=cat, sub_category=sub_category, template=template, langfuse_prompt=langfuse_prompt)
    session.add(db_prompt)
    session.commit()
    session.refresh(db_prompt)

def _workspace_name_2_sub_category(name:str) -> BriefingSubCategory:
    """
    Maps an XLeap WorkspaceType to a BriefingSubCategory
    :param name: an WorkspaceType constant from Java com.smartspeed.util.constants.WorkspaceType
    :return: the corresponding BriefingSubCategory
    :raise ValueError if the workspace type is unknown
    """
    match name:
        case 'brainstorm':
            return BriefingSubCategory.WS_BRAINSTORM
        case 'deepdive':
            return BriefingSubCategory.WS_DEEPDIVE
        case 'presentation':
            return BriefingSubCategory.WS_PRESENTATION
        case 'resulttable':
            return BriefingSubCategory.WS_RESULTS
        case 'resultmultitable':
            return BriefingSubCategory.WS_MULTI_RESULTS

    raise ValueError(f"Unhandled workspace name: '{name}'")

def _get_langfuse_prompt_name(*,
                             session: Session,
                             cat:BriefingCategory,
                             sub_category:BriefingSubCategory,
                             template: str) -> str:
    """
    Gets the name of a Prompt from an XLeap template string
    :param session: the SQL session
    :param cat: the category for the prompt
    :param sub_category:  the sub category of the prompt
    :param template: the language template
    :return: the name of the corresponding prompt in Langfuse
    """
    query = select(XLeapBriefingPrompt).where(
        XLeapBriefingPrompt.category == cat,
                    XLeapBriefingPrompt.sub_category == sub_category,
                    XLeapBriefingPrompt.template == template)
    briefing_prompt = session.exec(query).first()

    if not briefing_prompt is None:
        return briefing_prompt.langfuse_prompt

    if BriefingSubCategory.NONE == sub_category:
        name=f"xleap-{cat}-{uuid.uuid4()}"
    else:
        name=f"xleap-{cat}-{sub_category}-{uuid.uuid4()}"

    langfuse_prompt = langfuse_client.create_prompt(
        name=name,
        prompt=template,
        is_active=True)

    _create_xleap_prompt(session=session,
                         cat=cat,
                         sub_category=sub_category,
                         template=template,
                         langfuse_prompt=langfuse_prompt.name)

    return langfuse_prompt.name

def langfuse_base_from_briefing_base(session: Session, briefing_base: AIBriefing3Base) -> AIBriefing3LangfuseBase:
    """Converts templates from AIBriefing3Base to prompts in Langfuse and returns an object
       with all Langfuse prompt names that are used in the briefing

    Args:
        session (Session): Database session
        briefing_base (AIBriefing3Base): The briefing data

    Returns:
        AIBriefing3LangfuseBase: the result of the conversion
    """
    langfuse_base = AIBriefing3LangfuseBase()
    sub_category = BriefingSubCategory.MEDIUM
    if briefing_base.response_length == 1:
        sub_category = BriefingSubCategory.BRIEF
    elif briefing_base == 3:
        sub_category = BriefingSubCategory.DETAILED

    workspace_sub_category = _workspace_name_2_sub_category(briefing_base.workspace_type)

    langfuse_base.response_length_langfuse = _get_langfuse_prompt_name(session=session,
                                                                       cat=BriefingCategory.RESPONSE_LENGTH,
                                                                       sub_category=sub_category,
                                                                       template=briefing_base.response_length_template)
    if briefing_base.with_additional_info:
        langfuse_base.additional_info_langfuse = _get_langfuse_prompt_name(session=session,
                                                                           cat=BriefingCategory.ADDITIONAL_INFO,
                                                                           sub_category=BriefingSubCategory.NONE,
                                                                           template=briefing_base.additional_info_template)
    if briefing_base.with_persona:
        langfuse_base.persona_langfuse = _get_langfuse_prompt_name(session=session,
                                                                   cat=BriefingCategory.PERSONA,
                                                                   sub_category=BriefingSubCategory.NONE,
                                                                   template=briefing_base.persona_template)

    if briefing_base.with_tone:
        langfuse_base.tone_langfuse = _get_langfuse_prompt_name(session=session,
                                                                cat=BriefingCategory.TONE,
                                                                sub_category=BriefingSubCategory.NONE,
                                                                template=briefing_base.tone_template)

    if briefing_base.with_host_info:
        langfuse_base.host_info_langfuse = _get_langfuse_prompt_name(session=session,
                                                               cat=BriefingCategory.HOST_INFO,
                                                               sub_category=BriefingSubCategory.NONE,
                                                               template=briefing_base.host_info_template)

    if briefing_base.with_participant_info:
        langfuse_base.participant_info_langfuse = _get_langfuse_prompt_name(session=session,
                                                               cat=BriefingCategory.PARTICIPANT_INFO,
                                                               sub_category=BriefingSubCategory.NONE,
                                                               template=briefing_base.participant_info_template)

    if briefing_base.with_session_info:
        langfuse_base.session_info_langfuse = _get_langfuse_prompt_name(session=session,
                                                                       cat=BriefingCategory.SESSION_INFO,
                                                                       sub_category=workspace_sub_category,
                                                                       template=briefing_base.session_info_template)

    if briefing_base.with_workspace_info:
        langfuse_base.workspace_info_langfuse = _get_langfuse_prompt_name(session=session,
                                                           cat=BriefingCategory.WORKSPACE_PURPOSE_INFO,
                                                           sub_category=workspace_sub_category,
                                                           template=briefing_base.workspace_info_template)

    if briefing_base.with_num_exemplar > 0:
        langfuse_base.exemplar_langfuse = _get_langfuse_prompt_name(session=session,
                                                                         cat=BriefingCategory.EXEMPLAR,
                                                                         sub_category=BriefingSubCategory.NONE,
                                                                         template=briefing_base.exemplar_template)


    return langfuse_base


def langfuse_base_from_briefing_reference_base(session: Session, briefing_ref_base: AIBriefing3ReferenceBase) -> AIBriefing3ReferenceLangfuseBase:
    """Converts the template of a AIBriefing3ReferenceBase to a prompt in Langfuse and returns an object
       with the name of that prompt

    :param session: the database session
    :param briefing_ref_base: the reference definition
    :return: the AIBriefing3ReferenceLangfuseBase
    """
    langfuse_base = AIBriefing3ReferenceLangfuseBase()

    match briefing_ref_base.type:
        case 'link':
            langfuse_base.template_langfuse = _get_langfuse_prompt_name(session=session,
                                                                cat=BriefingCategory.LINK,
                                                                sub_category=BriefingSubCategory.NONE,
                                                                template=briefing_ref_base.template)
        case 'file':
            langfuse_base.template_langfuse = _get_langfuse_prompt_name(session=session,
                                                            cat=BriefingCategory.FILE,
                                                            sub_category=BriefingSubCategory.NONE,
                                                            template=briefing_ref_base.template)
        case 'xleap':
            workspace_sub_category = _workspace_name_2_sub_category(briefing_ref_base.workspace_type)
            langfuse_base.template_langfuse = _get_langfuse_prompt_name(session=session,
                                                                        cat=BriefingCategory.WORKSPACE_CONTENT,
                                                                        sub_category=workspace_sub_category,
                                                                        template=briefing_ref_base.template)
        case 'exemplar':
            langfuse_base.template_langfuse = _get_langfuse_prompt_name(session=session,
                                                                        cat=BriefingCategory.EXEMPLAR,
                                                                        sub_category=BriefingSubCategory.EXEMPLAR,
                                                                        template=briefing_ref_base.template)
        case _:
            raise ValueError(f"Unhandled reference type: '{briefing_ref_base.type}'")


    return langfuse_base
