from pathlib import Path

from ollama_code.app import Workspace


def test_approved_write_keeps_rollback_snapshot(tmp_path):
    target = tmp_path / "example.py"
    target.write_text("before = True\n", encoding="utf-8")
    ws = Workspace(tmp_path, approve=lambda _message: True)
    assert "Updated" in ws.write_file("example.py", "after = True\n")
    assert target.read_text(encoding="utf-8") == "after = True\n"
    assert "example.py" in ws.history()
    assert "Rolled back" in ws.rollback_last()
    assert target.read_text(encoding="utf-8") == "before = True\n"


def test_rollback_of_new_file_removes_it(tmp_path):
    ws = Workspace(tmp_path, approve=lambda _message: True)
    ws.write_file("created.txt", "hello\n")
    assert (tmp_path / "created.txt").exists()
    assert "Rolled back" in ws.rollback_last()
    assert not (tmp_path / "created.txt").exists()


def test_rejected_rollback_does_not_change_file(tmp_path):
    target = tmp_path / "example.txt"
    target.write_text("before\n", encoding="utf-8")
    ws = Workspace(tmp_path, approve=lambda _message: True)
    ws.write_file("example.txt", "after\n")
    ws.approve = lambda _message: False
    assert "rejected" in ws.rollback_last().lower()
    assert target.read_text(encoding="utf-8") == "after\n"
