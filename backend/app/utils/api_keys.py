import logging

from fastapi import HTTPException
from langchain_openai import ChatOpenAI
from openai import (
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
    NotFoundError
)
from langfuse.api.resources.commons.errors import (
 NotFoundError as PromptNotFoundError,
 UnauthorizedError as PromptAuthenticationError
)
from starlette import status

from app.core.config import settings
from app.orchestration.prompts import langfuse_client, langfuse_handler
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
)


def _get_or_create_api_key_validation_prompt_under_lock():
    """ returns the API validation prompt
        If the prompt is not present it will be created.
        This method acquires lock
    """
    lock = threading.Lock()
    lock.acquire()
    try:
        return langfuse_client.get_prompt("API_KEY_VALIDATION")  # check again if the prompt exists
    except PromptNotFoundError:  # otherwise created
        return langfuse_client.create_prompt(
                    name="API_KEY_VALIDATION",
                    prompt="Are you currently accepting any prompts? Answer with \"YES\"",
                    is_active=True)
    finally:
        lock.release()


def _get_api_key_validation_prompt():
    """ returns the API validation prompt
        If the prompt is not present it will be created
    """
    try:
        return langfuse_client.get_prompt("API_KEY_VALIDATION")
    except PromptAuthenticationError:
        logging.error("Internal Error: Got Unauthorized from Langfuse")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Langfuse authentication error"
        )
    except PromptNotFoundError:
        return _get_or_create_api_key_validation_prompt_under_lock()


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
        langfuse_prompt_obj = _get_api_key_validation_prompt()
    except PromptAuthenticationError:
        logging.error("Internal Error: Got Unauthorized from Langfuse")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Langfuse authentication error"
        )
    except Exception as err:
        logging.error(f"An error calling Langfuse: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        )

    try:
        if org_id:
            llm = ChatOpenAI(
                openai_api_key=api_key,  # type: ignore
                openai_organization=org_id,
                model_name=llm_model,
                openai_proxy=settings.HTTP_PROXY,
            )
        else:
            llm = ChatOpenAI(
                openai_api_key=api_key,  # type: ignore
                model_name=llm_model,
                openai_proxy=settings.HTTP_PROXY,
            )

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
