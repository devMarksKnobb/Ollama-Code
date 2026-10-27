#!/usr/bin/env bash
set -Eeuo pipefail
printf '\n\033[1;37m  OLLAMA CODE  |  INSTALLER\033[0m\n'
printf '  --------------------------------\n'
command -v python3 >/dev/null || { echo 'Python 3 is required'; exit 1; }
python3 - <<'CHECK'
import sys
if sys.version_info < (3,10): raise SystemExit('Python 3.10+ is required')
print('  [1/3] Python:',sys.version.split()[0])
CHECK
printf '  [2/3] Installing Ollama Code...\n'
python3 -m pip install -e .
printf '  [3/3] Checking Ollama...\n'
if command -v ollama >/dev/null; then
  ollama list || echo '  Ollama is installed but server is unavailable.'
else
  echo '  Ollama CLI not found. Install/start Ollama separately or configure --host.'
fi
printf '\n\033[1;32m  INSTALL COMPLETE\033[0m\n'
printf '  Run: ollama-code --workspace .\n'
printf '  Run: ollama-code --workspace . --cli   (mobile fallback)\n\n'
