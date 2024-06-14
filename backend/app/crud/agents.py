from sqlmodel import Session

from app.models import AIAgent, AIAgentCreate, AIAgentConfigBase


def create_ai_agent(*, session: Session, ai_agent: AIAgentCreate) -> AIAgent:
    """Store new AI Agent in the database

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object

    Returns:
        AIAgent: Created AI Agent object
    """
    db_obj = AIAgent.model_validate(
        {
            **ai_agent.xleap.model_dump(),
            **ai_agent.config.model_dump(),
        }  # , update={"hashed_password": get_password_hash(ai_agent.xleap.secret)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_ai_agent(*, session: Session, agent: AIAgent, ai_config_agent: AIAgentConfigBase) -> AIAgent:
    """Update the agent configuration for an existing agent

    Args:
        session (Session): Database session
        agent (AIAgent): The agent to update
        ai_config_agent (AIAgentConfigBase): AI Agent config object
    """

    agent.model = ai_config_agent.model
    agent.api_key = ai_config_agent.api_key
    agent.api_url = ai_config_agent.api_url
    agent.api_type = ai_config_agent.api_type
    agent.org_id = ai_config_agent.org_id

    session.merge(agent)
    session.commit()
    session.refresh(agent)

    return agent


def activate_ai_agent(*, session: Session, ai_agent: AIAgent) -> AIAgent:
    """Activate AI Agent

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object

    Returns:
        AIAgent: Activated AI Agent object
    """
    extra_data = {"is_active": True}
    ai_agent.sqlmodel_update(ai_agent, update=extra_data)
    session.add(ai_agent)
    session.commit()
    session.refresh(ai_agent)
    return ai_agent


def deactivate_ai_agent(*, session: Session, ai_agent: AIAgent) -> AIAgent:
    """Deactivate AI Agent

    Args:
        session (Session): Database session
        ai_agent (AIAgent): AI Agent object

    Returns:
        AIAgent: Deactivated AI Agent object
    """
    extra_data = {"is_active": False}
    ai_agent.sqlmodel_update(ai_agent, update=extra_data)
    session.add(ai_agent)
    session.commit()
    session.refresh(ai_agent)
    return ai_agent
