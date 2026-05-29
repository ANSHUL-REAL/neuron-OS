from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import resolve_data_dir
from .memory import MemoryStore
from .planner import Planner
from .providers import OllamaProvider
from .safety import SafetyPolicy
from .schemas import (
    ChatRequest,
    ChatResponse,
    EventRecord,
    ToolExecuteRequest,
    TranscriptionResponse,
)
from .tools import ToolBlockedError, ToolExecutor
from .voice import VoiceService


def create_app(data_dir: Path | None = None, tool_executor=None, provider_override=None) -> FastAPI:
    data_root = data_dir or resolve_data_dir()
    memory = MemoryStore(data_root / "neuronos.db", collection_path=data_root / "chroma")
    planner = Planner()
    provider = provider_override or OllamaProvider()
    safety = SafetyPolicy(workspace_root=Path.cwd())
    tools = tool_executor or ToolExecutor(memory, safety)
    voice = VoiceService()
    events: list[EventRecord] = []

    app = FastAPI(title="NeuronOS Assistant Core", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:1420",
            "http://127.0.0.1:1420",
            "http://localhost:1421",
            "http://127.0.0.1:1421",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        memory.save_conversation("user", request.message)
        plan = planner.build_plan(request.message)
        assistant_message = _initial_assistant_message(plan)
        memories = memory.search(request.message)
        execution_results = []
        for step in plan.steps:
            if step.tool == "conversation.respond":
                continue
            if step.requires_approval and request.safe_mode:
                continue
            try:
                result = tools.execute(
                    ToolExecuteRequest(
                        step_id=step.id,
                        tool=step.tool,
                        args=step.args,
                        approved=step.requires_approval and not request.safe_mode,
                    )
                )
                execution_results.append(result)
                if step.tool == "memory.write" and result.status == "completed":
                    _save_memory_from_step(memory, step.args)
                step.status = result.status
            except ToolBlockedError as exc:
                step.status = "blocked"
                memory.record_execution(step.id, step.tool, "blocked", str(exc))
        if execution_results:
            assistant_message = f"Done: {plan.summary}"
        elif _needs_model_response(plan):
            assistant_message = _recall_answer(memory, request.message, memories)
            if assistant_message is None:
                assistant_message = await provider.respond(request.message)
        memory.save_conversation("assistant", assistant_message)
        events.append(
            EventRecord(
                type="plan.created",
                message=plan.summary,
                payload=plan.model_dump(),
            )
        )
        return ChatResponse(
            assistant_message=assistant_message,
            plan=plan,
            execution_results=execution_results,
            memories=memories,
        )

    @app.post("/api/tools/execute")
    def execute_tool(request: ToolExecuteRequest):
        try:
            response = tools.execute(request)
        except ToolBlockedError as exc:
            memory.record_execution(request.step_id, request.tool, "blocked", str(exc))
            raise HTTPException(status_code=403, detail=f"Tool blocked: {exc}") from exc
        events.append(
            EventRecord(
                type="tool.completed",
                message=response.output,
                payload=response.model_dump(),
            )
        )
        return response

    @app.get("/api/memory/search")
    def search_memory(q: str) -> dict[str, list[dict]]:
        return {"results": [record.model_dump() for record in memory.search(q)]}

    @app.get("/api/events")
    async def stream_events():
        async def event_source():
            seen = 0
            while True:
                for event in events[seen:]:
                    yield f"data: {event.model_dump_json()}\\n\\n"
                seen = len(events)
                await asyncio.sleep(1)

        return StreamingResponse(event_source(), media_type="text/event-stream")

    @app.post("/api/voice/transcribe", response_model=TranscriptionResponse)
    async def transcribe(file: UploadFile = File(...)) -> TranscriptionResponse:
        audio_dir = data_root / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        target = audio_dir / file.filename
        target.write_bytes(await file.read())
        return TranscriptionResponse(transcript=voice.transcribe(target))

    return app


app = create_app()


def _needs_model_response(plan) -> bool:
    return all(step.tool == "conversation.respond" for step in plan.steps)


def _initial_assistant_message(plan) -> str:
    if _needs_model_response(plan):
        return "Thinking..."
    if any(step.requires_approval for step in plan.steps):
        return f"Ready when you approve: {plan.summary}"
    return f"Working on it: {plan.summary}"


def _recall_answer(memory: MemoryStore, message: str, memories) -> str | None:
    if _is_recent_recall_question(message):
        recent = _recent_user_message(memory, message)
        if recent:
            return f"You just said: {recent}"
    if _is_memory_recall_question(message) and memories:
        return f"I remember: {memories[0].content}"
    return None


def _save_memory_from_step(memory: MemoryStore, args: dict) -> None:
    content = str(args.get("content", "")).strip()
    if not content:
        return
    kind = str(args.get("kind", "note")).strip() or "note"
    memory.save_memory(kind, content)


def _recent_user_message(memory: MemoryStore, current_message: str) -> str | None:
    current = current_message.strip().lower()
    for row in memory.recent_conversations(limit=12):
        content = row["content"].strip()
        if row["role"] == "user" and content.lower() != current:
            return content
    return None


def _is_recent_recall_question(message: str) -> bool:
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in (
            "what did i just say",
            "what did i say before",
            "what was my last message",
            "what did i tell you",
            "what i said",
        )
    )


def _is_memory_recall_question(message: str) -> bool:
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in (
            "what is my",
            "what's my",
            "where is my",
            "do you remember",
            "do you know my",
        )
    )
