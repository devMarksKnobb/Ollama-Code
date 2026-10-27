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


def test_ollama_brand_and_dotted_logo_are_present():
    from pathlib import Path
    from ollama_code import tui
    assert '⠿' in tui.DOT_LOGO
    assert 'OLLAMA CODE' in Path(tui.__file__).read_text(encoding='utf-8')


def test_terminal_clear_is_safe_without_tty(monkeypatch):
    import io
    from ollama_code import tui

    class NonTTY(io.StringIO):
        def isatty(self):
            return False

    monkeypatch.setattr(tui.sys, 'stdout', NonTTY())
    assert tui.clear_terminal_visible() is False


def test_terminal_clear_does_not_clear_scrollback(monkeypatch):
    from ollama_code import tui

    class FakeTTY:
        def isatty(self):
            return True
        def fileno(self):
            return 987
        def flush(self):
            pass

    writes = []
    monkeypatch.setattr(tui.sys, 'stdout', FakeTTY())
    monkeypatch.setenv('TERM', 'xterm-256color')
    monkeypatch.setattr(tui.os, 'write', lambda fd, data: writes.append((fd, data)))
    assert tui.clear_terminal_visible() is True
    assert writes == [(987, b'\x1b[2J\x1b[H')]
    assert b'3J' not in writes[0][1]

def test_idle_ui_hides_duplicate_status_and_file_toolbar():
    from ollama_code.tui import CodeUI
    assert 'Task finished. Full response is in the conversation above.' not in CodeUI.__dict__.get('CSS', '')
    assert 'Screen.task-running #live { display: block; }' in CodeUI.CSS
    assert '#actions { display: none;' in CodeUI.CSS
    assert "update('READY  ·  Task complete')" not in __import__('inspect').getsource(CodeUI._finish)
