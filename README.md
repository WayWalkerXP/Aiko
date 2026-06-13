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
Jack often leaves socks around the home.
```

### Opinion generation

Strong patterns become simple subjective opinions. A pattern or opinion should stay concrete when the evidence only shows one recurring behavior. For example, the Jack socks pattern becomes:

```text
Jack often leaves socks around the home.
```

Broader household summaries are reserved for evidence that spans multiple behavior types, such as socks, dishes, and trash.

## Run tests

```bash
pytest
```

## Development notes

Constants such as decay rate, association boost factor, minimum pattern evidence count, and opinion strength threshold live at the top of their modules so the toy model can be tuned easily.

---

# Aiko Ollama Context Test Harness

This repository also includes a standalone Python CLI harness for experimenting with local LLM conversation continuity through Ollama. The harness is intentionally simple: it chats with a locally running Ollama model, periodically asks the model to summarize structured working memory, and occasionally rebuilds the active chat context from that memory plus a few recent verbatim turns.

## Purpose

`aiko_context_test.py` helps test whether a local model can remain coherent during longer conversations when the application uses two lightweight continuity techniques:

1. **Heartbeat memory synchronization**: every configured number of user messages, the model is asked to return JSON describing the current topic, user goals, important facts, open threads, emotional tone, and other continuity details.
2. **Context reset / rebuild**: every configured number of user messages, the script simulates clearing older context by rebuilding its local Ollama message list from the original starter prompt, the current working memory JSON, and the most recent turns.

The script does not depend on a special Ollama `/clear` command. It only rebuilds the local `messages` list that is sent to Ollama's `/api/chat` endpoint.

## Install dependencies

From the repository root, install the small runtime dependency set:

```bash
python -m pip install -r requirements.txt
```

The harness uses:

- `requests` for Ollama's HTTP API.
- `colorama` for cross-platform colored terminal output.
- `json-repair` for a last-chance heartbeat parser when a local model returns almost-valid JSON.

## Run Ollama

Install Ollama from <https://ollama.com/> if it is not already installed, then start the local server:

```bash
ollama serve
```

On many desktop installs, Ollama may already be running in the background. The sample configuration expects the server at:

```text
http://localhost:11434
```

## Pull a model

The sample INI file uses `gemma3:4b`:

```bash
ollama pull gemma3:4b
```

You can use another local model if it appears in:

```bash
ollama list
```

If you change models, update `model` in `aiko_context_test.ini`.

## Edit the INI file

All runtime settings live in `aiko_context_test.ini`:

```ini
[ollama]
base_url = http://localhost:11434
model = gemma3:4b

[prompt]
starter_prompt =
    You are Aiko, a warm, emotionally aware AI companion.
    Continue naturally and preserve conversational continuity.

[generation]
temperature = 0.7
top_p = 0.9
top_k = 40
repeat_penalty = 1.1
num_ctx = 8192
num_predict = 512
stream = true

[memory]
heartbeat_interval = 5
clear_interval = 15
recent_turns_to_keep = 4
use_ollama_json_mode = true
use_json_repair = true
log_raw_heartbeat = true

[logging]
log_dir = logs
save_full_transcript = true
debug = true
```

Important settings:

- `base_url`: Ollama server URL.
- `model`: local Ollama model name.
- `starter_prompt`: initial system prompt used at startup and after rebuilds.
- `heartbeat_interval`: number of user messages between automatic memory updates. Default behavior is 5 when omitted.
- `clear_interval`: number of user messages between automatic context rebuilds. Default behavior is 15 when omitted.
- `recent_turns_to_keep`: number of recent user/assistant turns to preserve verbatim during reset. Default behavior is 4 when omitted.
- `use_ollama_json_mode`: when `true`, heartbeat requests include Ollama's `"format": "json"` request option. This applies only to heartbeat memory synchronization calls, which are always sent with `stream = false`; normal chat responses can still use the global `stream` setting.
- `use_json_repair`: when `true`, the harness tries `json-repair` if direct `json.loads()` parsing fails for a heartbeat response.
- `log_raw_heartbeat`: when `true`, JSONL logs include the full raw and repaired heartbeat text. Set it to `false` to log response lengths instead.
- `stream`: when `true`, assistant tokens are printed as they arrive for normal chat responses.
- `save_full_transcript`: when `true`, full user and assistant text is written to the JSONL log.
- `debug`: when `true`, status messages show heartbeat/reset activity and a rough context-size estimate.

## Heartbeat JSON robustness

Heartbeat memory synchronization asks the model to return a fixed JSON object with keys such as `current_topic`, `important_facts`, `open_threads`, and `summary_since_last_heartbeat`. The harness now sends heartbeat calls to Ollama with JSON mode enabled by default:

```json
{
  "format": "json",
  "stream": false
}
```

JSON mode strongly nudges Ollama to produce parseable JSON, but malformed JSON can still happen with local models. A model may add explanatory text, wrap the response in markdown, omit a quote, or insert literal line breaks inside a quoted string value. Those responses may be semantically correct but still fail Python's strict `json.loads()` parser.

For that reason, heartbeat parsing is defensive:

1. The harness first tries `json.loads(raw_response)`.
2. If direct parsing fails and `use_json_repair = true`, it calls `json_repair.repair_json(raw_response)`.
3. It then tries `json.loads(repaired_response)`.
4. If repair still fails, the app logs the error and keeps the previous working memory instead of crashing.

After a heartbeat object is parsed, the harness validates the expected schema, fills missing keys with safe defaults, converts list fields that came back as strings into one-item lists, and joins string fields that came back as lists into single-line strings.

Raw heartbeat diagnostics are written to the JSONL log under the configured `log_dir`. Look for event types such as `heartbeat_started`, `heartbeat_raw_response`, `heartbeat_json_parse_succeeded`, `heartbeat_json_repair_attempted`, `heartbeat_json_repair_succeeded`, `heartbeat_json_repair_failed`, and `heartbeat_completed`. These events include the heartbeat prompt, raw model response when enabled, repaired response when repair was attempted, parse success/failure status, final parsed memory object, and parse errors.

To disable JSON mode or repair, edit the INI file:

```ini
[memory]
use_ollama_json_mode = false
use_json_repair = false
log_raw_heartbeat = false
```

Disabling `log_raw_heartbeat` is useful when you want smaller logs or do not want full conversation-derived heartbeat content written to disk.

## Run the chatbot

With Ollama running and the configured model pulled:

```bash
python aiko_context_test.py
```

To use a different configuration file:

```bash
python aiko_context_test.py --config path/to/other.ini
```

At startup, the script loads the INI file, connects to Ollama, checks that the requested model is available, places the starter prompt in the active message list as a system message, and opens a terminal chat loop.

## Slash commands

Inside the chat prompt, use:

- `/quit` exits the program.
- `/exit` exits the program.
- `/heartbeat` manually triggers a working-memory update.
- `/clear` manually rebuilds the active context from the memory packet and recent turns.
- `/memory` displays the current structured working memory.
- `/history` displays the currently retained active message history.
- `/help` displays available commands.

## Logs

The script creates one timestamped JSONL log file per run in the configured `log_dir`, which defaults to `logs`:

```text
logs/aiko_context_test_YYYYMMDDTHHMMSSZ.jsonl
```

Logged event types include:

- `program_start`
- `user_message`
- `assistant_message`
- `heartbeat_started`
- `heartbeat_completed`
- `heartbeat_parse_failed`
- `context_reset_started`
- `context_reset_completed`
- `ollama_error`
- `program_exit`

When `save_full_transcript = false`, user and assistant transcript events store message lengths instead of full content. Heartbeat prompts, heartbeat responses, parsed memory, reset packets, errors, and start/exit events are still logged for debugging the continuity experiment.

## What heartbeat means

A heartbeat is a memory synchronization pass. The script sends the current conversation plus a JSON-only instruction asking the model to update this structure:

```json
{
  "current_topic": "",
  "user_goal": "",
  "important_facts": [],
  "open_threads": [],
  "emotional_tone": "",
  "assistant_stance": "",
  "recent_references": [],
  "must_not_forget_next": [],
  "summary_since_last_heartbeat": ""
}
```

If the model returns valid JSON, the parsed object becomes the new working memory. If parsing fails, the raw response is logged, the previous memory is preserved, and chat continues.

## What reset means

A reset is a local context rebuild. The script preserves the working memory and the last configured number of recent user/assistant turns, then replaces the active message list with:

1. The original starter/system prompt.
2. A system continuity packet containing the current memory JSON and recent turns.
3. The recent turns themselves.

The next user message is then sent normally. The model is instructed not to mention that context was reset.

## Known limitations

- The token/context display is only a rough character-count estimate, not a tokenizer-accurate count.
- The heartbeat JSON is generated by the model and can be incomplete, stale, or invalid.
- The reset packet can omit older details if the heartbeat memory failed to capture them.
- The harness uses Ollama's HTTP API directly and does not implement retries, tool calling, embeddings, or persistent long-term memory.
- Very small or heavily quantized models may struggle to produce strict JSON or preserve subtle conversational continuity.
