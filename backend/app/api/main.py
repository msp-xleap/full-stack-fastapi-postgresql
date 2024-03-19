from fastapi import APIRouter

from app.api.routes import items, login, users, utils, agents, api_keys, ideas

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(api_keys.router, prefix="/api_keys", tags=["api_keys"])
api_router.include_router(ideas.router, tags=["ideas"])

