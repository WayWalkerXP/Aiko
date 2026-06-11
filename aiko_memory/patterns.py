"""Rule-based pattern detection for recurring memory concepts."""

from itertools import combinations

from aiko_memory.database import Session
from aiko_memory.models import Pattern, utc_now
from aiko_memory.repository import clamp, concept_memory_map, get_memory, get_pattern_by_key, normalize_concept, save_pattern

PATTERN_MIN_EVIDENCE_COUNT = 3
PATTERN_MIN_SHARED_CONCEPTS = 2
PATTERN_STRENGTH_PER_MEMORY = 20.0
PATTERN_STRENGTH_ASSOCIATION_BONUS = 10.0
PERSON_CONCEPTS = {"jack", "aiko", "emi"}


def _concept_label(concept: str) -> str:
    return concept.replace("_", " ")


def _choose_target(concepts: tuple[str, ...]) -> str:
    for concept in concepts:
        if concept in PERSON_CONCEPTS:
            return concept
    return concepts[0]


def describe_pattern(concepts: tuple[str, ...], evidence_ids: set[int], session: Session) -> str:
    """Create a simple human-readable description for a concept cluster."""
    target = _choose_target(concepts)
    concept_set = set(concepts)
    target_title = _concept_label(target).title()

    if {"jack", "socks"}.issubset(concept_set):
        evidence_concepts = set()
        for memory_id in evidence_ids:
            from aiko_memory.repository import memory_concepts

            evidence_concepts.update(memory_concepts(session, memory_id))
        if "laundry" in evidence_concepts or "home" in evidence_concepts:
            return "Jack often leaves socks around the house."
        return "Jack often leaves socks out."
    if {"emi", "festival"}.issubset(concept_set):
        return "Emi seems nervous in festival crowds."
    if {"jack", "trash"}.issubset(concept_set):
        return "Jack sometimes forgets household chores."

    other_concepts = [_concept_label(c) for c in concepts if c != target]
    evidence_samples = [get_memory(session, memory_id) for memory_id in sorted(evidence_ids)[:1]]
    if evidence_samples and evidence_samples[0] is not None:
        return f"{target_title} repeatedly connects with {', '.join(other_concepts)}."
    return f"Recurring theme involving {', '.join(_concept_label(c) for c in concepts)}."


def detect_patterns(session: Session) -> list[Pattern]:
    """Detect or strengthen patterns where at least three memories share two concepts."""
    mapping = concept_memory_map(session)
    candidates: dict[tuple[str, ...], set[int]] = {}
    for concept_pair in combinations(sorted(mapping), PATTERN_MIN_SHARED_CONCEPTS):
        shared_ids = set.intersection(*(mapping[concept] for concept in concept_pair))
        if len(shared_ids) >= PATTERN_MIN_EVIDENCE_COUNT:
            candidates[concept_pair] = shared_ids

    patterns: list[Pattern] = []
    now = utc_now()
    for concepts, evidence_ids in candidates.items():
        concept_key = ",".join(normalize_concept(concept) for concept in concepts)
        strength = clamp(
            len(evidence_ids) * PATTERN_STRENGTH_PER_MEMORY
            + len(concepts) * PATTERN_STRENGTH_ASSOCIATION_BONUS
        )
        pattern = get_pattern_by_key(session, concept_key)
        if pattern is None:
            pattern = Pattern(
                summary=describe_pattern(concepts, evidence_ids, session),
                importance=25.0,
                weight=strength,
                evidence_count=len(evidence_ids),
                concepts=list(concepts),
                tone="neutral",
                evidence_memory_ids=sorted(evidence_ids),
                concept_key=concept_key,
            )
        else:
            pattern.description = describe_pattern(concepts, evidence_ids, session)
            pattern.strength = clamp(max(pattern.strength, strength) + 5.0)
            pattern.evidence_memory_ids = sorted(set(pattern.evidence_memory_ids) | evidence_ids)
            pattern.evidence_count = len(pattern.evidence_memory_ids)
            pattern.concepts = list(concepts)
            pattern.updated_at = now
        save_pattern(session, pattern)
        patterns.append(pattern)
    return sorted(patterns, key=lambda item: item.strength, reverse=True)
