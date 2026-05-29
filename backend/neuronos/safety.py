from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str


class SafetyPolicy:
    """Windows-first guardrails for local task execution."""

    protected_roots = (
        Path("C:/Windows"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("C:/ProgramData"),
    )
    protected_fragments = (
        "system32",
        "$recycle.bin",
        "\\appdata\\roaming\\microsoft\\credentials",
        "\\appdata\\local\\microsoft\\credentials",
        "\\.ssh",
        "\\.gnupg",
    )
    destructive_tokens = (
        "remove-item",
        "del ",
        "erase ",
        "rd ",
        "rmdir ",
        "format ",
        "diskpart",
        "bcdedit",
        "takeown",
        "icacls",
        "cipher ",
        "shutdown ",
    )
    registry_tokens = ("reg delete", "reg add", "set-itemproperty hklm", "new-item hklm")
    security_tokens = (
        "set-mppreference",
        "disableantispyware",
        "disablerealtimemonitoring",
        "netsh advfirewall set",
        "stop-service windefend",
    )

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root.resolve() if workspace_root else None

    def check_terminal_command(self, command: str) -> SafetyDecision:
        normalized = _normalize_command(command)
        if not normalized:
            return SafetyDecision(False, "Empty command is blocked.")

        if any(token in normalized for token in self.registry_tokens):
            return SafetyDecision(False, "Registry changes are blocked.")

        if any(token in normalized for token in self.security_tokens):
            return SafetyDecision(False, "Security setting changes are blocked.")

        paths = _extract_windows_paths(command)
        if any(self._is_protected_path(path) for path in paths):
            return SafetyDecision(False, "Command targets a protected path.")

        has_destructive_token = any(token in normalized for token in self.destructive_tokens)
        has_recursive_flag = "-recurse" in normalized or "/s" in normalized
        if has_destructive_token and has_recursive_flag:
            return SafetyDecision(False, "Recursive destructive commands are blocked.")

        if has_destructive_token and not paths:
            return SafetyDecision(False, "Destructive commands require a safe explicit path.")

        return SafetyDecision(True, "Command is allowed.")

    def check_file_operation(self, operation: str, target: Path) -> SafetyDecision:
        if self._is_protected_path(target):
            return SafetyDecision(False, "File operation targets a protected path.")

        if operation.lower() in {"delete", "move", "write"} and self.workspace_root:
            try:
                target.resolve().relative_to(self.workspace_root)
            except ValueError:
                return SafetyDecision(
                    False,
                    "Write, move, and delete operations must stay inside the workspace.",
                )

        return SafetyDecision(True, "File operation is allowed.")

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

    def _is_protected_path(self, target: Path) -> bool:
        target_text = str(target).replace("/", "\\").lower()
        for fragment in self.protected_fragments:
            if fragment in target_text:
                return True

        try:
            target_resolved = target.resolve(strict=False)
        except OSError:
            target_resolved = target

        for root in self.protected_roots:
            if _same_or_child(target_resolved, root):
                return True
        return False


def _normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip().lower())


def _extract_windows_paths(command: str) -> list[Path]:
    matches = re.findall(r"[A-Za-z]:[\\/][^\s\"']+", command)
    return [Path(os.path.normpath(match)) for match in matches]


def _same_or_child(target: Path, root: Path) -> bool:
    try:
        target.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False
