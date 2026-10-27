# Ollama Code — performance guide

Version 22 introduces a smaller default context of 8,192 tokens (previously 32,768), model keep-alive of 10 minutes, and a 512-token generation cap for simple conversational prompts. Coding requests keep the configured output budget. These are responsiveness-focused defaults, **not** a guarantee of faster inference or better code quality.

## Run

```bash
ollama-code --workspace . --fast
ollama-code --workspace . --cli --context 16384
```

To disable the fast conversational cap, set `OLLAMA_CODE_FAST=0`. To override the default context, set `OLLAMA_CODE_CONTEXT=16384` or pass `--context` in CLI mode. The full-screen interface currently reads context from the environment, not the CLI flag.

## Troubleshooting

- Check `ollama ps` to see whether the model is loaded and which processor is in use.
- Use a model that fits available memory; swapping to storage can cause severe delays or process termination.
- Reduce the context size when memory is tight, but increase it for complex repositories if hardware allows.
- Keep the Ollama server running to avoid repeated cold starts.
- Token generation speed depends on hardware and model size. UI refresh optimisations only affect how quickly text appears on screen.
- No benchmark numbers are claimed without measuring a real server and model.
