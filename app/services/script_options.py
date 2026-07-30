from typing import Dict, Optional

from loguru import logger

STYLE_INSTRUCTIONS = {
    "general": """## Script Style: General (通用风格)
- **Tone**: Balanced, neutral, and clear — suitable for most audiences
- **Language**: Straightforward and easy to follow
- **Structure**: Standard informative flow — opening hook → main content → conclusion
- **Goal**: Convey information clearly without strong emotional coloring""",

    "professional": """## Script Style: Professional (专业深度)
- **Tone**: Authoritative, precise, and well-researched
- **Language**: Use domain-specific terminology where appropriate, support claims with data/examples
- **Structure**: Formal — thesis → evidence/analysis → conclusion with actionable insights
- **Goal**: Establish credibility and deliver in-depth expertise""",

    "popular": """## Script Style: Popular (通俗易懂)
- **Tone**: Friendly, accessible, and relatable
- **Language**: Use analogies, metaphors, and everyday examples — avoid jargon
- **Structure**: Engaging — relatable hook → simplified explanation → takeaway
- **Goal**: Make complex topics easy and enjoyable for a general audience""",

    "passionate": """## Script Style: Passionate (激情推广)
- **Tone**: Energetic, enthusiastic, and emotionally charged
- **Language**: Use strong, evocative words; short punchy sentences; rhetorical devices
- **Structure**: High-energy — bold claim → emotional buildup → inspiring call to action
- **Goal**: Excite, inspire, and motivate the audience to act""",

    "storytelling": """## Script Style: Storytelling (故事叙述)
- **Tone**: Narrative, immersive, and character-driven
- **Language**: Vivid descriptions, sensory details, dialogue-like delivery
- **Structure**: Classic story arc — setup (characters/conflict) → rising action → climax → resolution
- **Goal**: Engage emotions through narrative, make the audience feel invested""",

    "commentary": """## Script Style: Commentary (观点评论)
- **Overall Script Architecture**: The entire script follows a commentary/opinion structure, NOT per-scene transformation:
  1. **Opening Hook** (开场): 提出有争议性或引人深思的核心议题，直接亮明立场 — 用"你可能没想到…"或"很多人都错了…"式开场
  2. **Fact Foundation** (事实铺垫): 客观阐述原文的核心事实/观点，建立信息基础，让观众理解讨论的起点
  3. **Multi-Angle Analysis** (多角度剖析): 对核心观点进行至少2-3个角度的深入分析——支持方论据、反方批评、中立调和视角。每个角度单独展开，逻辑清晰
  4. **Engagement Climax** (互动高潮): 提出一个开放性问题，邀请观众思考和站队，但**不要**在此场景要求评论、点赞或关注。示例："你觉得哪种观点更有道理？"
  5. **Closing with CTA** (收尾引导): 用一句话总结核心论点，并**只在最后这一个场景**给出明确的评论互动引导。示例："在评论区告诉我你的想法"
- **Across All Scenes**: Maintain a provocative, analytical, debate-driven tone throughout the ENTIRE script
- **Interaction Hooks**: At key turning points, insert rhetorical questions or challenges that invite audience reflection and participation
- **CTA Uniqueness Rule**: 全文中只能有一个场景包含"在评论区告诉我你的想法"或类似的明确评论引导语，且必须放在最后一个场景。
- **Depth Control**: The selected preset (concise/standard/in-depth) controls how many perspectives each viewpoint gets and how much supporting data is included""",
}


PRESETS = {
    "concise": {
        "web_search_enabled": False,
        "search_results_count": 3,
        "search_rounds": 1,
        "search_source_preference": "balanced",
        "paragraph_number": 2,
        "paragraph_detail": "concise",
        "expansion_depth": "topic_only",
        "script_style": "general",
        "target_word_count": "200-400",
        "min_scenes": 3,
        "max_scenes": 4,
        "min_paragraph_words": 30,
        "max_paragraph_words": 75,
        "expansion_instruction": "Strictly围绕主题展开,不要偏离到无关的子话题",
        "detail_instruction": "每段只保留核心观点,不要展开细节,用最简洁的语言表达",
    },
    "standard": {
        "web_search_enabled": True,
        "search_results_count": 5,
        "search_rounds": 1,
        "search_source_preference": "balanced",
        "paragraph_number": 4,
        "paragraph_detail": "normal",
        "expansion_depth": "moderate",
        "script_style": "general",
        "target_word_count": "800-2000",
        "min_scenes": 5,
        "max_scenes": 12,
        "min_paragraph_words": 60,
        "max_paragraph_words": 200,
        "expansion_instruction": "以主题为核心,适度延伸至相关子话题,覆盖主要方面即可",
        "detail_instruction": "正常展开,每个观点用1-2句话说明,适当加入例子",
    },
    "in_depth": {
        "web_search_enabled": True,
        "search_results_count": 10,
        "search_rounds": 2,
        "search_source_preference": "authoritative",
        "paragraph_number": 8,
        "paragraph_detail": "detailed",
        "expansion_depth": "deep",
        "script_style": "professional",
        "target_word_count": "2000-5000",
        "min_scenes": 9,
        "max_scenes": 18,
        "min_paragraph_words": 100,
        "max_paragraph_words": 330,
        "expansion_instruction": "全面覆盖主题及其相关领域,深入分析多个角度,包括背景、现状、案例、数据、趋势等",
        "detail_instruction": "详细展开,包含具体数据、案例、对比分析,确保内容充实有深度",
    },
}


def get_preset(preset_name: str) -> Dict:
    preset = PRESETS.get(preset_name)
    if preset is None:
        logger.warning(f"Unknown preset '{preset_name}', falling back to 'standard'")
        preset = PRESETS["standard"]
    return dict(preset)


def resolve_options(
    script_preset: Optional[str] = "standard",
    web_search_enabled: Optional[bool] = None,
    search_results_count: Optional[int] = None,
    search_rounds: Optional[int] = None,
    search_source_preference: Optional[str] = None,
    expansion_depth: Optional[str] = None,
    paragraph_detail: Optional[str] = None,
    script_style: Optional[str] = None,
    max_scenes: Optional[int] = None,
    paragraph_number: Optional[int] = None,
) -> Dict:
    if script_preset and script_preset != "custom":
        resolved = get_preset(script_preset)
    else:
        resolved = get_preset("standard")
        resolved["script_preset"] = "custom"

    overrides = {
        "web_search_enabled": web_search_enabled,
        "search_results_count": search_results_count,
        "search_rounds": search_rounds,
        "search_source_preference": search_source_preference,
        "expansion_depth": expansion_depth,
        "paragraph_detail": paragraph_detail,
        "script_style": script_style,
        "max_scenes": max_scenes,
        "paragraph_number": paragraph_number,
    }

    for key, value in overrides.items():
        if value is not None:
            resolved[key] = value

    logger.debug(f"Resolved script options: preset={script_preset}, web_search={resolved.get('web_search_enabled')}, "
                 f"scenes={resolved.get('min_scenes')}-{resolved.get('max_scenes')}, "
                 f"detail={resolved.get('paragraph_detail')}, expansion={resolved.get('expansion_depth')}")

    return resolved


def build_length_instructions(options: Dict) -> str:
    expansion = options.get("expansion_instruction", "以主题为核心展开")
    detail = options.get("detail_instruction", "正常展开")
    target = options.get("target_word_count", "500-1500")
    min_scenes = options.get("min_scenes", 3)
    max_scenes = options.get("max_scenes", 10)
    min_words = options.get("min_paragraph_words", 30)
    max_words = options.get("max_paragraph_words", 150)

    instructions = f"""
## Length & Depth Requirements:
- Target total script length: ~{target} words
- Number of scenes: {min_scenes}-{max_scenes}
- Each scene script length: {min_words}-{max_words} characters
- Each sentence within a scene script should be short (Chinese: ~20-35 chars, English: ~40-80 chars) to keep subtitles readable and avoid line wrapping
- Topic expansion scope: {expansion}
- Detail level: {detail}
""".strip()
    return instructions


def build_style_instructions(options: Dict) -> str:
    style = options.get("script_style", "general")
    instructions = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["general"])
    return f"\n\n{instructions}"


def validate_enum(value: Optional[str], allowed: list, default: str, name: str) -> str:
    if value is None:
        return default
    if value not in allowed:
        logger.warning(f"Invalid {name} '{value}', must be one of {allowed}, using default '{default}'")
        return default
    return value


def validate_source_preference(value: Optional[str]) -> str:
    return validate_enum(value, ["balanced", "authoritative", "latest"], "balanced", "search_source_preference")


def validate_expansion_depth(value: Optional[str]) -> str:
    return validate_enum(value, ["topic_only", "moderate", "deep"], "moderate", "expansion_depth")


def validate_paragraph_detail(value: Optional[str]) -> str:
    return validate_enum(value, ["concise", "normal", "detailed"], "normal", "paragraph_detail")


def validate_script_style(value: Optional[str]) -> str:
    return validate_enum(value, ["general", "professional", "popular", "passionate", "storytelling", "commentary"], "general", "script_style")


def validate_script_preset(value: Optional[str]) -> str:
    return validate_enum(value, ["concise", "standard", "in_depth", "custom"], "standard", "script_preset")
