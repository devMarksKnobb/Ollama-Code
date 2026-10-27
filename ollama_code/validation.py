"""Dependency-free syntax checks and project test command discovery."""
import ast
import json
import shutil
import subprocess
from pathlib import Path

EXTENSIONS={'.py':'python','.js':'javascript','.cjs':'javascript','.mjs':'javascript','.jsx':'javascript','.ts':'typescript','.tsx':'typescript','.json':'json','.go':'go','.rs':'rust','.sh':'shell','.bash':'shell','.rb':'ruby','.php':'php'}

def check(path, content):
    """Return None on success, a diagnostic on failure, or an explicit skipped result."""
    path=Path(path); ext=path.suffix.lower()
    try:
        if ext=='.py': ast.parse(content,filename=str(path)); return None
        if ext=='.json': json.loads(content); return None
    except (SyntaxError,ValueError) as e:
        return f'{path}: {e}'
    # Only parse without executing project code. TypeScript and JSX need an external parser.
    parsers={'.js':['node','--check'],'.cjs':['node','--check'],'.mjs':['node','--check'],'.sh':['bash','-n'],'.bash':['bash','-n'],'.rb':['ruby','-c'],'.php':['php','-l']}
    cmd=parsers.get(ext)
    if cmd and shutil.which(cmd[0]):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp=Path(td)/('source'+ext);tmp.write_text(content,encoding='utf-8')
            try:
                p=subprocess.run(cmd+[str(tmp)],capture_output=True,text=True,timeout=12)
            except (OSError,subprocess.TimeoutExpired) as e:return f'{path}: parser failed: {e}'
            return None if p.returncode==0 else f'{path}: {(p.stderr or p.stdout)[:1200]}'
    return f'SKIPPED: no configured syntax parser for {path.name} ({EXTENSIONS.get(ext,"unknown language")})'

def detect_tests(root):
    root=Path(root)
    if (root/'pytest.ini').exists() or (root/'tests').is_dir() and any((root/'tests').glob('test_*.py')):return 'python -m pytest -q'
    if (root/'package.json').exists():
        try:
            scripts=json.loads((root/'package.json').read_text()).get('scripts',{})
            if 'test' in scripts and 'no test specified' not in scripts['test']:return 'npm test -- --runInBand' if 'jest' in scripts['test'] else 'npm test'
        except (OSError,ValueError,TypeError):pass
    if (root/'Cargo.toml').exists():return 'cargo test'
    if (root/'go.mod').exists():return 'go test ./...'
    return None
