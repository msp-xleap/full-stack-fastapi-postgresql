from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.models import AIAgentConfigBase
from app.utils import is_api_key_valid

router = APIRouter()

@router.post("/", response_model=bool, status_code=200)
def validate_api_key(
        *, session: SessionDep, agent_config: AIAgentConfigBase
) -> Any:
    """
    Validate API Key.

    To Do:
        - Make it model dependent. At the moment it only works for
          for OpenAI.
    """
    api_key = agent_config.api_key
    # api_key = "YOUR API KEY"
    result = is_api_key_valid(api_key=api_key)

    if result:
        return result
    else:
        raise HTTPException(status_code=401, detail="Provided API-key is invalid")