import tempfile
import unittest
from pathlib import Path
from ollama_code.app import Workspace
from ollama_code.devtools import DeveloperTools

class TestDevTools(unittest.TestCase):
    def test_repo_map_and_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'main.py').write_text('def hello():\n    return 42\n')
            tools=DeveloperTools(Workspace(tmp,approve=lambda _:True))
            self.assertIn('FunctionDef hello@1',tools.repository_map())
            self.assertIn('2:     return 42',tools.read_lines('main.py',1,2))
            self.assertIn('main.py',tools.glob_files('**/*.py'))
            self.assertEqual('Python syntax valid',tools.validate_python('main.py'))
    def test_edit_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp,'x.py');p.write_text('x=1\n')
            tools=DeveloperTools(Workspace(tmp,approve=lambda _:True))
            with self.assertRaises(ValueError):tools.edit_lines('x.py',1,1,'x=2\n',expected='wrong')
            tools.edit_lines('x.py',1,1,'x=2\n',expected='x=1\n')
            self.assertEqual('x=2\n',p.read_text())

if __name__=='__main__':unittest.main()
