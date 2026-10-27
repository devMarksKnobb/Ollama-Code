import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from ollama_code.sandbox import ContainerSandbox, SandboxUnavailable
from ollama_code.app import Workspace

class SandboxTests(unittest.TestCase):
    def test_flags_and_read_only_mount(self):
        with TemporaryDirectory() as directory, patch('shutil.which',return_value='/usr/bin/docker'):
            cmd=ContainerSandbox(directory).command('python -m pytest')
            self.assertIn('none',cmd)
            self.assertIn('--read-only',cmd)
            self.assertIn('--cap-drop',cmd)
            self.assertIn('--pids-limit',cmd)
            self.assertIn(f'type=bind,src={Path(directory).resolve()},dst=/source,readonly',cmd)
            self.assertEqual(cmd[-3],'/bin/sh')
    def test_missing_engine_fails_closed(self):
        with TemporaryDirectory() as directory, patch('shutil.which',return_value=None):
            with self.assertRaises(SandboxUnavailable):ContainerSandbox(directory).command('pytest')
    def test_rejected_command_never_runs(self):
        with TemporaryDirectory() as directory, patch('shutil.which',return_value='/usr/bin/docker'):
            ws=Workspace(directory,approve=lambda _:False)
            with patch('ollama_code.sandbox.subprocess.run') as run:
                self.assertIn('rejected',ws.run_command('pytest'))
                run.assert_not_called()
    def test_no_host_fallback(self):
        with TemporaryDirectory() as directory, patch('shutil.which',return_value=None):
            ws=Workspace(directory,approve=lambda _:True)
            self.assertIn('unavailable',ws.run_command('pytest'))
if __name__=='__main__':unittest.main()
