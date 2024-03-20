from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from app.core.config import settings

# Initialize Langfuse client (prompt management)
langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_SERVER_URL,
)

# Initialize Langfuse CallbackHandler for Langchain (tracing)
langfuse_handler = CallbackHandler(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_SERVER_URL,
)


