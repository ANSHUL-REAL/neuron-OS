from __future__ import annotations

import subprocess
import webbrowser
from functools import lru_cache
from os import environ
from pathlib import Path
from urllib.parse import quote_plus

from yt_dlp import YoutubeDL

from .memory import MemoryStore
from .safety import SafetyPolicy
from .schemas import ToolExecuteRequest, ToolExecuteResponse
from .windows_controls import (
    adjust_brightness,
    adjust_volume,
    open_default_target,
    open_settings_page,
    perform_power_action,
    toggle_network,
)


class ToolBlockedError(Exception):
    pass


class ToolExecutor:
    def __init__(self, memory: MemoryStore, safety: SafetyPolicy):
        self.memory = memory
        self.safety = safety

    def execute(self, request: ToolExecuteRequest) -> ToolExecuteResponse:
        if request.tool == "terminal.run" and not request.approved:
            raise ToolBlockedError("Terminal commands require approval.")
        if request.tool.startswith("system."):
            category = request.tool.split(".", 1)[1]
            decision = self.safety.check_system_action(category, request.args)
            is_approved_shutdown = (
                request.tool == "system.power"
                and str(request.args.get("action", "")).strip().lower() == "shutdown"
                and request.approved
            )
            if not decision.allowed and not is_approved_shutdown:
                raise ToolBlockedError(decision.reason)

        handlers = {
            "app.launch": self._launch_app,
            "app.open_default": self._app_open_default,
            "app.open_path": self._open_path,
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
        handler = handlers.get(request.tool)
        if not handler:
            raise ToolBlockedError(f"Unsupported tool: {request.tool}")

        output = handler(request.args)
        self.memory.record_execution(request.step_id, request.tool, "completed", output)
        return ToolExecuteResponse(
            step_id=request.step_id,
            tool=request.tool,
            status="completed",
            output=output,
        )

    def _launch_app(self, args: dict) -> str:
        app = str(args.get("app", "")).strip()
        if not app:
            raise ToolBlockedError("App name is required.")
        launch_target = _special_app_target(app)
        if launch_target:
            subprocess.Popen(["cmd", "/c", "start", "", launch_target], shell=False)
            return f"Launch requested for {app}."
        executable = _find_executable(app)
        if executable:
            subprocess.Popen([str(executable)], shell=False)
        else:
            app_id = _find_start_app_id(app)
            if app_id:
                subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"], shell=False)
            else:
                subprocess.Popen(["cmd", "/c", "start", "", app], shell=False)
        return f"Launch requested for {app}."

    def _browser_search(self, args: dict) -> str:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ToolBlockedError("Search query is required.")
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        return f"Opened browser search for {query}."

    def _browser_open_url(self, args: dict) -> str:
        url = str(args.get("url", "")).strip()
        if not url.startswith(("https://", "http://")):
            raise ToolBlockedError("Only http and https URLs can be opened.")
        browser = str(args.get("browser", "")).strip()
        if browser and _reuse_existing_browser_tab(browser, url):
            return f"Opened {url}."
        executable = _find_executable(browser) if browser else None
        if executable:
            subprocess.Popen([str(executable), url], shell=False)
        else:
            webbrowser.open(url)
        return f"Opened {url}."

    def _play_youtube(self, args: dict) -> str:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ToolBlockedError("YouTube query is required.")
        url = _resolve_youtube_watch_url(query)
        return self._browser_open_url({"browser": args.get("browser", ""), "url": url})

    def _app_open_default(self, args: dict) -> str:
        path_text = str(args.get("path", "")).strip()
        if not path_text:
            raise ToolBlockedError("Path is required.")
        return open_default_target(path_text)

    def _open_path(self, args: dict) -> str:
        app = str(args.get("app", "")).strip()
        path_text = str(args.get("path", "")).strip()
        if not app or not path_text:
            raise ToolBlockedError("App and path are required.")
        target = Path(path_text)
        executable = _find_executable(app)
        if app.lower() in {"vs code", "vscode", "code"} and executable:
            subprocess.Popen([str(executable), str(target)], shell=False)
            return f"Opened {path_text} in VS Code."
        if app.lower() in {"file explorer", "explorer"}:
            subprocess.Popen(["explorer.exe", str(target)], shell=False)
            return f"Opened {path_text} in File Explorer."
        raise ToolBlockedError(f"Opening a path in {app} is not supported yet.")

    def _terminal_run(self, args: dict) -> str:
        command = str(args.get("command", "")).strip()
        decision = self.safety.check_terminal_command(command)
        if not decision.allowed:
            raise ToolBlockedError(f"Command blocked: {decision.reason}")
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolBlockedError("Command timed out.") from exc
        stdout_text = (result.stdout or "").strip()
        stderr_text = (result.stderr or "").strip()
        if result.returncode != 0 and stderr_text:
            return stderr_text
        if stdout_text:
            return stdout_text
        if stderr_text:
            return stderr_text
        return f"Command exited {result.returncode}"

    def _file_write(self, args: dict) -> str:
        path_text = str(args.get("path", "")).strip()
        if not path_text:
            raise ToolBlockedError("Path is required.")
        target = Path(path_text)
        content = str(args.get("content", ""))
        decision = self.safety.check_file_operation("write", target)
        if not decision.allowed:
            raise ToolBlockedError(f"File write blocked: {decision.reason}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {target}."

    def _memory_write(self, args: dict) -> str:
        kind = str(args.get("kind", "note"))
        content = str(args.get("content", "")).strip()
        if not content:
            raise ToolBlockedError("Memory content is required.")
        self.memory.save_memory(kind, content)
        return "Saved to local memory."

    def _conversation_respond(self, args: dict) -> str:
        return str(args.get("message", "Ready."))

    def _system_audio(self, args: dict) -> str:
        direction = str(args.get("direction", "")).strip()
        if not direction:
            raise ToolBlockedError("Audio direction is required.")
        return adjust_volume(direction, int(args.get("amount", 10)))

    def _system_brightness(self, args: dict) -> str:
        if "percent" not in args:
            raise ToolBlockedError("Brightness percent is required.")
        return adjust_brightness(int(args["percent"]))

    def _system_network(self, args: dict) -> str:
        kind = str(args.get("kind", "")).strip()
        if not kind:
            raise ToolBlockedError("Network kind is required.")
        if "enabled" not in args:
            raise ToolBlockedError("Network enabled state is required.")
        return toggle_network(kind, _parse_enabled(args["enabled"]))

    def _system_settings(self, args: dict) -> str:
        page = str(args.get("page", "")).strip()
        if not page:
            raise ToolBlockedError("Settings page is required.")
        return open_settings_page(page)

    def _system_power(self, args: dict) -> str:
        action = str(args.get("action", "")).strip()
        if not action:
            raise ToolBlockedError("Power action is required.")
        return perform_power_action(action)


def _find_executable(app: str) -> Path | None:
    app_key = app.strip().lower()
    candidates: dict[str, list[Path]] = {
        "brave": [
            Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
            Path("C:/Program Files (x86)/BraveSoftware/Brave-Browser/Application/brave.exe"),
            Path(environ.get("LOCALAPPDATA", "")) / "BraveSoftware/Brave-Browser/Application/brave.exe",
        ],
        "vs code": [
            Path(environ.get("LOCALAPPDATA", "")) / "Programs/Microsoft VS Code/bin/code.cmd",
            Path("C:/Program Files/Microsoft VS Code/bin/code.cmd"),
        ],
        "vscode": [
            Path(environ.get("LOCALAPPDATA", "")) / "Programs/Microsoft VS Code/bin/code.cmd",
            Path("C:/Program Files/Microsoft VS Code/bin/code.cmd"),
        ],
        "code": [
            Path(environ.get("LOCALAPPDATA", "")) / "Programs/Microsoft VS Code/bin/code.cmd",
            Path("C:/Program Files/Microsoft VS Code/bin/code.cmd"),
        ],
        "chrome": [
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        ],
    }
    for candidate in candidates.get(app_key, []):
        if candidate.exists():
            return candidate
    return None


def _parse_enabled(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"false", "0", "no", "off"}:
            return False
        if normalized in {"true", "1", "yes", "on"}:
            return True
    return bool(value)


def _resolve_youtube_watch_url(query: str) -> str:
    search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    try:
        with YoutubeDL({"quiet": True, "skip_download": True, "extract_flat": True}) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
    except Exception:
        return search_url
    entries = info.get("entries") or []
    if not entries:
        return search_url
    video_id = entries[0].get("id")
    if not video_id:
        return search_url
    return f"https://www.youtube.com/watch?v={video_id}"


@lru_cache(maxsize=1)
def _windows_start_apps() -> dict[str, str]:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        import json

        payload = json.loads(result.stdout)
        rows = payload if isinstance(payload, list) else [payload]
        return {
            str(row.get("Name", "")).strip().lower(): str(row.get("AppID", "")).strip()
            for row in rows
            if row.get("Name") and row.get("AppID")
        }
    except Exception:
        return {}


def _find_start_app_id(app: str) -> str | None:
    app_key = app.strip().lower()
    apps = _windows_start_apps()
    if app_key in apps:
        return apps[app_key]
    for name, app_id in apps.items():
        if app_key == name or app_key in name or name in app_key:
            return app_id
    return None


def _special_app_target(app: str) -> str | None:
    app_key = app.strip().lower()
    special_targets = {
        "settings": "ms-settings:",
        "windows settings": "ms-settings:",
    }
    return special_targets.get(app_key)


def _reuse_existing_browser_tab(browser: str, url: str) -> bool:
    window_title = _browser_window_title(browser)
    if not window_title:
        return False
    powershell_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$wshell = New-Object -ComObject WScript.Shell
if (-not $wshell.AppActivate('{window_title}')) {{
  exit 1
}}
Set-Clipboard -Value @'
{url}
'@
Start-Sleep -Milliseconds 150
$wshell.SendKeys('^l')
Start-Sleep -Milliseconds 120
$wshell.SendKeys('^v')
Start-Sleep -Milliseconds 120
$wshell.SendKeys('{{ENTER}}')
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", powershell_script],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.returncode == 0


def _browser_window_title(browser: str) -> str | None:
    browser_key = browser.strip().lower()
    titles = {
        "brave": "Brave",
        "chrome": "Chrome",
    }
    return titles.get(browser_key)
