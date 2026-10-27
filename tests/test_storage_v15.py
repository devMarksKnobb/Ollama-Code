import pytest
from ollama_code.app import Workspace

def test_create_no_overwrite(tmp_path):
    w=Workspace(tmp_path,approve=lambda _:True)
    w.create_file('a.txt','hello')
    assert (tmp_path/'a.txt').read_text()=='hello'
    with pytest.raises(FileExistsError):w.create_file('a.txt','new')

def test_storage_roundtrip(tmp_path):
    w=Workspace(tmp_path/'project',approve=lambda _:True)
    w.root.mkdir()
    ext=tmp_path/'external.txt';ext.write_text('content')
    w.storage_import(str(ext),'sub/file.txt')
    out=tmp_path/'out.txt'
    w.storage_export('sub/file.txt',str(out))
    assert out.read_text()=='content'

def test_storage_reject(tmp_path):
    w=Workspace(tmp_path/'project',approve=lambda _:False);w.root.mkdir()
    ext=tmp_path/'external.txt';ext.write_text('content')
    assert w.storage_import(str(ext),'file.txt')=='Import rejected'
    assert not (w.root/'file.txt').exists()
