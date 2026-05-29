from neuronos.cli import run_local_command
from neuronos.schemas import Plan, PlanStep, ToolExecuteResponse


class FakeAssistantClient:
    def handle(self, message: str):
        return {
            "assistant_message": f"handled {message}",
            "plan": Plan(
                summary="Do the thing.",
                steps=[
                    PlanStep(
                        id="step-safe",
                        title="Open app",
                        tool="app.launch",
                        args={"app": "Brave"},
                    )
                ],
            ),
            "execution_results": [
                ToolExecuteResponse(
                    step_id="step-safe",
                    tool="app.launch",
                    status="completed",
                    output="Launch requested for Brave.",
                )
            ],
            "memories": [],
        }


def test_run_local_command_returns_assistant_text_and_execution_results():
    output = run_local_command("open brave", client=FakeAssistantClient())

    assert "handled open brave" in output
    assert "app.launch: Launch requested for Brave." in output
