from ollama_code.validation import check,detect_tests

def test_python_and_json():
    assert check('x.py','def f():\n return 1\n') is None
    assert 'x.py' in check('x.py','def (')
    assert check('a.json','{"ok":true}') is None
    assert 'a.json' in check('a.json','{bad')

def test_js_if_node_present():
    import shutil
    if shutil.which('node'):
        assert check('a.js','const x = 1;') is None
        assert check('a.js','const = ;')

def test_detection(tmp_path):
    assert detect_tests(tmp_path) is None
    (tmp_path/'go.mod').write_text('module example.com/test')
    assert detect_tests(tmp_path)=='go test ./...'
