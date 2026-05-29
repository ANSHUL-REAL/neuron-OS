from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Protocol

from .main import create_app
from .schemas import ChatRequest


class AssistantClient(Protocol):
    def handle(self, message: str) -> dict:
        ...


class InProcessAssistantClient:
    def __init__(self, data_dir: Path | None = None):
        self.app = create_app(data_dir=data_dir)

    def handle(self, message: str) -> dict:
        route = next(
            route
            for route in self.app.routes
            if getattr(route, "path", None) == "/api/chat"
            and "POST" in getattr(route, "methods", set())
        )
        result = route.endpoint(ChatRequest(message=message))
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        return result.model_dump()


def run_local_command(message: str, client: AssistantClient | None = None) -> str:
    assistant = client or InProcessAssistantClient()
    payload = assistant.handle(message)
    lines = [payload["assistant_message"], ""]
    plan = payload["plan"]
    lines.append(f"Plan: {plan.summary if hasattr(plan, 'summary') else plan['summary']}")

    execution_results = payload.get("execution_results", [])
    if execution_results:
        lines.append("Executed:")
        for result in execution_results:
            tool = result.tool if hasattr(result, "tool") else result["tool"]
            output = result.output if hasattr(result, "output") else result["output"]
            lines.append(f"- {tool}: {output}")
    else:
        lines.append("No safe steps were auto-executed. Approval may be required.")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a NeuronOS local assistant command.")
    parser.add_argument("message", nargs="+", help="Command for NeuronOS to execute")
    args = parser.parse_args()
    print(run_local_command(" ".join(args.message)))


if __name__ == "__main__":
    main()
