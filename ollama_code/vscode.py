"""VS Code integration: opt-in workspace tasks, never overwrites user configuration."""
import json
from pathlib import Path

def install_workspace_config(root,approve):
    root=Path(root).resolve(); dest=root/'.vscode'/'tasks.json'
    if dest.exists():return 'VS Code tasks already exist; no changes made'
    if not approve('Create VS Code workspace tasks?'):return 'User rejected VS Code setup'
    dest.parent.mkdir(parents=True,exist_ok=True)
    data={'version':'2.0.0','tasks':[{'label':'Ollama Code: Launch','type':'shell','command':'ollama-code','args':['--workspace','${workspaceFolder}'],'problemMatcher':[]},{'label':'Ollama Code: CLI','type':'shell','command':'ollama-code','args':['--workspace','${workspaceFolder}','--cli'],'problemMatcher':[]}] }
    dest.write_text(json.dumps(data,indent=2)+'\n')
    return 'Created .vscode/tasks.json. Run tasks via Terminal > Run Task in VS Code.'
