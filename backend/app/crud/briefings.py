from sqlmodel import Session, select
from fastapi import HTTPException


from app.models import (
    AIAgent,
    Briefing2,
    Briefing2Reference,
    AIBriefing2ReferenceBase,
    AIBriefing2Base
)

from app.utils import (
    get_briefing2_by_agent,
    get_briefing2_references_by_agent,
    langfuse_base_from_briefing_base,
    langfuse_base_from_briefing_reference_base,
)


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

    langfuse_base = langfuse_base_from_briefing_base(session, briefing_base)

    db_obj = Briefing2.model_validate(
        {
            **briefing_base.model_dump(),
            **langfuse_base.model_dump(),
            "agent_id": ai_agent.id
        })
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def _validate_briefing2_reference(
        *,
        briefing_ref_base: AIBriefing2ReferenceBase,
        langfuse_ref_base,
        agent_id: str
) -> Briefing2Reference:
    dump = {
        **briefing_ref_base.model_dump(),
        **langfuse_ref_base.model_dump(),
        "agent_id": agent_id
    }

    if dump['workspace_type'] is None:
        dump['workspace_type'] = ""

    return Briefing2Reference.model_validate(dump)


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

    langfuse_ref_base = langfuse_base_from_briefing_reference_base(session, briefing_ref_base)

    db_obj = _validate_briefing2_reference(
        briefing_ref_base=briefing_ref_base,
        langfuse_ref_base=langfuse_ref_base,
        agent_id=str(briefing.agent_id)
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_ai_agent_references(*, session: Session, agent: AIAgent) -> list[Briefing2Reference]:
    statement = select(Briefing2Reference).where(Briefing2Reference.agent_id == agent.id)
    session_user = session.exec(statement).all()
    return list(session_user)


def get_ai_agent_file_references(*, session: Session, agent: AIAgent) -> list[Briefing2Reference]:
    statement = (select(Briefing2Reference)
                 .where(Briefing2Reference.agent_id == agent.id)
                 .where(Briefing2Reference.type == 'file'))
    session_user = session.exec(statement).all()
    return list(session_user)


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

        langfuse_base = langfuse_base_from_briefing_base(session, briefing_base)

        db_obj = Briefing2.model_validate({
            **briefing_base.model_dump(),
            **langfuse_base.model_dump(),
            "agent_id": str(ai_agent.id)
        })
        session.merge(db_obj)
        session.commit()
        return briefing
    except HTTPException:
        briefing = create_ai_agent_briefing2(session=session, ai_agent=ai_agent, briefing_base=briefing_base)
        return briefing


def replace_briefing2_references(
    *, session: Session, agent_id: str, briefing_refs: list[AIBriefing2ReferenceBase],
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

            langfuse_ref_base = langfuse_base_from_briefing_reference_base(session, new_ref)

            db_obj = _validate_briefing2_reference(
                briefing_ref_base=new_ref,
                langfuse_ref_base=langfuse_ref_base,
                agent_id=agent_id
            )
            session.merge(db_obj)
        else:
            session.delete(existing_map.get(existing_id))

    # create any new reference
    for new_id in new_map:
        if new_id not in existing_map:
            new_ref = new_map.get(new_id)
            langfuse_ref_base = langfuse_base_from_briefing_reference_base(session, new_ref)
            db_obj = _validate_briefing2_reference(
                briefing_ref_base=new_ref,
                langfuse_ref_base=langfuse_ref_base,
                agent_id=agent_id
            )
            session.add(db_obj)
            updated_refs.append(db_obj)

    session.commit()
    for db_obj in updated_refs:
        session.refresh(db_obj)
