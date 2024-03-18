import aiohttp

import logging


async def get_agent_briefing(
        agent_id: str,
        server_address: str,
        xleap_session_id: str,
        xleap_workspace_id: str,
        xleap_instance_id: str,
        auth_token: str
) -> None:
    """
    Get briefing for the agent from XLeap server and store it in the database.

    Args:
        agent_id (str): UUID of the agent.
        server_address (str): XLeap server address.
        xleap_session_id (str): UUID of the XLeap session.
        xleap_workspace_id (str): UUID of the XLeap workspace.
        xleap_instance_id (str): UUID of the XLeap instance.
        auth_token (str): Authorization token.

    Returns
        None
    """
    logging.info(f"""
    Requesting briefing for agent {agent_id} from
    XLeap server: {server_address}
    XLeap session ID: {xleap_session_id}
    XLeap workspace ID: {xleap_workspace_id}
    XLeap instance ID: {xleap_instance_id}
    """)

    # Get agent briefing from XLeap server
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url=f"{server_address}services/api/sessions/"
                f"{xleap_session_id}/workspaces/{xleap_workspace_id}/settings/"
                f"ai/{xleap_instance_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        ) as agent_briefing_obj:
            agent_briefing = await agent_briefing_obj.json()
            logging.info(f"Agent briefing: {agent_briefing}")
