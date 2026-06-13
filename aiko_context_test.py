#!/usr/bin/env python3
"""Terminal harness for testing Ollama conversation continuity.

This script intentionally keeps all behavior configurable through an INI file so
local model, generation, memory, reset, logging, and display choices can be
changed without editing code.
"""

from __future__ import annotations

import argparse
import configparser
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from colorama import Fore, Style, init as colorama_init


MEMORY_TEMPLATE: dict[str, Any] = {
    "current_topic": "",
    "user_goal": "",
    "important_facts": [],
    "open_threads": [],
    "emotional_tone": "",
    "assistant_stance": "",
    "recent_references": [],
    "must_not_forget_next": [],
    "summary_since_last_heartbeat": "",
}

COMMANDS = {
    "/quit": "Exit the program.",
    "/exit": "Exit the program.",
    "/heartbeat": "Manually update the structured working memory.",
    "/clear": "Manually rebuild the active context from memory and recent turns.",
    "/memory": "Display the current working memory JSON.",
    "/history": "Display the retained active conversation history.",
    "/help": "Display this command list.",
}


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str
    model: str


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    num_ctx: int
    num_predict: int
    stream: bool


@dataclass(frozen=True)
class MemoryConfig:
    heartbeat_interval: int = 5
    clear_interval: int = 15
    recent_turns_to_keep: int = 4


@dataclass(frozen=True)
class LoggingConfig:
    log_dir: Path
    save_full_transcript: bool
    debug: bool


@dataclass(frozen=True)
class AppConfig:
    ollama: OllamaConfig
    starter_prompt: str
    generation: GenerationConfig
    memory: MemoryConfig
    logging: LoggingConfig


@dataclass
class JsonlLogger:
    log_dir: Path
    save_full_transcript: bool
    path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = self.log_dir / f"aiko_context_test_{timestamp}.jsonl"

    def write(self, event_type: str, **payload: Any) -> None:
        event = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(event, ensure_ascii=False) + "\n")


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def check_connection(self) -> list[str]:
        response = requests.get(f"{self.base_url}/api/tags", timeout=10)
        response.raise_for_status()
        data = response.json()
        return [model.get("name", "") for model in data.get("models", [])]

    def chat(
        self,
        messages: list[dict[str, str]],
        options: dict[str, Any],
        stream: bool,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "options": options,
            "stream": stream,
        }
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            stream=stream,
            timeout=self.timeout,
        )
        response.raise_for_status()

        if stream:
            return self._consume_stream(response)

        data = response.json()
        return data.get("message", {}).get("content", "")

    @staticmethod
    def _consume_stream(response: requests.Response) -> str:
        chunks: list[str] = []
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            data = json.loads(raw_line)
            content = data.get("message", {}).get("content", "")
            if content:
                print(Fore.GREEN + content + Style.RESET_ALL, end="", flush=True)
                chunks.append(content)
            if data.get("done"):
                break
        print()
        return "".join(chunks)


class AikoContextHarness:
    def __init__(self, config: AppConfig, logger: JsonlLogger) -> None:
        self.config = config
        self.logger = logger
        self.client = OllamaClient(config.ollama.base_url, config.ollama.model)
        self.working_memory: dict[str, Any] = dict(MEMORY_TEMPLATE)
        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": config.starter_prompt}
        ]
        self.user_message_count = 0

    @property
    def generation_options(self) -> dict[str, Any]:
        generation = self.config.generation
        return {
            "temperature": generation.temperature,
            "top_p": generation.top_p,
            "top_k": generation.top_k,
            "repeat_penalty": generation.repeat_penalty,
            "num_ctx": generation.num_ctx,
            "num_predict": generation.num_predict,
        }

    def run(self) -> None:
        self._log_start()
        if not self._connect_and_confirm_model():
            return

        self._status("Type /help for commands. Type /quit or /exit to leave.")
        self._status(self._context_risk_summary())

        try:
            while True:
                try:
                    user_input = input(Fore.CYAN + "You> " + Style.RESET_ALL).strip()
                except EOFError:
                    print()
                    break

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    should_continue = self._handle_command(user_input)
                    if not should_continue:
                        break
                    continue

                self._handle_user_message(user_input)
        except KeyboardInterrupt:
            print()
            self._status("Interrupted. Exiting.")
        finally:
            self.logger.write("program_exit")
            self._status(f"Log written to {self.logger.path}")

    def _log_start(self) -> None:
        self.logger.write(
            "program_start",
            config={
                "ollama": asdict(self.config.ollama),
                "starter_prompt": self.config.starter_prompt,
                "generation": asdict(self.config.generation),
                "memory": asdict(self.config.memory),
                "logging": {
                    "log_dir": str(self.config.logging.log_dir),
                    "save_full_transcript": self.config.logging.save_full_transcript,
                    "debug": self.config.logging.debug,
                },
            },
        )

    def _connect_and_confirm_model(self) -> bool:
        self._status(f"Connecting to Ollama at {self.config.ollama.base_url}...")
        try:
            models = self.client.check_connection()
        except requests.RequestException as exc:
            self._error(f"Could not connect to Ollama: {exc}")
            self.logger.write("ollama_error", operation="check_connection", error=str(exc))
            return False
        except json.JSONDecodeError as exc:
            self._error(f"Ollama returned invalid model-list JSON: {exc}")
            self.logger.write("ollama_error", operation="check_connection", error=str(exc))
            return False

        if self.config.ollama.model not in models:
            self._error(
                f"Model '{self.config.ollama.model}' was not found. "
                f"Available models: {', '.join(models) if models else '(none)'}"
            )
            self.logger.write(
                "ollama_error",
                operation="model_check",
                error="model_not_found",
                requested_model=self.config.ollama.model,
                available_models=models,
            )
            return False

        self._status(f"Connected. Using model {self.config.ollama.model}.")
        return True

    def _handle_user_message(self, content: str) -> None:
        self.user_message_count += 1
        self.messages.append({"role": "user", "content": content})
        self._log_transcript_event("user_message", content)

        try:
            if self.config.generation.stream:
                print(Fore.GREEN + "Aiko> " + Style.RESET_ALL, end="", flush=True)
            reply = self.client.chat(
                self.messages,
                self.generation_options,
                stream=self.config.generation.stream,
            )
            if not self.config.generation.stream:
                print(Fore.GREEN + f"Aiko> {reply}" + Style.RESET_ALL)
        except (requests.RequestException, json.JSONDecodeError) as exc:
            self._error(f"Ollama chat failed: {exc}")
            self.logger.write("ollama_error", operation="chat", error=str(exc))
            self.messages.pop()
            return

        self.messages.append({"role": "assistant", "content": reply})
        self._log_transcript_event("assistant_message", reply)
        self._debug(self._context_risk_summary())
        self._maybe_trigger_maintenance()

    def _maybe_trigger_maintenance(self) -> None:
        memory = self.config.memory
        if memory.heartbeat_interval > 0 and self.user_message_count % memory.heartbeat_interval == 0:
            self.perform_heartbeat()
        if memory.clear_interval > 0 and self.user_message_count % memory.clear_interval == 0:
            self.perform_context_reset()

    def _handle_command(self, command: str) -> bool:
        normalized = command.lower()
        if normalized in {"/quit", "/exit"}:
            return False
        if normalized == "/help":
            self.show_help()
        elif normalized == "/heartbeat":
            self.perform_heartbeat()
        elif normalized == "/clear":
            self.perform_context_reset()
        elif normalized == "/memory":
            self.show_memory()
        elif normalized == "/history":
            self.show_history()
        else:
            self._error(f"Unknown command: {command}. Type /help for commands.")
        return True

    def perform_heartbeat(self) -> None:
        self._debug("[heartbeat] Updating working memory...")
        prompt = self._heartbeat_prompt()
        heartbeat_messages = [*self.messages, {"role": "user", "content": prompt}]
        self.logger.write("heartbeat_started", prompt=prompt)

        try:
            raw_response = self.client.chat(
                heartbeat_messages,
                self.generation_options,
                stream=False,
            )
        except (requests.RequestException, json.JSONDecodeError) as exc:
            self._error(f"Heartbeat failed: {exc}")
            self.logger.write("ollama_error", operation="heartbeat", error=str(exc))
            return

        parsed = parse_memory_json(raw_response)
        if parsed is None:
            self._error("Heartbeat response was not valid JSON. Keeping previous memory.")
            self.logger.write(
                "heartbeat_parse_failed",
                raw_response=raw_response,
                previous_memory=self.working_memory,
            )
            return

        self.working_memory = normalize_memory(parsed)
        self.logger.write(
            "heartbeat_completed",
            raw_response=raw_response,
            parsed_memory=self.working_memory,
        )
        self._debug("[heartbeat] Working memory updated.")

    def perform_context_reset(self) -> None:
        self._debug("[reset] Rebuilding context from memory packet...")
        self.logger.write("context_reset_started", message_count=len(self.messages))
        recent_messages = self._recent_turn_messages(self.config.memory.recent_turns_to_keep)
        packet = self._continuity_packet(recent_messages)
        self.messages = [
            {"role": "system", "content": self.config.starter_prompt},
            {"role": "system", "content": packet},
            *recent_messages,
        ]
        self.logger.write(
            "context_reset_completed",
            continuity_packet=packet,
            retained_messages=recent_messages,
            message_count=len(self.messages),
        )
        self._debug("[reset] Context rebuilt. Continue chatting normally.")
        self._debug(self._context_risk_summary())

    def _heartbeat_prompt(self) -> str:
        return (
            "Update the structured working memory for this conversation. "
            "Return JSON only, with no markdown, commentary, or code fence.\n\n"
            "Use this exact object shape:\n"
            f"{json.dumps(MEMORY_TEMPLATE, ensure_ascii=False, indent=2)}\n\n"
            "Preserve durable facts from the existing working memory when still relevant.\n"
            "Existing working memory:\n"
            f"{json.dumps(self.working_memory, ensure_ascii=False, indent=2)}"
        )

    def _continuity_packet(self, recent_messages: list[dict[str, str]]) -> str:
        return (
            "Conversation continuity packet:\n\n"
            "You are continuing an existing conversation. Do not mention that context was reset.\n\n"
            "Current working memory:\n"
            f"{json.dumps(self.working_memory, ensure_ascii=False, indent=2)}\n\n"
            "Recent conversation turns:\n"
            f"{format_messages(recent_messages)}\n\n"
            "Continue naturally as if no reset occurred."
        )

    def _recent_turn_messages(self, turns_to_keep: int) -> list[dict[str, str]]:
        if turns_to_keep <= 0:
            return []
        chat_messages = [
            message for message in self.messages if message["role"] in {"user", "assistant"}
        ]
        return chat_messages[-turns_to_keep * 2 :]

    def show_help(self) -> None:
        self._status("Available commands:")
        for command, description in COMMANDS.items():
            self._status(f"  {command:<12} {description}")

    def show_memory(self) -> None:
        self._status(json.dumps(self.working_memory, ensure_ascii=False, indent=2))

    def show_history(self) -> None:
        self._status(format_messages(self.messages) or "(history is empty)")

    def _context_risk_summary(self) -> str:
        characters = sum(len(message.get("content", "")) for message in self.messages)
        estimated_tokens = max(1, characters // 4)
        percent = (estimated_tokens / self.config.generation.num_ctx) * 100
        return (
            f"[context] approx {estimated_tokens:,}/{self.config.generation.num_ctx:,} "
            f"tokens ({percent:.1f}%) based on {characters:,} characters."
        )

    def _log_transcript_event(self, event_type: str, content: str) -> None:
        if self.logger.save_full_transcript:
            self.logger.write(event_type, content=content)
        else:
            self.logger.write(event_type, content_length=len(content))

    def _status(self, message: str) -> None:
        print(Fore.YELLOW + message + Style.RESET_ALL)

    def _debug(self, message: str) -> None:
        if self.config.logging.debug:
            self._status(message)

    def _error(self, message: str) -> None:
        print(Fore.RED + message + Style.RESET_ALL, file=sys.stderr)


def parse_config(path: Path) -> AppConfig:
    parser = configparser.ConfigParser()
    if not parser.read(path, encoding="utf-8"):
        raise FileNotFoundError(f"Could not read INI file: {path}")

    return AppConfig(
        ollama=OllamaConfig(
            base_url=parser.get("ollama", "base_url"),
            model=parser.get("ollama", "model"),
        ),
        starter_prompt=parser.get("prompt", "starter_prompt"),
        generation=GenerationConfig(
            temperature=parser.getfloat("generation", "temperature"),
            top_p=parser.getfloat("generation", "top_p"),
            top_k=parser.getint("generation", "top_k"),
            repeat_penalty=parser.getfloat("generation", "repeat_penalty"),
            num_ctx=parser.getint("generation", "num_ctx"),
            num_predict=parser.getint("generation", "num_predict"),
            stream=parser.getboolean("generation", "stream"),
        ),
        memory=MemoryConfig(
            heartbeat_interval=parser.getint("memory", "heartbeat_interval", fallback=5),
            clear_interval=parser.getint("memory", "clear_interval", fallback=15),
            recent_turns_to_keep=parser.getint("memory", "recent_turns_to_keep", fallback=4),
        ),
        logging=LoggingConfig(
            log_dir=Path(parser.get("logging", "log_dir")),
            save_full_transcript=parser.getboolean(
                "logging", "save_full_transcript", fallback=True
            ),
            debug=parser.getboolean("logging", "debug", fallback=True),
        ),
    )


def parse_memory_json(raw_response: str) -> dict[str, Any] | None:
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    return data


def normalize_memory(memory: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(MEMORY_TEMPLATE)
    for key, default in MEMORY_TEMPLATE.items():
        value = memory.get(key, default)
        if isinstance(default, list) and not isinstance(value, list):
            value = [str(value)] if value else []
        elif isinstance(default, str) and not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False) if value else ""
        normalized[key] = value
    return normalized


def format_messages(messages: Iterable[dict[str, str]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = message.get("role", "unknown").upper()
        content = message.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test Ollama conversation continuity with heartbeat memory resets."
    )
    parser.add_argument(
        "--config",
        default="aiko_context_test.ini",
        help="Path to INI configuration file (default: aiko_context_test.ini).",
    )
    return parser


def main() -> int:
    colorama_init(autoreset=True)
    args = build_arg_parser().parse_args()
    try:
        config = parse_config(Path(args.config))
    except (configparser.Error, OSError, ValueError) as exc:
        print(Fore.RED + f"Configuration error: {exc}" + Style.RESET_ALL, file=sys.stderr)
        return 2

    logger = JsonlLogger(config.logging.log_dir, config.logging.save_full_transcript)
    harness = AikoContextHarness(config, logger)
    harness.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
