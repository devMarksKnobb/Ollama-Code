<div align="center">

# ✦ OLLAMA CODE

### A local-first coding agent for your terminal.

**Explore · Plan · Edit · Validate · Build**

[Quick start](#-quick-start) · [Features](#-what-it-does) · [Commands](#-terminal-commands) · [Security](#-security--privacy) · [Contributing](#-contributing)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Powered by Ollama](https://img.shields.io/badge/Powered%20by-Ollama-111827?style=for-the-badge)
![Terminal UI](https://img.shields.io/badge/UI-Textual-7C3AED?style=for-the-badge)
![License: MIT](https://img.shields.io/badge/License-MIT-16A34A?style=for-the-badge)

</div>

---

Ollama Code is an **unofficial, local-first terminal coding assistant** powered by models served by [Ollama](https://ollama.com/). It can inspect a workspace, answer questions about a codebase, propose changes, show diffs, and run available validation steps—all from a keyboard-friendly dark terminal UI.

> [!IMPORTANT]
> Ollama Code is an independent community project and is not affiliated with, endorsed by, or an official product of Ollama. The Ollama name belongs to its respective owners. This repository does not distribute model weights.

## ✨ What it does

| | Capability | Details |
|---|---|---|
| 💬 | **Streaming chat** | Live responses, activity indicators, session checkpoints, resume and continuation |
| 🧭 | **Codebase exploration** | Workspace file listing, text search, repository maps and line-numbered source views |
| 🛠️ | **Change proposals** | Targeted edits, multi-file patches, readable diffs and approval prompts |
| ✅ | **Validation** | Syntax checks, test discovery, patch conflict checks and rollback attempts |
| 🧰 | **Developer tools** | Git status/diffs, model switching, web search, file import/export and VS Code tasks |
| 🛡️ | **Safety controls** | Protected paths, configurable approvals and Docker/Podman isolation when configured |
| 🎨 | **Terminal UI** | Dark navy theme, large gradient wordmark with a dotted Ollama-inspired emblem, minimal idle chrome, and compact layouts |
| 📱 | **Narrow screens** | Compact layout and keyboard mode for small terminal windows, including Termux |

## 🚀 Quick start

### 1. Prerequisites

- Python **3.10 or newer**
- [Ollama](https://ollama.com/) installed and running
- A model pulled locally (the example below uses `qwen2.5-coder:1.5b`)

### 2. Install and launch

From the project directory:

```bash
python3 -m pip install -e .
ollama pull qwen2.5-coder:1.5b
ollama-code-doctor
ollama-code --workspace .
```

To use the classic scrolling command-line interface instead of the full-screen TUI:

```bash
ollama-code --workspace . --cli
```

### Android / Termux

The interface switches to a compact layout on narrow terminals. Use `/keyboard` or `Ctrl+K` to hide extra chrome while typing. The TUI clears the **visible terminal viewport** at launch and exit when connected to a compatible interactive terminal, so each session starts fresh. It deliberately preserves scrollback, shell history, project files, and logs; redirected/non-interactive output is left alone. To access shared storage, run `termux-setup-storage` and approve individual imports or exports when prompted.

> [!TIP]
> Start with a model your device can load comfortably. Larger models and longer context windows use more memory and do not automatically produce better code. Use `/context 32768` to change the context window for the current workspace; supported sizes depend on model and available RAM/VRAM.

## 🧭 Terminal commands

| Command | Action |
|---|---|
| `/help` | Show available commands |
| `/models`, `/model NAME` | List models or switch the active model |
| `/files`, `/view PATH [START END]`, `/code PATH` | Browse files or inspect source, optionally by line range |
| `Edit` button or `/editfile PATH` | Open the interactive terminal editor; Ctrl+S opens the approval review |
| `/history` and `/undo` | Review recent edits and request an approval-gated rollback |
| `/edit PATH [CHANGE]` | Ask the agent to edit a specific file; proposed changes require approval |
| `/context TOKENS` | Set the Ollama context window (4,096–131,072 tokens, hardware/model dependent) |
| `/search TEXT` | Search workspace contents |
| `/new PATH` | Create a file with approval |
| `/read PATH` | Attach a text file to your next prompt |
| `/image PATH` | Attach an image to your next prompt |
| `/video PATH` | Sample video frames for your next prompt |
| `/import SOURCE DEST` | Import an external file after approval |
| `/export SOURCE DEST` | Export a workspace file after approval |
| `/settings`, `/approval MODE` | View settings or change approval behavior |
| `/resume`, `/continue`, `/status` | Restore a checkpoint or inspect task progress |
| `/keyboard` | Toggle compact keyboard layout |
| `/health` | Check the Ollama connection and installed models (TUI) |
| `/save` | Save the visible conversation transcript (TUI) |
| `/vscode` | Create VS Code terminal tasks |
| `/clear`, `/quit` | Clear the chat or exit |

Transcripts are saved under `.ollama-code/transcripts/` and may contain source code or private prompts. Review them before sharing.

## 🎛️ Interface and shortcuts

- `Enter` — send a prompt
- `Ctrl+K` — toggle compact keyboard mode
- `Ctrl+R` — restore a saved session
- `Ctrl+L` — clear the visible conversation
- `Ctrl+C` — request cancellation
- `Ctrl+Q` — quit

The TUI uses [Textual](https://github.com/Textualize/textual) for layout and interaction and [Rich](https://github.com/Textualize/rich) for terminal text rendering. The wordmark has a blue-to-violet-to-rose gradient and a terminal-native dotted emblem inspired by Ollama’s circular visual identity (not an official Ollama asset). The logo adapts to terminal width; actual appearance depends on terminal font, Unicode support, color support, and available columns. Startup/exit clearing uses only the standard visible-screen ANSI sequence, never the scrollback-clear sequence.

## 🔐 Security & privacy

Ollama Code is designed to keep workspace operations reviewable, but it is not a substitute for understanding the code you run.

- File operations are constrained to the configured workspace unless you explicitly request an import or export. `/view` is read-only; `/edit` asks the agent to propose changes. The interactive TUI always shows a human approval screen before each write, with aligned before/proposed panes. Approved writes create rollback snapshots; `/history` lists recent changes and `/undo` requests an approval-gated rollback. File operations remain constrained to the configured workspace unless you explicitly request an import or export.
- Proposed changes are shown for review. Read diffs before approving them.
- File writes and external-file imports/exports always require a human approval decision, even when other actions use an automatic approval mode. Automatic approval for non-write actions can still be risky; use it only in workspaces you trust.
- Docker/Podman isolation is optional and depends on your configuration. Containers are not a complete security boundary.
- Remote Ollama-compatible endpoints and optional web-search tools may receive prompts, code snippets, or metadata. Check their privacy terms before enabling them.
- Back up important work. Validation and automated tests cannot guarantee correctness.
- Attachments are sent to the configured Ollama server when you submit the prompt. Use only files you are comfortable sharing with that endpoint.

## 🧪 Development

Clone or extract the project, then install development dependencies:

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q
python3 -m compileall -q ollama_code
```

The tests cover selected agent, workspace, patch, settings, and tool behavior. Live model inference, sandbox configuration, and physical-device UI testing require separate integration checks.

### Project layout

```text
ollama_code/
├── app.py           # Agent, model client, CLI and workspace operations
├── tui.py           # Responsive full-screen terminal interface
├── sandbox.py       # Isolated command execution
├── intelligence.py  # Repository indexing and retrieval
├── validation.py    # Syntax checks and test discovery
├── devtools.py      # Developer utilities
├── settings.py      # Workspace settings
├── continuity.py    # Session checkpoints
├── doctor.py        # Environment diagnostics
└── vscode.py        # VS Code terminal task integration
```

## 🤝 Contributing

Issues, bug reproductions, documentation fixes, tests, and focused pull requests are welcome.

When reporting a bug, include:
- Operating system and terminal
- Python version and Ollama version
- Model name
- Steps to reproduce and expected behavior
- A redacted error log, if relevant

Please remove API keys, access tokens, private prompts, and proprietary source code from reports.

## 🙌 Acknowledgements

Built with [Ollama](https://github.com/ollama/ollama), [Textual](https://github.com/Textualize/textual), and [Rich](https://github.com/Textualize/rich). The project is inspired by open-source terminal and coding workflows; it is not a fork of Ollama or `llama.cpp`.

## 📄 License

Released under the MIT License. See [`LICENSE`](LICENSE).

---

<details>
<summary><strong>Release notes and project history</strong></summary>

See [`RELEASE-23.md`](RELEASE-23.md) and [`PERFORMANCE.md`](PERFORMANCE.md) for additional project notes.

</details>
