from fastapi import APIRouter

from app.api.routes import agents, api_keys, ideas

api_router = APIRouter()
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(
    api_keys.router, prefix="/api_keys", tags=["api_keys"]
)
api_router.include_router(ideas.router, tags=["ideas"])
