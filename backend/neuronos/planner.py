from __future__ import annotations

import difflib
import re

from .schemas import Plan, PlanStep
from .site_catalog import COMMON_TRANSCRIPT_REPLACEMENTS, SITE_CATALOG


class Planner:
    """Small deterministic planner for MVP workflows.

    The Ollama provider can later replace or enrich this, but the MVP keeps
    predictable local plans for safety-critical tool routing.
    """

    def build_plan(self, message: str) -> Plan:
        text = _normalize_command_text(message)
        lowered = text.lower()
        lowered_plain = lowered.rstrip("?.!")

        if lowered.startswith("remember ") or "remember that" in lowered:
            content = re.sub(r"^remember\s+(that\s+)?", "", text, flags=re.I).strip()
            return Plan(
                summary="Save this preference or project note to memory.",
                steps=[
                    PlanStep(
                        title="Save memory",
                        tool="memory.write",
                        args={"kind": _memory_kind(content), "content": content},
                    )
                ],
            )

        youtube_query = _extract_youtube_video_query(text, lowered)
        if youtube_query:
            return Plan(
                summary=f"Open Brave and play {_title_case_song(youtube_query)} on YouTube.",
                steps=[
                    PlanStep(
                        title="Open Brave",
                        tool="app.launch",
                        args={"app": "Brave"},
                    ),
                    PlanStep(
                        title="Play on YouTube",
                        tool="browser.play_youtube",
                        args={
                            "browser": "Brave",
                            "query": youtube_query,
                        },
                    ),
                ],
            )

        direct_site_plan = _plan_known_site_open(text, lowered)
        if direct_site_plan:
            return direct_site_plan

        if _looks_like_browser_search(lowered):
            query = _extract_search_query(text)
            return Plan(
                summary=f"Open Brave and search for {query}.",
                steps=[
                    PlanStep(
                        title="Open Brave",
                        tool="app.launch",
                        args={"app": "Brave"},
                    ),
                    PlanStep(
                        title="Search the web",
                        tool="browser.search",
                        args={"browser": "Brave", "query": query},
                    ),
                ],
            )

        if lowered_plain.startswith(("run ", "execute ")):
            command = re.sub(r"^(run|execute)\s+", "", text, flags=re.I).strip().rstrip("?.!")
            return Plan(
                summary="Run a terminal command with approval.",
                steps=[
                    PlanStep(
                        title="Run terminal command",
                        tool="terminal.run",
                        args={"command": command},
                        requires_approval=True,
                    )
                ],
            )

        windows_control_plan = _plan_windows_control(text, lowered_plain)
        if windows_control_plan:
            return windows_control_plan

        app_open_plan = _plan_app_open(text, lowered)
        if app_open_plan:
            return app_open_plan

        return Plan(
            summary="Respond conversationally.",
            steps=[
                PlanStep(
                    title="Answer in conversation",
                    tool="conversation.respond",
                    args={"message": text},
                )
            ],
        )


def _extract_search_query(text: str) -> str:
    match = re.search(r"(?:search|look up|google)\s+(?:for\s+)?(.+)$", text, re.I)
    if match:
        return match.group(1).strip().rstrip(".")
    if "lo-fi" in text.lower():
        return "lo-fi music"
    if "lofi" in text.lower():
        return "lofi music"
    return text.strip()


def _memory_kind(content: str) -> str:
    lowered = content.lower()
    if "project" in lowered:
        return "project"
    if "prefer" in lowered or "like" in lowered:
        return "preference"
    return "note"


def _extract_youtube_song_query(text: str) -> str:
    match = re.search(r"play\s+(.+?)(?:\s+on\s+youtube|\s+in\s+youtube)?$", text, re.I)
    if not match:
        return "music"
    query = match.group(1).strip().rstrip(".")
    return query or "music"


def _extract_youtube_video_query(text: str, lowered: str) -> str | None:
    if "youtube" not in lowered and not re.search(r"\bplay\b", lowered):
        return None

    play_match = re.search(
        r"play\s+(?:a\s+)?(?:video\s+)?(?:on\s+|about\s+)?(.+?)(?:\s+on\s+youtube|\s+in\s+youtube)?$",
        text,
        re.I,
    )
    if play_match:
        return _cleanup_video_query(play_match.group(1))

    video_match = re.search(
        r"video\s+(?:on\s+|about\s+)?(.+?)(?:\s+on\s+youtube|\s+in\s+youtube)?$",
        text,
        re.I,
    )
    if video_match:
        return _cleanup_video_query(video_match.group(1))

    if "play" in lowered:
        return _cleanup_video_query(_extract_youtube_song_query(text))

    return None


def _cleanup_video_query(query: str) -> str:
    cleaned = query.strip().rstrip(".")
    cleaned = re.sub(r"^(about|on)\s+", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^youtube\s+(about\s+)?", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\s+(video|videos)$", "", cleaned, flags=re.I).strip()
    return cleaned or "music"


def _title_case_song(query: str) -> str:
    display = re.sub(r"\s+(song|music|track)$", "", query, flags=re.I).strip()
    return " ".join(word.capitalize() for word in (display or query).split())


def _plan_app_open(text: str, lowered: str) -> Plan | None:
    folder_match = re.match(r"open\s+([a-zA-Z]:[\\/].+?)\s+in\s+(vs\s*code|vscode|code)$", text, re.I)
    if folder_match:
        path_text = folder_match.group(1).strip()
        return Plan(
            summary=f"Open {path_text} in VS Code.",
            steps=[
                PlanStep(
                    title="Open folder in VS Code",
                    tool="app.open_path",
                    args={"app": "VS Code", "path": path_text},
                )
            ],
        )

    action_text = _normalize_open_request(text)
    action_lowered = action_text.lower()

    app_aliases = {
        "vs code": "VS Code",
        "vscode": "VS Code",
        "code": "VS Code",
        "visual studio code": "VS Code",
        "brave": "Brave",
        "discord": "Discord",
        "chrome": "Chrome",
        "file explorer": "File Explorer",
        "explorer": "File Explorer",
        "notepad": "Notepad",
        "settings": "Settings",
        "windows settings": "Settings",
    }
    for phrase, app_name in app_aliases.items():
        if action_lowered == f"open {phrase}" or action_lowered == f"launch {phrase}":
            return Plan(
                summary=f"Open {app_name}.",
                steps=[
                    PlanStep(
                        title=f"Open {app_name}",
                        tool="app.launch",
                        args={"app": app_name},
                    )
                ],
            )
    generic_match = re.match(r"^(open|launch)\s+([a-z0-9][a-z0-9 .&()+_-]*)$", action_lowered, re.I)
    if generic_match:
        requested = action_text.split(maxsplit=1)[1].strip().rstrip("?.!")
        blocked_tokens = ("search ", "play ", "youtube", "google", "bing", "http://", "https://")
        if (
            requested
            and not any(token in requested.lower() for token in blocked_tokens)
            and not _looks_like_compound_open_request(requested.lower())
        ):
            display = " ".join(part.capitalize() for part in requested.split())
            return Plan(
                summary=f"Open {display}.",
                steps=[
                    PlanStep(
                        title=f"Open {display}",
                        tool="app.launch",
                        args={"app": display},
                    )
                ],
            )
    return None


def _normalize_open_request(text: str) -> str:
    return _strip_conversational_prefixes(text).strip().rstrip("?.!")


def _looks_like_compound_open_request(requested: str) -> bool:
    return bool(re.search(r"\band\b\s+(open|launch|search|play|ask|go|then)\b", requested))


def _normalize_command_text(text: str) -> str:
    normalized = _strip_conversational_prefixes(text.strip())
    for pattern, replacement in COMMON_TRANSCRIPT_REPLACEMENTS:
        normalized = re.sub(pattern, replacement, normalized, flags=re.I)
    normalized = re.sub(r"\bwi[\s-]?fi\b", "wifi", normalized, flags=re.I)
    normalized = re.sub(r"\bshut\s+down\b", "shutdown", normalized, flags=re.I)
    normalized = re.sub(r"\bthen\s+", "", normalized, flags=re.I)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return re.sub(r"\s+([,.!?])", r"\1", normalized)


def _strip_conversational_prefixes(text: str) -> str:
    cleaned = text.strip()
    prefixes = (
        r"can you\s+",
        r"could you\s+",
        r"would you\s+",
        r"please\s+",
        r"can u\s+",
        r"i want to\s+",
        r"i wanna\s+",
        r"i would like to\s+",
        r"i'd like to\s+",
        r"i need to\s+",
    )
    for prefix in prefixes:
        cleaned = re.sub(f"^{prefix}", "", cleaned, flags=re.I)
    return cleaned


def _looks_like_browser_search(lowered: str) -> bool:
    return bool(
        ("brave" in lowered and ("search" in lowered or "lo-fi" in lowered or "lofi" in lowered))
        or re.match(r"^(search|look up|google)\b", lowered)
        or "lo-fi" in lowered
        or "lofi" in lowered
    )


def _plan_windows_control(text: str, lowered: str) -> Plan | None:
    volume_plan = _plan_volume_control(lowered)
    if volume_plan:
        return volume_plan

    brightness_plan = _plan_brightness_control(lowered)
    if brightness_plan:
        return brightness_plan

    settings_plan = _plan_settings_open(lowered)
    if settings_plan:
        return settings_plan

    network_plan = _plan_network_toggle(lowered)
    if network_plan:
        return network_plan

    power_plan = _plan_power_action(lowered)
    if power_plan:
        return power_plan

    return _plan_default_folder_open(lowered)


def _plan_volume_control(lowered: str) -> Plan | None:
    set_match = re.search(
        r"\b(?:set|increase|raise|turn up|lower|reduce|decrease|turn down)\s+(?:the\s+)?(?:volume|sound|audio)\s+to\s+(-?\d{1,3})\b",
        lowered,
    )
    if set_match:
        amount = max(0, min(100, int(set_match.group(1))))
        return Plan(
            summary=f"Set the volume to {amount}.",
            steps=[
                PlanStep(
                    title="Set volume",
                    tool="system.audio",
                    args={"direction": "set", "amount": amount},
                )
            ],
        )

    audio_targets = {"volume", "sound", "audio", "laptop", "pc", "computer"}

    if lowered == "unmute" or (
        "unmute" in lowered and any(target in lowered for target in audio_targets)
    ):
        return Plan(
            summary="Unmute the volume.",
            steps=[
                PlanStep(
                    title="Unmute volume",
                    tool="system.audio",
                    args={"direction": "unmute", "amount": 10},
                )
            ],
        )

    if lowered == "mute" or (
        re.search(r"\bmute\b", lowered) and any(target in lowered for target in audio_targets)
    ):
        return Plan(
            summary="Mute the volume.",
            steps=[
                PlanStep(
                    title="Mute volume",
                    tool="system.audio",
                    args={"direction": "mute", "amount": 10},
                )
            ],
        )

    if not any(target in lowered for target in {"volume", "sound", "audio"}):
        return None

    if re.search(r"\b(lower|reduce|decrease|turn down)\b", lowered):
        return Plan(
            summary="Lower the volume.",
            steps=[
                PlanStep(
                    title="Lower volume",
                    tool="system.audio",
                    args={"direction": "down", "amount": 10},
                )
            ],
        )
    if re.search(r"\b(increase|raise|turn up)\b", lowered) or lowered == "turn volume up":
        return Plan(
            summary="Raise the volume.",
            steps=[
                PlanStep(
                    title="Raise volume",
                    tool="system.audio",
                    args={"direction": "up", "amount": 10},
                )
            ],
        )
    return None


def _plan_brightness_control(lowered: str) -> Plan | None:
    set_match = re.search(r"\bset (?:the )?brightness to (-?\d{1,3})\b", lowered)
    if set_match:
        percent = max(0, min(100, int(set_match.group(1))))
        return Plan(
            summary=f"Set brightness to {percent} percent.",
            steps=[
                PlanStep(
                    title="Set brightness",
                    tool="system.brightness",
                    args={"percent": percent},
                )
            ],
        )

    if lowered in {"increase brightness", "raise brightness"}:
        return Plan(
            summary="Increase brightness.",
            steps=[
                PlanStep(
                    title="Increase brightness",
                    tool="system.brightness",
                    args={"percent": 70},
                )
            ],
        )

    if lowered in {"decrease brightness", "lower brightness", "reduce brightness"}:
        return Plan(
            summary="Decrease brightness.",
            steps=[
                PlanStep(
                    title="Decrease brightness",
                    tool="system.brightness",
                    args={"percent": 30},
                )
            ],
        )

    return None


def _plan_settings_open(lowered: str) -> Plan | None:
    page_aliases = {
        "bluetooth": ("bluetooth",),
        "wifi": ("wifi",),
        "display": ("display",),
        "sound": ("sound",),
        "apps": ("apps",),
        "power": ("power",),
    }

    for page, aliases in page_aliases.items():
        for alias in aliases:
            if lowered == f"open {alias} settings" or lowered == f"launch {alias} settings":
                return Plan(
                    summary=f"Open {alias.capitalize()} settings.",
                    steps=[
                        PlanStep(
                            title=f"Open {alias.capitalize()} settings",
                            tool="system.settings",
                            args={"page": page},
                        )
                    ],
                )
            if lowered == f"open settings and go to {alias}":
                return Plan(
                    summary=f"Open {alias.capitalize()} settings.",
                    steps=[
                        PlanStep(
                            title=f"Open {alias.capitalize()} settings",
                            tool="system.settings",
                            args={"page": page},
                        )
                    ],
                )
    return None


def _plan_network_toggle(lowered: str) -> Plan | None:
    match = re.search(r"\bturn (wifi|bluetooth) (on|off)\b", lowered)
    if not match:
        match = re.search(r"\bturn (on|off) (wifi|bluetooth)\b", lowered)
        if not match:
            return None
        state, kind = match.groups()
    else:
        kind, state = match.groups()

    enabled = state == "on"
    label = "Wi-Fi" if kind == "wifi" else "Bluetooth"
    action = "on" if enabled else "off"
    return Plan(
        summary=f"Turn {label} {action}.",
        steps=[
            PlanStep(
                title=f"Turn {label} {action}",
                tool="system.network",
                args={"kind": kind, "enabled": enabled},
            )
        ],
    )


def _plan_power_action(lowered: str) -> Plan | None:
    actions = {
        "restart": ("Restart the PC.", "Restart PC", False),
        "sleep": ("Sleep the PC.", "Sleep PC", False),
        "lock": ("Lock the PC.", "Lock PC", False),
        "shutdown": ("Shut down the PC.", "Shut down PC", True),
    }

    for action, (summary, title, requires_approval) in actions.items():
        if lowered in {
            action,
            f"{action} pc",
            f"{action} the pc",
            f"{action} my pc",
            f"{action} computer",
            f"{action} the computer",
            f"{action} my computer",
            f"{action} laptop",
            f"{action} the laptop",
            f"{action} my laptop",
        }:
            return Plan(
                summary=summary,
                steps=[
                    PlanStep(
                        title=title,
                        tool="system.power",
                        args={"action": action},
                        requires_approval=requires_approval,
                    )
                ],
            )
    return None


def _plan_default_folder_open(lowered: str) -> Plan | None:
    default_folders = {
        "downloads": r"%USERPROFILE%\Downloads",
        "documents": r"%USERPROFILE%\Documents",
        "desktop": r"%USERPROFILE%\Desktop",
    }
    for folder, path in default_folders.items():
        if lowered in {f"open {folder}", f"open {folder} folder"}:
            return Plan(
                summary=f"Open {folder.capitalize()}.",
                steps=[
                    PlanStep(
                        title=f"Open {folder.capitalize()}",
                        tool="app.open_default",
                        args={"path": path},
                    )
                ],
            )
    return None


def _plan_known_site_open(text: str, lowered: str) -> Plan | None:
    if not _looks_like_site_open_intent(lowered):
        return None
    if _site_query_targets_local_app(lowered):
        return None

    site = _extract_known_site(lowered)
    if not site:
        return None

    return Plan(
        summary=f"Open Brave and open {site['label']}.",
        steps=[
            PlanStep(
                title="Open Brave",
                tool="app.launch",
                args={"app": "Brave"},
            ),
            PlanStep(
                title=f"Open {site['label']}",
                tool="browser.open_url",
                args={"browser": "Brave", "url": site["url"]},
            ),
        ],
    )


def _looks_like_site_open_intent(lowered: str) -> bool:
    return bool(
        re.search(r"\b(open|go to|visit|launch)\b", lowered)
        or re.search(r"\bsearch\b.+\bopen\b", lowered)
    )


def _site_query_targets_local_app(lowered: str) -> bool:
    query = _cleanup_site_query(_extract_site_query(lowered))
    return query in {
        "discord",
        "discard",
        "settings",
        "windows settings",
        "file explorer",
        "explorer",
        "notepad",
        "vs code",
        "vscode",
        "visual studio code",
    }


def _extract_known_site(lowered: str) -> dict[str, str] | None:
    query_text = _extract_site_query(lowered)
    query_key = _site_key(query_text)
    catalog_keys: dict[str, tuple[str, str, int]] = {}
    direct_candidates: list[tuple[str, str, str, int]] = []

    for site in SITE_CATALOG:
        names = (site.label, *site.aliases)
        for name in names:
            token_count = len(re.findall(r"[a-z0-9]+", name.lower()))
            direct_candidates.append((name.lower(), site.label, site.url, token_count))
            catalog_keys[_site_key(name)] = (site.label, site.url, token_count)

    for candidate, label, url, token_count in sorted(
        direct_candidates, key=lambda item: len(item[0]), reverse=True
    ):
        if token_count > 1 and re.search(rf"\b{re.escape(candidate)}\b", query_text):
            return {"label": label, "url": url}
        if token_count == 1 and re.findall(r"[a-z0-9]+", query_text) == [candidate]:
            return {"label": label, "url": url}

    if query_key in catalog_keys:
        label, url, _token_count = catalog_keys[query_key]
        return {"label": label, "url": url}

    tokens = re.findall(r"[a-z0-9]+", query_text)
    for token in tokens:
        if token in {"open", "brave", "search", "and", "it", "in", "ask", "what", "is", "the", "weather", "today"}:
            continue
    all_match_keys = list(catalog_keys.keys())
    best = difflib.get_close_matches(query_key, all_match_keys, n=1, cutoff=0.72)
    if best:
        label, url, token_count = catalog_keys[best[0]]
        if token_count > 1 or len(tokens) == 1:
            return {"label": label, "url": url}
    return None


def _extract_site_query(lowered: str) -> str:
    search_match = re.search(r"search\s+(.+?)(?:\s+and\s+open\s+(?:it|that))?[.?!]?$", lowered)
    if search_match:
        return _cleanup_site_query(search_match.group(1))

    brave_open_match = re.search(r"open\s+brave\s+and\s+open\s+(.+?)[.?!]?$", lowered)
    if brave_open_match:
        return _cleanup_site_query(brave_open_match.group(1))

    open_match = re.search(
        r"(?:open|go to|visit|launch)\s+(.+?)(?:\s+and\s+open\s+(?:it|that))?[.?!]?$",
        lowered,
    )
    if open_match:
        candidate = open_match.group(1).strip()
        candidate = re.sub(r"^brave\s+(?:and\s+)?", "", candidate).strip()
        return _cleanup_site_query(candidate)

    return _cleanup_site_query(lowered)


def _cleanup_site_query(text: str) -> str:
    cleaned = text.strip().rstrip(".?!")
    cleaned = re.sub(r"\s+in\s+it\b.*$", "", cleaned).strip()
    cleaned = re.sub(r"\s+and\s+ask\b.*$", "", cleaned).strip()
    return cleaned


def _site_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())
