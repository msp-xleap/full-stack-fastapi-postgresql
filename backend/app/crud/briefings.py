from sqlmodel import Session
from fastapi import HTTPException

from app.models import (
    AIAgent,
    Briefing,
    Briefing2,
    Briefing2Reference,
    AIBriefing2ReferenceBase,
    AIBriefing2Base,
)

from app.utils import (
    get_briefing2_by_agent,
    get_briefing2_references_by_agent,
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

def create_ai_agent_briefing2(
        *, session: Session, ai_agent: AIAgent, briefing_base: AIBriefing2Base,
) -> Briefing2:
    """Stores the briefing of a new AI Agent in the database

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object
        briefing_base (AIBriefing2Base): The briefing data

    Returns:
        Briefing2: Created Briefing2 object
    """
    db_obj = Briefing2.model_validate(
        {
            **briefing_base.model_dump(),
            "agent_id": ai_agent.id
        })
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def create_ai_agent_briefing2_reference(
        *, session: Session, briefing: Briefing2, briefing_ref_base: AIBriefing2ReferenceBase,
) -> Briefing2Reference:
    """Stores the briefing references of a briefing in the database

    Args:
        session (Session): Database session
        briefing (Briefing2): Briefing2 object
        briefing_ref_base (AIBriefing2ReferenceBase): The briefing reference data

    Returns:
        Briefing2Reference: Created Briefing2 Reference object
    """
    db_obj = Briefing2Reference.model_validate({
        **briefing_ref_base.model_dump(),
        "briefing_id": briefing.id
    })
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def create_or_update_ai_agent_briefing2(
        *, session: Session, ai_agent: AIAgent, briefing_base: AIBriefing2Base,
) -> Briefing2:
    """Replaces (e.g. update or creates) the briefing of an existing agent

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object
        briefing_base (AIBriefing2Base): The briefing data

    Returns:
        Briefing2: Created Briefing2 object
    """

    try:
        briefing = get_briefing2_by_agent(str(ai_agent.id), session)

        db_obj = Briefing2.model_validate(
        {
            **briefing_base.model_dump(),
            "agent_id": str(ai_agent.id)
        })
        session.merge(db_obj)
        session.commit()
        return briefing
    except HTTPException as e:
        briefing = create_ai_agent_briefing2(session=session, ai_agent=ai_agent, briefing_base=briefing_base)
        return briefing


def replace_briefing2_references(
    *, session: Session, agent_id:str, briefing_refs: list[AIBriefing2ReferenceBase],
) -> None:
    """Replaces the references of the specified briefing with the specified references.

       More specifically: Deletes all references which currently exist in the database but
    where not specified, update existing references, and created new reference if they do not exist.

    Args:
        session (Session): Database session
        agent_id (src): ID of Agent
        briefing_refs (list[AIBriefing2ReferenceBase]): New briefing references

    Returns:
        None
    """
    existing = get_briefing2_references_by_agent(agent_id, session)

    new_map = {briefing_ref_base.ref_id: briefing_ref_base for briefing_ref_base in briefing_refs}
    existing_map = {ref.ref_id: ref for ref in existing}

    updated_refs = []

    # update existing or delete no longer needed references
    for existing_id in existing_map:
        if existing_id in new_map:
            new_ref = new_map.get(existing_id)
            db_obj = Briefing2Reference.model_validate({
                **new_ref.model_dump(),
                "agent_id": agent_id
            })
            session.merge(db_obj)
        else:
            session.delete(existing_map.get(existing_id))

    # create any new reference
    for new_id in new_map:
        if not new_id in existing_map:
            new_ref = new_map.get(new_id)
            db_obj = Briefing2Reference.model_validate(
                {
                    **new_ref.model_dump(),
                    "agent_id": agent_id
                })
            session.add(db_obj)
            updated_refs.append(db_obj)


    session.commit()
    for db_obj in updated_refs:
        session.refresh(db_obj)


