from pathlib import Path


def test_readme_has_installation_and_security():
    readme = (Path(__file__).resolve().parents[1] / 'README.md').read_text()
    assert 'ollama-code --workspace .' in readme
    assert 'Security & privacy' in readme
    assert 'unofficial' in readme.lower()


def test_transcript_commands_present():
    ui = (Path(__file__).resolve().parents[1] / 'ollama_code' / 'tui.py').read_text()
    assert "if prompt=='/save'" in ui
    assert "if prompt=='/health'" in ui
    assert "target.open('x'" in ui
