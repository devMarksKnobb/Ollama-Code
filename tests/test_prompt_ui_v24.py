from pathlib import Path


def test_prompt_is_multiline_and_enter_sends():
    src = (Path(__file__).parents[1] / "ollama_code" / "tui.py").read_text()
    assert "class PromptBox(TextArea)" in src
    assert "Binding(\"enter\", \"submit_prompt\", \"Send prompt\", priority=True)" in src
    assert "Binding(\"shift+enter\", \"insert_newline\", \"New line\", priority=True)" in src
    assert "Binding(\"ctrl+enter\", \"submit_prompt\", \"Send prompt\", priority=True)" in src
    assert "Paste multi-line text" in src
    assert "Enter send" in src
    assert "yield PromptBox('', id='prompt')" in src


def test_task_flow_and_clean_status_are_present():
    src = (Path(__file__).parents[1] / "ollama_code" / "tui.py").read_text()
    for stage in ("ANALYZING", "PLANNING", "IMPLEMENTING", "VALIDATING", "REVIEWING"):
        assert stage in src
    assert "MODE  {mode}    ·    STATE  {state}" in src
    assert "id='plan'" in src
