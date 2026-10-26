"""Repository exploration and precise edits for Ollama Code."""
import ast
import difflib
import fnmatch
import json
import re
import subprocess
from pathlib import Path

class DeveloperTools:
    def __init__(self, workspace):
        self.ws = workspace

    def glob_files(self, pattern='**/*.py', limit=200):
        limit=max(1,min(int(limit),500))
        matches=[]
        for path in self.ws.files():
            rel=path.relative_to(self.ws.root).as_posix()
            if fnmatch.fnmatch(rel,pattern) or (pattern.startswith('**/') and fnmatch.fnmatch(rel,pattern[3:])):
                matches.append(rel)
                if len(matches)>=limit:break
        return '\n'.join(matches) or 'No matching files'

    def read_lines(self,path,start=1,end=160):
        p=self.ws.path(path)
        if not p.is_file() or p.stat().st_size>1_000_000:raise ValueError('File missing or too large')
        start,end=int(start),int(end)
        if start<1 or end<start or end-start>400:raise ValueError('Invalid line range (max 401 lines)')
        lines=p.read_text(encoding='utf-8').splitlines()
        return '\n'.join(f'{i}: {lines[i-1]}' for i in range(start,min(end,len(lines))+1)) or '(empty range)'

    def repository_map(self,limit=180):
        limit=max(1,min(int(limit),500))
        out=[]
        for p in self.ws.files():
            rel=p.relative_to(self.ws.root).as_posix()
            if p.suffix=='.py':
                try:
                    tree=ast.parse(p.read_text(encoding='utf-8'))
                    symbols=[f'{type(n).__name__} {n.name}@{n.lineno}' for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
                    out.append(f'{rel}: '+', '.join(symbols[:25]))
                except (SyntaxError,UnicodeError,OSError):out.append(rel+' (unparsed)')
            elif p.name in {'package.json','Cargo.toml','go.mod','pyproject.toml','README.md'}:out.append(rel)
            if len(out)>=limit:break
        return '\n'.join(out)[:20000] or 'No source files found'

    def git_status(self):
        p=subprocess.run(['git','-C',str(self.ws.root),'status','--short','--untracked-files=normal'],capture_output=True,text=True,timeout=10)
        return (p.stdout or p.stderr or 'Clean working tree')[:12000]

    def git_diff(self):
        p=subprocess.run(['git','-C',str(self.ws.root),'diff','--no-ext-diff','--'],capture_output=True,text=True,timeout=10)
        return (p.stdout or p.stderr or 'No unstaged changes')[:20000]

    def edit_lines(self,path,start,end,replacement,expected=None):
        """Line-scoped edit, guarded by optional expected original text."""
        current=self.ws.read_file(path)
        lines=current.splitlines(keepends=True)
        start,end=int(start),int(end)
        if start<1 or end<start-1 or end>len(lines):raise ValueError('Invalid edit range')
        original=''.join(lines[start-1:end])
        if expected is not None and original!=expected:raise ValueError('Edit conflict: file content changed')
        updated=''.join(lines[:start-1])+replacement+''.join(lines[end:])
        return self.ws.write_file(path,updated)

    def validate_python(self,path):
        p=self.ws.path(path)
        if p.suffix!='.py':raise ValueError('Python files only')
        try:ast.parse(self.ws.read_file(path),filename=str(p))
        except SyntaxError as e:return f'Syntax error at line {e.lineno}: {e.msg}'
        return 'Python syntax valid'
