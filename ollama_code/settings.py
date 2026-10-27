"""Workspace-local settings and explicit approval policy."""
import json
from pathlib import Path

class Settings:
    DEFAULTS={'approval':'ask','theme':'rainbow','context':32768,'max_steps':80}
    def __init__(self,root):
        self.path=Path(root)/'.ollama-code'/'settings.json'
        self.values=self.DEFAULTS.copy()
        if self.path.exists():
            try:
                raw=json.loads(self.path.read_text())
                for key,value in raw.items():
                    if key in self.DEFAULTS:self._validate(key,value);self.values[key]=value
            except (OSError,ValueError,TypeError):pass
    def _validate(self,key,value):
        if key=='approval' and value not in ('ask','edits','all'):raise ValueError('Approval must be ask, edits, or all')
        if key=='theme' and value!='rainbow':raise ValueError('Unknown theme')
        if key in ('context','max_steps') and (type(value) is not int or not 1<=value<=131072):raise ValueError('Invalid numeric setting')
    def set(self,key,value):
        if key not in self.DEFAULTS:raise ValueError('Unknown setting')
        self._validate(key,value)
        self.values[key]=value
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(self.values,indent=2)+'\n')

class ApprovalPolicy:
    def __init__(self,settings):self.settings=settings
    def decide(self,message,prompt):
        mode=self.settings.values['approval']
        is_command='isolated container' in message.lower()
        if mode=='all' or (mode=='edits' and not is_command):return True
        return prompt()
