import pytest

from neuronos.windows_controls import (
    _set_bluetooth_state,
    _set_wifi_state,
    adjust_brightness,
    adjust_volume,
    open_default_target,
    open_settings_page,
    perform_power_action,
    toggle_network,
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


def test_open_settings_page_raises_for_unsupported_page(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda args, **kwargs: calls.append(args),
    )

    with pytest.raises(ValueError, match="Unsupported settings page: privacy"):
        open_settings_page("privacy")

    assert calls == []


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
    assert calls == [
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "$wshell = New-Object -ComObject WScript.Shell; 1..5 | ForEach-Object { $wshell.SendKeys([char]174) }",
        ]
    ]


def test_adjust_volume_down_zero_is_no_op(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: calls.append(args),
    )

    output = adjust_volume("down", amount=0)

    assert output == "Volume unchanged."
    assert calls == []


def test_adjust_volume_set_uses_core_audio(monkeypatch):
    calls = []
    class Result:
        returncode = 0
        stdout = "OK\n"

    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: calls.append(args) or Result(),
    )
    monkeypatch.setattr(
        "neuronos.windows_controls.open_settings_page",
        lambda page: "Opened Sound settings.",
    )

    output = adjust_volume("set", amount=64)

    assert output == "Set volume to 64 percent."
    assert len(calls) == 1
    assert calls[0][:3] == ["powershell", "-NoProfile", "-Command"]
    assert "SetMasterVolumeLevelScalar" in calls[0][3]
    assert "0.64" in calls[0][3]


def test_adjust_volume_set_falls_back_to_sound_settings(monkeypatch):
    calls = []
    settings_calls = []
    class Result:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: calls.append(args) or Result(),
    )
    monkeypatch.setattr(
        "neuronos.windows_controls.open_settings_page",
        lambda page: settings_calls.append(page) or "Opened Sound settings.",
    )

    output = adjust_volume("set", amount=35)

    assert output == "I couldn't set the volume to an exact level directly, so I opened Sound settings."
    assert calls
    assert settings_calls == ["sound"]


def test_adjust_volume_unmute_falls_back_to_sound_settings(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: calls.append(args),
    )
    monkeypatch.setattr(
        "neuronos.windows_controls.open_settings_page",
        lambda page: "Opened Sound settings.",
    )

    output = adjust_volume("unmute")

    assert output == "I couldn't unmute audio directly without risking a wrong toggle, so I opened Sound settings."
    assert calls == []


def test_set_bluetooth_state_is_conservative_no_op(monkeypatch):
    calls = []
    class Result:
        returncode = 1
        stdout = ""

    monkeypatch.setattr("subprocess.run", lambda args, **kwargs: calls.append(args) or Result())

    output = _set_bluetooth_state(True)

    assert output is False
    assert calls
    assert "Windows.Devices.Radios.Radio" in calls[0][3]
    assert "Bluetooth" in calls[0][3]
    assert "On" in calls[0][3]


def test_set_wifi_state_requires_adapter_match(monkeypatch):
    class Result:
        returncode = 0
        stdout = ""

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    output = _set_wifi_state(True)

    assert output is False
    assert len(calls) == 1
    assert calls[0][:3] == ["powershell", "-NoProfile", "-Command"]
    assert "$_.Name -match 'wi-?fi|wireless'" in calls[0][3]
    assert "$_.InterfaceDescription -match 'wi-?fi|wireless|802\\.11'" in calls[0][3]
    assert "Select-Object -First 1" in calls[0][3]
    assert "if (-not $adapter) { exit 1 }" in calls[0][3]
    assert "Enable-NetAdapter -Confirm:$false -PassThru" in calls[0][3]


def test_set_wifi_state_returns_true_when_wireless_adapter_changes(monkeypatch):
    class Result:
        returncode = 0
        stdout = "Intel(R) Wireless-AC 9560\n"

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    output = _set_wifi_state(True)

    assert output is True
    assert "Enable-NetAdapter -Confirm:$false -PassThru" in calls[0][3]


def test_set_wifi_state_disable_uses_disable_command(monkeypatch):
    class Result:
        returncode = 0
        stdout = "Wi-Fi\n"

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    output = _set_wifi_state(False)

    assert output is True
    assert "Disable-NetAdapter -Confirm:$false -PassThru" in calls[0][3]
    assert "Enable-NetAdapter" not in calls[0][3]


def test_toggle_network_wifi_falls_back_when_no_adapter_matches(monkeypatch):
    monkeypatch.setattr(
        "neuronos.windows_controls._set_wifi_state",
        lambda enabled: False,
    )
    monkeypatch.setattr(
        "neuronos.windows_controls.open_settings_page",
        lambda page: "Opened Wi-Fi settings.",
    )

    output = toggle_network("wifi", enabled=True)

    assert output == "I couldn't toggle Wi-Fi directly, so I opened Wi-Fi settings."


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


def test_adjust_brightness_falls_back_to_display_settings(monkeypatch):
    monkeypatch.setattr(
        "neuronos.windows_controls._set_brightness",
        lambda percent: False,
    )
    monkeypatch.setattr(
        "neuronos.windows_controls.open_settings_page",
        lambda page: "Opened Display settings.",
    )

    output = adjust_brightness(70)

    assert output == "I couldn't change brightness directly, so I opened Display settings."
