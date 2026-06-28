import glob
import os
import pathlib
import shutil
from typing import Union

from fastapi import BackgroundTasks, Depends, Path, Request, UploadFile
from fastapi.params import File
from fastapi.responses import FileResponse, StreamingResponse
from loguru import logger

from app.config import config
from app.controllers import base
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models import const
from app.models.schema import (
    AudioRequest,
    BgmRetrieveResponse,
    BgmUploadResponse,
    SubtitleRequest,
    TaskDeletionResponse,
    TaskQueryRequest,
    TaskQueryResponse,
    TaskResponse,
    TaskVideoRequest,
    VideoMaterialUploadResponse,
    VideoMaterialRetrieveResponse
)
from app.services import state as sm
from app.services import task as tm
from app.utils import utils

# 认证依赖项
# router = new_router(dependencies=[Depends(base.verify_token)])
router = new_router()


@router.post("/videos", response_model=TaskResponse, summary="Generate a short video")
def create_video(
    background_tasks: BackgroundTasks, request: Request, body: TaskVideoRequest
):
    return create_task(request, body, stop_at="video")


@router.post("/subtitle", response_model=TaskResponse, summary="Generate subtitle only")
def create_subtitle(
    background_tasks: BackgroundTasks, request: Request, body: SubtitleRequest
):
    return create_task(request, body, stop_at="subtitle")


@router.post("/audio", response_model=TaskResponse, summary="Generate audio only")
def create_audio(
    background_tasks: BackgroundTasks, request: Request, body: AudioRequest
):
    return create_task(request, body, stop_at="audio")


def create_task(
    request: Request,
    body: Union[TaskVideoRequest, SubtitleRequest, AudioRequest],
    stop_at: str,
):
    import time as _time
    task_create_time = _time.time()
    task_id = utils.get_uuid()
    request_id = base.get_task_id(request)
    
    # Task will be queued if another task is running (handled by thread_manager)
    try:
        task = {
            "task_id": task_id,
            "request_id": request_id,
            "params": body.model_dump(),
        }
        
        # Debug: Check what voice_name is being received
        if hasattr(body, 'voice_name'):
            logger.debug(f"[Task Creation] voice_name received: {body.voice_name[:100]}...")
            logger.debug(f"[Task Creation] voice_name starts with 'coze|': {body.voice_name.startswith('coze|')}")
        
        # Debug: Check host_visible
        if hasattr(body, 'host_visible'):
            logger.debug(f"[Task Creation] host_visible received: {body.host_visible}")
            logger.debug(f"[Task Creation] host_visible type: {type(body.host_visible)}")
        
        sm.state.update_task(task_id, state=const.TASK_STATE_PENDING, progress=0, task_type="video_generation")
        logger.debug(f"video_controller: Calling start_async for task_id={task_id}, thread_manager_id={id(tm)}")
        _, queue_status = tm.start_async(task_id, body, stop_at, task_create_time=task_create_time)
        
        # Get the task with task_type from state
        created_task = sm.state.get_task(task_id)
        
        # Provide appropriate message based on queue status
        if queue_status == "queued":
            message = "Parallel running task capacity used up and your task will be queued for next slot"
            logger.info(f"Task {task_id} queued: {message}")
        else:
            message = "success"
            logger.success(f"Task created: {utils.to_json(created_task)}")
        
        return utils.get_response(200, created_task, message=message)
    except ValueError as e:
        raise HttpException(
            task_id=task_id, status_code=400, message=f"{request_id}: {str(e)}"
        )

from fastapi import Query

@router.get("/tasks", response_model=TaskQueryResponse, summary="Get all tasks")
def get_all_tasks(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1)):
    request_id = base.get_task_id(request)
    tasks, total = sm.state.get_all_tasks(page, page_size)
    
    endpoint = config.app.get("endpoint", "")
    if not endpoint:
        endpoint = str(request.base_url)
    endpoint = endpoint.rstrip("/")
    task_dir = utils.task_dir()
    
    def file_to_uri(file):
        if not file.startswith(endpoint):
            _uri_path = file.replace(task_dir, "tasks").replace("\\", "/")
            _uri_path = f"{endpoint}/{_uri_path}"
        else:
            _uri_path = file
        return _uri_path
    
    def convert_task(task):
        status_map = {
            const.TASK_STATE_FAILED: "failed",
            const.TASK_STATE_PENDING: "pending",
            const.TASK_STATE_COMPLETE: "completed",
            const.TASK_STATE_CANCELLING: "cancelling",
            const.TASK_STATE_PROCESSING: "running"
        }
        if "state" in task:
            task["status"] = status_map.get(task["state"], "pending")
            del task["state"]
        
        if "videos" in task and task["videos"]:
            videos = task["videos"]
            urls = []
            for v in videos:
                urls.append(file_to_uri(v))
            task["videos"] = urls
        if "combined_videos" in task and task["combined_videos"]:
            combined_videos = task["combined_videos"]
            urls = []
            for v in combined_videos:
                urls.append(file_to_uri(v))
            task["combined_videos"] = urls
        return task
    
    converted_tasks = [convert_task(task) for task in tasks]

    response = {
        "tasks": converted_tasks,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return utils.get_response(200, response)



@router.get(
    "/tasks/{task_id}", response_model=TaskQueryResponse, summary="Query task status"
)
def get_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
    query: TaskQueryRequest = Depends(),
):
    endpoint = config.app.get("endpoint", "")
    if not endpoint:
        endpoint = str(request.base_url)
    endpoint = endpoint.rstrip("/")

    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if task:
        # Convert numeric status to string status
        status_map = {
            const.TASK_STATE_FAILED: "failed",
            const.TASK_STATE_PENDING: "pending",
            const.TASK_STATE_COMPLETE: "completed",
            const.TASK_STATE_CANCELLING: "cancelling",
            const.TASK_STATE_PROCESSING: "running"
        }
        if "state" in task:
            task["status"] = status_map.get(task["state"], "pending")
            del task["state"]
        
        task_dir = utils.task_dir()

        def file_to_uri(file):
            if not file.startswith(endpoint):
                _uri_path = file.replace(task_dir, "tasks").replace("\\", "/")
                _uri_path = f"{endpoint}/{_uri_path}"
            else:
                _uri_path = file
            return _uri_path

        if "videos" in task:
            videos = task["videos"]
            urls = []
            for v in videos:
                urls.append(file_to_uri(v))
            task["videos"] = urls
        if "combined_videos" in task:
            combined_videos = task["combined_videos"]
            urls = []
            for v in combined_videos:
                urls.append(file_to_uri(v))
            task["combined_videos"] = urls
        return utils.get_response(200, task)

    raise HttpException(
        task_id=task_id, status_code=404, message=f"{request_id}: task not found"
    )


@router.delete(
    "/tasks/{task_id}",
    response_model=TaskDeletionResponse,
    summary="Delete a generated short video task",
)
def delete_video(request: Request, task_id: str = Path(..., description="Task ID")):
    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if task:
        tasks_dir = utils.task_dir()
        current_task_dir = os.path.join(tasks_dir, task_id)
        if os.path.exists(current_task_dir):
            shutil.rmtree(current_task_dir)

        # 删除任务的日志
        from app.services.log_service import log_service
        log_service.clear_task_logs(task_id)

        sm.state.delete_task(task_id)
        logger.success(f"video deleted: {utils.to_json(task)}")
        return utils.get_response(200)

    raise HttpException(
        task_id=task_id, status_code=404, message=f"{request_id}: task not found"
    )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskDeletionResponse,
    summary="Cancel a running task",
)
def cancel_task(request: Request, task_id: str = Path(..., description="Task ID")):
    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if task:
        # 这里需要调用 thread_manager.cancel_task 来取消任务
        # 但是我们需要确保 thread_manager 能够访问到
        from app.services.thread_manager import thread_manager
        thread_manager.cancel_task(task_id)
        
        # 更新任务状态为 cancelling（线程实际退出时由 _run_task 更新为 cancelled）
        sm.state.update_task(task_id, const.TASK_STATE_CANCELLING, **{"status": "cancelling"})
        
        logger.success(f"Task cancelled: {task_id}")
        return utils.get_response(200)

    raise HttpException(
        task_id=task_id, status_code=404, message=f"{request_id}: task not found"
    )


@router.get(
    "/musics", response_model=BgmRetrieveResponse, summary="Retrieve local BGM files"
)
def get_bgm_list(request: Request):
    suffix = "*.mp3"
    song_dir = utils.song_dir()
    files = glob.glob(os.path.join(song_dir, suffix))
    bgm_list = []
    for file in files:
        bgm_list.append(
            {
                "name": os.path.basename(file),
                "size": os.path.getsize(file),
                "file": file,
            }
        )
    response = {"files": bgm_list}
    return utils.get_response(200, response)


@router.post(
    "/musics",
    response_model=BgmUploadResponse,
    summary="Upload the BGM file to the songs directory",
)
def upload_bgm_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    # check file ext
    if file.filename.endswith("mp3"):
        song_dir = utils.song_dir()
        save_path = os.path.join(song_dir, file.filename)
        # save file
        with open(save_path, "wb+") as buffer:
            # If the file already exists, it will be overwritten
            file.file.seek(0)
            buffer.write(file.file.read())
        response = {"file": save_path}
        return utils.get_response(200, response)

    raise HttpException(
        "", status_code=400, message=f"{request_id}: Only *.mp3 files can be uploaded"
    )

@router.get(
    "/video_materials", response_model=VideoMaterialRetrieveResponse, summary="Retrieve local video materials"
)
def get_video_materials_list(request: Request):
    allowed_suffixes = ("mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png")
    local_videos_dir = utils.storage_dir("local_videos", create=True)
    files = []
    for suffix in allowed_suffixes:
        files.extend(glob.glob(os.path.join(local_videos_dir, f"*.{suffix}")))
    video_materials_list = []
    for file in files:
        video_materials_list.append(
            {
                "name": os.path.basename(file),
                "size": os.path.getsize(file),
                "file": file,
            }
        )
    response = {"files": video_materials_list}
    return utils.get_response(200, response)


@router.post(
    "/video_materials",
    response_model=VideoMaterialUploadResponse,
    summary="Upload the video material file to the local videos directory",
)
def upload_video_material_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    # check file ext
    allowed_suffixes = ("mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png", "gif")
    if file.filename.endswith(allowed_suffixes):
        local_videos_dir = utils.storage_dir("local_videos", create=True)
        save_path = os.path.join(local_videos_dir, file.filename)
        # save file
        with open(save_path, "wb+") as buffer:
            # If the file already exists, it will be overwritten
            file.file.seek(0)
            buffer.write(file.file.read())
        response = {"file": save_path}
        return utils.get_response(200, response)

    raise HttpException(
        "", status_code=400, message=f"{request_id}: Only files with extensions {', '.join(allowed_suffixes)} can be uploaded"
    )


@router.post(
    "/intro-video/{task_id}",
    response_model=VideoMaterialUploadResponse,
    summary="Upload intro video to task-specific intro_videos directory",
)
def upload_intro_video(request: Request, task_id: str, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    # check file ext
    allowed_suffixes = ("mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png", "gif")
    if file.filename.endswith(allowed_suffixes):
        # Create task-specific intro_videos directory at storage root
        task_intro_videos_dir = utils.storage_dir("intro_videos", create=True)
        task_intro_videos_dir = os.path.join(task_intro_videos_dir, task_id)
        if not os.path.exists(task_intro_videos_dir):
            os.makedirs(task_intro_videos_dir)
        
        save_path = os.path.join(task_intro_videos_dir, file.filename)
        # save file
        with open(save_path, "wb+") as buffer:
            # If the file already exists, it will be overwritten
            file.file.seek(0)
            buffer.write(file.file.read())
        response = {"file": save_path}
        return utils.get_response(200, response)

    raise HttpException(
        "", status_code=400, message=f"{request_id}: Only files with extensions {', '.join(allowed_suffixes)} can be uploaded"
    )

@router.get("/stream/{file_path:path}")
async def stream_video(request: Request, file_path: str):
    tasks_dir = utils.task_dir()
    video_path = os.path.join(tasks_dir, file_path)
    range_header = request.headers.get("Range")
    video_size = os.path.getsize(video_path)
    start, end = 0, video_size - 1

    length = video_size
    if range_header:
        range_ = range_header.split("bytes=")[1]
        start, end = [int(part) if part else None for part in range_.split("-")]
        if start is None:
            start = video_size - end
            end = video_size - 1
        if end is None:
            end = video_size - 1
        length = end - start + 1

    def file_iterator(file_path, offset=0, bytes_to_read=None):
        with open(file_path, "rb") as f:
            f.seek(offset, os.SEEK_SET)
            remaining = bytes_to_read or video_size
            while remaining > 0:
                bytes_to_read = min(4096, remaining)
                data = f.read(bytes_to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = StreamingResponse(
        file_iterator(video_path, start, length), media_type="video/mp4"
    )
    response.headers["Content-Range"] = f"bytes {start}-{end}/{video_size}"
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(length)
    response.status_code = 206  # Partial Content

    return response


@router.get("/download/{file_path:path}")
async def download_video(_: Request, file_path: str):
    """
    download video
    :param _: Request request
    :param file_path: video file path, eg: /cd1727ed-3473-42a2-a7da-4faafafec72b/final-1.mp4
    :return: video file
    """
    tasks_dir = utils.task_dir()
    video_path = os.path.join(tasks_dir, file_path)
    file_path = pathlib.Path(video_path)
    filename = file_path.stem
    extension = file_path.suffix
    headers = {"Content-Disposition": f"attachment; filename={filename}{extension}"}
    return FileResponse(
        path=video_path,
        headers=headers,
        filename=f"{filename}{extension}",
        media_type=f"video/{extension[1:]}",
    )


@router.get("/title-styles", summary="Get available title styles")
def get_title_styles(request: Request):
    from app.services.title import get_available_title_styles
    
    styles = get_available_title_styles()
    return utils.get_response(200, styles)


@router.post("/title-preview", summary="Preview title style")
def preview_title(request: Request, body: dict):
    from app.services.title import create_title_clip, _get_valid_font_path
    from app.models.schema import VideoParams
    from loguru import logger
    from moviepy import ColorClip, CompositeVideoClip
    
    params = VideoParams()
    params.title_enabled = body.get('title_enabled', True)
    params.title_text = body.get('title_text', 'Preview Title')
    params.title_font_name = body.get('title_font_name', 'MicrosoftYaHeiBold.ttc')
    params.title_font_size = body.get('title_font_size', 72)
    params.title_text_color = body.get('title_text_color', '#FFFFFF')
    params.title_stroke_color = body.get('title_stroke_color', '#000000')
    params.title_stroke_width = body.get('title_stroke_width', 2.0)
    params.title_background_color = body.get('title_background_color', 'transparent')
    params.title_position = body.get('title_position', 'center')
    params.title_margin = body.get('title_margin', 0.05)
    params.title_margin_left = body.get('title_margin_left', 0.05)
    params.title_margin_right = body.get('title_margin_right', 0.05)
    params.title_align = body.get('title_align', 'center')
    params.title_animation = body.get('title_animation', 'none')
    params.title_animation_duration = body.get('title_animation_duration', 0.5)
    
    logger.info(f"Title preview request - text: '{params.title_text}', font: '{params.title_font_name}'")
    
    font_path = _get_valid_font_path(params.title_font_name)
    logger.info(f"Resolved font path: '{font_path}', exists: {os.path.exists(font_path)}")
    logger.info(f"Font directory: '{utils.font_dir()}'")
    logger.info(f"Available fonts: {os.listdir(utils.font_dir())}")
    
    video_aspect = body.get('video_aspect', '9:16')
    aspect_map = {
        'portrait': '9:16', 'portrait_9_16': '9:16',
        'landscape': '16:9', 'landscape_16_9': '16:9',
        'square': '1:1', 'portrait_3_4': '3:4',
        '1:1': '1:1', '9:16': '9:16', '16:9': '16:9', '3:4': '3:4',
    }
    normalized = aspect_map.get(video_aspect, '9:16')
    if normalized == '9:16':
        width, height = 1080, 1920
    elif normalized == '16:9':
        width, height = 1920, 1080
    elif normalized == '1:1':
        width, height = 1080, 1080
    elif normalized == '3:4':
        width, height = 1080, 1920
    else:
        width, height = 1080, 1920
    
    title_clip = create_title_clip(width, height, params)
    
    if title_clip is None:
        raise HttpException(task_id="", status_code=400, message="Failed to create title clip")
    
    preview_dir = utils.storage_dir("title_previews", create=True)
    preview_name = f"title_preview_{utils.get_uuid()[:8]}.png"
    preview_path = os.path.join(preview_dir, preview_name)
    
    # Render title on full video frame so preview image matches video proportions
    duration = getattr(title_clip, 'duration', None) or 5.0
    if normalized == '3:4':
        # Show pillarbox bars visually: content area (1440px) in gray, bars in dark gray
        content_h = 1440
        pad_h = (height - content_h) // 2  # 240
        content_bg = ColorClip(size=(width, content_h), color=(80, 80, 80), duration=duration)
        bar = ColorClip(size=(width, pad_h), color=(20, 20, 20), duration=duration)
        bg = CompositeVideoClip([
            content_bg.with_position((0, pad_h)),
            bar.with_position((0, 0)),
            bar.with_position((0, height - pad_h)),
        ], size=(width, height))
    else:
        bg = ColorClip(size=(width, height), color=(80, 80, 80), duration=duration)
    composite = CompositeVideoClip([bg, title_clip], size=(width, height))
    composite.save_frame(preview_path, t=1.0)
    
    logger.info(f"Title preview saved to: {preview_path}")
    
    response = {"preview_path": f"/title-preview-image/{preview_name}"}
    return utils.get_response(200, response)


@router.post("/subtitle-preview", summary="Preview subtitle style")
def preview_subtitle(request: Request, body: dict):
    from app.services.title import _get_valid_font_path
    from app.services.video_utils import wrap_text, parse_color
    from loguru import logger
    from moviepy import ColorClip, CompositeVideoClip, ImageClip
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    subtitle_enabled = body.get('subtitle_enabled', True)
    subtitle_text = body.get('subtitle_text', '这是一段示例字幕文字\n用于展示字幕效果')
    font_name = body.get('font_name', 'MicrosoftYaHeiBold.ttc')
    font_size_pt = int(body.get('font_size', 60))
    text_fore_color = body.get('text_fore_color', '#FFFF00')
    stroke_color = body.get('stroke_color', '#000000')
    stroke_width = body.get('stroke_width', 1.5)
    subtitle_position = body.get('subtitle_position', 'bottom')
    custom_position = float(body.get('custom_position', 80.0))
    subtitle_auto_fit = body.get('subtitle_auto_fit', False)
    subtitle_margin = body.get('subtitle_margin')
    if subtitle_margin is None:
        subtitle_margin = config.ui.get("subtitle_margin", 0.05)

    logger.info(f"Subtitle preview request - text: '{subtitle_text}', font: '{font_name}', font_size_pt: {font_size_pt}, position: {subtitle_position}, margin: {subtitle_margin}")

    font_path = _get_valid_font_path(font_name, subtitle_text)
    logger.info(f"Resolved font path: '{font_path}', exists: {os.path.exists(font_path)}")

    video_aspect = body.get('video_aspect', '9:16')
    aspect_map = {
        'portrait': '9:16', 'portrait_9_16': '9:16',
        'landscape': '16:9', 'landscape_16_9': '16:9',
        'square': '1:1', 'portrait_3_4': '3:4',
        '1:1': '1:1', '9:16': '9:16', '16:9': '16:9', '3:4': '3:4',
    }
    normalized = aspect_map.get(video_aspect, '9:16')
    if normalized == '9:16':
        width, height = 1080, 1920
    elif normalized == '16:9':
        width, height = 1920, 1080
    elif normalized == '1:1':
        width, height = 1080, 1080
    elif normalized == '3:4':
        width, height = 1080, 1920
    else:
        width, height = 1080, 1920

    if not subtitle_enabled or not subtitle_text.strip():
        preview_dir = utils.storage_dir("subtitle_previews", create=True)
        preview_name = f"subtitle_preview_{utils.get_uuid()[:8]}.png"
        preview_path = os.path.join(preview_dir, preview_name)
        duration = 3.0
        if normalized == '3:4':
            content_h = 1440
            pad_h = (height - content_h) // 2
            content_bg = ColorClip(size=(width, content_h), color=(80, 80, 80), duration=duration)
            bar = ColorClip(size=(width, pad_h), color=(20, 20, 20), duration=duration)
            bg = CompositeVideoClip([
                content_bg.with_position((0, pad_h)),
                bar.with_position((0, 0)),
                bar.with_position((0, height - pad_h)),
            ], size=(width, height))
        else:
            bg = ColorClip(size=(width, height), color=(80, 80, 80), duration=duration)
        bg.save_frame(preview_path, t=1.0)
        logger.info(f"Subtitle preview (disabled) saved to: {preview_path}")
        response = {"preview_path": f"/subtitle-preview-image/{preview_name}"}
        return utils.get_response(200, response)

    _play_res_y = 1080
    font_size_px = max(1, int(font_size_pt * height / _play_res_y))

    margin_px = height * subtitle_margin
    max_width = width * (1 - 2 * subtitle_margin) * 0.95

    try:
        wrapped_text, text_h, actual_font_size_px = wrap_text(
            subtitle_text, max_width=max_width, font=font_path,
            fontsize=font_size_px, auto_fit=subtitle_auto_fit
        )
    except Exception as e:
        logger.warning(f"wrap_text failed for subtitle preview: {e}")
        wrapped_text = subtitle_text
        actual_font_size_px = font_size_px

    # Render subtitle using Pillow directly to correctly handle top-offset
    # of fonts like MicrosoftYaHeiBold.ttc whose PIL bbox has positive 'top'
    # values, which would otherwise cause the bottom line to be clipped when
    # the clip is positioned near the video bottom.
    lines = wrapped_text.split('\n') if wrapped_text else []
    if not lines:
        lines = ['']

    try:
        pil_font = ImageFont.truetype(font_path, actual_font_size_px)
    except Exception as e:
        logger.error(f"Failed to load font for subtitle preview: {e}")
        raise HttpException(task_id="", status_code=400, message=f"Failed to load font: {str(e)}")

    # Measure each line and accumulate heights with per-line top offset compensation.
    # We treat each line as starting at y = 0, but we need to know the bbox's
    # 'top' value (which can be positive for some fonts). We compensate by
    # shifting each line's draw position upward by -top so the rendered glyphs
    # align with the same baseline that an ImageClip would have.
    line_gap = 4  # small vertical gap between lines
    line_metrics = []  # each: {'height': int, 'top': int, 'width': int}
    max_line_width = 0
    for line in lines:
        if not line.strip():
            empty_height = int(actual_font_size_px * 1.2)
            line_metrics.append({"height": empty_height, "top": 0, "width": 0})
            continue
        bbox = pil_font.getbbox(line, stroke_width=int(stroke_width) if stroke_width > 0 else 0)
        height_line = bbox[3] - bbox[1]
        line_metrics.append({
            "height": height_line,
            "top": bbox[1],
            "width": bbox[2] - bbox[0],
        })
        max_line_width = max(max_line_width, bbox[2] - bbox[0])

    # Compute total text block height including per-line top offsets so
    # negative 'top' values are preserved (no line gets clipped at the top).
    cursor_y = 0
    positions = []  # (y_offset_within_image) for each line's draw position
    for i, m in enumerate(line_metrics):
        positions.append(cursor_y)
        cursor_y += m["height"] + (line_gap if i < len(line_metrics) - 1 else 0)
    total_height = cursor_y

    if total_height <= 0 or max_line_width <= 0:
        logger.warning(f"Zero-size subtitle image: {max_line_width}x{total_height}")
        raise HttpException(task_id="", status_code=400, message="Subtitle image has zero size")

    # Pad the image to leave room for negative 'top' offsets (e.g. descenders).
    # Without this, lines whose top offset is negative would be clipped at the
    # top of the image. We pre-shift all draw positions by -min_top so the
    # smallest top offset maps to y=0.
    min_top = min((m["top"] for m in line_metrics), default=0)
    y_shift = -min_top if min_top < 0 else 0
    img_height = total_height + y_shift
    img_width = max_line_width

    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    text_rgb = parse_color(text_fore_color)
    stroke_rgb = parse_color(stroke_color)
    int_stroke_width = int(stroke_width) if stroke_width > 0 else 0

    for i, (line, m) in enumerate(zip(lines, line_metrics)):
        y_pos = positions[i] + y_shift
        if not line.strip():
            continue
        # Compensate for positive 'top' offset: shift draw position down by +top
        # (which cancels the visual upward offset so the line's top sits at y_pos).
        draw_y = y_pos - m["top"]
        # Center each line horizontally within the image.
        draw_x = (img_width - m["width"]) / 2
        draw.text(
            (draw_x, draw_y),
            line,
            font=pil_font,
            fill=text_rgb,
            stroke_width=int_stroke_width,
            stroke_fill=stroke_rgb,
        )

    # Convert PIL image to ImageClip so we can composite it onto the video frame.
    img_array = np.array(img)
    txt_clip = ImageClip(img_array)
    txt_clip.duration = 3.0
    txt_clip.end = 3.0

    logger.info(f"Subtitle image size: {img_width}x{img_height}, clip size: {txt_clip.w}x{txt_clip.h}")

    if txt_clip.h <= 0 or txt_clip.w <= 0:
        logger.warning(f"Zero-size subtitle clip: {txt_clip.w}x{txt_clip.h}")
        txt_clip.close()
        raise HttpException(task_id="", status_code=400, message="Subtitle clip has zero size")

    if subtitle_position == "bottom":
        y_pos = height - margin_px - txt_clip.h
    elif subtitle_position == "top":
        y_pos = margin_px
    elif subtitle_position == "custom":
        max_y = height - txt_clip.h - margin_px
        min_y = margin_px
        y_pos = (height - txt_clip.h) * (custom_position / 100)
        y_pos = max(min_y, min(y_pos, max_y))
    else:
        y_pos = "center"

    txt_clip = txt_clip.with_position(("center", y_pos))

    preview_dir = utils.storage_dir("subtitle_previews", create=True)
    preview_name = f"subtitle_preview_{utils.get_uuid()[:8]}.png"
    preview_path = os.path.join(preview_dir, preview_name)

    duration = 3.0
    if normalized == '3:4':
        content_h = 1440
        pad_h = (height - content_h) // 2
        content_bg = ColorClip(size=(width, content_h), color=(80, 80, 80), duration=duration)
        bar = ColorClip(size=(width, pad_h), color=(20, 20, 20), duration=duration)
        bg = CompositeVideoClip([
            content_bg.with_position((0, pad_h)),
            bar.with_position((0, 0)),
            bar.with_position((0, height - pad_h)),
        ], size=(width, height))
    else:
        bg = ColorClip(size=(width, height), color=(80, 80, 80), duration=duration)
    composite = CompositeVideoClip([bg, txt_clip], size=(width, height))
    composite.save_frame(preview_path, t=1.0)

    txt_clip.close()
    composite.close()
    bg.close()

    logger.info(f"Subtitle preview saved to: {preview_path}")

    response = {"preview_path": f"/subtitle-preview-image/{preview_name}"}
    return utils.get_response(200, response)


@router.post("/scene-integration/scan", summary="Scan task directory for scene integration")
def scan_scene_integration(request: Request, body: dict):
    """Scan task directory for scene integration"""
    task_id_or_path = body.get("task_id") or body.get("task_path")
    if not task_id_or_path:
        raise HttpException(task_id="", status_code=400, message="Task ID or path is required")
    
    from app.services.video import scan_task_files
    
    try:
        result = scan_task_files(task_id_or_path)
        
        scene_videos = [s for s in result["scene_videos"] if s["video"] is not None]
        
        response = {
            "sceneVideos": len(scene_videos),
            "sceneAudio": len([s for s in result["scene_videos"] if s["audio"] is not None]),
            "subtitle": result["global_subtitle"] is not None,
            "totalScenes": result["total_scenes"],
            "isValid": result["is_valid"],
            "taskDir": result["task_dir"]
        }
        
        return utils.get_response(200, response)
    except Exception as e:
        logger.error(f"Error scanning scene integration: {e}")
        raise HttpException(task_id=task_id_or_path, status_code=500, message=f"Failed to scan task: {str(e)}")


@router.post("/scene-integration/recover", summary="Recover video synthesis from existing scene files")
def recover_scene_integration(request: Request, body: dict):
    """Recover video synthesis from existing scene files"""
    task_id_or_path = body.get("task_id") or body.get("task_path")
    start_scene = body.get("start_scene", 1)
    end_scene = body.get("end_scene", None)
    
    # Extract subtitle parameters from request (filter None so fallback chain works)
    subtitle_params = {k: v for k, v in {
        'subtitle_enabled': body.get('subtitle_enabled'),
        'font_name': body.get('font_name'),
        'font_size': body.get('font_size'),
        'text_fore_color': body.get('text_fore_color'),
        'text_background_color': body.get('text_background_color'),
        'stroke_color': body.get('stroke_color'),
        'stroke_width': body.get('stroke_width'),
        'subtitle_position': body.get('subtitle_position'),
        'custom_position': body.get('custom_position')
    }.items() if v is not None}
    
    # Extract BGM parameters from request (filter None so fallback chain works)
    bgm_params = {k: v for k, v in {
        'bgm_type': body.get('bgm_type'),
        'bgm_file': body.get('bgm_file'),
        'bgm_volume': body.get('bgm_volume')
    }.items() if v is not None}
    
    if not task_id_or_path:
        raise HttpException(task_id="", status_code=400, message="Task ID or path is required")
    
    from app.services import state as sm
    from app.models import const
    from app.services.task import thread_manager
    
    # Capture task creation time for duration logging
    import time as _time
    task_create_time = _time.time()
    
    # Generate unique task_id for tracking
    task_id = utils.get_uuid()
    
    # Register task immediately so it appears in task management
    sm.state.update_task(task_id, state=const.TASK_STATE_PENDING, progress=0, task_type="scene_integration")
    
    # Submit to thread manager for proper concurrency control
    from app.services.video import recover_video_synthesis
    _, queue_status = thread_manager.submit_task(
        task_id,
        recover_video_synthesis,
        task_id_or_path,
        None,           # progress_callback
        start_scene,    # start_scene
        end_scene,      # end_scene
        task_id,        # task_id (for recover_video_synthesis)
        subtitle_params=subtitle_params,
        bgm_params=bgm_params,
        task_create_time=task_create_time,
    )
    
    # Get the task with task_type from state
    created_task = sm.state.get_task(task_id)
    
    # Provide appropriate message based on queue status
    if queue_status == "queued":
        message = "Parallel running task capacity used up and your task will be queued for next slot"
        logger.info(f"Scene integration task {task_id} queued: {message}")
    else:
        message = "success"
        logger.success(f"Scene integration task created: {utils.to_json(created_task)}")
    
    return utils.get_response(200, created_task, message=message)
