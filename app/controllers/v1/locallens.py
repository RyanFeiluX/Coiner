from fastapi import Request
from loguru import logger

from app.config import config
from app.controllers.v1.base import new_router
from app.services import locallens
from app.utils import utils

router = new_router()


@router.get("/locallens/status", summary="Get LocalLens server status")
def get_locallens_status(request: Request):
    """Return server reachability, config and feature flags used by the UI
    to enable/disable the per-scene local-search toggles."""
    try:
        status = locallens.get_status()
        return utils.get_response(
            200,
            {
                "available": status["available"],
                "base_url": status["base_url"],
                "enabled": config.locallens.get("enabled", False),
                "last_probe_ts": status["last_probe_ts"],
                "probe_count": status["probe_count"],
                "last_latency_ms": status["last_latency_ms"],
            },
        )
    except Exception as e:
        logger.error(f"[LocalLens] failed to build status: {e}")
        return utils.get_response(500, {"error": str(e)})


@router.post("/locallens/probe", summary="Probe LocalLens server health")
def probe_locallens(request: Request):
    """Perform an immediate reachability probe and update availability state."""
    ok = locallens.force_probe()
    logger.info(f"[LocalLens] manual probe result: {ok}")
    return utils.get_response(200, {"available": ok})