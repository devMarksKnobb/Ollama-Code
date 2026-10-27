from ollama_code.continuity import SessionStore
from ollama_code.app import Agent, Workspace

def test_session_roundtrip(tmp_path):
    store=SessionStore(tmp_path)
    assert store.load() is None
    store.save([{'role':'user','content':'hello'}],{'status':'working'})
    history, progress=store.load()
    assert history[0]['content']=='hello'
    assert progress['status']=='working'

def test_agent_long_context(tmp_path, monkeypatch):
    monkeypatch.setenv('OLLAMA_CODE_CONTEXT','65536')
    agent=Agent(Workspace(tmp_path), 'test','http://127.0.0.1:11434')
    assert agent.options['num_ctx']==65536
    assert agent.max_steps==160
