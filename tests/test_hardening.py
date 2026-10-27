from pathlib import Path
import pytest
from ollama_code.app import Workspace

def test_sensitive_files_blocked(tmp_path):
    w=Workspace(tmp_path,approve=lambda _: True)
    for name in ['.env','.env.production','id_rsa','id_ed25519']:
        with pytest.raises(ValueError):w.path(name)

def test_command_allowlist(tmp_path):
    w=Workspace(tmp_path,approve=lambda _: True)
    assert 'blocked' in w.run_command('bash -c whoami')
    assert 'blocked' in w.run_command('git reset --hard')

def test_audit_and_atomic_write(tmp_path):
    w=Workspace(tmp_path,approve=lambda _: True)
    w.write_file('hello.py','print(123)\n')
    assert (tmp_path/'hello.py').read_text()=='print(123)\n'
    assert 'write_file' in (tmp_path/'.ollama-code-audit.jsonl').read_text()
