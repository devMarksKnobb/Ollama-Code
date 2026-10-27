"""Fail-closed container command runner. No host execution fallback."""
import os
import shlex
import shutil
import subprocess
from pathlib import Path

class SandboxUnavailable(RuntimeError):
    pass

class ContainerSandbox:
    def __init__(self, root, engine=None, image=None):
        self.root = Path(root).resolve()
        self.engine = engine or os.getenv('OLLAMA_CODE_CONTAINER_ENGINE', 'docker')
        self.image = image or os.getenv('OLLAMA_CODE_SANDBOX_IMAGE', 'python:3.12-slim')

    def command(self, command):
        args = shlex.split(command)
        if not args:
            raise ValueError('Empty command')
        if not shutil.which(self.engine):
            raise SandboxUnavailable(f'{self.engine} is unavailable. Install Docker or Podman; host execution is disabled.')
        # Workspace is mounted read-only. Copy to isolated, ephemeral /work to allow tests to write.
        # Network, privileges, host process namespace and host filesystem are not exposed.
        inner = 'cp -a /source/. /work/ && cd /work && exec ' + shlex.join(args)
        return [self.engine, 'run', '--rm', '--init', '--network', 'none',
                '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--pids-limit', '128', '--memory', '1g', '--cpus', '1.5',
                '--user', '65534:65534', '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m',
                '--tmpfs', '/work:rw,nosuid,nodev,size=512m,uid=65534,gid=65534',
                '--mount', f'type=bind,src={self.root},dst=/source,readonly',
                '--workdir', '/work', '--env', 'HOME=/tmp', '--env', 'PYTHONDONTWRITEBYTECODE=1',
                self.image, '/bin/sh', '-c', inner]

    def run(self, command, timeout=120):
        argv = self.command(command)
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True, timeout=timeout, env={'PATH':os.environ.get('PATH','')})
            return f'exit={result.returncode}\nstdout:\n{result.stdout[-16000:]}\nstderr:\n{result.stderr[-8000:]}'
        except subprocess.TimeoutExpired:
            return f'Container command timed out after {timeout}s (container may require manual cleanup)'
