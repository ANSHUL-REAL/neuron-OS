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

SETTINGS_LABELS = {
    "bluetooth": "Bluetooth settings",
    "wifi": "Wi-Fi settings",
    "display": "Display settings",
    "sound": "Sound settings",
    "apps": "Apps settings",
    "power": "Power settings",
}

WIFI_ADAPTER_SELECTOR = (
    "Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { "
    "$_.Name -match 'wi-?fi|wireless' -or "
    "$_.InterfaceDescription -match 'wi-?fi|wireless|802\\.11' "
    "} | Select-Object -First 1"
)


def open_settings_page(page: str) -> str:
    key = page.strip().lower()
    uri = SETTINGS_URIS.get(key)
    if not uri:
        raise ValueError(f"Unsupported settings page: {page}")
    subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False)
    return f"Opened {SETTINGS_LABELS[key]}."


def perform_power_action(action: str) -> str:
    action_key = action.strip().lower()
    if action_key == "restart":
        subprocess.run(["shutdown", "/r", "/t", "0"], check=False)
        return "Restarting your PC."
    if action_key == "sleep":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
        return "Putting your PC to sleep."
    if action_key == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
        return "Shutting down your PC."
    if action_key == "lock":
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        return "Locking your PC."
    raise ValueError(f"Unsupported power action: {action}")


def adjust_volume(direction: str, amount: int = 10) -> str:
    direction_key = direction.strip().lower()
    if direction_key == "set":
        bounded = max(0, min(100, amount))
        if _set_exact_volume(bounded):
            return f"Set volume to {bounded} percent."
        open_settings_page("sound")
        return "I couldn't set the volume to an exact level directly, so I opened Sound settings."
    if direction_key == "unmute":
        open_settings_page("sound")
        return "I couldn't unmute audio directly without risking a wrong toggle, so I opened Sound settings."
    if direction_key in {"up", "down"} and amount <= 0:
        return "Volume unchanged."
    script = _volume_script(direction_key, amount)
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)
    labels = {
        "down": "Lowered volume.",
        "up": "Raised volume.",
        "mute": "Muted volume.",
    }
    return labels[direction_key]


def toggle_network(kind: str, enabled: bool) -> str:
    kind_key = kind.strip().lower()
    if kind_key == "bluetooth":
        if _set_bluetooth_state(enabled):
            return "Turned Bluetooth on." if enabled else "Turned Bluetooth off."
        open_settings_page("bluetooth")
        return "I couldn't toggle Bluetooth directly, so I opened Bluetooth settings."
    if kind_key == "wifi":
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


def adjust_brightness(percent: int) -> str:
    bounded = max(0, min(100, percent))
    if _set_brightness(bounded):
        return f"Set brightness to {bounded} percent."
    open_settings_page("display")
    return "I couldn't change brightness directly, so I opened Display settings."


def _volume_script(direction: str, amount: int) -> str:
    bounded = max(0, min(100, amount))
    if direction == "mute":
        return "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
    if direction == "up":
        return "$wshell = New-Object -ComObject WScript.Shell; 1..{0} | ForEach-Object {{ $wshell.SendKeys([char]175) }}".format(
            max(1, bounded // 2)
        )
    if direction == "down":
        return "$wshell = New-Object -ComObject WScript.Shell; 1..{0} | ForEach-Object {{ $wshell.SendKeys([char]174) }}".format(
            max(1, bounded // 2)
        )
    raise ValueError(f"Unsupported volume direction: {direction}")


def _set_exact_volume(percent: int) -> bool:
    scalar = max(0, min(100, percent)) / 100
    scalar_text = f"{scalar:.2f}"
    script = f"""
$code = @'
using System;
using System.Runtime.InteropServices;

[Guid("BCDE0395-E52F-467C-8E3D-C4579291692E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator
{{
    int NotImpl1();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice
{{
    int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams, out IAudioEndpointVolume ppInterface);
}}

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume
{{
    int RegisterControlChangeNotify(IntPtr pNotify);
    int UnregisterControlChangeNotify(IntPtr pNotify);
    int GetChannelCount(out int pnChannelCount);
    int SetMasterVolumeLevel(float fLevelDB, Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, Guid pguidEventContext);
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetChannelVolumeLevel(uint nChannel, float fLevelDB, Guid pguidEventContext);
    int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, Guid pguidEventContext);
    int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
    int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
    int SetMute(bool bMute, Guid pguidEventContext);
    int GetMute(out bool pbMute);
    int GetVolumeStepInfo(out uint pnStep, out uint pnStepCount);
    int VolumeStepUp(Guid pguidEventContext);
    int VolumeStepDown(Guid pguidEventContext);
    int QueryHardwareSupport(out uint pdwHardwareSupportMask);
    int GetVolumeRange(out float pflVolumeMindB, out float pflVolumeMaxdB, out float pflVolumeIncrementdB);
}}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject {{ }}

public class AudioVolume
{{
    public static void Set(float level)
    {{
        var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice device;
        Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out device));
        Guid endpointVolumeGuid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume endpoint;
        Marshal.ThrowExceptionForHR(device.Activate(ref endpointVolumeGuid, 23, IntPtr.Zero, out endpoint));
        Marshal.ThrowExceptionForHR(endpoint.SetMasterVolumeLevelScalar(level, Guid.Empty));
    }}
}}
'@
Add-Type -TypeDefinition $code
[AudioVolume]::Set({scalar_text})
Write-Output 'OK'
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and "OK" in result.stdout


def _set_wifi_state(enabled: bool) -> bool:
    command = (
        f"$adapter = {WIFI_ADAPTER_SELECTOR}; "
        "if (-not $adapter) { exit 1 }; "
        "$adapter | Enable-NetAdapter -Confirm:$false -PassThru | Select-Object -ExpandProperty Name"
        if enabled
        else f"$adapter = {WIFI_ADAPTER_SELECTOR}; "
        "if (-not $adapter) { exit 1 }; "
        "$adapter | Disable-NetAdapter -Confirm:$false -PassThru | Select-Object -ExpandProperty Name"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def _set_bluetooth_state(enabled: bool) -> bool:
    desired = "On" if enabled else "Off"
    script = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Devices.Radios.Radio, Windows.Devices.Radios, ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Radios.RadioState, Windows.Devices.Radios, ContentType=WindowsRuntime] | Out-Null
$operation = [Windows.Devices.Radios.Radio]::GetRadiosAsync()
$task = [System.WindowsRuntimeSystemExtensions]::AsTask($operation)
$task.Wait()
$radio = $task.Result | Where-Object {{ $_.Kind.ToString() -eq 'Bluetooth' }} | Select-Object -First 1
if (-not $radio) {{ exit 1 }}
$setOperation = $radio.SetStateAsync([Windows.Devices.Radios.RadioState]::{desired})
$setTask = [System.WindowsRuntimeSystemExtensions]::AsTask($setOperation)
$setTask.Wait()
if ($setTask.Result.ToString() -eq 'Success') {{
    Write-Output 'OK'
}} else {{
    exit 1
}}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and "OK" in result.stdout


def _set_brightness(percent: int) -> bool:
    command = (
        "$value = {value}; "
        "Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods "
        "| Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{{Brightness=$value; Timeout=1}}"
    ).format(value=percent)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
