"""Application implementation - ASGI."""

import os
import threading
import time

from fastapi import FastAPI, Request, APIRouter
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import config
from app.models.exception import HttpException
from app.router import root_api_router
from app.utils import utils

# Import log_service to register the logger handler
from app.services import log_service  # noqa: F401
from app.services import locallens


def exception_handler(request: Request, e: HttpException):
    return JSONResponse(
        status_code=e.status_code,
        content=utils.get_response(e.status_code, e.data, e.message),
    )


def validation_exception_handler(request: Request, e: RequestValidationError):
    errors = e.errors()
    msg = errors[0].get("msg", "field required") if errors else "field required"
    return JSONResponse(
        status_code=400,
        content=utils.get_response(status=400, data=errors, message=msg),
    )


def get_application() -> FastAPI:
    """Initialize FastAPI application.

    Returns:
       FastAPI: Application object instance.

    """
    instance = FastAPI(
        title=config.project_name,
        description=config.project_description,
        version=config.project_version,
        debug=False,
    )
    # 挂载 API 路由到 /api 前缀
    api_router = APIRouter(prefix="/api")
    api_router.include_router(root_api_router)
    instance.include_router(api_router)
    instance.add_exception_handler(HttpException, exception_handler)
    instance.add_exception_handler(RequestValidationError, validation_exception_handler)
    return instance


app = get_application()

# Configures the CORS middleware for the FastAPI app
cors_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
origins = cors_allowed_origins_str.split(",") if cors_allowed_origins_str else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

task_dir = utils.task_dir()
app.mount(
    "/tasks", StaticFiles(directory=task_dir, html=True, follow_symlink=True), name=""
)

title_preview_dir = utils.storage_dir("title_previews", create=True)
app.mount(
    "/title-preview-image", StaticFiles(directory=title_preview_dir), name="title-preview"
)

subtitle_preview_dir = utils.storage_dir("subtitle_previews", create=True)
app.mount(
    "/subtitle-preview-image", StaticFiles(directory=subtitle_preview_dir), name="subtitle-preview"
)

public_dir = utils.public_dir()
app.mount("/", StaticFiles(directory=public_dir, html=True), name="")


def _periodic_storage_cleanup():
    interval_hours = config.storage.get("storage_cleanup_interval_hours", 6)
    interval = interval_hours * 3600
    while True:
        time.sleep(interval)
        for fn in (
            utils.cleanup_stale_previews,
            utils.cleanup_stale_local_videos,
            utils.cleanup_stale_cache_videos,
            utils.cleanup_stale_cache_downscaled,
            utils.cleanup_stale_temp,
        ):
            try:
                fn()
            except Exception as e:
                logger.warning(f"Periodic storage cleanup failed for {fn.__name__}: {e}")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("shutdown event")
    locallens.stop_monitor()


@app.on_event("startup")
def startup_event():
    logger.info("startup event")
    logger.info(f"Static mount task_dir: {task_dir} (exists: {os.path.exists(task_dir)})")
    logger.info(f"Static mount public_dir: {public_dir} (exists: {os.path.exists(public_dir)})")
    locallens.start_monitor()
    utils.cleanup_stale_previews()
    utils.cleanup_stale_local_videos()
    utils.cleanup_stale_cache_videos()
    utils.cleanup_stale_cache_downscaled()
    utils.cleanup_stale_temp()
    t = threading.Thread(target=_periodic_storage_cleanup, daemon=True)
    t.start()
