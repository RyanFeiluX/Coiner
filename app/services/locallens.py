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
        """Connectivity / health check. Returns True when reachable.

        Intentionally silent (no logging): all probe logging is centralized in
        ``force_probe()`` to avoid per-cycle debug/warning spam.
        """
        try:
            resp = requests.get(
                f"{self.base_url}/api/ping",
                proxies=config.proxy,
                verify=False,
                timeout=get_timeout(),
            )
        except Exception:
            return False
        return resp.status_code == 200

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

_state = {
    "available": False,
    "last_probe_ts": 0.0,
    "probe_count": 0,
    "last_latency_ms": 0.0,
    "state_log_ts": 0.0,
}
_lock = threading.Lock()
_client = LocallensClient()
_stop_event = threading.Event()
_monitor_thread = None


def get_heartbeat_interval() -> float:
    return float(config.locallens.get("probe_heartbeat_interval_seconds", 60))


def is_available() -> bool:
    """Whether the LocalLens server is currently reachable."""
    with _lock:
        return _state["available"]


def set_available(flag: bool) -> None:
    """Manually set availability (used by force_probe and tests)."""
    with _lock:
        _state["available"] = bool(flag)


def get_status() -> dict:
    """Diagnostic summary of the latest probe, useful for the UI / troubleshooting."""
    with _lock:
        return {
            "available": _state["available"],
            "base_url": get_base_url(),
            "last_probe_ts": _state["last_probe_ts"],
            "probe_count": _state["probe_count"],
            "last_latency_ms": _state["last_latency_ms"],
        }


def force_probe() -> bool:
    """Perform a single immediate connectivity probe, update state and log at the
    right level.

    Logging policy (suppresses per-cycle spam):
      - first probe            : info (or warning if it fails immediately)
      - state change           : info when restored, warning when lost
      - steady state           : heartbeat every ``probe_heartbeat_interval_seconds``
                                 (info when ok, warning when failed)
    """
    start = time.monotonic()
    ok = _client.ping()
    latency_ms = (time.monotonic() - start) * 1000

    with _lock:
        _state["probe_count"] += 1
        _state["last_probe_ts"] = time.time()
        _state["last_latency_ms"] = latency_ms
        changed = ok != _state["available"]
        _state["available"] = ok

    is_first = _state["probe_count"] == 1
    level, message = _decide_probe_log(
        ok=ok,
        is_first=is_first,
        changed=changed,
        last_log_ts=_state["state_log_ts"],
        heartbeat_interval=get_heartbeat_interval(),
        probe_count=_state["probe_count"],
        latency_ms=_state["last_latency_ms"],
        base_url=get_base_url(),
        now=time.time(),
    )
    if level is not None:
        _emit(level, message)
        _mark_logged()
    return ok


def _decide_probe_log(ok, is_first, changed, last_log_ts, heartbeat_interval, probe_count, latency_ms, base_url, now):
    """Pure logging decision. Returns ``(level, message)`` or ``(None, '')`` to skip.

    - first probe:            log always (info/warning)
    - state change:           log (info when restored, warning when lost)
    - steady state:           throttle a heartbeat to ``heartbeat_interval`` seconds
    """
    if is_first:
        if ok:
            return "info", f"{_PREFIX} initial probe ok, local search available ({base_url})"
        return "warning", f"{_PREFIX} initial probe failed ({base_url}), local search disabled"

    if changed:
        if ok:
            return "info", f"{_PREFIX} local search server restored ({base_url})"
        return "warning", f"{_PREFIX} local search server lost ({base_url}), probing continues"

    if now - last_log_ts >= heartbeat_interval:
        state = "ok" if ok else "fail"
        msg = (
            f"{_PREFIX} watchdog alive, state={state}, "
            f"probe #{probe_count}, latency={latency_ms:.1f}ms ({base_url})"
        )
        return ("info" if ok else "warning"), msg

    return None, ""


def _emit(level: str, message: str) -> None:
    if level == "warning":
        logger.warning(message)
    elif level == "success":
        logger.success(message)
    else:
        logger.info(message)


def _mark_logged() -> None:
    with _lock:
        _state["state_log_ts"] = time.time()


def _probe_loop(interval: float) -> None:
    # Probe immediately once, then loop on the interval (watchdog style).
    while not _stop_event.is_set():
        force_probe()
        _stop_event.wait(interval)


def start_monitor() -> None:
    """Start the background health-probe thread (idempotent).

    Performs an immediate synchronous probe first so availability is correct at
    startup, then runs periodic watchdog probes on the configured interval.
    """
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        return
    interval = float(config.locallens.get("probe_interval_seconds", 10))
    _stop_event.clear()
    # Immediate synchronous probe (watchdog initial check).
    ok = force_probe()
    logger.info(f"{_PREFIX} app startup probe -> available={ok} ({get_base_url()})")
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