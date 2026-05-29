# NeuronOS Windows Control Expansion Design

## Goal

Expand NeuronOS from a launcher-and-browser assistant into a broader Windows desktop helper that can perform most everyday local tasks directly, while still blocking truly risky actions.

## Scope

This design covers:

- broader Windows task routing from natural language
- system controls such as volume, mute, brightness, Wi-Fi, and Bluetooth
- direct navigation to Windows settings pages
- controlled automatic changes for a small set of system settings
- broader app, file, and folder opening behavior
- power actions with different safety levels
- clear spoken and visual execution feedback

This design does not cover:

- unrestricted arbitrary UI automation across any app
- destructive file management
- registry editing
- security-policy or firewall changes
- admin-only system modification flows

## Product Behavior

NeuronOS should handle most routine PC tasks without making the user babysit the interaction. If the user says things like:

- `reduce volume`
- `mute the laptop`
- `open bluetooth settings`
- `turn on bluetooth`
- `open display settings`
- `open calculator`
- `open downloads`
- `restart the pc`

the assistant should route those requests into deterministic local actions and respond with short readable status updates, plus brief spoken feedback for task execution.

If a system change cannot be completed directly, NeuronOS should try the direct path first and then fall back to opening the exact Windows settings page with a message that explains the fallback.

Example:

`I couldn't toggle Bluetooth directly, so I opened Bluetooth settings.`

## Architecture

### Planner

`backend/neuronos/planner.py` remains the intent router. It should continue distinguishing between:

- conversational questions
- browser and site tasks
- app launch and path open tasks
- Windows control tasks

The planner should stay deterministic for common system commands. It should not require the LLM for actions like audio changes, settings navigation, or power actions.

### Windows Control Layer

Add a new module at `backend/neuronos/windows_controls.py` that owns Windows-specific controls. This module should expose focused functions for:

- audio control
- brightness control
- settings-page opening
- network toggles
- power actions
- default file and folder opens
- approved UI automation fallback helpers

This keeps Windows behavior out of `planner.py` and prevents `tools.py` from turning into a single large mixed-responsibility file.

### Tool Executor

`backend/neuronos/tools.py` remains the execution gateway, but delegates Windows-specific actions to `windows_controls.py`.

New tool families should include:

- `system.audio`
- `system.brightness`
- `system.network`
- `system.settings`
- `system.power`
- `app.open_default`

The executor should continue recording execution results in memory and returning concise output strings that the UI can display and speak back.

### UI

The frontend should not need a major structural change. It should consume better execution outputs and speak brief task progress lines such as:

- `Lowering volume.`
- `Opening Bluetooth settings.`
- `Turning Wi-Fi off.`
- `Restarting your PC.`

Conversation rendering should continue favoring readable status blocks over dense paragraphs for action-oriented responses.

## Capability Groups

### 1. Device Controls

Support:

- volume up
- volume down
- set volume to a percentage
- mute
- unmute
- brightness up
- brightness down
- set brightness to a percentage when supported by the machine

Implementation should prefer native Windows or PowerShell-accessible APIs. If brightness cannot be controlled on a given machine, NeuronOS should open display settings instead of silently failing.

### 2. Settings Actions

Support:

- open specific settings pages using `ms-settings:` URIs
- attempt direct toggles for common settings where feasible
- fall back to opening the exact page if the direct path fails

Examples:

- Bluetooth settings
- Wi-Fi settings
- display settings
- sound settings
- apps settings
- power and battery settings

Direct settings changes should be narrow and approved by design, not arbitrary generalized UI clicking.

### 3. Network Toggles

Support:

- turn Wi-Fi on or off
- turn Bluetooth on or off when Windows exposes a reliable path

Where direct toggles are inconsistent across machines, NeuronOS should attempt the direct method once and fall back to the correct settings page.

### 4. App, File, and Folder Actions

Expand current behavior to:

- better fuzzy matching for installed apps via Start menu app catalog and aliases
- open folders with File Explorer
- open files with their default Windows apps
- open paths in known apps such as VS Code when explicitly requested

This should make phrases like `open downloads`, `open this folder in vscode`, or `open that pdf` feel natural.

### 5. Power Actions

Support:

- sleep
- restart
- shutdown
- lock screen

Safety handling:

- sleep: auto-run
- restart: auto-run
- shutdown: ask once before execution
- lock screen: auto-run

## Safety Model

### Auto-Run Safe Actions

These should run without extra confirmation:

- app launches
- known-site opens
- file and folder opens
- volume and mute changes
- brightness changes
- settings-page opens
- Wi-Fi and Bluetooth toggles where supported
- sleep
- restart
- lock screen

### Ask Once Before Running

These should request one approval:

- shutdown
- allowed terminal commands that still carry meaningful impact
- file writes outside assistant-owned data directories

### Blocked Outright

These stay blocked:

- destructive file deletion or move behavior in protected or broad paths
- registry edits
- firewall or antivirus changes
- credential or account-security changes
- arbitrary process termination
- admin-only system modifications
- suspicious shell commands

## Natural Language Handling

The planner should broaden support for everyday phrasing and common speech mistakes. It should recognize both direct and conversational forms such as:

- `reduce volume`
- `lower the sound`
- `turn volume down a bit`
- `open settings and go to bluetooth`
- `turn wifi off`
- `restart my laptop`
- `open calculator`
- `open downloads folder`

Transcript cleanup should continue correcting common app and site misrecognitions, but the new work should add a similar alias layer for Windows controls and settings phrases.

## Reliability Strategy

To keep the assistant fast and trustworthy:

- common actions stay deterministic
- the LLM is not required for routine desktop control
- each Windows control helper returns explicit success or fallback text
- UI automation fallback stays small in scope and focused on known settings surfaces
- every new action family receives planner tests and tool execution tests

## Testing

### Unit Tests

Add tests for:

- planner routing for system controls
- alias and fuzzy matching for Windows tasks
- safety rules for power and system actions
- executor delegation to Windows control helpers

### Integration Tests

Add tests for:

- `reduce volume`
- `mute`
- `open bluetooth settings`
- `turn wifi off`
- `open downloads`
- `restart the pc`
- `shutdown the pc` requiring approval

These tests should mock direct Windows command execution where needed so the suite stays deterministic.

### Manual Verification

Manual checks should confirm:

- task actions feel immediate
- status text is short and readable
- spoken task feedback matches the actual action
- failure paths open the correct settings page instead of stalling

## File Plan

Expected primary file changes:

- create `backend/neuronos/windows_controls.py`
- modify `backend/neuronos/tools.py`
- modify `backend/neuronos/planner.py`
- modify `backend/neuronos/schemas.py` if new tool shapes are needed
- modify `backend/neuronos/safety.py`
- add `backend/tests/test_windows_controls.py`
- expand `backend/tests/test_planner.py`
- expand `backend/tests/test_tools.py`
- expand frontend status tests if spoken feedback strings change

## Rollout Order

Recommended implementation order:

1. audio controls
2. settings URIs and settings-page routing
3. power actions and approval handling
4. file and folder default opens
5. Wi-Fi and Bluetooth toggles with fallback behavior
6. brightness control with fallback behavior

This order gives the fastest path to a noticeably more capable assistant while keeping platform-specific risk manageable.

## Open Decisions Resolved

- broad everyday task support is desired
- NeuronOS should handle most tasks except very risky ones
- direct system changes should be attempted automatically first
- sleep and restart should run directly
- shutdown should ask once before running

## Implementation Readiness

This design is scoped to one coherent expansion of the existing MVP rather than a fully open-ended autonomous desktop agent. It reuses the current planner and executor architecture, adds a focused Windows control layer, and keeps the assistant fast by avoiding unnecessary model involvement in routine system actions.
