import type { ChatResponse, PlanStep } from "./types";

const API_BASE = import.meta.env.VITE_NEURONOS_API ?? "http://127.0.0.1:8000";

export async function sendChat(message: string, safeMode: boolean): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, safe_mode: safeMode })
  });

  if (!response.ok) {
    throw new Error(`Chat failed with ${response.status}`);
  }
  return response.json();
}

export async function executeStep(step: PlanStep, approved: boolean) {
  const response = await fetch(`${API_BASE}/api/tools/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      step_id: step.id,
      tool: step.tool,
      args: step.args,
      approved
    })
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Tool failed with ${response.status}`);
  }
  return response.json();
}

export async function transcribeAudio(blob: Blob): Promise<string> {
  const form = new FormData();
  form.append("file", blob, "command.webm");
  const response = await fetch(`${API_BASE}/api/voice/transcribe`, {
    method: "POST",
    body: form
  });
  if (!response.ok) {
    throw new Error(`Transcription failed with ${response.status}`);
  }
  const payload = await response.json();
  return payload.transcript;
}
