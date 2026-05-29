import { Check, ShieldAlert, X } from "lucide-react";

import type { Plan, PlanStep } from "../types";

interface Props {
  plan?: Plan;
  onApprove: (step: PlanStep) => void;
  onDeny: (step: PlanStep) => void;
}

export function PlanPanel({ plan, onApprove, onDeny }: Props) {
  return (
    <aside className="panel plan-panel" aria-label="Plan steps">
      <div className="panel-heading">
        <h2>Plan</h2>
        <span>{plan ? `${plan.steps.length} steps` : "idle"}</span>
      </div>
      <p className="panel-summary">{plan?.summary ?? "Send a command to generate a local execution plan."}</p>
      <div className="step-list">
        {plan?.steps.map((step) => (
          <div className="step-row" key={step.id}>
            <div>
              <strong>{step.title}</strong>
              <span>{step.tool}</span>
            </div>
            <StatusBadge step={step} />
            {step.requires_approval && step.status === "pending" ? (
              <div className="approval-actions">
                <button aria-label={`Approve ${step.title}`} onClick={() => onApprove(step)} type="button">
                  <Check size={15} />
                </button>
                <button aria-label={`Deny ${step.title}`} onClick={() => onDeny(step)} type="button">
                  <X size={15} />
                </button>
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </aside>
  );
}

function StatusBadge({ step }: { step: PlanStep }) {
  return (
    <span className={`status ${step.status}`}>
      {step.requires_approval ? <ShieldAlert size={13} /> : null}
      {step.status}
    </span>
  );
}
