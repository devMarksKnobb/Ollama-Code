from pathlib import Path
from unittest.mock import patch
from ollama_code.app import Workspace, Agent

def test_multifile_patch(tmp_path):
    ws=Workspace(tmp_path,approve=lambda _:True)
    result=ws.apply_patch([{'path':'src/a.py','content':'print(1)\n'},{'path':'src/b.py','content':'print(2)\n'}])
    assert '2 file' in result
    assert (tmp_path/'src/a.py').read_text()=='print(1)\n'
    assert (tmp_path/'src/b.py').read_text()=='print(2)\n'

def test_patch_rejected(tmp_path):
    ws=Workspace(tmp_path,approve=lambda _:False)
    assert 'rejected' in ws.apply_patch([{'path':'x','content':'hello'}])
    assert not (tmp_path/'x').exists()

def test_escape_blocked(tmp_path):
    ws=Workspace(tmp_path)
    try:ws.path('../outside')
    except ValueError:pass
    else:raise AssertionError('workspace escape allowed')

def test_streaming_tool_call(tmp_path):
    import io,json
    ws=Workspace(tmp_path)
    agent=Agent(ws,'test','http://localhost:11434',max_steps=2)
    chunks=[{'message':{'tool_calls':[{'function':{'name':'list_files','arguments':{}}}]}}, {'done':True}]
    response=io.BytesIO(('\n'.join(json.dumps(x) for x in chunks)+'\n').encode())
    class Context:
        def __enter__(self):return response
        def __exit__(self,*args):pass
    with patch('urllib.request.urlopen',return_value=Context()):
        agent.ask('list files',emit=lambda _:None)
    assert any(x['role']=='tool' for x in agent.history)
