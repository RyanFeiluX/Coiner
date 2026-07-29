import os
from typing import Any, Dict, List


def _file_is_valid(path: Any) -> bool:
    """Check if a file path is a non-empty string pointing to an existing non-empty file."""
    if not path or not isinstance(path, str):
        return False
    return os.path.exists(path) and os.path.getsize(path) > 0


def verify_scene_results(
    scenes: List[Dict[str, Any]],
    scene_results: List[Dict[str, Any]],
    stop_at: str = None,
) -> Dict[str, Any]:
    """
    Verify that generated scene artifacts actually exist on disk.

    Args:
        scenes: Expected scene list (used for count and ordering).
        scene_results: Scene result dicts returned by process_scene.
        stop_at: Optional early-stop stage. When set, only artifacts up to that
                 stage are validated (e.g. 'audio' only checks audio files).

    Returns:
        {
            "valid_scene_indices": [0, 1, ...],
            "invalid_scenes": [
                {"scene_index": 3, "reason": "missing_video", "path": "..."},
                ...
            ],
            "summary": "3/5 scenes valid",
            "is_fully_valid": False,
        }
    """
    total_scenes = len(scenes)
    valid_scene_indices = []
    invalid_scenes = []

    # Normalize stop_at to lower case for robust comparison
    stop_stage = (stop_at or "").lower()

    # Stages before scene processing do not produce per-scene artifacts
    if stop_stage in ("script", "terms"):
        return {
            "valid_scene_indices": list(range(total_scenes)),
            "invalid_scenes": [],
            "summary": f"{total_scenes}/{total_scenes} scenes valid (stop_at={stop_at})",
            "is_fully_valid": total_scenes > 0,
        }

    for expected_index, scene in enumerate(scenes):
        scene_index = scene.get("scene_index", expected_index)
        result = next(
            (r for r in scene_results if r and r.get("scene_index") == scene_index),
            None,
        )

        if not result:
            invalid_scenes.append(
                {
                    "scene_index": scene_index,
                    "reason": "missing_result",
                    "path": None,
                }
            )
            continue

        scene_valid = True

        # Audio is required for audio stage and beyond
        if stop_stage in ("", "audio", "subtitle", "materials", "video"):
            if not _file_is_valid(result.get("audio_file")):
                invalid_scenes.append(
                    {
                        "scene_index": scene_index,
                        "reason": "missing_audio",
                        "path": result.get("audio_file"),
                    }
                )
                scene_valid = False

        # Subtitle is required for subtitle stage and beyond
        if scene_valid and stop_stage in ("", "subtitle", "materials", "video"):
            if not _file_is_valid(result.get("subtitle_path")):
                invalid_scenes.append(
                    {
                        "scene_index": scene_index,
                        "reason": "missing_subtitle",
                        "path": result.get("subtitle_path"),
                    }
                )
                scene_valid = False

        # Combined video is required for materials stage (per-scene video materials)
        # and the final video stage
        if scene_valid and stop_stage in ("", "materials", "video"):
            if not _file_is_valid(result.get("combined_video_path")):
                invalid_scenes.append(
                    {
                        "scene_index": scene_index,
                        "reason": "missing_video",
                        "path": result.get("combined_video_path"),
                    }
                )
                scene_valid = False

        if scene_valid:
            valid_scene_indices.append(scene_index)

    is_fully_valid = len(valid_scene_indices) == total_scenes and total_scenes > 0
    summary = f"{len(valid_scene_indices)}/{total_scenes} scenes valid"

    return {
        "valid_scene_indices": valid_scene_indices,
        "invalid_scenes": invalid_scenes,
        "summary": summary,
        "is_fully_valid": is_fully_valid,
    }
