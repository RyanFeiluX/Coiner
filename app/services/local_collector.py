"""
LocalLens collection orchestration.

Given a scene's keywords and the resources already used in the current task,
query the LocalLens server one keyword at a time and assemble a deduplicated,
ranked list of local video assets. Callers fall back to online search when the
collected count is below the required number.
"""
from typing import List, Optional, Set

from loguru import logger

from app.models.schema import MaterialInfo

_PREFIX = "[LocalLens]"


def collect_local_assets(client, keywords: List[str], used_paths: Optional[Set[str]], needed_count: int, max_per_keyword: int = 10) -> List[MaterialInfo]:
    """Collect up to `needed_count` unique local video assets.

    Each keyword is searched semantically (one request per keyword). Results are
    deduplicated by the content fingerprint id (falling back to path) and by the
    set of already-used paths so an asset already consumed earlier in the same
    task is skipped.

    Returns:
        List[MaterialInfo] ordered by relevance with url set to the asset path.
    """
    if used_paths is None:
        used_paths = set()
    if needed_count < 1:
        needed_count = 1

    collected: List[MaterialInfo] = []
    seen_ids: Set[str] = set()

    for kw in keywords:
        if len(collected) >= needed_count:
            break

        results = client.search(kw, type_="video", n=max(needed_count, max_per_keyword))
        logger.info(f"{_PREFIX} keyword '{kw}' returned {len(results)} results")

        for asset in results:
            if len(collected) >= needed_count:
                break

            path = asset.get("path")
            if not path:
                continue

            asset_id = asset.get("id") or path

            if asset_id in seen_ids:
                logger.debug(f"{_PREFIX} skip duplicate asset within scene: {path}")
                continue
            if path in used_paths:
                logger.info(f"{_PREFIX} skip already-used asset: {path}")
                continue

            seen_ids.add(asset_id)
            collected.append(MaterialInfo(provider="locallens", url=path))

    logger.info(f"{_PREFIX} collected {len(collected)}/{needed_count} local assets for {len(keywords)} keyword(s)")
    return collected