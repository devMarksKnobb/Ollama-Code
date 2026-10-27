import tempfile,unittest
from pathlib import Path
from ollama_code.app import Workspace
class WorkspaceTests(unittest.TestCase):
 def test_search_and_confinement(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'hello.py').write_text('print("hello")')
   w=Workspace(d)
   self.assertIn('hello.py',w.list_files())
   self.assertIn('hello.py:1',w.search_files('hello'))
   with self.assertRaises(ValueError):w.path('../outside')
 def test_replace_requires_unique_match(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'a.txt').write_text('x x')
   self.assertIn('found 2',Workspace(d).replace_text('a.txt','x','y'))
if __name__=='__main__':unittest.main()
