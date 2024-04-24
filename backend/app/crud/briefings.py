from sqlmodel import Session
from fastapi import HTTPException

from app.models import (
    AIAgent,
    Briefing,
    Briefing3,
    Briefing3Reference,
    AIBriefing3ReferenceBase,
    AIBriefing3Base,
    BriefingCategory,
    BriefingSubCategory,
    AIBriefing3LangfuseBase,
)

from app.utils import (
    get_briefing3_by_agent,
    get_briefing3_references_by_agent,
    langfuse_base_from_briefing_base,
    langfuse_base_from_briefing_reference_base,
)

def create_ai_agent_briefing(
    *, session: Session, ai_agent: AIAgent
) -> Briefing:
    """Store new AI Agent in the database

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object

    Returns:
        AIAgent: Created AI Agent object
    """
    db_obj = Briefing.model_validate({"agent_id": ai_agent.id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def create_ai_agent_briefing3(
        *, session: Session, ai_agent: AIAgent, briefing_base: AIBriefing3Base,
) -> Briefing3:
    """Stores the briefing of a new AI Agent in the database

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object
        briefing_base (AIBriefing3Base): The briefing data

    Returns:
        Briefing3: Created Briefing3 object
    """

    langfuse_base = langfuse_base_from_briefing_base(session, briefing_base)

    db_obj = Briefing3.model_validate(
        {
            **briefing_base.model_dump(),
            **langfuse_base.model_dump(),
            "agent_id": ai_agent.id
        })
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_ai_agent_briefing3_reference(
        *, session: Session, briefing: Briefing3, briefing_ref_base: AIBriefing3ReferenceBase,
) -> Briefing3Reference:
    """Stores the briefing references of a briefing in the database

    Args:
        session (Session): Database session
        briefing (Briefing3): Briefing3 object
        briefing_ref_base (AIBriefing3ReferenceBase): The briefing reference data

    Returns:
        Briefing3Reference: Created Briefing3 Reference object
    """

    langfuse_ref_base = langfuse_base_from_briefing_reference_base(session, briefing_ref_base)

    db_obj = Briefing3Reference.model_validate({
        **briefing_ref_base.model_dump(),
        **langfuse_ref_base.model_dump(),
        "briefing_id": briefing.id
    })
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_or_update_ai_agent_briefing3(
        *, session: Session, ai_agent: AIAgent, briefing_base: AIBriefing3Base,
) -> Briefing3:
    """Replaces (e.g. update or creates) the briefing of an existing agent

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object
        briefing_base (AIBriefing3Base): The briefing data

    Returns:
        Briefing3: Created Briefing3 object
    """

    try:
        briefing = get_briefing3_by_agent(str(ai_agent.id), session)

        langfuse_base = langfuse_base_from_briefing_base(session, briefing_base)

        db_obj = Briefing3.model_validate(
        {
            **briefing_base.model_dump(),
            **langfuse_base.model_dump(),
            "agent_id": str(ai_agent.id)
        })
        session.merge(db_obj)
        session.commit()
        return briefing
    except HTTPException as e:
        briefing = create_ai_agent_briefing3(session=session, ai_agent=ai_agent, briefing_base=briefing_base)
        return briefing


def replace_briefing3_references(
    *, session: Session, agent_id:str, briefing_refs: list[AIBriefing3ReferenceBase],
) -> None:
    """Replaces the references of the specified briefing with the specified references.

       More specifically: Deletes all references which currently exist in the database but
    where not specified, update existing references, and created new reference if they do not exist.

    Args:
        session (Session): Database session
        agent_id (src): ID of Agent
        briefing_refs (list[AIBriefing3ReferenceBase]): New briefing references

    Returns:
        None
    """
    existing = get_briefing3_references_by_agent(agent_id, session)

    new_map = {briefing_ref_base.ref_id: briefing_ref_base for briefing_ref_base in briefing_refs}
    existing_map = {ref.ref_id: ref for ref in existing}

    updated_refs = []

    # update existing or delete no longer needed references
    for existing_id in existing_map:
        if existing_id in new_map:
            new_ref = new_map.get(existing_id)

            langfuse_ref_base = langfuse_base_from_briefing_reference_base(session, new_ref)

            db_obj = Briefing3Reference.model_validate({
                **new_ref.model_dump(),
                **langfuse_ref_base.model_dump(),
                "agent_id": agent_id
            })
            session.merge(db_obj)
        else:
            session.delete(existing_map.get(existing_id))

    # create any new reference
    for new_id in new_map:
        if not new_id in existing_map:
            new_ref = new_map.get(new_id)
            langfuse_ref_base = langfuse_base_from_briefing_reference_base(session, new_ref)
            db_obj = Briefing3Reference.model_validate(
                {
                    **new_ref.model_dump(),
                    **langfuse_ref_base.model_dump(),
                    "agent_id": agent_id
                })
            session.add(db_obj)
            updated_refs.append(db_obj)


    session.commit()
    for db_obj in updated_refs:
        session.refresh(db_obj)


