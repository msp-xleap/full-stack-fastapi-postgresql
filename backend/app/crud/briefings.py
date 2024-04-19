from sqlmodel import Session

from app.models import AIAgent, Briefing, Briefing2, Briefing2Reference, AIBriefing2ReferenceBase, AIBriefing2Base


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
    """Store new AI Agent in the database

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
    """Store new AI Agent in the database

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
