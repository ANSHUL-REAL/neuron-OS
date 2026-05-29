export type StepStatus = "pending" | "running" | "completed" | "failed" | "blocked" | "denied";

export interface PlanStep {
  id: string;
  title: string;
  tool: string;
  args: Record<string, unknown>;
  requires_approval: boolean;
  status: StepStatus;
}

export interface Plan {
  id: string;
  summary: string;
  steps: PlanStep[];
}

export interface MemoryRecord {
  id: number;
  kind: string;
  content: string;
  created_at: string;
}

export interface ChatResponse {
  assistant_message: string;
  plan: Plan;
  execution_results: Array<{
    step_id: string;
    tool: string;
    status: StepStatus;
    output: string;
  }>;
  memories: MemoryRecord[];
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
}
