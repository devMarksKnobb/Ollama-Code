"""Deterministic repository retrieval, bounded context, and benchmark scoring."""
import hashlib
import json
import re
import sqlite3
from pathlib import Path

TOKEN = re.compile(r'[A-Za-z_][A-Za-z_0-9]{2,}')

class RepoIndex:
    def __init__(self, workspace, db=None):
        self.ws=workspace
        self.db=Path(db) if db else workspace.root/'.ollama-code-index.sqlite3'
        self.db.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.db) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS documents(path TEXT PRIMARY KEY, digest TEXT, body TEXT)')
            conn.execute('CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(path UNINDEXED, body)')
    def refresh(self):
        found=set(); changed=0
        with sqlite3.connect(self.db) as conn:
            for p in self.ws.files():
                if p.resolve()==self.db.resolve() or p.suffix in {'.sqlite3','.db'}:continue
                try:
                    raw=p.read_bytes()
                    if b'\0' in raw:continue
                    body=raw.decode('utf-8'); relative=p.relative_to(self.ws.root).as_posix()
                except (OSError,UnicodeError):continue
                found.add(relative); digest=hashlib.sha256(raw).hexdigest()
                old=conn.execute('SELECT digest FROM documents WHERE path=?',(relative,)).fetchone()
                if old and old[0]==digest:continue
                conn.execute('DELETE FROM search WHERE path=?',(relative,))
                conn.execute('INSERT INTO search(path,body) VALUES (?,?)',(relative,body))
                conn.execute('INSERT OR REPLACE INTO documents VALUES (?,?,?)',(relative,digest,body))
                changed+=1
            for (path,) in conn.execute('SELECT path FROM documents').fetchall():
                if path not in found:
                    conn.execute('DELETE FROM documents WHERE path=?',(path,))
                    conn.execute('DELETE FROM search WHERE path=?',(path,))
        return f'Indexed {len(found)} files; {changed} updated'
    def search(self, query, limit=8):
        words=TOKEN.findall(query)[:12]
        if not words:return 'No searchable terms'
        expression=' OR '.join('"'+w.replace('"','')+'"' for w in words)
        with sqlite3.connect(self.db) as conn:
            try:
                rows=conn.execute('SELECT path, snippet(search,1,"[", "]", " … ", 18), bm25(search) FROM search WHERE search MATCH ? ORDER BY bm25(search) LIMIT ?', (expression,min(int(limit),30))).fetchall()
            except sqlite3.OperationalError:return 'No matching indexed files'
        return '\n'.join(f'{p}: {snippet[:500]}' for p,snippet,_ in rows) or 'No matching indexed files'

class ContextManager:
    def __init__(self, max_chars=240000):self.max_chars=max_chars
    def compact(self, messages):
        if len(messages)<3:return messages
        size=sum(len(json.dumps(m)) for m in messages)
        if size<=self.max_chars:return messages
        system=messages[0]; rest=messages[1:]; keep=[]; used=len(json.dumps(system))
        # Keep complete tool cycles: never start retained history with a tool result.
        for m in reversed(rest):
            length=len(json.dumps(m))
            if used+length>self.max_chars and keep:break
            keep.insert(0,m);used+=length
        while keep and keep[0].get('role')=='tool':keep.pop(0)
        return [system,{'role':'system','content':'Earlier conversation was compacted. Reinspect repository files before editing; do not assume old tool outputs are current.'}]+keep

def score_benchmark(cases):
    """Score independently recorded coding tasks; does not fabricate agent runs."""
    if not cases:raise ValueError('Benchmark requires at least one case')
    results=[]
    for case in cases:
        required={'id','test_exit_code','expected_files','changed_files'}
        if not required.issubset(case):raise ValueError(f'Missing benchmark fields: {required-set(case)}')
        expected=set(case['expected_files']); changed=set(case['changed_files'])
        results.append({'id':case['id'],'passed':case['test_exit_code']==0 and expected.issubset(changed),'test_exit_code':case['test_exit_code']})
    return {'passed':sum(x['passed'] for x in results),'total':len(results),'cases':results}
