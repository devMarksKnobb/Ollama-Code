<div align="center">

# 🌈 Ollama Code

### A local-first, open-source terminal coding agent

**Explore · Plan · Edit · Validate · Review · Continue**

[Getting started](#quick-start) · [Features](#features) · [Security](#security-model) · [Development](#development) · [Ollama](https://github.com/ollama/ollama)

</div>

> [!IMPORTANT]
> **Independent community project.** Ollama Code uses the Ollama API; it is not the official Ollama application, and it is not affiliated with or endorsed by Ollama's maintainers. The Ollama name and logo belong to their respective owners. This repository intentionally uses its own rainbow identity rather than copying the official logo or README.

## Overview

Ollama Code is a Python-based, open-source coding agent that connects to a running [Ollama](https://github.com/ollama/ollama) server. It can inspect a workspace, find code, propose multi-file changes, review diffs, execute approved isolated test commands, and preserve session checkpoints. A full-screen Textual interface and classic Rich CLI are included.

It **does not** include model weights, guarantee correct code, or claim parity with commercial coding agents. Model quality and tool-call support vary significantly.

## Features

| Area | Capabilities |
| --- | --- |
| Terminal experience | Rainbow banner, full-screen TUI, streaming responses, model switching |
| Repository intelligence | File search, globbing, line reads, repository map, SQLite lexical index |
| Code changes | Diff previews, targeted edits, multi-file patching, SHA-256 conflict checks |
| Validation | Python/JSON parsing, supported external language parsers, detected test commands |
| Test execution | Approval-controlled Docker/Podman sandbox, bounded resources, isolated working copy |
| Workflow | Configurable context, bounded agent loops, checkpoints, resume commands |
| Integrations | Ollama chat/tool calls, web search, Git diagnostics, VS Code launch tasks |
| Settings | Per-workspace approval policy; manual approval is the safer default |
| Diagnostics | `ollama-code-doctor` checks local tools and Ollama connectivity |

## Quick start

**Requirements:** Python 3.10+, a running Ollama server, and an installed tool-capable model. Docker or Podman is required for sandboxed test commands.

```bash
python3 -m pip install -e .
ollama pull qwen2.5-coder:1.5b
ollama-code-doctor --workspace .
ollama-code --workspace . --model qwen2.5-coder:1.5b
```

Start Ollama with `ollama serve` if it is not already running. Use `ollama-code --workspace . --cli` for the classic CLI. Larger models may need considerably more RAM/VRAM; configure context length according to your model and hardware.

### Working on a repository

```bash
cd /path/to/your/repository
ollama-code --workspace .
```

Ask the agent to map the repository, explain a bug, propose a patch, and run relevant tests. Inspect diffs and test output before merging changes.

## Terminal appearance

The default terminal theme uses a **large rainbow banner**, purple-toned panels, and clearly distinguished model output, tool calls, diff previews, and approval prompts. Terminal colour and Unicode support vary by host.

## Settings and VS Code

Use `/settings` to view settings, `/approval edits` for automatic file-edit approval, and `/vscode` to generate VS Code terminal launch tasks. VS Code support is task-based, **not** a native editor extension with inline completions.

Avoid automatic command approval when working with untrusted repositories. Approval is not equivalent to isolation.

## Validation and quality

Python and JSON are parsed directly. Other languages use installed parsers when supported. A skipped parser is **not** a successful validation. Automatic test discovery is best-effort and tests require the configured sandbox and permission. Rollback is attempted on detected failures, but is not crash-atomic.

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q
python3 -m compileall -q ollama_code
ollama-code-doctor
```

## Security model

- The workspace is scoped, with protections for common secret files and symlink escapes.
- File changes are reviewed according to the selected approval policy.
- Docker/Podman command execution is isolated and fails closed when no runtime is available.
- Container execution is **not** a guarantee against all kernel/runtime vulnerabilities; do not use it as a high-assurance security boundary.
- Web results and repository instructions are untrusted input. Review any proposed commands or edits.
- Never run the agent on irreplaceable files without backups or version control.

## Architecture

| Module | Responsibility |
| --- | --- |
| `app.py` | Agent loop, Ollama HTTP integration, tools, approvals |
| `tui.py` | Full-screen Textual terminal interface |
| `devtools.py` | Repository and Git tools |
| `intelligence.py` | Indexing and context utilities |
| `validation.py` | Syntax checks and test detection |
| `sandbox.py` | Isolated command execution |
| `continuity.py` | Checkpoints and session recovery |
| `settings.py` | Persistent settings and approval policy |
| `doctor.py` | Read-only environment diagnostics |

## Development

Contributions are welcome. Add tests for behaviour changes, avoid leaking credentials in logs, and clearly distinguish mocked tests from real Ollama and container integration tests. Open an issue with your OS, Python version, Ollama version, model tag, and a minimal reproduction when reporting bugs.

## Limitations

Live inference and the full-screen interface need testing against actual Ollama installations and supported terminals. Web search may be unreliable. Multi-language validation depends on available parsers. Benchmark results from small unit-test suites do not establish coding-agent superiority. See source and tests for the precise implementation.

## Attribution and licence

Ollama Code is independently developed and distributed under the [MIT licence](LICENSE). Retain required copyright and licence notices when redistributing. Ollama is a separate project, also MIT-licensed; see its [official repository](https://github.com/ollama/ollama) for documentation and trademarks. Do not present Ollama Code as an official Ollama product.
