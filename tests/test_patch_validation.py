import hashlib
from ollama_code.app import Workspace

def test_syntax_rejection(tmp_path):
    ws=Workspace(tmp_path, approve=lambda _: True)
    assert 'VALIDATION FAILED' in ws.apply_patch([{'path':'bad.py','content':'def broken('}])
    assert not (tmp_path/'bad.py').exists()

def test_stale_hash(tmp_path):
    p=tmp_path/'a.py'; p.write_text('x=1\n')
    ws=Workspace(tmp_path, approve=lambda _: True)
    try:
        ws.apply_patch([{'path':'a.py','content':'x=2\n','expected_sha256':'0'*64}])
    except ValueError as e: assert 'conflict' in str(e).lower()
    else: assert False
    assert p.read_text()=='x=1\n'

def test_concurrent_edit_at_approval(tmp_path):
    p=tmp_path/'a.py';p.write_text('x=1\n')
    def approve(_):
        p.write_text('x=3\n');return True
    ws=Workspace(tmp_path,approve=approve)
    assert 'CONFLICT' in ws.apply_patch([{'path':'a.py','content':'x=2\n'}])
    assert p.read_text()=='x=3\n'

def test_multiple_files(tmp_path):
    ws=Workspace(tmp_path,approve=lambda _: True)
    result=ws.apply_patch([{'path':'a.py','content':'x=1\n','expected_sha256':None},{'path':'b.py','content':'y=2\n'}])
    assert 'Applied 2 files' in result
    assert ws.file_fingerprint('a.py')==hashlib.sha256(b'x=1\n').hexdigest()

def test_rollback_on_failed_tests(tmp_path):
    p=tmp_path/'a.py';p.write_text('x=1\n')
    ws=Workspace(tmp_path,approve=lambda _: True)
    ws.run_command=lambda command:'exit=1: failed'
    result=ws.apply_patch([{'path':'a.py','content':'x=2\n'}],test_command='pytest')
    assert 'rolled back' in result
    assert p.read_text()=='x=1\n'
