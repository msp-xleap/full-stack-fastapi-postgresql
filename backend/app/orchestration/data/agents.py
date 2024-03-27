import logging

import aiohttp

from app.models import AIAgent


async def get_agent_briefing(
    agent: AIAgent,
) -> None:
    """
    Get briefing for the agent from XLeap server and store it in the database.

    Args:
        agent_id (str): Agent of which the briefing is to be fetched

    Returns
        None
    """
    logging.info(
        f"""
    Requesting briefing for agent {agent.id} from
    XLeap server: {agent.server_address}
    XLeap session ID: {agent.session_id}
    XLeap workspace ID: {agent.workspace_id}
    XLeap instance ID: {agent.instance_id}
    """
    )

    # Get agent briefing from XLeap server
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url=f"{agent.server_address}/services/api/sessions"
            f"/{agent.session_id}/workspaces/"
            f"{agent.workspace_id}/settings/ai/{agent.instance_id}",
            headers={"Authorization": f"Bearer {agent.secret}"},
        ) as agent_briefing_obj:
            agent_briefing = await agent_briefing_obj.json()
            logging.info(f"Agent briefing: {agent_briefing}")
