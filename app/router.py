from fastapi import APIRouter

from app.controllers.v1 import llm, video, logs, settings
from app.controllers import ping

root_api_router = APIRouter()
root_api_router.include_router(video.router)
root_api_router.include_router(llm.router)
root_api_router.include_router(logs.router)
root_api_router.include_router(settings.router)
root_api_router.include_router(ping.router)
