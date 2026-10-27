import tempfile
import unittest
from pathlib import Path
from ollama_code.app import Workspace
from ollama_code.intelligence import RepoIndex, ContextManager, score_benchmark

class IntelligenceTests(unittest.TestCase):
    def test_index_updates_and_deletes(self):
        with tempfile.TemporaryDirectory() as root:
            ws=Workspace(root)
            p=Path(root)/'alpha.py';p.write_text('def spectacular_function(): pass')
            index=RepoIndex(ws)
            self.assertIn('1 updated',index.refresh())
            self.assertIn('alpha.py',index.search('spectacular_function'))
            p.write_text('def another_function(): pass')
            index.refresh()
            self.assertEqual(index.search('spectacular_function'),'No matching indexed files')
            p.unlink();index.refresh()
            self.assertEqual(index.search('another_function'),'No matching indexed files')
    def test_compact_preserves_system_and_recent(self):
        messages=[{'role':'system','content':'instructions'}]+[{'role':'user','content':'x'*1000} for _ in range(20)]
        result=ContextManager(4000).compact(messages)
        self.assertEqual(result[0],messages[0]);self.assertLess(len(result),len(messages))
    def test_benchmark(self):
        outcome=score_benchmark([{'id':'one','test_exit_code':0,'expected_files':['a'],'changed_files':['a','b']}, {'id':'two','test_exit_code':1,'expected_files':['c'],'changed_files':['c']}])
        self.assertEqual(outcome['passed'],1)
if __name__=='__main__':unittest.main()
