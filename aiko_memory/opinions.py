"""Opinion generation from strong patterns."""

from aiko_memory.database import Session
from aiko_memory.models import Opinion, Pattern, utc_now
from aiko_memory.repository import clamp, get_opinion_by_key, save_opinion, strong_patterns

OPINION_MIN_PATTERN_STRENGTH = 60.0
OPINION_CONFIDENCE_OFFSET = -10.0


def opinion_from_pattern(pattern: Pattern) -> tuple[str, str] | None:
    """Map a known MVP pattern description into a subjective opinion."""
    description = pattern.description.lower()
    if "jack" in description and "socks" in description:
        return "Jack", "Jack often leaves socks around the home."
    if "jack" in description and "household chores" in description:
        return "Jack", "Jack can be unreliable with small household chores."
    if "emi" in description and "nervous" in description:
        return "Emi", "Emi may need reassurance in crowded events."
    return None


def generate_opinions(session: Session) -> list[Opinion]:
    """Create or update opinions from strong patterns."""
    patterns = strong_patterns(session, OPINION_MIN_PATTERN_STRENGTH)
    opinions: list[Opinion] = []
    now = utc_now()
    for pattern in patterns:
        mapped = opinion_from_pattern(pattern)
        if mapped is None or pattern.id is None:
            continue
        target, belief = mapped
        opinion_key = f"{target.lower()}:{belief.lower()}"
        confidence = clamp(pattern.strength + OPINION_CONFIDENCE_OFFSET)
        opinion = get_opinion_by_key(session, opinion_key)
        if opinion is None:
            opinion = Opinion(
                target=target,
                belief=belief,
                confidence=confidence,
                supporting_pattern_ids=[pattern.id],
                opinion_key=opinion_key,
            )
        else:
            opinion.confidence = clamp(max(opinion.confidence, confidence))
            opinion.supporting_pattern_ids = sorted(set(opinion.supporting_pattern_ids) | {pattern.id})
            opinion.updated_at = now
        save_opinion(session, opinion)
        opinions.append(opinion)
    return sorted(opinions, key=lambda item: item.confidence, reverse=True)
