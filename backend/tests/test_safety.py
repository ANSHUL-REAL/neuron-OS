from pathlib import Path

from neuronos.safety import SafetyDecision, SafetyPolicy


def test_allows_safe_read_only_terminal_command():
    decision = SafetyPolicy().check_terminal_command("dir D:\\Games")

    assert decision == SafetyDecision(allowed=True, reason="Command is allowed.")


def test_blocks_recursive_delete_against_windows_system_path():
    decision = SafetyPolicy().check_terminal_command(
        "Remove-Item -Recurse -Force C:\\Windows\\System32"
    )

    assert decision.allowed is False
    assert "protected path" in decision.reason.lower()


def test_blocks_registry_and_security_changes():
    policy = SafetyPolicy()

    regedit = policy.check_terminal_command("reg delete HKLM\\Software\\Example /f")
    firewall = policy.check_terminal_command(
        "Set-MpPreference -DisableRealtimeMonitoring $true"
    )

    assert regedit.allowed is False
    assert "registry" in regedit.reason.lower()
    assert firewall.allowed is False
    assert "security" in firewall.reason.lower()


def test_allows_file_write_inside_user_workspace(tmp_path: Path):
    decision = SafetyPolicy(workspace_root=tmp_path).check_file_operation(
        operation="write",
        target=tmp_path / "notes" / "memory.txt",
    )

    assert decision.allowed is True


def test_blocks_file_operation_for_protected_path():
    decision = SafetyPolicy().check_file_operation(
        operation="delete",
        target=Path("C:/Windows/System32/drivers/etc/hosts"),
    )

    assert decision.allowed is False
    assert "protected path" in decision.reason.lower()


def test_shutdown_system_action_requires_approval():
    decision = SafetyPolicy().check_system_action("power", {"action": "shutdown"})

    assert decision.allowed is False
    assert "approval" in decision.reason.lower()


def test_restart_system_action_is_allowed():
    decision = SafetyPolicy().check_system_action("power", {"action": "restart"})

    assert decision.allowed is True


def test_safe_system_control_actions_are_allowed():
    policy = SafetyPolicy()

    assert policy.check_system_action("audio", {"direction": "down"}).allowed is True
    assert policy.check_system_action("brightness", {"percent": 50}).allowed is True
    assert policy.check_system_action("settings", {"page": "bluetooth"}).allowed is True
    assert policy.check_system_action("network", {"kind": "wifi", "enabled": False}).allowed is True


def test_unsupported_system_action_is_blocked():
    decision = SafetyPolicy().check_system_action("process", {"action": "kill"})

    assert decision.allowed is False
    assert "unsupported" in decision.reason.lower()
