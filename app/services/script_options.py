from typing import Dict, Optional

from loguru import logger

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
        "max_scenes": 5,
        "min_paragraph_words": 30,
        "max_paragraph_words": 60,
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
        "target_word_count": "500-1500",
        "min_scenes": 6,
        "max_scenes": 10,
        "min_paragraph_words": 60,
        "max_paragraph_words": 150,
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
        "target_word_count": "1500-4000",
        "min_scenes": 10,
        "max_scenes": 20,
        "min_paragraph_words": 150,
        "max_paragraph_words": 300,
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
- Topic expansion scope: {expansion}
- Detail level: {detail}
""".strip()
    return instructions


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
    return validate_enum(value, ["general", "professional", "popular", "passionate", "storytelling"], "general", "script_style")


def validate_script_preset(value: Optional[str]) -> str:
    return validate_enum(value, ["concise", "standard", "in_depth", "custom"], "standard", "script_preset")
