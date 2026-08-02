"""
LocalLens external search API integration.

LocalLens runs a lightweight REST API on 127.0.0.1 (localhost-only) while the
desktop application is running. This module provides:
  - LocallensClient: thin HTTP client for /api/ping and /api/search.
  - Health monitoring: a background daemon thread periodically probes the
    server and tracks availability so the UI can gate local-search buttons.
"""
import threading
import time
from typing import Dict, List

import requests
from loguru import logger

from app.config import config
from app.models.schema import MaterialInfo

_PREFIX = "[LocalLens]"


def get_base_url() -> str:
    """Resolve the base URL (host + port) from config, defaulting to 127.0.0.1:8123."""
    host = (config.locallens.get("base_url", "http://127.0.0.1") or "http://127.0.0.1").rstrip("/")
    port = int(config.locallens.get("port", 8123))
    return f"{host}:{port}"


def get_timeout() -> float:
    return float(config.locallens.get("timeout_seconds", 3))


class LocallensClient:
    """Minimal HTTP client for the LocalLens REST API."""

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or get_base_url()).rstrip("/")

    def ping(self) -> bool:
        """Connectivity / health check. Returns True when reachable."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/ping",
                proxies=config.proxy,
                verify=False,
                timeout=get_timeout(),
            )
            ok = resp.status_code == 200
            if not ok:
                logger.debug(f"{_PREFIX} ping returned status {resp.status_code}")
            return ok
        except Exception as e:
            logger.debug(f"{_PREFIX} ping failed: {e}")
            return False

    def search(self, query: str, type_: str = "video", n: int = 10) -> List[Dict]:
        """Semantic search for local assets, constrained to a single asset type."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/search",
                params={"q": query, "type": type_, "n": n},
                proxies=config.proxy,
                verify=False,
                timeout=get_timeout(),
            )
            if resp.status_code != 200:
                logger.error(f"{_PREFIX} search failed (status {resp.status_code}): {resp.text[:200]}")
                return []
            data = resp.json()
            if not isinstance(data, list):
                logger.warning(f"{_PREFIX} search returned unexpected payload type={type(data)}")
                return []
            return data
        except Exception as exc:
            logger.error(f"{_PREFIX} search '{query}' failed: {exc}")
            return []


# ---------------------------------------------------------------------------
# Health monitoring
# ---------------------------------------------------------------------------

_state = {"available": False}
_lock = threading.Lock()
_client = LocallensClient()
_stop_event = threading.Event()
_monitor_thread = None


def is_available() -> bool:
    """Whether the LocalLens server is currently reachable."""
    with _lock:
        return _state["available"]


def set_available(flag: bool) -> None:
    """Manually set availability (used by force_probe and tests)."""
    with _lock:
        _state["available"] = bool(flag)


def force_probe() -> bool:
    """Perform a single immediate connectivity probe and update state."""
    ok = _client.ping()
    _update_from_probe(ok)
    return ok


def _update_from_probe(ok: bool) -> None:
    with _lock:
        changed = ok != _state["available"]
        if changed:
            if ok:
                logger.success(f"{_PREFIX} server connection restored ({_client.base_url})")
            else:
                logger.warning(f"{_PREFIX} server connection lost ({_client.base_url}), local search disabled")
        _state["available"] = ok


def _probe_loop(interval: float) -> None:
    # Probe immediately once, then loop on the interval.
    while not _stop_event.is_set():
        force_probe()
        _stop_event.wait(interval)


def start_monitor() -> None:
    """Start the background health-probe thread (idempotent)."""
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        return
    interval = float(config.locallens.get("probe_interval_seconds", 10))
    _stop_event.clear()
    _monitor_thread = threading.Thread(
        target=_probe_loop,
        args=(interval,),
        name="locallens-probe",
        daemon=True,
    )
    _monitor_thread.start()
    logger.info(f"{_PREFIX} monitoring started (interval={interval}s)")


def stop_monitor() -> None:
    """Stop the background health-probe thread (idempotent)."""
    global _monitor_thread
    if not _monitor_thread:
        return
    _stop_event.set()
    if _monitor_thread.is_alive():
        _monitor_thread.join(timeout=2)
    _monitor_thread = None
    logger.info(f"{_PREFIX} monitoring stopped")