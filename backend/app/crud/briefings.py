from sqlmodel import Session

from app.models import AIAgent, Briefing


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
