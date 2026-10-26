"""Crash-safe, private local conversation checkpoints."""
import json, os, tempfile, time
from pathlib import Path

class SessionStore:
    def __init__(self, root):
        self.dir=Path(root)/'.ollama-code'
        self.file=self.dir/'session.json'
    def save(self, history, progress):
        self.dir.mkdir(mode=0o700,parents=True,exist_ok=True)
        payload={'version':1,'saved_at':time.time(),'history':history,'progress':progress}
        fd,name=tempfile.mkstemp(prefix='.session-',dir=self.dir)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(payload,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
            os.chmod(name,0o600)
            os.replace(name,self.file)
        finally:
            if os.path.exists(name):os.unlink(name)
    def load(self):
        if not self.file.exists():return None
        data=json.loads(self.file.read_text(encoding='utf-8'))
        if data.get('version')!=1:raise ValueError('Unsupported session format')
        return data['history'],data['progress']
