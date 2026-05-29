import subprocess
from pathlib import Path

from neuronos.memory import MemoryStore
from neuronos.safety import SafetyPolicy
from neuronos.schemas import ToolExecuteRequest
from neuronos.tools import ToolBlockedError, ToolExecutor, _resolve_youtube_watch_url


class FakeProcess:
    pass


def make_executor(tmp_path: Path) -> ToolExecutor:
    memory = MemoryStore(tmp_path / "neuronos.db")
    return ToolExecutor(memory, SafetyPolicy(workspace_root=tmp_path))


def test_launch_app_uses_installed_brave_path(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools._find_executable",
        lambda app: Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
    )
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())

    output = make_executor(tmp_path)._launch_app({"app": "Brave"})

    assert output == "Launch requested for Brave."
    assert Path(calls[0][0]) == Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe")


def test_browser_open_url_uses_brave_when_requested(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("neuronos.tools._reuse_existing_browser_tab", lambda browser, url: False)
    monkeypatch.setattr(
        "neuronos.tools._find_executable",
        lambda app: Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
    )
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())

    output = make_executor(tmp_path)._browser_open_url(
        {"browser": "Brave", "url": "https://www.youtube.com/results?search_query=faded+song"}
    )

    assert "youtube.com" in output
    assert Path(calls[0][0]) == Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe")
    assert calls[0][1] == "https://www.youtube.com/results?search_query=faded+song"


def test_browser_open_url_reuses_existing_brave_tab_when_available(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("neuronos.tools._reuse_existing_browser_tab", lambda browser, url: True)
    monkeypatch.setattr(
        "neuronos.tools._find_executable",
        lambda app: Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
    )
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())

    output = make_executor(tmp_path)._browser_open_url(
        {"browser": "Brave", "url": "https://chatgpt.com/"}
    )

    assert output == "Opened https://chatgpt.com/."
    assert calls == []


def test_open_path_uses_vscode_with_folder_argument(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools._find_executable",
        lambda app: Path("C:/Users/example/AppData/Local/Programs/Microsoft VS Code/bin/code.cmd"),
    )
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())

    output = make_executor(tmp_path)._open_path({"app": "VS Code", "path": "D:/Games/ui"})

    assert output == "Opened D:/Games/ui in VS Code."
    assert Path(calls[0][0]) == Path("C:/Users/example/AppData/Local/Programs/Microsoft VS Code/bin/code.cmd")
    assert Path(calls[0][1]) == Path("D:/Games/ui")


def test_open_path_uses_real_vs_code_name_without_executable_monkeypatch(monkeypatch, tmp_path):
    calls = []
    real_exists = Path.exists

    def fake_exists(self):
        return str(self).endswith("Microsoft VS Code/bin/code.cmd") or real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())

    output = make_executor(tmp_path)._open_path({"app": "VS Code", "path": "D:/Games/ui"})

    assert output == "Opened D:/Games/ui in VS Code."
    assert Path(calls[0][0]).name == "code.cmd"
    assert "Microsoft VS Code" in str(calls[0][0])
    assert Path(calls[0][1]) == Path("D:/Games/ui")


def test_play_youtube_resolves_watch_url(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("neuronos.tools._reuse_existing_browser_tab", lambda browser, url: False)
    monkeypatch.setattr(
        "neuronos.tools._find_executable",
        lambda app: Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
    )
    monkeypatch.setattr(
        "neuronos.tools._resolve_youtube_watch_url",
        lambda query: "https://www.youtube.com/watch?v=abc123",
    )
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())

    output = make_executor(tmp_path)._play_youtube({"browser": "Brave", "query": "faded song"})

    assert output == "Opened https://www.youtube.com/watch?v=abc123."
    assert Path(calls[0][0]) == Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe")
    assert calls[0][1] == "https://www.youtube.com/watch?v=abc123"


def test_resolve_youtube_watch_url_falls_back_to_search_on_extraction_failure(monkeypatch):
    class FailingYoutubeDL:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, *_args, **_kwargs):
            raise RuntimeError("network failure")

    monkeypatch.setattr("neuronos.tools.YoutubeDL", FailingYoutubeDL)

    output = _resolve_youtube_watch_url("faded song")

    assert output == "https://www.youtube.com/results?search_query=faded+song"


def test_launch_app_falls_back_to_windows_start_app(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("neuronos.tools._find_executable", lambda app: None)
    monkeypatch.setattr("neuronos.tools._find_start_app_id", lambda app: "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App")
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())

    output = make_executor(tmp_path)._launch_app({"app": "Calculator"})

    assert output == "Launch requested for Calculator."
    assert calls == [["explorer.exe", "shell:AppsFolder\\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"]]


def test_launch_settings_uses_ms_settings_uri(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("neuronos.tools._find_executable", lambda app: None)
    monkeypatch.setattr("neuronos.tools._find_start_app_id", lambda app: None)
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())

    output = make_executor(tmp_path)._launch_app({"app": "Settings"})

    assert output == "Launch requested for Settings."
    assert calls == [["cmd", "/c", "start", "", "ms-settings:"]]


def test_execute_app_open_default_delegates_to_windows_controls(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools.open_default_target",
        lambda path_text: calls.append(path_text) or f"Opened {path_text}.",
    )

    response = make_executor(tmp_path).execute(
        ToolExecuteRequest(
            step_id="step-open-default",
            tool="app.open_default",
            args={"path": "D:/Games/ui"},
        )
    )

    assert response.output == "Opened D:/Games/ui."
    assert calls == ["D:/Games/ui"]


def test_execute_system_audio_delegates_to_windows_controls(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools.adjust_volume",
        lambda direction, amount=10: calls.append((direction, amount)) or "Raised volume.",
    )

    response = make_executor(tmp_path).execute(
        ToolExecuteRequest(
            step_id="step-audio",
            tool="system.audio",
            args={"direction": "up", "amount": 20},
        )
    )

    assert response.output == "Raised volume."
    assert calls == [("up", 20)]


def test_execute_system_settings_delegates_to_windows_controls(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools.open_settings_page",
        lambda page: calls.append(page) or "Opened Display settings.",
    )

    response = make_executor(tmp_path).execute(
        ToolExecuteRequest(
            step_id="step-settings",
            tool="system.settings",
            args={"page": "display"},
        )
    )

    assert response.output == "Opened Display settings."
    assert calls == ["display"]


def test_execute_system_network_delegates_to_windows_controls(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools.toggle_network",
        lambda kind, enabled: calls.append((kind, enabled)) or "Turned Wi-Fi off.",
    )

    response = make_executor(tmp_path).execute(
        ToolExecuteRequest(
            step_id="step-network",
            tool="system.network",
            args={"kind": "wifi", "enabled": False},
        )
    )

    assert response.output == "Turned Wi-Fi off."
    assert calls == [("wifi", False)]


def test_execute_system_network_parses_falsey_strings_safely(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools.toggle_network",
        lambda kind, enabled: calls.append((kind, enabled)) or "Turned Wi-Fi off.",
    )

    falsey_inputs = ["false", "False", "0", "no"]
    for index, raw_value in enumerate(falsey_inputs, start=1):
        response = make_executor(tmp_path).execute(
            ToolExecuteRequest(
                step_id=f"step-network-{index}",
                tool="system.network",
                args={"kind": "wifi", "enabled": raw_value},
            )
        )
        assert response.output == "Turned Wi-Fi off."

    assert calls == [("wifi", False), ("wifi", False), ("wifi", False), ("wifi", False)]


def test_execute_system_brightness_delegates_to_windows_controls(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools.adjust_brightness",
        lambda percent: calls.append(percent) or "Set brightness to 65 percent.",
    )

    response = make_executor(tmp_path).execute(
        ToolExecuteRequest(
            step_id="step-brightness",
            tool="system.brightness",
            args={"percent": 65},
        )
    )

    assert response.output == "Set brightness to 65 percent."
    assert calls == [65]


def test_execute_system_power_blocks_shutdown_without_approval(tmp_path):
    executor = make_executor(tmp_path)

    try:
        executor.execute(
            ToolExecuteRequest(
                step_id="step-power",
                tool="system.power",
                args={"action": "shutdown"},
                approved=False,
            )
        )
    except ToolBlockedError as exc:
        assert str(exc) == "Shutdown requires approval."
    else:
        raise AssertionError("Expected ToolBlockedError")


def test_execute_system_power_blocks_unsupported_action(tmp_path):
    executor = make_executor(tmp_path)

    try:
        executor.execute(
            ToolExecuteRequest(
                step_id="step-power",
                tool="system.power",
                args={"action": "hibernate"},
                approved=True,
            )
        )
    except ToolBlockedError as exc:
        assert str(exc) == "Unsupported power action."
    else:
        raise AssertionError("Expected ToolBlockedError")


def test_execute_system_audio_uses_safety_policy(monkeypatch, tmp_path):
    executor = make_executor(tmp_path)
    monkeypatch.setattr(
        executor.safety,
        "check_system_action",
        lambda category, args: type("Decision", (), {"allowed": False, "reason": "Blocked by policy."})(),
    )

    try:
        executor.execute(
            ToolExecuteRequest(
                step_id="step-audio",
                tool="system.audio",
                args={"direction": "down"},
            )
        )
    except ToolBlockedError as exc:
        assert str(exc) == "Blocked by policy."
    else:
        raise AssertionError("Expected ToolBlockedError")


def test_execute_system_power_delegates_when_approved(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "neuronos.tools.perform_power_action",
        lambda action: calls.append(action) or "Locking your PC.",
    )

    response = make_executor(tmp_path).execute(
        ToolExecuteRequest(
            step_id="step-power",
            tool="system.power",
            args={"action": "lock"},
            approved=True,
        )
    )

    assert response.output == "Locking your PC."
    assert calls == ["lock"]


def test_file_write_rejects_missing_path(tmp_path):
    executor = make_executor(tmp_path)

    try:
        executor._file_write({"path": "", "content": "hello"})
    except ToolBlockedError as exc:
        assert str(exc) == "Path is required."
    else:
        raise AssertionError("Expected ToolBlockedError")


def test_terminal_run_raises_controlled_error_on_timeout(monkeypatch, tmp_path):
    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=30)

    monkeypatch.setattr("subprocess.run", fake_run)

    try:
        make_executor(tmp_path)._terminal_run({"command": "Get-Date"})
    except ToolBlockedError as exc:
        assert str(exc) == "Command timed out."
    else:
        raise AssertionError("Expected ToolBlockedError")


def test_terminal_run_prefers_stderr_on_nonzero_exit(monkeypatch, tmp_path):
    class FakeCompletedProcess:
        returncode = 1
        stdout = "partial output"
        stderr = "actual failure"

    monkeypatch.setattr("subprocess.run", lambda *_args, **_kwargs: FakeCompletedProcess())

    output = make_executor(tmp_path)._terminal_run({"command": "Write-Output partial; exit 1"})

    assert output == "actual failure"


def test_terminal_run_ignores_whitespace_only_stderr_on_nonzero_exit(monkeypatch, tmp_path):
    class FakeCompletedProcess:
        returncode = 1
        stdout = "partial output"
        stderr = "  \n\t  "

    monkeypatch.setattr("subprocess.run", lambda *_args, **_kwargs: FakeCompletedProcess())

    output = make_executor(tmp_path)._terminal_run({"command": "Write-Output partial; exit 1"})

    assert output == "partial output"


def test_terminal_run_returns_exit_code_when_nonzero_has_no_meaningful_output(monkeypatch, tmp_path):
    class FakeCompletedProcess:
        returncode = 7
        stdout = ""
        stderr = " \n "

    monkeypatch.setattr("subprocess.run", lambda *_args, **_kwargs: FakeCompletedProcess())

    output = make_executor(tmp_path)._terminal_run({"command": "exit 7"})

    assert output == "Command exited 7"


def test_terminal_run_returns_stderr_when_success_has_stderr_only_output(monkeypatch, tmp_path):
    class FakeCompletedProcess:
        returncode = 0
        stdout = ""
        stderr = "warning from tool"

    monkeypatch.setattr("subprocess.run", lambda *_args, **_kwargs: FakeCompletedProcess())

    output = make_executor(tmp_path)._terminal_run({"command": "Write-Error warning"})

    assert output == "warning from tool"
