import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "../src/App";

describe("Command Center", () => {
  it("submits a command and renders plan steps", async () => {
    const speak = vi.fn();
    let lastUtterance: { voice?: SpeechSynthesisVoice; rate?: number; pitch?: number } | undefined;
    class FakeSpeechSynthesisUtterance {
      text: string;
      voice?: SpeechSynthesisVoice;
      rate?: number;
      pitch?: number;
      volume?: number;
      constructor(text: string) {
        this.text = text;
        lastUtterance = this;
      }
    }
    Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
      configurable: true,
      value: FakeSpeechSynthesisUtterance
    });
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        cancel: vi.fn(),
        speak,
        getVoices: () => [
          { name: "Microsoft David Desktop", lang: "en-US" },
          { name: "Microsoft Zira Desktop", lang: "en-US" }
        ]
      }
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        assistant_message: "Opening Brave and preparing a search.",
        execution_results: [
          {
            step_id: "step-1",
            tool: "app.launch",
            status: "completed",
            output: "Launch requested for Brave."
          },
          {
            step_id: "step-2",
            tool: "browser.search",
            status: "completed",
            output: "Opened browser search for lo-fi music."
          }
        ],
        plan: {
          id: "plan-1",
          summary: "Open Brave and search for lo-fi music.",
          steps: [
            {
              id: "step-1",
              title: "Open Brave",
              tool: "app.launch",
              args: { app: "Brave" },
              requires_approval: false,
              status: "pending"
            },
            {
              id: "step-2",
              title: "Search the web",
              tool: "browser.search",
              args: { query: "lo-fi music" },
              requires_approval: false,
              status: "pending"
            }
          ]
        },
        memories: []
      })
    } as Response);

    render(<App />);
    await userEvent.type(screen.getByPlaceholderText("Ask NeuronOS..."), "Open Brave and search lo-fi music");
    await userEvent.click(screen.getByRole("button", { name: "Send command" }));

    await waitFor(() => expect(screen.getByText("Open Brave")).toBeInTheDocument());
    expect(screen.getByText("Search the web")).toBeInTheDocument();
    expect(screen.getByText("Opening Brave and preparing a search.")).toBeInTheDocument();
    expect(screen.getByText("app.launch: Launch requested for Brave.")).toBeInTheDocument();
    expect(screen.getByText("In Progress")).toBeInTheDocument();
    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(lastUtterance?.voice?.name).toBe("Microsoft Zira Desktop");
    expect(lastUtterance?.rate).toBe(0.92);
    expect(lastUtterance?.pitch).toBe(1.04);
  });

  it("shows approval actions for risky pending steps", () => {
    render(<App initialPlan={{
      id: "plan-approval",
      summary: "Run a terminal command.",
      steps: [{
        id: "step-terminal",
        title: "Run terminal command",
        tool: "terminal.run",
        args: { command: "dir" },
        requires_approval: true,
        status: "pending"
      }]
    }} />);

    expect(screen.getByRole("button", { name: "Approve Run terminal command" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deny Run terminal command" })).toBeInTheDocument();
  });

  it("handles older chat responses without execution_results", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        assistant_message: "I prepared the task.",
        plan: {
          id: "plan-old",
          summary: "Open Brave.",
          steps: [
            {
              id: "step-1",
              title: "Open Brave",
              tool: "app.launch",
              args: { app: "Brave" },
              requires_approval: false,
              status: "pending"
            }
          ]
        },
        memories: []
      })
    } as Response);

    render(<App />);
    await userEvent.type(screen.getByPlaceholderText("Ask NeuronOS..."), "open brave");
    await userEvent.click(screen.getByRole("button", { name: "Send command" }));

    await waitFor(() => expect(screen.getByText("I prepared the task.")).toBeInTheDocument());
    expect(screen.getByText("Plan created: Open Brave.")).toBeInTheDocument();
  });

  it("renders contact links in the top-right menu", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Contact Me" }));

    expect(screen.getByRole("link", { name: "GitHub" })).toHaveAttribute("href", "https://github.com/ANSHUL-REAL");
    expect(screen.getByRole("link", { name: "LinkedIn" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/anshul-nautiyal-42760236b/"
    );
    expect(screen.getByRole("link", { name: "Email" })).toHaveAttribute(
      "href",
      "mailto:anshulnautiyal0512@gmail.com"
    );
  });

  it("toggles safe mode and sends the state with chat requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        assistant_message: "Done.",
        execution_results: [],
        plan: {
          id: "plan-safe-mode",
          summary: "Run a terminal command with approval.",
          steps: [
            {
              id: "step-terminal",
              title: "Run terminal command",
              tool: "terminal.run",
              args: { command: "dir" },
              requires_approval: true,
              status: "pending"
            }
          ]
        },
        memories: []
      })
    } as Response);
    globalThis.fetch = fetchMock;

    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Turn Safe Mode Off" }));
    expect(screen.getByText("Safe Mode Off")).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText("Ask NeuronOS..."), "run dir");
    await userEvent.click(screen.getByRole("button", { name: "Send command" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/chat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ message: "run dir", safe_mode: false })
      })
    );
  });

  it("formats completed task responses as readable status cards", () => {
    render(<App initialPlan={{
      id: "plan-complete",
      summary: "Open Brave.",
      steps: []
    }} />);

    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Ask me a question, or tell me what to do on this machine.")).toBeInTheDocument();
  });

  it("speaks short status updates for system tasks", async () => {
    const speak = vi.fn();
    const utterances: Array<{ text: string }> = [];
    class FakeSpeechSynthesisUtterance {
      text: string;
      constructor(text: string) {
        this.text = text;
        utterances.push(this);
      }
    }
    Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
      configurable: true,
      value: FakeSpeechSynthesisUtterance
    });
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        cancel: vi.fn(),
        speak,
        getVoices: () => []
      }
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        assistant_message: "Done: Lower the volume.",
        execution_results: [
          {
            step_id: "step-volume",
            tool: "system.audio",
            status: "completed",
            output: "Lowered volume."
          }
        ],
        plan: {
          id: "plan-volume",
          summary: "Lower the volume.",
          steps: [
            {
              id: "step-volume",
              title: "Lower volume",
              tool: "system.audio",
              args: { direction: "down", amount: 10 },
              requires_approval: false,
              status: "pending"
            }
          ]
        },
        memories: []
      })
    } as Response);

    render(<App />);
    await userEvent.type(screen.getByPlaceholderText("Ask NeuronOS..."), "lower the volume");
    await userEvent.click(screen.getByRole("button", { name: "Send command" }));

    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(utterances[utterances.length - 1]?.text).toBe("Lower the volume.");
  });

  it("prefers natural female voices when available", async () => {
    let lastUtterance: { voice?: SpeechSynthesisVoice } | undefined;
    class FakeSpeechSynthesisUtterance {
      text: string;
      voice?: SpeechSynthesisVoice;
      constructor(text: string) {
        this.text = text;
        lastUtterance = this;
      }
    }
    Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
      configurable: true,
      value: FakeSpeechSynthesisUtterance
    });
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        cancel: vi.fn(),
        speak: vi.fn(),
        getVoices: () => [
          { name: "Microsoft David Desktop", lang: "en-US" },
          { name: "Microsoft Aria Online (Natural) - English", lang: "en-US" }
        ]
      }
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        assistant_message: "Done.",
        execution_results: [
          {
            step_id: "step-open",
            tool: "app.launch",
            status: "completed",
            output: "Launch requested for Brave."
          }
        ],
        plan: {
          id: "plan-open",
          summary: "Open Brave.",
          steps: [
            {
              id: "step-open",
              title: "Open Brave",
              tool: "app.launch",
              args: { app: "Brave" },
              requires_approval: false,
              status: "pending"
            }
          ]
        },
        memories: []
      })
    } as Response);

    render(<App />);
    await userEvent.type(screen.getByPlaceholderText("Ask NeuronOS..."), "open brave");
    await userEvent.click(screen.getByRole("button", { name: "Send command" }));

    await waitFor(() => expect(lastUtterance?.voice?.name).toContain("Aria Online"));
  });
});
