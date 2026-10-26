import threading, hashlib, ipaddress, socket, time, argparse, difflib, json, os, re, shlex, subprocess, sys, urllib.request, urllib.error, urllib.parse, html, tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax

C=Console()
SKIP={'.ollama-code','.git','node_modules','.venv','venv','__pycache__','dist','build','.next'}
SYSTEM='''You are Ollama Code, a careful autonomous software engineering assistant. Use tools to inspect the actual project before changing code. Make minimal, coherent fixes. After editing, run relevant tests where possible. Never claim unverified success. Never access files outside the workspace. Prefer repository_map, glob_files, read_lines, and search_files before edits. Use precise targeted edits, inspect diffs, and validate tests before reporting completion. Tools may require user approval. Keep final response concise with files changed and tests executed.'''

def request(url, payload=None, timeout=120):
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        detail=e.read().decode(errors='replace')[:500]
        raise RuntimeError(f'Ollama HTTP {e.code}: {detail}') from e
    except urllib.error.URLError as e:raise RuntimeError(f'Cannot connect to Ollama: {e.reason}. Start `ollama serve`.') from e

class Workspace:
    def __init__(self,root,approve=None):
        self.root=Path(root).expanduser().resolve()
        from .settings import Settings, ApprovalPolicy
        self.settings=Settings(self.root)
        self.policy=ApprovalPolicy(self.settings)
        self.approve=approve or (lambda message: self.policy.decide(message,lambda: Confirm.ask(message,default=False)))
        self.audit_path=self.root/'.ollama-code-audit.jsonl'
    def path(self,p):
        target=(self.root/p).resolve()
        if not target.is_relative_to(self.root):raise ValueError('Path is outside workspace')
        if any(part in SKIP for part in target.relative_to(self.root).parts):raise ValueError('Protected/ignored directory')
        if target.name in {'.env','.env.local','id_rsa','id_ed25519'} or target.name.startswith('.env.') or target==self.audit_path:raise ValueError('Sensitive file is protected')
        return target
    def audit(self,action,detail):
        record={'time':time.time(),'action':action,'detail':str(detail)[:500]}
        try:
            with self.audit_path.open('a',encoding='utf-8') as log:log.write(json.dumps(record)+'\n')
        except OSError:pass
    def files(self):
        count=0
        for base,dirs,files in os.walk(self.root):
            dirs[:]=[d for d in dirs if d not in SKIP and not (Path(base)/d).is_symlink()]
            for name in files:
                p=Path(base)/name
                if p.is_symlink() or p.name.startswith('.env') or p.name in {'id_rsa','id_ed25519','.ollama-code-audit.jsonl','.ollama-code-index.sqlite3','.ollama-code-index.sqlite3-wal','.ollama-code-index.sqlite3-shm'} or p.stat().st_size>1_000_000:continue
                yield p
                count+=1
                if count>=10000:return
    def list_files(self):return '\n'.join(str(p.relative_to(self.root)) for p in self.files())[:16000]
    def search_files(self,query):
        if not query:raise ValueError('Empty search query')
        out=[]
        for p in self.files():
            try:
                for n,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
                    if query.lower() in line.lower():out.append(f'{p.relative_to(self.root)}:{n}: {line[:200]}')
                    if len(out)>=100:return '\n'.join(out)
            except (UnicodeError,OSError):pass
        return '\n'.join(out) or 'No matches'
    def read_file(self,path):
        p=self.path(path)
        if p.stat().st_size>200_000:raise ValueError('File too large for read_file')
        return p.read_text(encoding='utf-8')
    def write_file(self,path,content):
        p=self.path(path)
        if len(content)>500_000:raise ValueError('Content too large')
        before=p.read_text(encoding='utf-8') if p.exists() else ''
        diff=''.join(difflib.unified_diff(before.splitlines(True),content.splitlines(True),fromfile=f'a/{path}',tofile=f'b/{path}'))
        if not hasattr(self,'preview'): C.print(Panel(Syntax(diff[:18000] or '(no changes)','diff',theme='monokai'),title=f'Proposed change: {path}',border_style='yellow'))
        else: self.preview(path,diff)
        if not self.approve('Apply this file change?'):return 'User rejected change'
        p.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=p.parent,delete=False) as f:
            f.write(content);tmp=Path(f.name)
        try:tmp.replace(p)
        finally:tmp.unlink(missing_ok=True)
        self.audit('write_file',path)
        return f'Updated {path} ({len(content)} characters)'
    def apply_patch(self, changes, test_command=None):
        """Optimistic concurrency checks, syntax gates and rollback on failed validation.

        Each change may include expected_sha256 (SHA256 of current UTF-8 bytes).
        A null expected_sha256 explicitly asserts that the file does not exist.
        """
        from .validation import check, detect_tests
        if not isinstance(changes, list) or not 1 <= len(changes) <= 30:
            raise ValueError('Provide 1–30 file changes')
        prepared, seen, warnings = [], set(), []
        for item in changes:
            if not isinstance(item, dict) or not {'path','content'} <= item.keys():
                raise ValueError('Each change needs path and content')
            path, content = item['path'], item['content']
            if not isinstance(path, str) or not isinstance(content, str) or len(content.encode('utf-8')) > 500_000:
                raise ValueError('Invalid patch path or content')
            target = self.path(path)
            if target in seen: raise ValueError('Duplicate path in patch')
            seen.add(target)
            if target.is_symlink() or (target.exists() and (not target.is_file() or target.stat().st_size > 500_000)):
                raise ValueError('Unsupported file type or size')
            before = target.read_bytes() if target.exists() else None
            digest = hashlib.sha256(before).hexdigest() if before is not None else None
            if 'expected_sha256' in item and item['expected_sha256'] != digest:
                raise ValueError(f'Patch conflict: {path} changed since it was read')
            diagnostic=check(path,content)
            if diagnostic and not diagnostic.startswith('SKIPPED:'):
                return f'VALIDATION FAILED: {diagnostic}; no files changed'
            if diagnostic and diagnostic.startswith('SKIPPED:'):
                warnings.append(diagnostic)
            original = before.decode('utf-8') if before is not None else ''
            diff = ''.join(difflib.unified_diff(original.splitlines(True), content.splitlines(True), fromfile='a/'+path,tofile='b/'+path))
            prepared.append((target, before, digest, content, diff))
        for target, before, digest, content, diff in prepared:
            name = str(target.relative_to(self.root))
            if hasattr(self,'preview'): self.preview(name, diff)
            else: C.print(Panel(Syntax(diff[:16000] or '(unchanged)', 'diff', theme='monokai'),title=name,border_style='yellow'))
        if not self.approve(f'Apply {len(prepared)} validated file changes?'): return 'User rejected patch'
        # Detect edits made while the user was reviewing the proposed diff.
        for target, before, digest, content, diff in prepared:
            actual = target.read_bytes() if target.exists() else None
            if actual != before: return f'PATCH CONFLICT: {target.relative_to(self.root)} changed during approval; no files changed'
        written = []
        try:
            for target, before, digest, content, diff in prepared:
                target.parent.mkdir(parents=True,exist_ok=True)
                with tempfile.NamedTemporaryFile('wb',dir=target.parent,delete=False) as f:
                    f.write(content.encode('utf-8')); temp=Path(f.name)
                try: temp.replace(target)
                finally: temp.unlink(missing_ok=True)
                written.append((target,before))
            # Post-write validation and tests are mandatory; fail closed when unavailable.
            for target, before, digest, content, diff in prepared:
                diagnostic=check(str(target.relative_to(self.root)),target.read_text(encoding='utf-8'))
                if diagnostic and not diagnostic.startswith('SKIPPED:'):
                    raise RuntimeError('Post-write syntax failure: '+diagnostic)
            command=test_command or detect_tests(self.root)
            if command:
                result=self.run_command(command)
                if not re.search(r'(?:^|\s)exit=0(?:\s|$)|exit code: 0',result,re.I):
                    raise RuntimeError('Post-patch tests failed or could not run: '+result[:1500])
            else:
                warnings.append('No project test command detected; tests NOT RUN')
        except Exception as exc:
            for target, before in reversed(written):
                if before is None: target.unlink(missing_ok=True)
                else:
                    with tempfile.NamedTemporaryFile('wb',dir=target.parent,delete=False) as f:
                        f.write(before); temp=Path(f.name)
                    temp.replace(target)
            self.audit('patch_rollback',str(exc))
            return f'VALIDATION FAILED; all changes rolled back: {exc}'
        self.audit('apply_patch',[str(x[0].relative_to(self.root)) for x in prepared])
        return f'Applied {len(prepared)} files; syntax checks completed; '+('tests passed' if command else 'tests not run')+('; WARNINGS: '+' | '.join(warnings) if warnings else '')

    def file_fingerprint(self,path):
        """Read SHA256 before proposing a conflict-aware patch."""
        target=self.path(path)
        if not target.exists(): return 'NOT_FOUND (use expected_sha256: null)'
        if not target.is_file(): raise ValueError('Not a regular file')
        return hashlib.sha256(target.read_bytes()).hexdigest()

    def web_search(self,query):
        """Retrieve links/snippets from DuckDuckGo's HTML endpoint, no arbitrary URL fetch."""
        if not query.strip():raise ValueError('Query required')
        url='https://html.duckduckgo.com/html/?'+urllib.parse.urlencode({'q':query[:250]})
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 OllamaCode/5.0'})
        with urllib.request.urlopen(req,timeout=12) as response:
            page=response.read(300000).decode('utf-8','replace')
        from html.parser import HTMLParser
        class Results(HTMLParser):
            def __init__(self):super().__init__();self.active=False;self.items=[];self.url='';self.parts=[]
            def handle_starttag(self,tag,attrs):
                d=dict(attrs)
                if tag=='a' and 'result__a' in d.get('class',''):
                    self.active=True;self.url=d.get('href','');self.parts=[]
            def handle_data(self,data):
                if self.active:self.parts.append(data)
            def handle_endtag(self,tag):
                if tag=='a' and self.active:
                    title=' '.join(self.parts).strip()
                    if title:self.items.append(f'{title} — {self.url}')
                    self.active=False
        parser=Results();parser.feed(page)
        self.audit('web_search',query)
        return '\n'.join(parser.items[:8])[:10000] or 'No search results (search provider may be unavailable)'
    def glob_files(self,pattern='**/*.py',limit=200):
        from .devtools import DeveloperTools
        return DeveloperTools(self).glob_files(pattern,limit)
    def read_lines(self,path,start=1,end=160):
        from .devtools import DeveloperTools
        return DeveloperTools(self).read_lines(path,start,end)
    def repository_map(self,limit=180):
        from .devtools import DeveloperTools
        return DeveloperTools(self).repository_map(limit)
    def git_status(self):
        from .devtools import DeveloperTools
        return DeveloperTools(self).git_status()
    def git_diff(self):
        from .devtools import DeveloperTools
        return DeveloperTools(self).git_diff()
    def edit_lines(self,path,start,end,replacement,expected=None):
        from .devtools import DeveloperTools
        return DeveloperTools(self).edit_lines(path,start,end,replacement,expected)
    def validate_python(self,path):
        from .devtools import DeveloperTools
        return DeveloperTools(self).validate_python(path)
    def index_repository(self):
        from .intelligence import RepoIndex
        return RepoIndex(self).refresh()
    def semantic_search(self,query):
        from .intelligence import RepoIndex
        index=RepoIndex(self)
        index.refresh()
        return index.search(query)
    def test_and_repair(self,command,goal,max_attempts=2):
        """Run sandboxed tests; return failures to agent for a follow-up edit cycle."""
        if max_attempts<1 or max_attempts>3:raise ValueError('max_attempts must be 1–3')
        result=self.run_command(command)
        return ('TEST RESULTS for '+goal+'\n'+result+'\nIf tests failed, inspect the output, patch relevant files, and rerun the tests. '
                'Do not claim success without exit=0. Maximum suggested retries: '+str(max_attempts))
    def replace_text(self,path,old,new):
        if not old:raise ValueError('old must not be empty')
        current=self.read_file(path)
        n=current.count(old)
        if n!=1:return f'Replacement not applied: expected exactly one match, found {n}'
        return self.write_file(path,current.replace(old,new,1))
    def run_command(self,command):
        from .sandbox import ContainerSandbox
        args=shlex.split(command)
        allowed={'python','python3','pytest','ruff','mypy','node','npm','npx','cargo','go','git'}
        if not args or args[0] not in allowed:return 'Command blocked: executable not allowlisted'
        if args[0]=='git' and (len(args)<2 or args[1] not in {'status','diff','log','show'}):return 'Command blocked: git subcommand'
        sandbox=ContainerSandbox(self.root)
        try: argv=sandbox.command(command)
        except Exception as e: return f'Sandbox unavailable: {e}'
        if hasattr(self,'preview'): self.preview('Isolated command',command+'\n\nContainer: '+sandbox.image+'\nNetwork: disabled; workspace: read-only host mount')
        else: C.print(Panel(command+'\n[dim]Isolated container, no network, host workspace read-only[/dim]',title='Command approval',border_style='yellow'))
        if not self.approve('Run in isolated container?'):return 'User rejected command'
        self.audit('sandbox_command',command)
        try:return sandbox.run(command)
        except Exception as e:return f'Container execution failed: {type(e).__name__}: {e}'

SCHEMAS={
'glob_files':('Find files by glob pattern',{'pattern':'Glob pattern, e.g. **/*.py'}),
'read_lines':('Read file with line numbers and a bounded range',{'path':'Relative file path','start':'First line number','end':'Last line number'}),
'repository_map':('Show repository structure and Python top-level symbols',{}),
'git_status':('Show Git working tree status',{}),
'git_diff':('Show unstaged Git diff',{}),
'edit_lines':('Apply an exact line-range edit after approval',{'path':'Relative file path','start':'First line number','end':'Last line number','replacement':'New text'}),
'validate_python':('Parse a Python file to detect syntax errors',{'path':'Relative file path'}),
'list_files':('List workspace files',{}),
'index_repository':('Incrementally index repository files for ranked full-text retrieval',{}),
'semantic_search':('Rank repository matches by lexical relevance',{'query':'Coding task or search terms'}),
'test_and_repair':('Execute isolated tests and return failure diagnostics for an agent repair iteration',{'command':'Test command','goal':'What should be verified'}),
'search_files':('Search text in workspace files',{'query':'Search string'}),
'read_file':('Read a UTF-8 workspace file',{'path':'Relative file path'}),
'write_file':('Propose full file contents for review and approval',{'path':'Relative file path','content':'Complete UTF-8 file content'}),
'replace_text':('Propose a single exact replacement in a file',{'path':'Relative file path','old':'Existing exact text','new':'Replacement text'}),
'run_command':('Run a command in a network-disabled, isolated Docker/Podman container after approval',{'command':'Executable and arguments'}),
'web_search':('Search public web pages for documentation; requires internet',{'query':'Search query'}),
'file_fingerprint':('Get file SHA256 for optimistic patch conflict detection',{'path':'Relative file path'}),
'apply_patch':('Propose multi-file patch; automatic syntax checks and isolated project tests when detected',{'changes':'Array of {path, content, optional expected_sha256}','test_command':'Optional isolated validation command'})}
TOOLS=[{'type':'function','function':{'name':name,'description':description,'parameters':{'type':'object','properties':{key:{'type':'array','items':{'type':'object','properties':{'path':{'type':'string'},'content':{'type':'string'},'expected_sha256':{'type':['string','null']}},'required':['path','content']}} if key=='changes' else {'type':'integer','description':desc} if key in {'start','end','limit'} else {'type':'string','description':desc} for key,desc in params.items()},'required':[k for k in params if k != 'test_command']}}} for name,(description,params) in SCHEMAS.items()]

class Agent:
    def __init__(self,workspace,model,host,max_steps=80):
        self.ws=workspace;self.model=model;self.host=host.rstrip('/');self.max_steps=max_steps
        self.history=[{'role':'system','content':SYSTEM+f'\nWorkspace: {workspace.root}'}]
        self.cancel=threading.Event()
        self.max_history=160
        from .continuity import SessionStore
        self.session=SessionStore(workspace.root)
        self.options={'temperature':0.1,'num_ctx':int(os.getenv('OLLAMA_CODE_CONTEXT','32768')),'num_predict':int(os.getenv('OLLAMA_CODE_PREDICT','4096'))}
        self.progress={'goal':'','steps':0,'status':'idle'}
    def models(self):return [m.get('name') or m.get('model') for m in request(self.host+'/api/tags').get('models',[])]
    def ask(self,prompt,emit=None):
        self.history.append({'role':'user','content':prompt})
        self.progress={'goal':prompt,'steps':0,'status':'working'}
        self.session.save(self.history,self.progress)
        if len(self.history)>self.max_history:self.history=[self.history[0]]+self.history[-(self.max_history-1):]
        self.cancel.clear()
        from .intelligence import ContextManager
        self.history=ContextManager().compact(self.history)
        for step in range(self.max_steps):
            self.progress['steps']=step+1
            self.session.save(self.history,self.progress)
            if self.cancel.is_set(): return
            self.history=ContextManager().compact(self.history)
            payload={'model':self.model,'messages':self.history,'tools':TOOLS,'stream':True,'options':self.options}
            req=urllib.request.Request(self.host+'/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            msg={'role':'assistant','content':''}
            with urllib.request.urlopen(req,timeout=600) as response:
                for line in response:
                    if not line.strip():continue
                    if self.cancel.is_set(): return
                    chunk=json.loads(line)
                    if chunk.get('error'): raise RuntimeError(str(chunk['error']))
                    delta=chunk.get('message',{})
                    piece=delta.get('content','')
                    if piece:
                        msg['content']+=piece
                        if emit:emit(piece)
                    if delta.get('tool_calls'):
                        calls=msg.setdefault('tool_calls',[])
                        for idx,call in enumerate(delta['tool_calls']):
                            while len(calls)<=idx: calls.append({'function':{'name':'','arguments':{}}})
                            fn=call.get('function',{})
                            if fn.get('name'): calls[idx]['function']['name']=fn['name']
                            if 'arguments' in fn:
                                old=calls[idx]['function'].get('arguments',{})
                                new=fn['arguments']
                                calls[idx]['function']['arguments']=(old+new if isinstance(old,str) and isinstance(new,str) else new)
            if emit:emit('\n')
            self.history.append(msg)
            if msg.get('content') and not emit:C.print(Panel(Markdown(msg['content']),title='Ollama Code',border_style='cyan'))
            calls=msg.get('tool_calls') or []
            if not calls:
                self.progress['status']='completed'
                self.session.save(self.history,self.progress)
                return
            for call in calls:
                fn=call.get('function',{});name=fn.get('name','');args=fn.get('arguments',{})
                if isinstance(args,str):
                    try:args=json.loads(args)
                    except json.JSONDecodeError:args={}
                if emit:emit(f'\n⚙ {name}\n')
                else:C.print(f'[bold cyan]⚙ {name}[/bold cyan] [dim]{str(args)[:180]}[/dim]')
                try:
                    if self.cancel.is_set(): return
                    if name not in SCHEMAS:out='Unknown tool'
                    else:
                        if not isinstance(args,dict):raise ValueError('Tool arguments must be an object')
                        unexpected=set(args)-set(SCHEMAS[name][1])
                        if unexpected:raise ValueError(f'Unexpected tool arguments: {sorted(unexpected)}')
                        out=str(getattr(self.ws,name)(**args))
                except Exception as e:out=f'Tool error: {type(e).__name__}: {e}'
                if emit:emit(out[:3000]+'\n')
                else:C.print(Panel(out[:5000],border_style='dim'))
                self.history.append({'role':'tool','tool_name':name,'content':out[:14000]})
                self.session.save(self.history,self.progress)
        self.progress['status']='paused at step budget'
        self.session.save(self.history,self.progress)
        if emit:emit('Paused at step budget. Use /continue to resume with saved context.\n')
        else:C.print('[yellow]Paused at step budget. Use /continue to resume.[/yellow]')

def main():
    parser=argparse.ArgumentParser(description='Ollama Code — open-source terminal coding agent')
    parser.add_argument('--workspace',default='.');parser.add_argument('--model',default=os.getenv('OLLAMA_CODE_MODEL','qwen2.5-coder:1.5b'))
    parser.add_argument('--host',default=os.getenv('OLLAMA_HOST','http://127.0.0.1:11434'))
    parser.add_argument('--context',type=int,default=None,help='Ollama context tokens (model and RAM dependent)');parser.add_argument('--max-steps',type=int,default=80)
    parser.add_argument('--approval',choices=['ask','edits','all'],default=None,help='ask=all actions; edits=auto approve edits; all=auto approve edits and isolated commands')
    parser.add_argument('--cli',action='store_true',help='Classic terminal with interactive file approvals')
    args=parser.parse_args()
    if not args.cli:
        from .tui import run
        return run(args.workspace,args.model,args.host,args.approval)
    ws=Workspace(args.workspace)
    if args.approval: ws.settings.set('approval',args.approval)
    agent=Agent(ws,args.model,args.host,max_steps=args.max_steps)
    if args.context:agent.options['num_ctx']=args.context
    C.print(Panel('[bold #f9d65c] O L L A M A   C O D E [/bold #f9d65c]\n[cyan]Local-first coding agent[/cyan]\n[dim]Read · Search · Edit · Test · Review[/dim]',border_style='magenta'))
    C.print(f'[dim]Workspace[/dim] {ws.root}  [dim]Model[/dim] {agent.model}')
    C.print('[dim]/help · /models · /model NAME · /files · /search TEXT · /clear · /exit[/dim]')
    while True:
        try:prompt=Prompt.ask('[bold #f9d65c]❯[/bold #f9d65c]').strip()
        except (EOFError,KeyboardInterrupt):C.print('\n[dim]Goodbye[/dim]');break
        if not prompt:continue
        if prompt in ('/exit','/quit'):break
        if prompt=='/help':C.print('Coding agent commands: /settings /approval ask|edits|all /vscode /models /model NAME /files /search TEXT /clear /resume /continue /exit');continue
        if prompt=='/settings':C.print(ws.settings.values);continue
        if prompt.startswith('/approval '):
            try:ws.settings.set('approval',prompt.split(' ',1)[1]);C.print(ws.settings.values)
            except ValueError as e:C.print(str(e))
            continue
        if prompt=='/vscode':
            from .vscode import install_workspace_config
            C.print(install_workspace_config(ws.root,ws.approve));continue
        if prompt=='/resume':
            loaded=agent.session.load()
            if loaded:agent.history,agent.progress=loaded;C.print('[green]Session restored[/green]')
            else:C.print('[yellow]No saved session[/yellow]')
            continue
        if prompt=='/continue':prompt='Continue the unfinished coding task. Inspect current files and tests, finish remaining steps, verify results. Do not restart completed work.'
        if prompt=='/status':C.print(agent.progress);continue
        if prompt=='/clear':agent.history=agent.history[:1];C.print('[green]Conversation cleared[/green]');continue
        if prompt=='/files':C.print(ws.list_files());continue
        if prompt.startswith('/search '):C.print(ws.search_files(prompt[8:]));continue
        if prompt=='/models':
            try:C.print('\n'.join(agent.models()) or 'No models installed')
            except Exception as e:C.print(f'[red]{e}[/red]')
            continue
        if prompt.startswith('/model '):agent.model=prompt[7:].strip();C.print(f'Model: {agent.model}');continue
        try:agent.ask(prompt)
        except KeyboardInterrupt:C.print('[yellow]Interrupted[/yellow]')
        except Exception as e:C.print(Panel(str(e),title='Agent error',border_style='red'))
if __name__=='__main__':main()
