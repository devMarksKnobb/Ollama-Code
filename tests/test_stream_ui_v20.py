from pathlib import Path

def test_dark_ui_has_separate_activity_and_stream():
    src = (Path(__file__).parents[1] / 'ollama_code' / 'tui.py').read_text()
    assert "id='activity'" in src
    assert 'self._stream_lock' in src
    assert 'version == self._shown_version' in src
    assert "'●' if i == self._activity_tick % 4" in src
    assert "#090909" in src
