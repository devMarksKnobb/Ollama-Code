import tempfile
from pathlib import Path
from ollama_code.settings import Settings,ApprovalPolicy
from ollama_code.vscode import install_workspace_config

def test_approval_modes():
    with tempfile.TemporaryDirectory() as d:
        s=Settings(d);p=ApprovalPolicy(s)
        assert not p.decide('Run in isolated container?',lambda:False)
        s.set('approval','edits')
        assert not p.decide('Apply this file change?',lambda:False)
        assert p.decide('Apply this file change?',lambda:True)
        assert p.decide('Read workspace files',lambda:False)
        assert not p.decide('Run in isolated container?',lambda:False)
        s.set('approval','all')
        assert p.decide('Run in isolated container?',lambda:False)
        assert not p.decide('Apply 2 validated file changes?',lambda:False)
        assert Settings(d).values['approval']=='all'

def test_vscode_never_overwrites():
    with tempfile.TemporaryDirectory() as d:
        assert 'Created' in install_workspace_config(d,lambda _:True)
        p=Path(d)/'.vscode/tasks.json';original=p.read_bytes()
        assert 'already exist' in install_workspace_config(d,lambda _:True)
        assert p.read_bytes()==original
