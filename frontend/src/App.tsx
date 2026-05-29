import { Brain, Database, ListChecks, Settings, Terminal } from "lucide-react";
import { useState } from "react";

import { executeStep, sendChat } from "./api";
import { CommandInput } from "./components/CommandInput";
import { ContactMenu } from "./components/ContactMenu";
import { Conversation } from "./components/Conversation";
import { ExecutionLog } from "./components/ExecutionLog";
import { MemoryPanel } from "./components/MemoryPanel";
import { PlanPanel } from "./components/PlanPanel";
import type { ConversationMessage, MemoryRecord, Plan, PlanStep } from "./types";
import { speakTaskStatus } from "./voiceStatus";

interface AppProps {
  initialPlan?: Plan;
}

export default function App({ initialPlan }: AppProps) {
  const [safeMode, setSafeMode] = useState(true);
  const [messages, setMessages] = useState<ConversationMessage[]>(makeSeedMessages(true));
  const [plan, setPlan] = useState<Plan | undefined>(initialPlan);
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function submitCommand(message: string) {
    setBusy(true);
    setMessages((current) => [...current, makeMessage("user", message)]);
    try {
      const response = await sendChat(message, safeMode);
      setPlan(response.plan);
      setMemories(response.memories);
      setMessages((current) => [...current, makeMessage("assistant", response.assistant_message)]);
      const executionLogs = (response.execution_results ?? []).map((result) => `${result.tool}: ${result.output}`);
      setLogs((current) => [...executionLogs, `Plan created: ${response.plan.summary}`, ...current]);
      if (response.execution_results?.length) {
        speakTaskStatus(response.plan.summary);
      }
    } catch (error) {
      setMessages((current) => [...current, makeMessage("assistant", error instanceof Error ? error.message : "Command failed.")]);
    } finally {
      setBusy(false);
    }
  }

  async function approveStep(step: PlanStep) {
    updateStep(step.id, { status: "running" });
    try {
      const result = await executeStep(step, true);
      updateStep(step.id, { status: result.status });
      setLogs((current) => [`${step.title}: ${result.output}`, ...current]);
      speakTaskStatus(step.title);
    } catch (error) {
      updateStep(step.id, { status: "blocked" });
      setLogs((current) => [`${step.title}: ${error instanceof Error ? error.message : "blocked"}`, ...current]);
    }
  }

  function denyStep(step: PlanStep) {
    updateStep(step.id, { status: "denied" });
    setLogs((current) => [`${step.title}: denied by user`, ...current]);
  }

  function updateStep(id: string, patch: Partial<PlanStep>) {
    setPlan((current) => {
      if (!current) return current;
      return {
        ...current,
        steps: current.steps.map((step) => (step.id === id ? { ...step, ...patch } : step))
      };
    });
  }

  function toggleSafeMode() {
    setSafeMode((current) => {
      const next = !current;
      setMessages((messages) => [
        ...messages,
        makeMessage(
          "system",
          next
            ? "Safe Mode is on. NeuronOS will ask before risky terminal or file actions."
            : "Safe Mode is off. NeuronOS will auto-run approved-capable tasks, but dangerous commands still stay blocked."
        )
      ]);
      setLogs((logs) => [
        `Safe Mode ${next ? "enabled" : "disabled"}.`,
        ...logs
      ]);
      return next;
    });
  }

  return (
    <main className="app-shell">
      <div className="ambient-texture" />
      <div className="background-beam background-beam-a" />
      <div className="background-beam background-beam-b" />
      <div className="background-beam background-beam-c" />

      <header className="topbar">
        <div className="brand-block">
          <h1>NeuronOS</h1>
          <span>Local Desktop Assistant</span>
        </div>
        <div className="topbar-right">
          <div className="status-strip">
            <span>Windows-first</span>
            <span>Gemma Local</span>
            <button
              aria-label={safeMode ? "Turn Safe Mode Off" : "Turn Safe Mode On"}
              className="status-pill-button"
              onClick={toggleSafeMode}
              type="button"
            >
              {safeMode ? "Safe Mode On" : "Safe Mode Off"}
            </button>
          </div>
          <ContactMenu />
        </div>
      </header>

      <div className="workspace">
        <section className="center-stage">
          <Conversation messages={messages} />
          <CommandInput disabled={busy} onSubmit={submitCommand} />
        </section>

        <aside className="side-rail">
          <div className="rail-brand">
            <div className="rail-logo">
              <Brain size={24} />
            </div>
            <div>
              <strong>NeuronOS</strong>
              <span>Local Assistant Shell</span>
            </div>
          </div>
          <nav className="rail-tabs" aria-label="Assistant sections">
            <button className="active" type="button">
              <ListChecks size={18} />
              <span>Live Plan</span>
            </button>
            <button type="button">
              <Database size={18} />
              <span>Memory</span>
            </button>
            <button type="button">
              <Terminal size={18} />
              <span>Execution Log</span>
            </button>
          </nav>
          <PlanPanel onApprove={approveStep} onDeny={denyStep} plan={plan} />
          <MemoryPanel memories={memories} />
          <ExecutionLog logs={logs} />
          <div className="inference-card">
            <div className="inference-row">
              <span>Inference Active</span>
              <small>ID: GEMMA-LOCAL</small>
            </div>
            <div className="meter-block">
              <div>
                <span>Local Runtime</span>
                <strong>Online</strong>
              </div>
              <div className="meter"><i /></div>
            </div>
            <button type="button">
              <Settings size={17} />
              <span>System Settings</span>
            </button>
          </div>
        </aside>
      </div>
    </main>
  );
}

function makeMessage(role: ConversationMessage["role"], content: string): ConversationMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content
  };
}

function makeSeedMessages(safeMode: boolean): ConversationMessage[] {
  return [
    {
      id: "seed-system",
      role: "system",
      content: safeMode
        ? "Safe Mode is on. NeuronOS will ask before risky terminal or file actions."
        : "Safe Mode is off. NeuronOS will auto-run approved-capable tasks, but dangerous commands still stay blocked."
    },
    {
      id: "seed-assistant",
      role: "assistant",
      content: "Ready. Ask me a question, or tell me what to do on this machine."
    }
  ];
}
