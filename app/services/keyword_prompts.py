"""
Centralized keyword generation prompts and policy.

All keyword-related LLM prompts across the project should reference
KEYWORD_POLICY / the builders below, so that the definition of "what a good
keyword looks like" lives in exactly one place.
"""
from typing import Optional


# Shared policy that every keyword generator must enforce.
KEYWORD_POLICY = """
- Each keyword must be a short (1-3 words), concrete noun phrase that can represent a single video scene or clip.
- It must be complete: do NOT output incomplete action phrases missing an object (e.g., "美国增派", "deploy", "increase").
- It must be visualizable: avoid overly abstract concepts like "变革", "趋势", "impact", "future". A good keyword should let you search a stock-video site and find a matching clip.
- Before finalizing, ask yourself: "Can I type this keyword into a stock-video search box and get a relevant clip?" If the answer is no, rewrite it.
- Good examples: "伊朗邮轮", "美军部署", "新闻发布会", "chip factory", "protest crowd".
- Bad examples: "美国增派", "加强", "未来", "trend", "impact", "economic development".
""".strip()


def build_video_terms_prompt(
    video_subject: str,
    video_script: str,
    amount: int,
    language: Optional[str] = None,
    feedback: Optional[str] = None,
) -> str:
    """Prompt for generating video-level search terms."""
    feedback_section = f"\n\n## Feedback on Previous Attempt\n{feedback}\n" if feedback else ""
    return f"""
# Role: Video Search Terms Generator

## Goals:
Generate {amount} search terms for stock videos, depending on the subject of a video.

## Constraints:
1. The search terms are to be returned as a JSON array of strings.
2. Each search term should consist of 1-3 words, always add the main subject of the video.
3. You must only return the JSON array of strings. You must not return anything else. You must not return the script.
4. The search terms must be related to the subject of the video.
5. Generate both English and Chinese search terms to get more relevant videos.
{KEYWORD_POLICY}

## Output Example:
["design patterns", "设计模式", "software design", "软件设计", "coding best practices", "编程最佳实践", "object oriented", "面向对象", "design principles", "设计原则"]
{feedback_section}

## Context:
### Video Subject
{video_subject}

### Video Script
{video_script}

Please generate both English and Chinese search terms to ensure better search results.
""".strip()


def build_scene_keywords_prompt(
    scene_script: str,
    scene_camera: str,
    amount: int,
    language: Optional[str] = None,
    purpose: str = "search",
    feedback: Optional[str] = None,
) -> str:
    """
    Prompt for generating per-scene keywords/tags.

    Args:
        scene_script: Narration/script for the scene.
        scene_camera: Camera/visual description for the scene.
        amount: Number of keywords to generate.
        language: Target language (used for the final instruction line).
        purpose: "search" for scene search terms, "tag" for material-matching tags.
        feedback: Optional feedback from a previous validation attempt.
    """
    if purpose == "tag":
        role = "Scene Tag Generator"
        goal = f"Generate {amount} relevant tags for a video scene based on its script content and visual requirements."
    else:
        role = "Scene-Specific Video Search Terms Generator"
        goal = f"Generate {amount} search terms for stock videos for a specific scene."

    context = f"### Scene Script\n{scene_script}"
    if scene_camera and scene_camera.strip():
        context = f"### Scene Camera/Visual Description\n{scene_camera}\n\n{context}"

    feedback_section = f"\n\n## Feedback on Previous Attempt\n{feedback}\n" if feedback else ""

    return f"""
# Role: {role}

## Goals:
{goal}

## Constraints:
1. The keywords are to be returned as a JSON array of strings.
2. {KEYWORD_POLICY}
3. You must only return the JSON array of strings. You must not return anything else.
4. Generate keywords in the same language as the scene script.
5. Focus on visual elements mentioned in the camera/visual description.

## Output Example:
["伊朗邮轮", "军舰甲板", "港口夜景", "海上航行", "乘客登船"]
{feedback_section}

## Context:
{context}

Please generate keywords in the same language as the scene script.
""".strip()


def build_multi_scene_keyword_instruction() -> str:
    """
    Instruction used inside multi-scene script prompts.

    It is meant to be inserted directly after the item number, e.g.:
        5. **Keyword Extraction (CRITICAL)**: {build_multi_scene_keyword_instruction()}
    """
    return f"""Extract 3-5 core keywords for each scene. Obey the following:
   {KEYWORD_POLICY.replace(chr(10), chr(10) + '   ')}"""
