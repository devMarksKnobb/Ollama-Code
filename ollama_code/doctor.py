"""Read-only environment diagnostics; no model downloads or commands are launched."""
import argparse
import json
import shutil
import urllib.request
from pathlib import Path

def diagnose(host='http://127.0.0.1:11434', workspace='.'):
    root=Path(workspace).expanduser().resolve()
    report={'workspace':str(root),'workspace_exists':root.is_dir(),
            'tools':{name:bool(shutil.which(name)) for name in ('git','docker','podman','node','npm','python','go','cargo','tsc')},
            'ollama':{'reachable':False,'models':[]}}
    try:
        with urllib.request.urlopen(host.rstrip('/')+'/api/tags',timeout=3) as response:
            data=json.load(response)
        report['ollama']={'reachable':True,'models':[m.get('name','') for m in data.get('models',[])]}
    except Exception as exc:
        report['ollama']['error']=str(exc)[:250]
    return report

def main():
    parser=argparse.ArgumentParser(description='Diagnose Ollama Code installation')
    parser.add_argument('--host',default='http://127.0.0.1:11434')
    parser.add_argument('--workspace',default='.')
    args=parser.parse_args()
    print(json.dumps(diagnose(args.host,args.workspace),indent=2))
if __name__=='__main__':main()
