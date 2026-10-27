from ollama_code.doctor import diagnose

def test_diagnostics_offline(tmp_path):
    report=diagnose('http://127.0.0.1:1',str(tmp_path))
    assert report['workspace_exists']
    assert report['ollama']['reachable'] is False
    assert 'git' in report['tools']
