import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import emails  # type: ignore
from fastapi import HTTPException
from jinja2 import Template
from jose import JWTError, jwt
from langchain_openai import OpenAI
from openai import AuthenticationError, APITimeoutError, RateLimitError
from starlette import status

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import AIAgent

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str,
                          context: dict[str, Any]) -> str:
    template_str = (Path(
        __file__).parent / "email-templates" / "build" / template_name).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(*, email_to: str, subject: str = "",
               html_content: str = "", ) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(subject=subject, html=html_content, mail_from=(
    settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL), )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logging.info(f"send email result: {response}")


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(template_name="test_email.html",
                                         context={
                                             "project_name": settings.PROJECT_NAME,
                                             "email": email_to}, )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str,
                                  token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.server_host}/reset-password?token={token}"
    html_content = render_email_template(template_name="reset_password.html",
                                         context={
                                             "project_name": settings.PROJECT_NAME,
                                             "username": email,
                                             "email": email_to,
                                             "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
                                             "link": link, }, )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(email_to: str, username: str,
                               password: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(template_name="new_account.html",
                                         context={
                                             "project_name": settings.PROJECT_NAME,
                                             "username": username,
                                             "password": password,
                                             "email": email_to,
                                             "link": settings.server_host, }, )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode({"exp": exp, "nbf": now, "sub": email},
                             settings.SECRET_KEY, algorithm="HS256", )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY,
                                   algorithms=["HS256"])
        return str(decoded_token["sub"])
    except JWTError:
        return None


async def is_api_key_valid(api_key: str) -> None:
    """ Validates API Key asynchronously.

    Args:
        api_key (str): OpenAI API key.

    Raises:
        HTTPException - 401: If the API key is invalid.
        HTTPException - 408: If the request timed out.
        HTTPException - 429: If the rate limit is exceeded.

    Returns:
        None
    """
    try:
        llm = OpenAI(openai_api_key=api_key)
        llm.invoke("Are you ready? Yes or no?")
    except AuthenticationError as auth_err:
        logging.error(f"Unauthorized: Invalid API key")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid API key")
    except APITimeoutError as timeout_err:
        logging.error(f"Request timed out: {timeout_err}")
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT,
                            detail="Request timed out")
    except RateLimitError as rate_limit_err:
        logging.error(f"Rate limit exceeded: {rate_limit_err}")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Rate limit exceeded")
    except Exception as err:
        logging.error(f"An error occurred: {err}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(err))


def get_agent(agent_id: str, session: SessionDep) -> AIAgent:
    """Get agent by ID

    Args:
        agent_id (str): UUID of the agent to be activated
        session (SessionDep): Database session

    Raises:
        HTTPException - 404: If the agent is not found.

    Returns:
        AIAgent: Agent object
    """
    try:
        # Find agent by ID
        agent = session.get(AIAgent, agent_id)
    except Exception as e:
        # Handle cases where the agent_id is invalid or not found
        raise HTTPException(
            status_code=404,
            detail="The agent with this id does not exist in the system"
        ) from e
    return agent
