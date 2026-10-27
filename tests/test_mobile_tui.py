import pytest
pytest.importorskip("textual")
from ollama_code.tui import CodeUI

def test_mobile_shortcuts_and_layout():
    assert 'keyboard-open' in CodeUI.CSS
    assert 'Screen.narrow' in CodeUI.CSS
    assert 'ctrl+k' in [binding[0] for binding in CodeUI.BINDINGS]
    assert 'ctrl+r' in [binding[0] for binding in CodeUI.BINDINGS]

def test_stream_buffer():
    obj=CodeUI.__new__(CodeUI)
    obj.streaming=''
    obj._emit('a'*110000)
    assert len(obj.streaming)==100000
