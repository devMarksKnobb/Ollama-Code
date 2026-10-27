import os
from unittest.mock import patch
from ollama_code.app import Agent
from ollama_code.intelligence import ContextManager

class Workspace:
    root='.'

def test_long_context_defaults():
    with patch.dict(os.environ, {}, clear=True):
        agent=Agent(Workspace(),'model','http://localhost')
    assert agent.options['num_ctx']==32768
    assert agent.options['num_predict']==8192
    assert agent.auto_continue
    assert agent.max_steps==160

def test_context_compaction_keeps_system():
    messages=[{'role':'system','content':'instructions'}]+[{'role':'user','content':'a'*1000} for _ in range(10)]
    result=ContextManager(max_chars=3000).compact(messages)
    assert result[0]==messages[0]
    assert len(result)<len(messages)
