import json
import os
import time
from typing import List, Optional
from loguru import logger

from app.config import config
from app.models import const
from app.utils import utils


def scan_task_for_split(task_id_or_path: str, min_duration: float = 30, max_duration: float = 90) -> dict:
    """
    Scan a source task directory and return scene information with suggested segments.

    Args:
        task_id_or_path: Task ID or direct directory path
        min_duration: Minimum segment duration in seconds
        max_duration: Maximum segment duration in seconds

    Returns:
        Dictionary with scenes list, total duration, and suggested segments
    """
    from app.services.video_synthesis import scan_task_files

    if os.path.isdir(task_id_or_path):
        task_dir = task_id_or_path
        task_id = os.path.basename(task_dir)
    else:
        task_id = task_id_or_path
        task_dir = utils.task_dir(task_id)

    result = {
        "task_id": task_id,
        "task_dir": task_dir,
        "scenes": [],
        "total_duration": 0,
        "suggested_segments": [],
        "original_title_enabled": False,
    }

    if not os.path.exists(task_dir):
        logger.error(f"Task directory does not exist: {task_dir}")
        return result

    task_files = scan_task_files(task_id_or_path)
    if not task_files["is_valid"]:
        logger.warning(f"No valid scene videos found in {task_dir}")
        return result

    all_scenes = task_files["scene_videos"]

    # Read script.json for scene scripts
    script_path = os.path.join(task_dir, "script.json")
    script_scenes = []
    if os.path.exists(script_path):
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.loads(f.read())
            script_scenes = script_data.get("params", {}).get("scenes", [])
        except Exception as e:
            logger.warning(f"Failed to read script.json: {e}")

    total_duration = 0.0
    for scene_info in all_scenes:
        scene_num = scene_info["scene_num"]
        video_path = scene_info.get("video")
        duration = 0.0

        if video_path and os.path.exists(video_path):
            try:
                from moviepy import VideoFileClip
                clip = VideoFileClip(video_path)
                duration = clip.duration
                clip.close()
            except Exception as e:
                logger.warning(f"Failed to get duration for scene {scene_num}: {e}")

        # Get script preview from script.json
        script_preview = ""
        scene_index = scene_num - 1
        if scene_index < len(script_scenes):
            scene_script = script_scenes[scene_index].get("script", "")
            if scene_script:
                script_preview = scene_script[:80] + ("..." if len(scene_script) > 80 else "")

        total_duration += duration
        result["scenes"].append({
            "scene_num": scene_num,
            "duration": round(duration, 2),
            "video_path": video_path,
            "subtitle_path": scene_info.get("subtitle"),
            "script_preview": script_preview,
        })

    result["total_duration"] = round(total_duration, 2)
    result["suggested_segments"] = plan_segments(result["scenes"], min_duration, max_duration)

    # Auto-generate titles for segments if original task has title_enabled
    original_title_enabled = False
    original_language = None
    if os.path.exists(script_path):
        try:
            if not script_data:
                with open(script_path, "r", encoding="utf-8") as f:
                    script_data = json.loads(f.read())
            original_title_enabled = script_data.get("params", {}).get("title_enabled", False)
            original_language = script_data.get("params", {}).get("video_language")
        except Exception:
            pass

    result["original_title_enabled"] = original_title_enabled

    if original_title_enabled and result["suggested_segments"]:
        try:
            from app.services.scene_parser import generate_video_title
            for seg in result["suggested_segments"]:
                seg_script = seg.get("script_preview", "")
                if seg_script:
                    title = generate_video_title(seg_script, original_language)
                    seg["title"] = title
                else:
                    seg["title"] = ""
        except Exception as e:
            logger.warning(f"Failed to generate segment titles: {e}")

    return result


def plan_segments(scenes: list, min_duration: float, max_duration: float) -> list:
    """
    Plan segments using greedy grouping based on scene durations.

    Args:
        scenes: List of scene dicts with 'scene_num' and 'duration'
        min_duration: Minimum segment duration in seconds
        max_duration: Maximum segment duration in seconds

    Returns:
        List of segment dicts: [{scene_nums: [1,2,3], duration: 45.0, script_preview: "..."}]
    """
    if not scenes:
        return []

    segments = []
    current_scene_nums = []
    current_duration = 0.0
    current_scripts = []

    for scene in scenes:
        scene_num = scene["scene_num"]
        scene_duration = scene["duration"]
        scene_script = scene.get("script_preview", "")

        # Check if adding this scene would exceed max_duration
        if current_scene_nums and (current_duration + scene_duration) > max_duration:
            # Only finalize the current segment if we've met the minimum
            if current_duration >= min_duration:
                segments.append({
                    "scene_nums": current_scene_nums[:],
                    "duration": round(current_duration, 2),
                    "script_preview": " ".join(current_scripts),
                })
                current_scene_nums = []
                current_duration = 0.0
                current_scripts = []

        current_scene_nums.append(scene_num)
        current_duration += scene_duration
        if scene_script:
            current_scripts.append(scene_script)

    # Finalize the last segment
    if current_scene_nums:
        segments.append({
            "scene_nums": current_scene_nums[:],
            "duration": round(current_duration, 2),
            "script_preview": " ".join(current_scripts),
        })

    return segments


def execute_split(
    source_task_id_or_path: str,
    new_task_id: str,
    segments: list,
    min_duration: float = 30,
    max_duration: float = 90,
    subtitle_params: dict = None,
    bgm_params: dict = None,
    title_params: dict = None,
    video_enhance_params: dict = None,
    progress_callback=None,
    check_cancelled=None,
    task_create_time: float = None,
) -> Optional[str]:
    """
    Execute the video split operation.

    Creates short videos from the source task's scene videos based on the segment plan.

    Args:
        source_task_id_or_path: Source task ID or directory path
        new_task_id: New task ID for the split results
        segments: List of segment dicts with 'scene_nums' lists
        min_duration: Minimum segment duration (for reference)
        max_duration: Maximum segment duration (for reference)
        subtitle_params: Optional subtitle parameters override
        bgm_params: Optional BGM parameters
        title_params: Optional title parameters
        video_enhance_params: Optional video enhancement parameters
        progress_callback: Optional callback function(progress, message)
        check_cancelled: Optional callable that returns True if task should stop
        task_create_time: Optional task creation timestamp

    Returns:
        Path to the output directory, or None on failure
    """
    from app.services import state as sm
    from app.services.state import set_task_running, set_task_completed

    start_time = time.time()
    task_id = new_task_id

    # Resolve source task directory
    if os.path.isdir(source_task_id_or_path):
        source_task_dir = source_task_id_or_path
        source_task_id = os.path.basename(source_task_dir)
    else:
        source_task_id = source_task_id_or_path
        source_task_dir = utils.task_dir(source_task_id)

    # Create output directory
    output_dir = utils.task_dir(task_id)
    short_videos_dir = os.path.join(output_dir, "short_videos")
    os.makedirs(short_videos_dir, exist_ok=True)

    # Create log file
    log_path = os.path.join(output_dir, "split.log")
    log_handler_id = logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}\n",
        level="DEBUG",
        rotation="10 MB",
        compression="zip",
    )
    logger.info(f"Video split task log: {log_path}")

    # Register task in state
    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=0, task_type="video_split")
    set_task_running("video_split", task_id)

    # Save split config
    split_config = {
        "source_task_id": source_task_id,
        "segments": segments,
        "min_duration": min_duration,
        "max_duration": max_duration,
    }
    config_path = os.path.join(output_dir, "split_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(split_config, ensure_ascii=False, indent=2))

    # Save original task ID reference
    original_task_info_path = os.path.join(output_dir, "original_task_id.txt")
    with open(original_task_info_path, "w") as f:
        f.write(source_task_id)
    logger.info(f"Source task ID recorded: {source_task_id}")

    # Read original params from script.json for subtitle/BGM consistency
    script_path = os.path.join(source_task_dir, "script.json")
    original_params = {}
    if os.path.exists(script_path):
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.loads(f.read())
            original_params = script_data.get("params", {})
        except Exception:
            pass

    # Load config values
    _cfg = config.app
    video_config = config.video
    audio_config = config.audio
    subtitle_config = config.subtitle
    title_config = config.title

    # Merge subtitle params: provided > original > config defaults
    effective_subtitle = {
        "subtitle_enabled": True,
        "font_name": "STHeitiMedium.ttc",
        "font_size": 60,
        "text_fore_color": "white",
        "text_background_color": "transparent",
        "stroke_color": "black",
        "stroke_width": 2,
        "subtitle_position": "bottom",
        "custom_position": 70.0,
    }
    for key in effective_subtitle:
        if subtitle_params and key in subtitle_params and subtitle_params[key] is not None:
            effective_subtitle[key] = subtitle_params[key]
        elif key in original_params and original_params[key] is not None:
            effective_subtitle[key] = original_params[key]
        elif key == "font_name":
            effective_subtitle[key] = _cfg.get("font_name", subtitle_config.get("font_name", "STHeitiMedium.ttc"))
        elif key == "font_size":
            effective_subtitle[key] = int(_cfg.get("font_size", subtitle_config.get("font_size", 60)))
        elif key == "text_fore_color":
            effective_subtitle[key] = _cfg.get("text_fore_color", subtitle_config.get("text_fore_color", "white"))
        elif key == "stroke_color":
            effective_subtitle[key] = _cfg.get("stroke_color", subtitle_config.get("stroke_color", "black"))
        elif key == "stroke_width":
            effective_subtitle[key] = int(_cfg.get("stroke_width", subtitle_config.get("stroke_width", 2)))
        elif key == "subtitle_position":
            effective_subtitle[key] = _cfg.get("subtitle_position", subtitle_config.get("subtitle_position", "bottom"))
        elif key == "custom_position":
            effective_subtitle[key] = float(_cfg.get("custom_position", subtitle_config.get("custom_position", 70.0)))

    # Merge BGM params
    effective_bgm = {
        "bgm_type": "random",
        "bgm_file": "",
        "bgm_volume": 0.2,
    }
    if bgm_params:
        effective_bgm.update({k: v for k, v in bgm_params.items() if v is not None})
    else:
        effective_bgm["bgm_type"] = _cfg.get("bgm_type", audio_config.get("bgm_type", "random"))
        effective_bgm["bgm_volume"] = float(_cfg.get("bgm_volume", audio_config.get("bgm_volume", 0.2)))

    # Resolve BGM file
    audio_file = None
    bgm_type = effective_bgm.get("bgm_type", "random")
    bgm_file_param = effective_bgm.get("bgm_file", "")
    bgm_volume = float(effective_bgm.get("bgm_volume", 0.2))

    if bgm_type and bgm_type != "none":
        from app.services.video_utils import get_bgm_file
        bgm_file = get_bgm_file(bgm_type=bgm_type, bgm_file=bgm_file_param)
        if bgm_file and os.path.exists(bgm_file):
            logger.info(f"Using BGM: {bgm_file} (volume: {bgm_volume})")
            audio_file = bgm_file
        else:
            logger.info("No valid BGM file found")

    # Get silence duration
    from app.config.config import silence_duration as default_silence_duration
    config_silence_duration = default_silence_duration
    if video_enhance_params and "silence_duration" in video_enhance_params:
        config_silence_duration = video_enhance_params["silence_duration"]

    # Merge title params: provided > original > config defaults
    effective_title = {
        "title_enabled": False,
        "title_duration": 3.0,
        "title_font_name": "MicrosoftYaHeiBold.ttc",
        "title_font_size": 72,
        "title_text_color": "#FFFFFF",
        "title_stroke_color": "#000000",
        "title_stroke_width": 2.0,
        "title_background_color": "transparent",
        "title_position": "center",
        "title_margin": 0.05,
        "title_align": "center",
        "title_animation": "none",
        "title_animation_duration": 0.5,
        "title_background_overlay": False,
        "title_overlay_color": "rgba(0,0,0,0.5)",
        "title_margin_left": 0.05,
        "title_margin_right": 0.05,
    }
    for key in effective_title:
        if title_params and key in title_params and title_params[key] is not None:
            effective_title[key] = title_params[key]
        elif key in original_params and original_params[key] is not None:
            effective_title[key] = original_params[key]
        elif key in title_config:
            effective_title[key] = title_config[key]

    total_segments = len(segments)
    completed_segments = 0
    segment_results = []

    # Calculate duration-based progress weights (0-90%)
    total_duration = sum(seg.get("duration", 0) for seg in segments)
    if total_duration == 0:
        total_duration = total_segments  # fallback: equal weight per segment
    cumulative_duration = 0.0

    for seg_idx, segment in enumerate(segments):
        if check_cancelled and check_cancelled():
            logger.info("Task cancelled during split execution")
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, progress=0, status="cancelled")
            set_task_completed()
            return None

        scene_nums = segment["scene_nums"]
        segment_duration = segment.get("duration", 0)
        segment_weight = segment_duration / total_duration
        seg_base_progress = int((cumulative_duration / total_duration) * 90)
        logger.info(f"Processing segment {seg_idx + 1}/{total_segments}: scenes {scene_nums} ({segment_duration:.1f}s)")

        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_PROCESSING,
            progress=seg_base_progress,
            detail={
                "key": "SplitProgress_CollectingVideos",
                "seg_idx": seg_idx + 1,
                "total_segments": total_segments,
                "scene_start": scene_nums[0],
                "scene_end": scene_nums[-1],
                "duration": segment_duration,
            },
        )

        # Collect video paths for this segment
        video_paths = []
        scene_subtitle_results = []
        for scene_num in scene_nums:
            scene_video_path = os.path.join(source_task_dir, f"scene_{scene_num:02d}", "combined.mp4")
            if not os.path.exists(scene_video_path):
                # Try alternate naming
                scene_video_path = os.path.join(source_task_dir, f"scene_{scene_num}", "combined.mp4")
            if os.path.exists(scene_video_path):
                video_paths.append(scene_video_path)

                # Collect subtitle for this scene
                scene_sub_path = os.path.join(source_task_dir, f"scene_{scene_num:02d}", "subtitle.srt")
                if not os.path.exists(scene_sub_path):
                    scene_sub_path = os.path.join(source_task_dir, f"scene_{scene_num}", "subtitle.srt")
                if os.path.exists(scene_sub_path):
                    scene_subtitle_results.append({
                        "subtitle_path": scene_sub_path,
                        "combined_video_path": scene_video_path,
                    })

        if not video_paths:
            logger.warning(f"Segment {seg_idx + 1}: no video files found, skipping")
            continue

        # Build segment video using combine_all_scenes
        try:
            from app.services.task import combine_all_scenes
            from app.models.schema import VideoParams, VideoAspect, VideoConcatMode

            # Detect video aspect from first scene
            from app.services.video_utils import analyze_video_params
            video_params_info = analyze_video_params(video_paths[0])
            if video_params_info:
                width, height = video_params_info["width"], video_params_info["height"]
                gcd = __import__("math").gcd(width, height)
                aspect_ratio = f"{width // gcd}:{height // gcd}"
            else:
                aspect_ratio = video_config.get("video_aspect", "9:16")

            params = VideoParams(
                video_subject="Video Split",
                video_aspect=VideoAspect(aspect_ratio),
                video_concat_mode=VideoConcatMode(video_config.get("video_concat_mode", "random")),
                subtitle_enabled=effective_subtitle.get("subtitle_enabled", True),
                font_name=effective_subtitle.get("font_name", "STHeitiMedium.ttc"),
                font_size=effective_subtitle.get("font_size", 60),
                text_fore_color=effective_subtitle.get("text_fore_color", "white"),
                text_background_color=effective_subtitle.get("text_background_color", "transparent"),
                stroke_color=effective_subtitle.get("stroke_color", "black"),
                stroke_width=effective_subtitle.get("stroke_width", 2),
                subtitle_position=effective_subtitle.get("subtitle_position", "bottom"),
                custom_position=effective_subtitle.get("custom_position", 70.0),
                bgm_type=effective_bgm.get("bgm_type", "random"),
                bgm_file=effective_bgm.get("bgm_file", ""),
                bgm_volume=float(effective_bgm.get("bgm_volume", 0.2)),
                output_bg_color=video_enhance_params.get("output_bg_color", "black") if video_enhance_params else "black",
                title_enabled=effective_title.get("title_enabled", False),
                title_text=segment.get("title", ""),
                title_duration=effective_title.get("title_duration", 3.0),
                title_font_name=effective_title.get("title_font_name", "MicrosoftYaHeiBold.ttc"),
                title_font_size=effective_title.get("title_font_size", 72),
                title_text_color=effective_title.get("title_text_color", "#FFFFFF"),
                title_stroke_color=effective_title.get("title_stroke_color", "#000000"),
                title_stroke_width=effective_title.get("title_stroke_width", 2.0),
                title_background_color=effective_title.get("title_background_color", "transparent"),
                title_position=effective_title.get("title_position", "center"),
                title_margin=effective_title.get("title_margin", 0.05),
                title_align=effective_title.get("title_align", "center"),
                title_animation=effective_title.get("title_animation", "none"),
                title_animation_duration=effective_title.get("title_animation_duration", 0.5),
                title_background_overlay=effective_title.get("title_background_overlay", False),
                title_overlay_color=effective_title.get("title_overlay_color", "rgba(0,0,0,0.5)"),
                title_margin_left=effective_title.get("title_margin_left", 0.05),
                title_margin_right=effective_title.get("title_margin_right", 0.05),
            )

            scene_results = [{"combined_video_path": vp} for vp in video_paths]

            # Combine scene videos (0%~40% of this segment's weight)
            sm.state.update_task(
                task_id,
                state=const.TASK_STATE_PROCESSING,
                progress=seg_base_progress + int(segment_weight * 0.05 * 90),
                detail={
                    "key": "SplitProgress_CombiningScenes",
                    "seg_idx": seg_idx + 1,
                    "total_segments": total_segments,
                    "scene_start": scene_nums[0],
                    "scene_end": scene_nums[-1],
                    "duration": segment_duration,
                },
            )
            combined_video_path = os.path.join(short_videos_dir, f"temp_segment_{seg_idx + 1}.mp4")
            combined_video_path, _segment_duration = combine_all_scenes(
                task_id=task_id,
                params=params,
                scene_results=scene_results,
            )

            if not combined_video_path or not os.path.exists(combined_video_path):
                logger.warning(f"Segment {seg_idx + 1}: failed to combine scenes, skipping")
                continue

            # Merge subtitles for this segment (40%~50% of this segment's weight)
            merged_subtitle = None
            if scene_subtitle_results:
                sm.state.update_task(
                    task_id,
                    state=const.TASK_STATE_PROCESSING,
                    progress=seg_base_progress + int(segment_weight * 0.45 * 90),
                    detail={
                        "key": "SplitProgress_MergingSubtitles",
                        "seg_idx": seg_idx + 1,
                        "total_segments": total_segments,
                        "scene_start": scene_nums[0],
                        "scene_end": scene_nums[-1],
                        "duration": segment_duration,
                    },
                )
                try:
                    from app.services.subtitle import merge_scene_subtitles
                    merged_subtitle = merge_scene_subtitles(
                        task_id,
                        scene_subtitle_results,
                        silence_duration=config_silence_duration,
                    )
                except Exception as e:
                    logger.warning(f"Segment {seg_idx + 1}: subtitle merge failed: {e}")

            # Process final video (BGM, title, subtitles, encoding) (50%~100% of this segment's weight)
            from app.services.video_target import process_final_video
            output_path = os.path.join(short_videos_dir, f"segment_{seg_idx + 1}.mp4")

            def _segment_progress_callback(sub_progress, sub_message):
                """Map process_final_video's 0-100 progress to this segment's weight."""
                mapped = seg_base_progress + int(segment_weight * (0.50 + sub_progress / 100 * 0.50) * 90)
                # Map sub_message to translation key
                if "encoding" in sub_message.lower() or "writing" in sub_message.lower():
                    detail_key = "SplitProgress_Encoding"
                elif "subtitle" in sub_message.lower():
                    detail_key = "SplitProgress_BurningSubtitles"
                elif "bgm" in sub_message.lower() or "audio" in sub_message.lower():
                    detail_key = "SplitProgress_AddingBGM"
                elif "title" in sub_message.lower():
                    detail_key = "SplitProgress_AddingTitle"
                else:
                    detail_key = "SplitProgress_ProcessingVideo"
                sm.state.update_task(
                    task_id,
                    state=const.TASK_STATE_PROCESSING,
                    progress=mapped,
                    detail={
                        "key": detail_key,
                        "seg_idx": seg_idx + 1,
                        "total_segments": total_segments,
                        "scene_start": scene_nums[0],
                        "scene_end": scene_nums[-1],
                        "duration": segment_duration,
                    },
                )

            final_path = process_final_video(
                task_id=task_id,
                params=params,
                scene_results=scene_results,
                combined_video_path=combined_video_path,
                subtitle_file=merged_subtitle,
                audio_file=audio_file,
                output_file=output_path,
                progress_callback=_segment_progress_callback,
                task_create_time=task_create_time,
                task_start_time=start_time,
                skip_subtitles=False if merged_subtitle else True,
                silence_duration=config_silence_duration,
            )

            if final_path and os.path.exists(final_path):
                logger.success(f"Segment {seg_idx + 1} completed: {final_path}")
                segment_results.append({
                    "segment_index": seg_idx + 1,
                    "scene_nums": scene_nums,
                    "duration": round(segment_duration, 2),
                    "output_path": final_path,
                })
                completed_segments += 1
            else:
                logger.warning(f"Segment {seg_idx + 1}: final video generation failed")

            cumulative_duration += segment_duration

            # Cleanup temp combined file
            temp_combined = os.path.join(short_videos_dir, f"temp_segment_{seg_idx + 1}.mp4")
            if os.path.exists(temp_combined):
                try:
                    os.remove(temp_combined)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Segment {seg_idx + 1}: processing failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    # Save results to split_config.json
    split_config["results"] = segment_results
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(split_config, ensure_ascii=False, indent=2))

    # Collect output video paths for task state
    output_videos = [r["output_path"] for r in segment_results]

    # Update task progress to 100%
    sm.state.update_task(
        task_id,
        state=const.TASK_STATE_COMPLETE,
        progress=100,
        detail={
            "key": "SplitProgress_Completed",
            "completed_segments": completed_segments,
            "total_segments": total_segments,
        },
        videos=output_videos,
        original_task_id=source_task_id,
    )

    set_task_completed()

    # Log duration
    end_time = time.time()
    total_time = end_time - start_time
    hours, remainder = divmod(total_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    logger.success(f"Video split completed: {completed_segments}/{total_segments} segments")
    logger.info(f"Task duration: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")

    # Remove log handler
    try:
        logger.remove(log_handler_id)
    except Exception:
        pass

    return output_dir
