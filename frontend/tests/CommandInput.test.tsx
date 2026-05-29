import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CommandInput } from "../src/components/CommandInput";

vi.mock("../src/api", () => ({
  transcribeAudio: vi.fn(async () => "open brave")
}));

describe("CommandInput", () => {
  it("shows a clear voice error when microphone APIs are unavailable", async () => {
    const originalMediaDevices = navigator.mediaDevices;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: undefined
    });

    render(<CommandInput disabled={false} onSubmit={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Start voice recording" }));

    expect(screen.getByText("Voice input is not available in this browser.")).toBeInTheDocument();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: originalMediaDevices
    });
  });

  it("submits the transcript after recording stops", async () => {
    const onSubmit = vi.fn();
    let recorder: FakeMediaRecorder | undefined;
    class FakeMediaRecorder {
      ondataavailable?: (event: { data: Blob }) => void;
      onstop?: () => void;
      constructor() {
        recorder = this;
      }
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob(["audio"]) });
        this.onstop?.();
      }
    }
    Object.defineProperty(globalThis, "MediaRecorder", {
      configurable: true,
      value: FakeMediaRecorder
    });
    const getUserMedia = vi.fn(async () => ({
      getTracks: () => [{ stop: vi.fn() }]
    }));
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia
      }
    });

    render(<CommandInput disabled={false} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole("button", { name: "Start voice recording" }));
    await userEvent.click(screen.getByRole("button", { name: "Stop voice recording" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("open brave"));
    expect(getUserMedia).toHaveBeenCalledWith({
      audio: {
        autoGainControl: true,
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 48000
      }
    });
    expect(recorder).toBeDefined();
  });

  it("shows the voice orb surface while idle and recording", async () => {
    let recorder: FakeMediaRecorder | undefined;
    class FakeMediaRecorder {
      ondataavailable?: (event: { data: Blob }) => void;
      onstop?: () => void;
      constructor() {
        recorder = this;
      }
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob(["audio"]) });
        this.onstop?.();
      }
    }
    Object.defineProperty(globalThis, "MediaRecorder", {
      configurable: true,
      value: FakeMediaRecorder
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn(async () => ({
          getTracks: () => [{ stop: vi.fn() }]
        }))
      }
    });

    render(<CommandInput disabled={false} onSubmit={vi.fn()} />);

    expect(screen.getByLabelText("Voice orb")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start voice recording" }));
    expect(screen.getByText("Listening...")).toBeInTheDocument();
    expect(recorder).toBeDefined();
  });
});
