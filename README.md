# Aiko Memory Engine

Aiko Memory Engine is a small Python CLI that models how experiences become memories, memories become associations, repeated memories become patterns, and patterns become opinions.

The MVP is intentionally local and inspectable: Python, SQLite, a small standard-library CLI, and pytest. There is no chatbot, LLM integration, web UI, or world simulation in this first layer.

## Install

```bash
python -m pip install -e '.[test]'
```

You can also run the CLI directly without installing the console script:

```bash
python -m aiko_memory.cli --help
```

Requires Python 3.12 or newer.

## CLI quickstart

Add memories with concept tags:

```bash
aiko-mem add "Jack left socks on the floor." --importance 20 --weight 70 --tags jack --tags socks --tags laundry --tags home
aiko-mem add "Jack left socks beside the bed." --importance 20 --weight 70 --tags jack --tags socks --tags laundry --tags home
aiko-mem add "Jack left socks near the couch." --importance 20 --weight 70 --tags jack --tags socks --tags laundry --tags home
aiko-mem add "Jack broke his leg in the park." --importance 95 --weight 80 --tags jack --tags park --tags injury --tags worry --tags walking
aiko-mem add "Aiko saw a squirrel gathering nuts." --importance 10 --weight 50 --tags aiko --tags squirrel --tags nature
aiko-mem add "Emi got nervous in the festival crowd." --importance 70 --weight 65 --tags emi --tags festival --tags crowd --tags nervous
```

Show memories sorted by what is most top-of-mind:

```bash
aiko-mem memories
```

Apply time decay:

```bash
aiko-mem tick --days 1
```

Activate a concept and reactivate associated memories:

```bash
aiko-mem activate park
aiko-mem activate socks
```

Detect recurring patterns:

```bash
aiko-mem patterns
```

Generate subjective opinions from strong patterns:

```bash
aiko-mem opinions
```

Show Aiko's current active thoughts:

```bash
aiko-mem thoughts
```

## Data model

The engine stores four core entities in SQLite:

- **Memory**: a specific experience with `importance`, active `weight`, creation time, and last activation time.
- **Association**: a directed link between a memory/concept/pattern/opinion and another node.
- **Pattern**: a recurring theme detected from memories that share concepts.
- **Opinion**: a subjective belief generated from strong patterns.

## Behavior

### Decay

Memory weight decays faster when importance is low and slower when importance is high:

```python
weight_decay = days * (1.0 + ((100 - importance) / 25))
importance_decay = days * 0.05
```

Both `weight` and `importance` are clamped between 0 and 100.

### Activation

Activating a concept finds memories associated with that concept and boosts their weight:

```python
memory.weight += association.strength * 0.25
```

The boosted memory is clamped to 100 and its `last_activated_at` timestamp is updated.

### Pattern detection

For the MVP, pattern detection is deliberately simple. If three or more memories share two or more concepts, the engine creates or strengthens a pattern. The first hardcoded template recognizes Jack/socks/laundry evidence as:

```text
Jack often leaves socks around the house.
```

### Opinion generation

Strong patterns become simple subjective opinions. For example, the Jack socks pattern can become:

```text
Jack tends to forget small household chores, especially laundry.
```

## Run tests

```bash
pytest
```

## Development notes

Constants such as decay rate, association boost factor, minimum pattern evidence count, and opinion strength threshold live at the top of their modules so the toy model can be tuned easily.
