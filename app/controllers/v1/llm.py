from fastapi import Request, Body
from loguru import logger

from app.controllers.v1.base import new_router
from app.models.schema import (
    VideoScriptRequest,
    VideoScriptResponse,
    VideoTermsRequest,
    VideoTermsResponse,
)
from app.services import llm
from app.services import scene_parser
from app.utils import utils

# authentication dependency
# router = new_router(dependencies=[Depends(base.verify_token)])
router = new_router()


@router.post(
    "/scripts",
    response_model=VideoScriptResponse,
    summary="Create a script for the video",
)
def generate_video_script(request: Request, body: VideoScriptRequest):
    search_context = ""
    options = None

    if body.web_search_enabled:
        from app.services.search import search_and_summarize
        search_context = search_and_summarize(
            topic=body.video_subject,
            rounds=body.search_rounds or 1,
            num_results=body.search_results_count or 5,
            source_preference=body.search_source_preference or "balanced",
            expansion_depth=body.expansion_depth or "moderate",
        )
        logger.info(f"Web search context length: {len(search_context)} chars for subject '{body.video_subject}'")

    if body.script_preset:
        from app.services.script_options import resolve_options
        options = resolve_options(
            script_preset=body.script_preset,
            web_search_enabled=body.web_search_enabled,
            search_results_count=body.search_results_count,
            search_rounds=body.search_rounds,
            search_source_preference=body.search_source_preference,
            expansion_depth=body.expansion_depth,
            paragraph_detail=body.paragraph_detail,
            script_style=body.script_style,
            paragraph_number=body.paragraph_number,
        )

    video_script = llm.generate_script(
        video_subject=body.video_subject,
        language=body.video_language,
        paragraph_number=body.paragraph_number,
        search_context=search_context,
        options=options,
    )
    response = {"video_script": video_script}
    return utils.get_response(200, response)


@router.post(
    "/terms",
    response_model=VideoTermsResponse,
    summary="Generate video terms based on the video script",
)
def generate_video_terms(request: Request, body: VideoTermsRequest):
    video_terms = llm.generate_terms(
        video_subject=body.video_subject,
        video_script=body.video_script,
        amount=body.amount,
    )
    response = {"video_terms": video_terms}
    return utils.get_response(200, response)


@router.post(
    "/parse-script",
    summary="Parse video script into scenes",
)
def parse_video_script(request: Request, body: dict = Body(...)):
    video_script = body.get("video_script")
    if not video_script:
        return utils.get_response(400, {"error": "Video script is required"})

    language = body.get("language")
    host_visible = body.get("host_visible", True)
    script_style = body.get("script_style")
    script_preset = body.get("script_preset", "standard")
    web_search_enabled = body.get("web_search_enabled")
    search_results_count = body.get("search_results_count")
    search_rounds = body.get("search_rounds")
    search_source_preference = body.get("search_source_preference")
    expansion_depth = body.get("expansion_depth")
    paragraph_detail = body.get("paragraph_detail")

    result = scene_parser.auto_parse_script(
        video_script,
        language=language,
        host_visible=host_visible,
        script_style=script_style,
        script_preset=script_preset,
        web_search_enabled=web_search_enabled,
        search_results_count=search_results_count,
        search_rounds=search_rounds,
        search_source_preference=search_source_preference,
        expansion_depth=expansion_depth,
        paragraph_detail=paragraph_detail,
    )
    logger.info(
        f"Parse script result: status={result['status']}, "
        f"scenes_count={len(result.get('scenes', []))}, "
        f"script_preset={script_preset}, script_style={script_style}"
    )
    return utils.get_response(200, result)
