"""Command-line interface for the Aiko memory engine."""

import argparse
from pathlib import Path

from aiko_memory.activation import activate_concept
from aiko_memory.database import DEFAULT_DB_PATH, get_session
from aiko_memory.consolidation import consolidate_memories
from aiko_memory.decay import apply_decay
from aiko_memory.opinions import generate_opinions
from aiko_memory.patterns import detect_patterns
from aiko_memory.repository import add_memory, list_memories, list_opinions, list_patterns, memory_concepts
from aiko_memory.thoughts import current_thoughts


def _print_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    print(title)
    print("=" * len(title))
    if not rows:
        print("(none)")
        return
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


def _print_memories(session, memories) -> None:  # noqa: ANN001
    _print_table(
        "Memories",
        ["ID", "Summary", "Importance", "Weight", "Concepts"],
        [
            [
                str(memory.id),
                memory.summary,
                f"{memory.importance:.1f}",
                f"{memory.weight:.1f}",
                ", ".join(sorted(memory_concepts(session, memory.id or 0))),
            ]
            for memory in memories
        ],
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Aiko Memory Engine MVP")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a memory and concept associations.")
    add_parser.add_argument("summary")
    add_parser.add_argument("--importance", type=float, default=50.0)
    add_parser.add_argument("--weight", type=float, default=50.0)
    add_parser.add_argument("--tags", nargs="*", default=[])

    tick_parser = subparsers.add_parser("tick", help="Apply time decay.")
    tick_parser.add_argument("--days", type=float, default=1.0)

    activate_parser = subparsers.add_parser("activate", help="Reactivate memories associated with a concept.")
    activate_parser.add_argument("concept")

    memories_parser = subparsers.add_parser("memories", help="Display memories sorted by active weight.")
    memories_parser.add_argument("--include-absorbed", action="store_true", help="Include memories absorbed into patterns.")

    subparsers.add_parser("consolidate", help="Summarize repeated low-importance memories into patterns.")
    subparsers.add_parser("patterns", help="Detect and display recurring patterns.")
    subparsers.add_parser("opinions", help="Generate and display opinions.")
    thoughts_parser = subparsers.add_parser("thoughts", help="Display what is currently on Aiko's mind.")
    thoughts_parser.add_argument("--include-absorbed", action="store_true", help="Include absorbed memories in current thoughts.")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the CLI."""
    args = build_parser().parse_args(argv)
    with get_session(args.db) as session:
        if args.command == "add":
            memory = add_memory(session, args.summary, args.importance, args.weight, args.tags)
            print(f"Added memory #{memory.id}: {memory.summary}")
        elif args.command == "tick":
            memories = apply_decay(session, args.days)
            print(f"Decayed {len(memories)} memories over {args.days:g} day(s).")
        elif args.command == "activate":
            memories = activate_concept(session, args.concept)
            print(f"Activated {len(memories)} memories associated with '{args.concept}'.")
            _print_memories(session, sorted(memories, key=lambda memory: memory.weight, reverse=True))
        elif args.command == "memories":
            _print_memories(session, list_memories(session, include_absorbed=args.include_absorbed))
        elif args.command == "consolidate":
            patterns = consolidate_memories(session)
            print(f"Consolidated {len(patterns)} pattern(s).")
            _print_table(
                "Patterns",
                ["ID", "Summary", "Importance", "Weight", "Evidence", "Concepts", "Tone"],
                [
                    [
                        str(pattern.id),
                        pattern.summary,
                        f"{pattern.importance:.1f}",
                        f"{pattern.weight:.1f}",
                        str(pattern.evidence_count),
                        ", ".join(pattern.concepts),
                        pattern.tone,
                    ]
                    for pattern in patterns
                ],
            )
        elif args.command == "patterns":
            detect_patterns(session)
            _print_table(
                "Patterns",
                ["ID", "Summary", "Importance", "Weight", "Evidence", "Concepts", "Tone"],
                [
                    [
                        str(pattern.id),
                        pattern.summary,
                        f"{pattern.importance:.1f}",
                        f"{pattern.weight:.1f}",
                        str(pattern.evidence_count),
                        ", ".join(pattern.concepts),
                        pattern.tone,
                    ]
                    for pattern in list_patterns(session)
                ],
            )
        elif args.command == "opinions":
            detect_patterns(session)
            generate_opinions(session)
            _print_table(
                "Opinions",
                ["ID", "Target", "Belief", "Confidence"],
                [
                    [str(opinion.id), opinion.target, opinion.belief, f"{opinion.confidence:.1f}"]
                    for opinion in list_opinions(session)
                ],
            )
        elif args.command == "thoughts":
            detect_patterns(session)
            generate_opinions(session)
            thoughts = current_thoughts(session, include_absorbed=args.include_absorbed)
            print("Current Thoughts\n")
            print("Memories:")
            for memory in thoughts.memories:
                print(f"- {memory.summary} (weight {memory.weight:.1f})")
            print("\nPatterns:")
            for pattern in thoughts.patterns:
                print(f"- {pattern.summary} (weight {pattern.weight:.1f})")
            print("\nOpinions:")
            for opinion in thoughts.opinions:
                print(f"- {opinion.belief} (confidence {opinion.confidence:.1f})")


def app() -> None:
    """Console-script entry point."""
    main()


if __name__ == "__main__":
    main()
