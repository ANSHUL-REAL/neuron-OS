from fastapi.testclient import TestClient

from neuronos.main import create_app
from neuronos.schemas import ToolExecuteResponse


class FakeToolExecutor:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return ToolExecuteResponse(
            step_id=request.step_id,
            tool=request.tool,
            status="completed",
            output=f"executed {request.tool}",
        )


class FakeProvider:
    def __init__(self, response: str = "provider reply"):
        self.calls = []
        self.response = response

    async def respond(self, message: str):
        self.calls.append(message)
        return self.response


def test_chat_endpoint_returns_plan_and_persists_conversation(tmp_path):
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "Open Brave and search lo-fi music"})

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]
    assert body["plan"]["steps"][0]["tool"] == "app.launch"
    assert body["plan"]["steps"][1]["tool"] == "browser.search"


def test_chat_endpoint_executes_safe_steps_immediately(tmp_path):
    fake_tools = FakeToolExecutor()
    fake_provider = FakeProvider()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools, provider_override=fake_provider)
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "Open Brave and search lo-fi music"})

    assert response.status_code == 200
    body = response.json()
    assert [item["tool"] for item in body["execution_results"]] == [
        "app.launch",
        "browser.search",
    ]
    assert all(item["status"] == "completed" for item in body["execution_results"])
    assert len(fake_tools.requests) == 2
    assert fake_provider.calls == []


def test_chat_endpoint_does_not_execute_steps_requiring_approval(tmp_path):
    fake_tools = FakeToolExecutor()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools)
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "run dir"})

    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["steps"][0]["requires_approval"] is True
    assert body["execution_results"] == []
    assert fake_tools.requests == []


def test_chat_endpoint_executes_approval_steps_when_safe_mode_is_off(tmp_path):
    fake_tools = FakeToolExecutor()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools)
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "run dir", "safe_mode": False})

    assert response.status_code == 200
    body = response.json()
    assert [item["tool"] for item in body["execution_results"]] == ["terminal.run"]
    assert fake_tools.requests[0].approved is True


def test_chat_endpoint_runs_restart_without_approval(tmp_path):
    fake_tools = FakeToolExecutor()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools)
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "restart the pc", "safe_mode": True})

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"] == "Done: Restart the PC."
    assert [item["tool"] for item in body["execution_results"]] == ["system.power"]
    assert fake_tools.requests[0].approved is False


def test_chat_endpoint_leaves_shutdown_pending_in_safe_mode(tmp_path):
    fake_tools = FakeToolExecutor()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools)
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "shutdown the pc", "safe_mode": True})

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"] == "Ready when you approve: Shut down the PC."
    assert body["plan"]["steps"][0]["requires_approval"] is True
    assert body["execution_results"] == []
    assert fake_tools.requests == []


def test_chat_endpoint_response_matches_youtube_plan(tmp_path):
    fake_tools = FakeToolExecutor()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools)
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"message": "open brave and then in it open youtube and play faded song"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["summary"] == "Open Brave and play Faded on YouTube."
    assert body["assistant_message"] == "Done: Open Brave and play Faded on YouTube."


def test_chat_endpoint_executes_global_warming_youtube_request(tmp_path):
    fake_tools = FakeToolExecutor()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools)
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"message": "Open the raise and open YouTube and video on global warming."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["summary"] == "Open Brave and play Global Warming on YouTube."
    assert [item["tool"] for item in body["execution_results"]] == [
        "app.launch",
        "browser.play_youtube",
    ]


def test_general_question_uses_chat_response_without_executing_conversation_step(tmp_path):
    fake_tools = FakeToolExecutor()
    fake_provider = FakeProvider("LangGraph is a graph orchestration library.")
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools, provider_override=fake_provider)
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "What is LangGraph?"})

    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["steps"][0]["tool"] == "conversation.respond"
    assert body["assistant_message"] == "LangGraph is a graph orchestration library."
    assert body["execution_results"] == []
    assert fake_tools.requests == []
    assert fake_provider.calls == ["What is LangGraph?"]


def test_chat_endpoint_answers_recent_conversation_recall(tmp_path):
    fake_tools = FakeToolExecutor()
    fake_provider = FakeProvider("provider should not be used")
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools, provider_override=fake_provider)
    client = TestClient(app)

    client.post("/api/chat", json={"message": "open brave and open gmail"})
    response = client.post("/api/chat", json={"message": "what did I just say?"})

    assert response.status_code == 200
    body = response.json()
    assert "open brave and open gmail" in body["assistant_message"].lower()
    assert fake_provider.calls == []


def test_chat_endpoint_answers_saved_memory_recall(tmp_path):
    fake_tools = FakeToolExecutor()
    fake_provider = FakeProvider("provider should not be used")
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools, provider_override=fake_provider)
    client = TestClient(app)

    client.post("/api/chat", json={"message": "remember that my name is Anshul"})
    response = client.post("/api/chat", json={"message": "what is my name?"})

    assert response.status_code == 200
    body = response.json()
    assert "my name is Anshul" in body["assistant_message"]
    assert fake_provider.calls == []


def test_chat_endpoint_executes_chatgpt_open_request(tmp_path):
    fake_tools = FakeToolExecutor()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools)
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"message": "open brave and search chatgpt and open it"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["summary"] == "Open Brave and open ChatGPT."
    assert [item["tool"] for item in body["execution_results"]] == [
        "app.launch",
        "browser.open_url",
    ]


def test_chat_endpoint_executes_direct_chatgpt_open_without_saying_brave(tmp_path):
    fake_tools = FakeToolExecutor()
    fake_provider = FakeProvider("provider should not be used")
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools, provider_override=fake_provider)
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "i want to open chatgpt"})

    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["summary"] == "Open Brave and open ChatGPT."
    assert [item["tool"] for item in body["execution_results"]] == [
        "app.launch",
        "browser.open_url",
    ]
    assert fake_provider.calls == []


def test_chat_endpoint_executes_google_cloud_open_request(tmp_path):
    fake_tools = FakeToolExecutor()
    app = create_app(data_dir=tmp_path, tool_executor=fake_tools)
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"message": "Open Brave and Search Google Cloud and Open Hit."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["summary"] == "Open Brave and open Google Cloud."
    assert [item["tool"] for item in body["execution_results"]] == [
        "app.launch",
        "browser.open_url",
    ]


def test_memory_search_endpoint_returns_saved_memory(tmp_path):
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)
    client.post(
        "/api/chat",
        json={"message": "Remember that my LangGraph project is in D:\\Projects\\langgraph"},
    )

    response = client.get("/api/memory/search", params={"q": "LangGraph"})

    assert response.status_code == 200
    assert response.json()["results"][0]["kind"] == "project"


def test_tool_execute_blocks_dangerous_command(tmp_path):
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/tools/execute",
        json={
            "step_id": "danger",
            "tool": "terminal.run",
            "args": {"command": "Remove-Item -Recurse -Force C:\\Windows\\System32"},
            "approved": True,
        },
    )

    assert response.status_code == 403
    assert "blocked" in response.json()["detail"].lower()


def test_cors_allows_vite_loopback_origin(tmp_path):
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    response = client.options(
        "/api/chat",
        headers={
            "Origin": "http://127.0.0.1:1420",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:1420"
