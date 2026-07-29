"""
Centralized keyword parsing and validation utilities.

Provides helpers to normalize keywords and validate them against the project's
quality policy: each keyword must be short, concrete, complete, and expressible
as a single video scene or clip.
"""
import ast
import re
from dataclasses import dataclass
from typing import List, Optional, Union


# ---------------------------------------------------------------------------
# Keyword normalization
# ---------------------------------------------------------------------------

def parse_keywords(value: Union[str, list, None]) -> List[str]:
    """
    Normalize a keyword value into a list of non-empty, stripped strings.

    Args:
        value: Keywords as a list, a JSON/Python list literal string,
               a comma-separated string, or None/empty.

    Returns:
        A list of cleaned keyword strings. Returns an empty list when the input
        is None, empty, or cannot be parsed.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return [str(term).strip() for term in value if term and str(term).strip()]

    value = str(value).strip()
    if not value:
        return []

    # Try to parse as a Python/JSON list literal first (e.g. "['a', 'b']")
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [str(term).strip() for term in parsed if term and str(term).strip()]
    except (ValueError, SyntaxError):
        pass

    # Fall back to comma-separated string parsing
    return [term.strip() for term in value.split(",") if term.strip()]


# ---------------------------------------------------------------------------
# Keyword validation
# ---------------------------------------------------------------------------

# Abstract concepts that cannot be visualized as a concrete scene.
ABSTRACT_KEYWORDS = {
    # Chinese
    "变革", "趋势", "影响", "未来", "发展", "重要性", "意义", "作用", "价值",
    "挑战", "机遇", "时代", "历史", "文化", "社会", "经济", "政治", "科技",
    "进步", "创新", "竞争", "合作", "冲突", "矛盾", "问题", "现状", "前景",
    "核心", "关键", "重点", "本质", "根源", "结果", "后果", "过程", "变化",
    # English
    "change", "trend", "impact", "future", "development", "importance",
    "significance", "value", "challenge", "opportunity", "era", "history",
    "culture", "society", "economy", "politics", "technology", "progress",
    "innovation", "competition", "cooperation", "conflict", "contradiction",
    "problem", "status", "prospect", "core", "key", "focus", "essence",
    "root", "result", "consequence", "process", "transformation",
}

# Incomplete action phrases that are missing an object and cannot be used alone
# to search for a video clip.
# NOTE: These are exact-match or carefully-scoped patterns to avoid false
# positives on valid noun phrases such as "美军部署" (military deployment).
INCOMPLETE_PATTERNS = [
    # Chinese bare verbs / obviously incomplete fragments
    re.compile(
        r"^(增派|加强|提升|推动|促进|提高|增加|减少|支持|扩大|深化|加快|推进|"
        r"强化|落实|贯彻|执行|开展|组织|进行|实现|完成|达成|确保|维护|保障|坚持|"
        r"美国增派|中国增派|俄军增派|美军增派|美国加强|中国加强|美国支持|中国支持)$",
        re.IGNORECASE,
    ),
    # English bare verbs
    re.compile(
        r"^(deploy|increase|decrease|strengthen|support|promote|enhance|boost|"
        r"expand|deepen|accelerate|advance|implement|execute|conduct|organize|"
        r"achieve|complete|ensure|maintain|uphold|insist|intensify)$",
        re.IGNORECASE,
    ),
]

# Thresholds for keyword length.
_MAX_CHINESE_CHARS = 6          # e.g. "新闻发布会" is acceptable, longer is suspicious
_MAX_ENGLISH_CHARS = 25         # three English words are usually below this
_MAX_TOKENS_WITH_SPACE = 3      # "chip factory" (2), "protest crowd" (2)


@dataclass
class KeywordValidationResult:
    """Result of validating a single keyword."""

    term: str
    is_valid: bool
    reason: Optional[str] = None

    def __repr__(self) -> str:
        return f"KeywordValidationResult(term={self.term!r}, is_valid={self.is_valid}, reason={self.reason})"


def _count_segments(term: str) -> int:
    """
    Count the number of semantic segments in a keyword.

    - Terms with whitespace are split on whitespace (English/multi-word).
    - Pure CJK terms without whitespace are treated as one segment; their
      absolute length is guarded separately by _MAX_CHINESE_CHARS.
    - Mixed terms count CJK runs as one segment each and whitespace-split
      English tokens as separate segments.
    """
    term = term.strip()
    if not term:
        return 0

    # If the term contains whitespace, count each whitespace-separated token.
    if re.search(r"\s", term):
        return len([p for p in re.split(r"\s+", term) if p])

    # No whitespace: treat as a single segment.
    return 1


def validate_keywords(terms: List[str]) -> List[KeywordValidationResult]:
    """
    Validate a list of keywords against the project keyword quality policy.

    Rules:
      - Length: 1-3 segments (words for English, characters for pure CJK).
      - Concrete: must not be in the abstract keyword blacklist.
      - Complete: must not match incomplete action-phrase patterns.

    Args:
        terms: List of keyword strings.

    Returns:
        A list of KeywordValidationResult, one per input term.
    """
    results = []
    for term in terms:
        term = term.strip() if term else ""
        if not term:
            results.append(KeywordValidationResult(term=term, is_valid=False, reason="empty"))
            continue

        # 1. Length check
        segments = _count_segments(term)
        if segments > _MAX_TOKENS_WITH_SPACE:
            results.append(KeywordValidationResult(term=term, is_valid=False, reason="too_long"))
            continue

        # 2. Abstract concept check (case-insensitive)
        lower_term = term.lower()
        if lower_term in ABSTRACT_KEYWORDS:
            results.append(KeywordValidationResult(term=term, is_valid=False, reason="abstract"))
            continue

        # 3. Incomplete phrase check
        if any(pattern.search(term) for pattern in INCOMPLETE_PATTERNS):
            results.append(KeywordValidationResult(term=term, is_valid=False, reason="incomplete"))
            continue

        # 4. Heuristic length guard for edge cases
        if re.fullmatch(r"[\u4e00-\u9fa5]+", term) and len(term) > _MAX_CHINESE_CHARS:
            results.append(KeywordValidationResult(term=term, is_valid=False, reason="too_long"))
            continue
        if re.fullmatch(r"[a-zA-Z\s]+", term) and len(term.replace(" ", "")) > _MAX_ENGLISH_CHARS:
            results.append(KeywordValidationResult(term=term, is_valid=False, reason="too_long"))
            continue

        results.append(KeywordValidationResult(term=term, is_valid=True))

    return results


def format_feedback(results: List[KeywordValidationResult]) -> str:
    """
    Format validation results into a concise feedback string for LLM re-generation.

    Example output:
        Invalid keywords and reasons:
        - "美国增派": incomplete (missing object)
        - "未来": abstract (not visualizable)
        Please regenerate only compliant keywords.
    """
    invalid = [r for r in results if not r.is_valid]
    if not invalid:
        return ""

    reason_text = {
        "too_long": "too long (must be 1-3 words/segments)",
        "abstract": "abstract (not visualizable as a concrete scene)",
        "incomplete": "incomplete (action phrase missing an object)",
        "empty": "empty",
    }

    lines = ["Invalid keywords and reasons:"]
    for r in invalid:
        desc = reason_text.get(r.reason, r.reason or "non-compliant")
        lines.append(f'- "{r.term}": {desc}')
    lines.append("Please regenerate only compliant, concrete noun phrases that can be expressed as a single video scene.")
    return "\n".join(lines)


def has_invalid_keywords(terms: List[str]) -> bool:
    """Return True if any keyword in the list fails validation."""
    return any(not r.is_valid for r in validate_keywords(terms))
