import logging

from fastapi import HTTPException
from langchain_openai import ChatOpenAI
from openai import (
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)
from starlette import status

from app.orchestration.prompts import langfuse_client, langfuse_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
)


async def is_api_key_valid(
    api_key: str, org_id: str | None, llm_model: str = "gpt-3.5-turbo"
) -> None:
    """Validates API Key asynchronously.

    Args:
        api_key (str): OpenAI API key.
        org_id: (str|None): OpenAI organization ID.
        llm_model: (str): OpenAI language model. Defaults to
            "gpt-3.5-turbo-instruct".

    Raises:
        HTTPException - 401: If the API key is invalid.
        HTTPException - 408: If the request timed out.
        HTTPException - 429: If the rate limit is exceeded.

    Returns:
        None
    """
    try:
        if org_id:
            llm = ChatOpenAI(
                openai_api_key=api_key,  # type: ignore
                openai_organization=org_id,
                model_name=llm_model,
            )
        else:
            llm = ChatOpenAI(
                openai_api_key=api_key,  # type: ignore
                model_name=llm_model,
            )

        langfuse_prompt_obj = langfuse_client.get_prompt("API_KEY_VALIDATION")
        llm.invoke(
            langfuse_prompt_obj.prompt,
            config={"callbacks": [langfuse_handler]},
        )

    except AuthenticationError:
        logging.error("Unauthorized: Invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    except NotFoundError as not_found_err:
        logging.error(
            f"Provided large language model not found:" f" {not_found_err}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="LLM not found"
        )
    except APITimeoutError as timeout_err:
        logging.error(f"Request timed out: {timeout_err}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timed out",
        )
    except RateLimitError as rate_limit_err:
        logging.error(f"Rate limit exceeded: {rate_limit_err}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
    except Exception as err:
        logging.error(f"An error occurred: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        )
