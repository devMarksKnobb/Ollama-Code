<div align="center">

# OLLAMA CODE

**An unofficial, local-first coding agent for your terminal.**

*Explore · Plan · Edit · Validate · Build*

[Quick start](#quick-start) · [Features](#features) · [Commands](#terminal-commands) · [Safety](#security--privacy) · [Contributing](#contributing)

![Python](https://img.shields.io/badge/Python-3.10%2B-111111?style=flat-square&logo=python&logoColor=white) ![License](https://img.shields.io/badge/License-MIT-111111?style=flat-square) ![Ollama](https://img.shields.io/badge/Powered%20by-Ollama-111111?style=flat-square) ![UI](https://img.shields.io/badge/Terminal-Textual-111111?style=flat-square)

</div>

---

## Why Ollama Code?

Ollama Code combines local model inference with repository-aware tools in a dark, keyboard-friendly terminal interface. Explore unfamiliar projects, inspect source with line numbers, propose multi-file edits, review diffs, and run validation in an isolated environment when configured.

> **Independent project:** Ollama Code is unofficial and is not affiliated with or endorsed by Ollama. The Ollama name belongs to its respective owners. This repository does not distribute model weights or official Ollama branding.

## Features

| Area | Capabilities |
| --- | --- |
| Chat | Streaming responses, animated activity, checkpoints, resume and continuation |
| Code | Workspace search, repository map, numbered source views, targeted edits, multi-file patches |
| Quality | Python and other available syntax checks, project test discovery, patch conflict checks, rollback attempts |
| Tools | Git status/diffs, file import/export, web search, model switching |
| Safety | Approval policies, protected paths, Docker/Podman command isolation (when available) |
| Interface | Dark monochrome Textual TUI, compact mobile layout, file controls, keyboard mode |
| Developer experience | Workspace settings, doctor command, VS Code terminal launch tasks, transcripts |

**Status:** Features are under active development. Automated tests do not establish that all models, operating systems, sandboxes, or mobile keyboards work end-to-end. Treat changes as proposals and review them before using them in important repositories.

## Quick start

Install [Ollama](https://ollama.com/) and Python 3.10 or later. In the extracted project directory:

```bash
python3 -m pip install -e .
ollama pull qwen2.5-coder:1.5b
ollama-code-doctor
ollama-code --workspace .
```

For the classic scrolling CLI, use:

```bash
ollama-code --workspace . --cli
```

For isolated command execution, install Docker or Podman and ensure your configured image has the language tools needed by your project. The agent does not silently fall back to unrestricted host execution when isolation is unavailable.

### Android / Termux

The compact terminal layout is intended to help with narrow displays. Run `/keyboard` or `Ctrl+K` to hide extra chrome while typing. For optional shared-storage access, run `termux-setup-storage` in Termux and explicitly approve individual imports/exports. Android may still terminate a process under memory pressure; checkpoints cannot guarantee recovery of an in-progress tool operation.

## Terminal commands

| Command | Purpose |
| --- | --- |
| `/help` | List available commands |
| `/models`, `/model NAME` | Discover or switch models |
| `/files`, `/code PATH` | Browse and inspect source |
| `/search TEXT` | Search workspace content |
| `/new PATH` | Create a file with approval |
| `/import SOURCE DEST` | Import a file from a permitted location |
| `/export SOURCE DEST` | Export a workspace file |
| `/settings`, `/approval MODE` | Inspect or update workspace settings |
| `/resume`, `/continue`, `/status` | Recover and inspect task progress |
| `/keyboard` | Compact the mobile layout |
| `/health` | Check connection and available models (TUI) |
| `/save` | Save the visible text transcript (TUI) |
| `/vscode` | Create VS Code terminal tasks |
| `/clear`, `/quit` | Clear the chat or exit |

Transcripts are written to `.ollama-code/transcripts/` and may contain source code or private prompts. Review them before sharing.

## Model and performance tips

Start with a model your machine can actually load. Context size and agent step budgets are configurable, but larger values consume more memory and do not automatically improve correctness. Tool-calling quality differs across models; review generated patches and run the project's own tests.

## Security & privacy

- Read/write operations are constrained to the configured workspace unless you explicitly request an import/export.
- Approval modes can automate decisions. Use automatic approval only for trusted workspaces.
- Containers limit command execution, but they are not a substitute for reviewing untrusted code or securing the host.
- External web search and remote Ollama-compatible endpoints can send queries, code, or metadata to third parties. Check their privacy terms before enabling them.
- Back up important repositories and review diffs before accepting changes.
- **No warranty:** This software is provided under the MIT License, without warranty. Review the license and applicable law; no disclaimer removes rights that cannot legally be excluded.

## Development and testing

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q
python3 -m compileall -q ollama_code
```

The test suite covers selected agent, workspace, patch, settings and tool behaviors. Live inference and physical-device UI testing are separate integration requirements.

## Architecture

```text
ollama_code/
  app.py           Agent, model client, CLI, workspace operations
  tui.py           Responsive full-screen terminal interface
  sandbox.py       Isolated command execution
  intelligence.py  Repository indexing and retrieval
  validation.py    Syntax and test discovery
  devtools.py      Developer utilities
  settings.py      Persistent workspace settings
  continuity.py    Session checkpoints
  doctor.py        Environment diagnostics
  vscode.py        VS Code terminal task integration
```

## Contributing

Issues, bug reproductions, documentation corrections, tests, and focused pull requests are welcome. Include your operating system, Python version, model name, steps to reproduce, and a redacted error log when reporting bugs. Never include API keys or private project files in an issue.

## Acknowledgements

Built to work with [Ollama](https://github.com/ollama/ollama), using [Textual](https://github.com/Textualize/textual) and [Rich](https://github.com/Textualize/rich) for the terminal experience. Inspired by established open-source terminal and coding workflows; not a fork of Ollama or llama.cpp.

## License

MIT — see [LICENSE](LICENSE).


## 20.0 · File and media attachments

Ollama Code now accepts explicit, queued attachments from either the classic CLI or full-screen terminal chat:

```text
/read README.md
/image ~/Pictures/screenshot.png
/video ~/Videos/demo.mp4
Explain the screenshot, review the README, and summarize the sampled video frames.
```

`/read` attaches text files up to 128 KiB; `/image` attaches PNG/JPEG/WebP up to 12 MiB; `/video` extracts up to four frames using the optional `ffmpeg` executable (video up to 250 MiB). Images require a vision-capable Ollama model. Video processing provides sampled still frames only, not full motion or audio understanding. Attachments are transmitted to the configured Ollama server when you send your next prompt. Avoid sending sensitive files to untrusted remote endpoints. Paths may be absolute (including Termux shared storage after permission) or relative to the workspace.

### Installer

From the extracted project folder:

```bash
bash install.sh
ollama-code --workspace .
```

The installer installs the Python package and checks for the Ollama CLI; it does not install Ollama itself or download models. On Android, use `termux-setup-storage` to grant storage access. The classic CLI remains available with `--cli` for narrow screens.

## Dark terminal 20.0: responsive streaming

The full-screen UI uses a monochrome **OLLAMA CODE** banner, spacious conversation area, separate four-dot activity animation, and an independently refreshed live response. The animation advances through `●···`, `·●··`, `··●·`, `···●` without redrawing the response. Incoming text is batched for display at up to ten refreshes per second; this reduces terminal rendering work but cannot increase the underlying model's token generation speed.

For Android, use Ctrl+K to hide the large header while the keyboard is open. For slow inference, use a smaller model, verify the Ollama host is reachable, and lower the configured context window if RAM is insufficient. Model speed depends on hardware, model size, context and server load.

## Conversational chat

Ollama Code is not restricted to code generation. Say `Hi`, `What are you?`, or ask for an explanation. Short conversational messages use normal Ollama chat without supplying coding tools, while coding tasks retain the full tool-enabled agent. Responses come from your configured Ollama model and can vary.

## Performance tuning (v22)

Ollama Code now defaults to an 8K context window to reduce memory pressure on mobile hardware; override it for larger coding tasks. Simple greetings use a shorter output budget, while coding tasks retain the full configured budget. Requests ask Ollama to keep the model loaded for ten minutes to reduce repeated cold-start overhead. See [PERFORMANCE.md](PERFORMANCE.md) for settings and limitations.


## Long-running coding tasks (23.0)

The default context request is now **32,768 tokens** and the output budget is **8,192 tokens**. A task can use up to 160 agent steps per continuation round, with up to 3 rounds before the safety limit. The agent automatically continues between rounds and saves checkpoints. This avoids requiring `/continue` for normal step-budget exhaustion.

```bash
ollama-code --workspace . --context 32768 --max-steps 160
```

Environment options: `OLLAMA_CODE_CONTEXT=65536`, `OLLAMA_CODE_PREDICT=8192`, `OLLAMA_CODE_AUTO_CONTINUE=1`, and `OLLAMA_CODE_CONTINUATION_ROUNDS=3`. Larger contexts consume significantly more memory and may fail to load on low-RAM devices. The server and model must support the selected window. Automatic continuation cannot guarantee completion after crashes, network failures, or model context exhaustion. Old context is compacted to fit an approximate character budget; it is not token-accurate.
