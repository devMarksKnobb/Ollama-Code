from ollama_code.app import Agent

def test_fast_defaults(tmp_path):
    from ollama_code.app import Workspace
    agent=Agent(Workspace(str(tmp_path)), 'example', 'http://127.0.0.1:11434')
    assert agent.fast_mode in (True,False)
    assert agent.options['num_ctx'] > 0
    assert agent.last_metrics == {}
