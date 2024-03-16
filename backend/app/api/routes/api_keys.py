from fastapi import APIRouter, HTTPException
from starlette import status

from app.api.deps import SessionDep
from app.models import AIAgentConfigBase
from app.utils import is_api_key_valid

router = APIRouter()


@router.post("/", responses={401: {"detail": "Invalid API key"},
                             408: {"detail": "Request timed out"},
                             429: {"detail": "Rate limit exceeded"}},
             status_code=status.HTTP_204_NO_CONTENT)
async def validate_api_key(*, session: SessionDep,
        agent_config: AIAgentConfigBase) -> None:
    """
    Validates API Key.


    Raises:
        HTTPException - 401: If the API key is invalid.
        HTTPException - 408: If the request timed out.
        HTTPException - 429: If the rate limit is exceeded.

    Returns:
        None

    To Do:
        - Make it model dependent. At the moment it only works for
          for OpenAI.
    """
    api_key = agent_config.api_key
    try:
        await is_api_key_valid(api_key)
    except HTTPException as http_exc:
        raise http_exc
