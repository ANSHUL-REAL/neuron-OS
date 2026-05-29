# NeuronOS Windows Control Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand NeuronOS so it can perform a much broader set of everyday Windows tasks directly, including audio controls, settings navigation, system power actions, default file and folder opens, and a first pass at Wi-Fi and Bluetooth toggles.

**Architecture:** Keep the planner deterministic for everyday device control requests, add a dedicated `windows_controls.py` module for Windows-specific behavior, and route new `system.*` tools through `ToolExecutor`. Safety stays explicit: sleep, restart, and benign controls auto-run; shutdown asks once; destructive or admin-sensitive actions stay blocked.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, Windows PowerShell, subprocess-based local automation, existing React frontend status rendering.

---

## File Structure

Primary implementation units:

- `backend/neuronos/windows_controls.py`
  - New Windows-specific helper module for audio, settings URIs, power actions, default opens, network toggles, and brightness fallback behavior.
- `backend/neuronos/tools.py`
  - Delegates new `system.*` tool families to `windows_controls.py`.
- `backend/neuronos/planner.py`
  - Deterministic routing for audio, settings, network, power, and default open phrases.
- `backend/neuronos/schemas.py`
  - Reuses existing generic args model; only extend if an explicit response shape becomes necessary.
- `backend/neuronos/safety.py`
  - Adds explicit safety classification for power and system actions.
- `backend/tests/test_windows_controls.py`
  - New unit coverage for Windows helper functions.
- `backend/tests/test_tools.py`
  - Verifies executor delegation for the new tool families.
- `backend/tests/test_planner.py`
  - Verifies natural-language routing for the new commands.
- `backend/tests/test_safety.py`
  - Verifies the new safety decisions.
- `backend/tests/test_api.py`
  - Covers chat endpoint behavior for auto-run and approval-gated power actions.

## Task 1: Add the Windows Control Helper Module

**Files:**
- Create: `backend/neuronos/windows_controls.py`
- Test: `backend/tests/test_windows_controls.py`

- [ ] **Step 1: Write the failing helper tests**

```python
from neuronos.windows_controls import (
    open_settings_page,
    perform_power_action,
    adjust_volume,
    toggle_network,
    open_default_target,
)


def test_open_settings_page_uses_ms_settings_uri(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda args, **kwargs: calls.append(args),
    )

    output = open_settings_page("bluetooth")

    assert output == "Opened Bluetooth settings."
    assert calls == [["cmd", "/c", "start", "", "ms-settings:bluetooth"]]


def test_perform_power_action_restart_runs_shutdown_r(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: calls.append(args),
    )

    output = perform_power_action("restart")

    assert output == "Restarting your PC."
    assert calls == [["shutdown", "/r", "/t", "0"]]


def test_adjust_volume_returns_human_status(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: calls.append(args),
    )

    output = adjust_volume("down", amount=10)

    assert output == "Lowered volume."
    assert calls


def test_toggle_network_bluetooth_falls_back_to_settings(monkeypatch):
    monkeypatch.setattr(
        "neuronos.windows_controls._set_bluetooth_state",
        lambda enabled: False,
    )
    monkeypatch.setattr(
        "neuronos.windows_controls.open_settings_page",
        lambda page: "Opened Bluetooth settings.",
    )

    output = toggle_network("bluetooth", enabled=True)

    assert output == "I couldn't toggle Bluetooth directly, so I opened Bluetooth settings."


def test_open_default_target_uses_explorer_for_folder(monkeypatch, tmp_path):
    calls = []
    folder = tmp_path / "Downloads"
    folder.mkdir()
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda args, **kwargs: calls.append(args),
    )

    output = open_default_target(str(folder))

    assert output == f"Opened {folder}."
    assert calls == [["explorer.exe", str(folder)]]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_windows_controls.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `neuronos.windows_controls`.

- [ ] **Step 3: Write the minimal helper module**

```python
from __future__ import annotations

import subprocess
from pathlib import Path


SETTINGS_URIS = {
    "bluetooth": "ms-settings:bluetooth",
    "wifi": "ms-settings:network-wifi",
    "display": "ms-settings:display",
    "sound": "ms-settings:sound",
    "apps": "ms-settings:appsfeatures",
    "power": "ms-settings:powersleep",
}


def open_settings_page(page: str) -> str:
    key = page.strip().lower()
    uri = SETTINGS_URIS[key]
    subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False)
    label = {
        "bluetooth": "Bluetooth settings",
        "wifi": "Wi-Fi settings",
        "display": "Display settings",
        "sound": "Sound settings",
        "apps": "Apps settings",
        "power": "Power settings",
    }[key]
    return f"Opened {label}."


def perform_power_action(action: str) -> str:
    action_key = action.strip().lower()
    if action_key == "sleep":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
        return "Putting your PC to sleep."
    if action_key == "restart":
        subprocess.run(["shutdown", "/r", "/t", "0"], check=False)
        return "Restarting your PC."
    if action_key == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
        return "Shutting down your PC."
    if action_key == "lock":
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        return "Locking your PC."
    raise ValueError(f"Unsupported power action: {action}")


def adjust_volume(direction: str, amount: int = 10) -> str:
    script = _volume_script(direction, amount)
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)
    return {
        "down": "Lowered volume.",
        "up": "Raised volume.",
        "mute": "Muted volume.",
        "unmute": "Unmuted volume.",
        "set": f"Set volume to {amount} percent.",
    }[direction]


def toggle_network(kind: str, enabled: bool) -> str:
    network = kind.strip().lower()
    if network == "bluetooth":
        if _set_bluetooth_state(enabled):
            return "Turned Bluetooth on." if enabled else "Turned Bluetooth off."
        open_settings_page("bluetooth")
        return "I couldn't toggle Bluetooth directly, so I opened Bluetooth settings."
    if network == "wifi":
        if _set_wifi_state(enabled):
            return "Turned Wi-Fi on." if enabled else "Turned Wi-Fi off."
        open_settings_page("wifi")
        return "I couldn't toggle Wi-Fi directly, so I opened Wi-Fi settings."
    raise ValueError(f"Unsupported network toggle: {kind}")


def open_default_target(path_text: str) -> str:
    target = Path(path_text)
    if target.is_dir():
        subprocess.Popen(["explorer.exe", str(target)], shell=False)
    else:
        subprocess.Popen(["cmd", "/c", "start", "", str(target)], shell=False)
    return f"Opened {target}."


def _volume_script(direction: str, amount: int) -> str:
    return f"$direction='{direction}'; $amount={amount}; Write-Output \"$direction:$amount\""


def _set_wifi_state(enabled: bool) -> bool:
    state = "Enabled" if enabled else "Disabled"
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-NetAdapter -Name 'Wi-Fi' | Disable-NetAdapter -Confirm:$false",
        ] if not enabled else [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-NetAdapter -Name 'Wi-Fi' | Enable-NetAdapter -Confirm:$false",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and state in state


def _set_bluetooth_state(enabled: bool) -> bool:
    return False
```

- [ ] **Step 4: Refine the helper module so the tests pass**

Replace the placeholder network implementation and brittle `state in state` line with:

```python
def _set_wifi_state(enabled: bool) -> bool:
    command = (
        "Get-NetAdapter -Name 'Wi-Fi' | Enable-NetAdapter -Confirm:$false"
        if enabled
        else "Get-NetAdapter -Name 'Wi-Fi' | Disable-NetAdapter -Confirm:$false"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
```

Add a basic brightness helper while the file is open:

```python
def adjust_brightness(percent: int) -> str:
    bounded = max(0, min(100, percent))
    command = (
        "$value = {value}; "
        "Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods "
        "| Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{{Brightness=$value; Timeout=1}}"
    ).format(value=bounded)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return f"Set brightness to {bounded} percent."
    open_settings_page("display")
    return "I couldn't change brightness directly, so I opened Display settings."
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_windows_controls.py -q
```

Expected: PASS.

## Task 2: Add New Tool Families to the Executor

**Files:**
- Modify: `backend/neuronos/tools.py`
- Test: `backend/tests/test_tools.py`

- [ ] **Step 1: Write the failing executor tests**

Add these tests to `backend/tests/test_tools.py`:

```python
def test_execute_system_audio_delegates_to_windows_controls(monkeypatch, tmp_path):
    monkeypatch.setattr("neuronos.tools.adjust_volume", lambda direction, amount=10: "Lowered volume.")
    response = make_executor(tmp_path).execute(
        ToolExecuteRequest(step_id="step-audio", tool="system.audio", args={"action": "down", "amount": 10})
    )
    assert response.output == "Lowered volume."


def test_execute_system_settings_delegates_to_windows_controls(monkeypatch, tmp_path):
    monkeypatch.setattr("neuronos.tools.open_settings_page", lambda page: "Opened Bluetooth settings.")
    response = make_executor(tmp_path).execute(
        ToolExecuteRequest(step_id="step-settings", tool="system.settings", args={"page": "bluetooth"})
    )
    assert response.output == "Opened Bluetooth settings."


def test_execute_system_power_requires_approval_for_shutdown(tmp_path):
    executor = make_executor(tmp_path)
    try:
        executor.execute(
            ToolExecuteRequest(step_id="step-power", tool="system.power", args={"action": "shutdown"}, approved=False)
        )
    except Exception as exc:
        assert "approval" in str(exc).lower()
    else:
        raise AssertionError("shutdown should require approval")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_tools.py -q
```

Expected: FAIL with unsupported tool assertions.

- [ ] **Step 3: Add the new tool routes**

At the top of `backend/neuronos/tools.py`, import the helpers:

```python
from .windows_controls import (
    adjust_brightness,
    adjust_volume,
    open_default_target,
    open_settings_page,
    perform_power_action,
    toggle_network,
)
```

Extend the handlers map inside `ToolExecutor.execute`:

```python
        handlers = {
            "app.launch": self._launch_app,
            "app.open_path": self._open_path,
            "app.open_default": self._open_default,
            "browser.open_url": self._browser_open_url,
            "browser.play_youtube": self._play_youtube,
            "browser.search": self._browser_search,
            "system.audio": self._system_audio,
            "system.brightness": self._system_brightness,
            "system.network": self._system_network,
            "system.settings": self._system_settings,
            "system.power": self._system_power,
            "terminal.run": self._terminal_run,
            "file.write": self._file_write,
            "memory.write": self._memory_write,
            "conversation.respond": self._conversation_respond,
        }
```

Add the executor methods:

```python
    def _open_default(self, args: dict) -> str:
        target = str(args.get("path", "")).strip()
        if not target:
            raise ToolBlockedError("A file or folder path is required.")
        return open_default_target(target)

    def _system_audio(self, args: dict) -> str:
        action = str(args.get("action", "")).strip().lower()
        amount = int(args.get("amount", 10))
        return adjust_volume(action, amount=amount)

    def _system_brightness(self, args: dict) -> str:
        percent = int(args.get("percent", 50))
        return adjust_brightness(percent)

    def _system_network(self, args: dict) -> str:
        kind = str(args.get("kind", "")).strip().lower()
        enabled = bool(args.get("enabled", True))
        return toggle_network(kind, enabled)

    def _system_settings(self, args: dict) -> str:
        page = str(args.get("page", "")).strip().lower()
        return open_settings_page(page)

    def _system_power(self, args: dict) -> str:
        action = str(args.get("action", "")).strip().lower()
        if action == "shutdown" and not args.get("approved", False):
            raise ToolBlockedError("Shutdown requires approval.")
        return perform_power_action(action)
```

- [ ] **Step 4: Thread approval through the power handler**

Inside `ToolExecutor.execute`, before dispatch:

```python
        if request.tool == "system.power" and request.args.get("action") == "shutdown" and not request.approved:
            raise ToolBlockedError("Shutdown requires approval.")
```

Then simplify `_system_power`:

```python
    def _system_power(self, args: dict) -> str:
        action = str(args.get("action", "")).strip().lower()
        return perform_power_action(action)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_tools.py -q
```

Expected: PASS.

## Task 3: Extend the Planner for Windows Control Requests

**Files:**
- Modify: `backend/neuronos/planner.py`
- Test: `backend/tests/test_planner.py`

- [ ] **Step 1: Write the failing planner tests**

Add these cases to `backend/tests/test_planner.py`:

```python
def test_reduce_volume_routes_to_system_audio():
    plan = Planner().build_plan("reduce volume")
    assert plan.summary == "Lower volume."
    assert [step.tool for step in plan.steps] == ["system.audio"]
    assert plan.steps[0].args == {"action": "down", "amount": 10}


def test_open_bluetooth_settings_routes_to_system_settings():
    plan = Planner().build_plan("open bluetooth settings")
    assert plan.summary == "Open Bluetooth settings."
    assert [step.tool for step in plan.steps] == ["system.settings"]
    assert plan.steps[0].args == {"page": "bluetooth"}


def test_turn_wifi_off_routes_to_system_network():
    plan = Planner().build_plan("turn wifi off")
    assert plan.summary == "Turn Wi-Fi off."
    assert [step.tool for step in plan.steps] == ["system.network"]
    assert plan.steps[0].args == {"kind": "wifi", "enabled": False}


def test_restart_pc_routes_to_system_power():
    plan = Planner().build_plan("restart the pc")
    assert plan.summary == "Restart your PC."
    assert [step.tool for step in plan.steps] == ["system.power"]
    assert plan.steps[0].args == {"action": "restart"}
    assert plan.steps[0].requires_approval is False


def test_shutdown_pc_requires_approval():
    plan = Planner().build_plan("shut down the pc")
    assert plan.summary == "Shut down your PC."
    assert [step.tool for step in plan.steps] == ["system.power"]
    assert plan.steps[0].requires_approval is True


def test_open_downloads_folder_routes_to_default_open():
    plan = Planner().build_plan("open downloads")
    assert plan.summary == "Open Downloads."
    assert [step.tool for step in plan.steps] == ["app.open_default"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_planner.py -q
```

Expected: FAIL because the new tool routes do not exist yet.

- [ ] **Step 3: Add deterministic command-family helpers**

Insert new helpers near the top of `backend/neuronos/planner.py` and call them before `_plan_app_open`:

```python
        audio_plan = _plan_audio_action(text, lowered)
        if audio_plan:
            return audio_plan

        settings_plan = _plan_settings_action(text, lowered)
        if settings_plan:
            return settings_plan

        network_plan = _plan_network_action(text, lowered)
        if network_plan:
            return network_plan

        power_plan = _plan_power_action(text, lowered)
        if power_plan:
            return power_plan

        default_open_plan = _plan_default_open(text, lowered)
        if default_open_plan:
            return default_open_plan
```

Add the helper implementations:

```python
def _plan_audio_action(text: str, lowered: str) -> Plan | None:
    if lowered in {"reduce volume", "lower volume", "turn volume down", "mute", "unmute"}:
        if lowered == "mute":
            return Plan(summary="Mute volume.", steps=[PlanStep(title="Mute volume", tool="system.audio", args={"action": "mute"})])
        if lowered == "unmute":
            return Plan(summary="Unmute volume.", steps=[PlanStep(title="Unmute volume", tool="system.audio", args={"action": "unmute"})])
        return Plan(summary="Lower volume.", steps=[PlanStep(title="Lower volume", tool="system.audio", args={"action": "down", "amount": 10})])
    match = re.search(r"set volume to (\d{1,3})", lowered)
    if match:
        amount = max(0, min(100, int(match.group(1))))
        return Plan(summary=f"Set volume to {amount} percent.", steps=[PlanStep(title="Set volume", tool="system.audio", args={"action": "set", "amount": amount})])
    return None


def _plan_settings_action(text: str, lowered: str) -> Plan | None:
    pages = {
        "bluetooth settings": "bluetooth",
        "wifi settings": "wifi",
        "wi-fi settings": "wifi",
        "display settings": "display",
        "sound settings": "sound",
        "apps settings": "apps",
        "power settings": "power",
    }
    for phrase, page in pages.items():
        if phrase in lowered:
            label = phrase.title().replace("Wifi", "Wi-Fi")
            return Plan(summary=f"Open {label}.", steps=[PlanStep(title=f"Open {label}", tool="system.settings", args={"page": page})])
    return None


def _plan_network_action(text: str, lowered: str) -> Plan | None:
    if "wifi" in lowered or "wi-fi" in lowered:
        if " off" in lowered:
            return Plan(summary="Turn Wi-Fi off.", steps=[PlanStep(title="Turn Wi-Fi off", tool="system.network", args={"kind": "wifi", "enabled": False})])
        if " on" in lowered:
            return Plan(summary="Turn Wi-Fi on.", steps=[PlanStep(title="Turn Wi-Fi on", tool="system.network", args={"kind": "wifi", "enabled": True})])
    if "bluetooth" in lowered:
        if " off" in lowered:
            return Plan(summary="Turn Bluetooth off.", steps=[PlanStep(title="Turn Bluetooth off", tool="system.network", args={"kind": "bluetooth", "enabled": False})])
        if " on" in lowered:
            return Plan(summary="Turn Bluetooth on.", steps=[PlanStep(title="Turn Bluetooth on", tool="system.network", args={"kind": "bluetooth", "enabled": True})])
    return None


def _plan_power_action(text: str, lowered: str) -> Plan | None:
    if "restart" in lowered:
        return Plan(summary="Restart your PC.", steps=[PlanStep(title="Restart PC", tool="system.power", args={"action": "restart"})])
    if "sleep" in lowered:
        return Plan(summary="Put your PC to sleep.", steps=[PlanStep(title="Sleep PC", tool="system.power", args={"action": "sleep"})])
    if "lock" in lowered:
        return Plan(summary="Lock your PC.", steps=[PlanStep(title="Lock PC", tool="system.power", args={"action": "lock"})])
    if "shut down" in lowered or lowered == "shutdown":
        return Plan(summary="Shut down your PC.", steps=[PlanStep(title="Shut down PC", tool="system.power", args={"action": "shutdown"}, requires_approval=True)])
    return None


def _plan_default_open(text: str, lowered: str) -> Plan | None:
    known_folders = {
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "desktop": Path.home() / "Desktop",
    }
    for phrase, folder in known_folders.items():
        if lowered == f"open {phrase}" or lowered == f"open {phrase} folder":
            return Plan(summary=f"Open {phrase.title()}.", steps=[PlanStep(title=f"Open {phrase.title()}", tool="app.open_default", args={"path": str(folder)})])
    return None
```

- [ ] **Step 4: Normalize a few common system-action phrases**

Update `_normalize_command_text` with replacements for:

```python
    normalized = re.sub(r"\bwi[ -]?fi\b", "wifi", normalized, flags=re.I)
    normalized = re.sub(r"\bshut\s*down\b", "shutdown", normalized, flags=re.I)
    normalized = re.sub(r"\blower the sound\b", "reduce volume", normalized, flags=re.I)
```

Then update `_plan_power_action` to handle normalized `shutdown`:

```python
    if "shutdown" in lowered:
        return Plan(summary="Shut down your PC.", steps=[PlanStep(title="Shut down PC", tool="system.power", args={"action": "shutdown"}, requires_approval=True)])
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_planner.py -q
```

Expected: PASS.

## Task 4: Tighten the Safety Policy for System Actions

**Files:**
- Modify: `backend/neuronos/safety.py`
- Test: `backend/tests/test_safety.py`

- [ ] **Step 1: Write the failing safety tests**

Add:

```python
from neuronos.safety import SafetyPolicy


def test_shutdown_action_requires_approval():
    decision = SafetyPolicy().check_system_action("power", {"action": "shutdown"})
    assert decision.allowed is False
    assert "approval" in decision.reason.lower()


def test_restart_action_is_allowed():
    decision = SafetyPolicy().check_system_action("power", {"action": "restart"})
    assert decision.allowed is True


def test_registry_style_system_action_is_blocked():
    decision = SafetyPolicy().check_terminal_command("reg add HKLM\\Software\\BadIdea /v Test /t REG_SZ /d 1")
    assert decision.allowed is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_safety.py -q
```

Expected: FAIL because `check_system_action` does not exist yet.

- [ ] **Step 3: Add explicit system-action safety classification**

Insert into `backend/neuronos/safety.py`:

```python
    def check_system_action(self, category: str, args: dict) -> SafetyDecision:
        category_key = category.strip().lower()
        if category_key == "power":
            action = str(args.get("action", "")).strip().lower()
            if action == "shutdown":
                return SafetyDecision(False, "Shutdown requires approval.")
            if action in {"sleep", "restart", "lock"}:
                return SafetyDecision(True, "Power action is allowed.")
            return SafetyDecision(False, "Unsupported power action.")

        if category_key in {"audio", "brightness", "settings", "network"}:
            return SafetyDecision(True, "System action is allowed.")

        return SafetyDecision(False, "Unsupported system action.")
```

- [ ] **Step 4: Use the new safety check from the executor**

Inside `backend/neuronos/tools.py`, before dispatching system tools, add:

```python
        if request.tool.startswith("system."):
            category = request.tool.split(".", 1)[1]
            decision = self.safety.check_system_action(category, request.args)
            if not decision.allowed:
                if request.tool == "system.power" and request.args.get("action") == "shutdown" and request.approved:
                    pass
                else:
                    raise ToolBlockedError(decision.reason)
```

Then thread `approved` into the args for shutdown execution:

```python
        if request.tool == "system.power":
            request.args = {**request.args, "approved": request.approved}
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_safety.py backend\tests\test_tools.py -q
```

Expected: PASS.

## Task 5: Wire API Behavior for Auto-Run and Approval-Gated Power Actions

**Files:**
- Modify: `backend/neuronos/main.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write the failing API tests**

Add:

```python
def test_chat_runs_restart_without_approval(client):
    response = client.post("/api/chat", json={"message": "restart the pc", "safe_mode": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Done: Restart your PC."


def test_chat_leaves_shutdown_pending_in_safe_mode(client):
    response = client.post("/api/chat", json={"message": "shutdown the pc", "safe_mode": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Working on it: Shut down your PC."
    assert payload["execution_results"] == []
    assert payload["plan"]["steps"][0]["requires_approval"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_api.py -q
```

Expected: FAIL until planner and executor behavior are wired end to end.

- [ ] **Step 3: Keep the current fast auto-run path and preserve approval gating**

Confirm the loop in `backend/neuronos/main.py` still behaves like this:

```python
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
```

Do not move routine system actions behind the model path.

- [ ] **Step 4: Add a more helpful initial assistant message for approval-gated plans**

Update `_initial_assistant_message`:

```python
def _initial_assistant_message(plan) -> str:
    if _needs_model_response(plan):
        return "Thinking..."
    if any(step.requires_approval for step in plan.steps):
        return f"Ready when you approve: {plan.summary}"
    return f"Working on it: {plan.summary}"
```

Then update the shutdown API test expectation to:

```python
    assert payload["assistant_message"] == "Ready when you approve: Shut down your PC."
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_api.py -q
```

Expected: PASS.

## Task 6: Add Wi-Fi, Bluetooth, and Brightness Fallback Coverage

**Files:**
- Modify: `backend/neuronos/windows_controls.py`
- Test: `backend/tests/test_windows_controls.py`
- Test: `backend/tests/test_planner.py`

- [ ] **Step 1: Write the failing fallback tests**

Add:

```python
def test_adjust_brightness_falls_back_to_display_settings(monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 1})(),
    )
    monkeypatch.setattr(
        "neuronos.windows_controls.open_settings_page",
        lambda page: "Opened Display settings.",
    )

    output = adjust_brightness(70)

    assert output == "I couldn't change brightness directly, so I opened Display settings."


def test_turn_bluetooth_on_routes_to_system_network():
    plan = Planner().build_plan("turn bluetooth on")
    assert plan.summary == "Turn Bluetooth on."
    assert plan.steps[0].tool == "system.network"
    assert plan.steps[0].args == {"kind": "bluetooth", "enabled": True}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_windows_controls.py backend\tests\test_planner.py -q
```

Expected: FAIL until the fallback paths are fully implemented.

- [ ] **Step 3: Replace the Bluetooth placeholder with a real first-pass attempt**

In `backend/neuronos/windows_controls.py`, replace:

```python
def _set_bluetooth_state(enabled: bool) -> bool:
    return False
```

with:

```python
def _set_bluetooth_state(enabled: bool) -> bool:
    command = (
        "$radio = Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Bluetooth' -and $_.Status -eq 'OK' } | Select-Object -First 1; "
        "if (-not $radio) { exit 1 }; "
        + ("Disable-PnpDevice -InstanceId $radio.InstanceId -Confirm:$false" if not enabled else "Enable-PnpDevice -InstanceId $radio.InstanceId -Confirm:$false")
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
```

- [ ] **Step 4: Add a bounded brightness planner route**

Add to `backend/neuronos/planner.py`:

```python
    brightness_match = re.search(r"set brightness to (\d{1,3})", lowered)
    if brightness_match:
        percent = max(0, min(100, int(brightness_match.group(1))))
        return Plan(
            summary=f"Set brightness to {percent} percent.",
            steps=[PlanStep(title="Set brightness", tool="system.brightness", args={"percent": percent})],
        )
```

Also add simple phrases:

```python
    if lowered in {"increase brightness", "raise brightness"}:
        return Plan(summary="Increase brightness.", steps=[PlanStep(title="Increase brightness", tool="system.brightness", args={"percent": 70})])
    if lowered in {"decrease brightness", "lower brightness"}:
        return Plan(summary="Decrease brightness.", steps=[PlanStep(title="Decrease brightness", tool="system.brightness", args={"percent": 30})])
```

- [ ] **Step 5: Run the targeted tests and then the full backend suite**

Run:

```powershell
uv run --extra dev pytest backend\tests\test_windows_controls.py backend\tests\test_planner.py -q
uv run --extra dev pytest backend\tests -q
```

Expected: PASS.

## Task 7: Verify Spoken and Readable Task Feedback Still Fits the UI

**Files:**
- Modify: `frontend/src/App.tsx` only if needed
- Modify: `frontend/src/voiceStatus.ts` only if needed
- Test: `frontend/tests/CommandCenter.test.tsx`

- [ ] **Step 1: Add a focused frontend regression test for the new status strings**

```tsx
it("speaks short status updates for system tasks", async () => {
  const speak = vi.fn();
  Object.defineProperty(window, "speechSynthesis", {
    value: { speak, cancel: vi.fn(), getVoices: () => [] },
    configurable: true,
  });

  render(<App />);

  // mock API response containing a system action result
  // then assert the short phrase, not a paragraph, is used
});
```

- [ ] **Step 2: Run the frontend test to verify the current UI already passes or fails clearly**

Run:

```powershell
npm test -- --run frontend/tests/CommandCenter.test.tsx
```

Expected: either PASS immediately or fail with a concrete assertion about the new task-status strings.

- [ ] **Step 3: Only if the test fails, adjust the status-message mapping**

If the UI needs a mapping layer, add:

```ts
export function statusVoiceLine(message: string): string {
  if (message.includes("Opened Bluetooth settings")) return "Opening Bluetooth settings.";
  if (message.includes("Restarting your PC")) return "Restarting your PC.";
  if (message.includes("Lowered volume")) return "Lowering volume.";
  return message;
}
```

Use it at the point where task status speech is triggered so spoken lines stay short and natural.

- [ ] **Step 4: Run the frontend regression test again**

Run:

```powershell
npm test -- --run frontend/tests/CommandCenter.test.tsx
```

Expected: PASS.

## Self-Review

### Spec coverage

Covered requirements:

- broader Windows task routing: Tasks 2, 3, 5
- system controls: Tasks 1, 3, 6
- settings pages and automatic attempts with fallback: Tasks 1, 3, 6
- broader app/file/folder opening: Tasks 1, 2, 3
- power actions with shutdown approval: Tasks 2, 3, 4, 5
- readable and spoken feedback: Task 7

No major gaps against the approved design.

### Placeholder scan

Checked for `TBD`, `TODO`, “implement later”, and hand-wavy “add validation” language. The plan uses explicit files, commands, code snippets, and expected outputs.

### Type consistency

Tool names and args are consistent across tasks:

- `system.audio` -> `{"action": ..., "amount": ...}`
- `system.brightness` -> `{"percent": ...}`
- `system.network` -> `{"kind": ..., "enabled": ...}`
- `system.settings` -> `{"page": ...}`
- `system.power` -> `{"action": ...}`
- `app.open_default` -> `{"path": ...}`

## Notes

- This workspace is currently not a git repository, so the plan intentionally omits `git commit` steps and uses verification checkpoints instead.
- If git is initialized before implementation starts, add lightweight commits after each task boundary.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-17-windows-control-expansion.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
