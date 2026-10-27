"""Responsive terminal chat UI for desktop and narrow mobile terminals."""
import logging
from datetime import datetime, timezone
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, Button
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual import work
from rich.text import Text
from .app import Agent, Workspace

COLORS=['#e8e8e8']
BIG_LOGO = ('██╗     ██╗      █████╗ ███╗   ███╗ █████╗      ██████╗ ██████╗ ██████╗ ███████╗\n'
'██║     ██║     ██╔══██╗████╗ ████║██╔══██╗    ██╔════╝██╔═══██╗██╔══██╗██╔════╝\n'
'██║     ██║     ███████║██╔████╔██║███████║    ██║     ██║   ██║██║  ██║█████╗  \n'
'██║     ██║     ██╔══██║██║╚██╔╝██║██╔══██║    ██║     ██║   ██║██║  ██║██╔══╝  \n'
'███████╗███████╗██║  ██║██║ ╚═╝ ██║██║  ██║    ╚██████╗╚██████╔╝██████╔╝███████╗\n'
'╚══════╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝')

class Approval(ModalScreen[bool]):
    CSS='''Approval { align: center middle; background: #120617 80%; } #dialog { width: 90%; max-width: 75; height: auto; max-height: 75%; background: #310d31; border: heavy #f5c95b; padding: 1; } #message { margin-bottom: 1; color: #fff0b4; } #buttons { height: 3; align: center middle; }'''
    BINDINGS=[('escape','reject','Reject')]
    def __init__(self,message):super().__init__();self.message=message
    def compose(self):
        with Vertical(id='dialog'):
            yield Static('⚠ APPROVAL REQUIRED')
            yield Static(self.message,id='message')
            with Horizontal(id='buttons'):
                yield Button('Reject',id='reject',variant='error')
                yield Button('Approve',id='approve',variant='success')
    def on_button_pressed(self,event):self.dismiss(event.button.id=='approve')
    def action_reject(self):self.dismiss(False)

class FileAction(ModalScreen[tuple | None]):
    """Touch-friendly form for local and shared-storage operations."""
    CSS = """FileAction { align: center middle; background: #120617 85%; }
    #file-dialog { width: 94%; max-width: 88; height: auto; max-height: 90%; background: #310d31; border: heavy #c58ff0; padding: 1 2; }
    #file-dialog Input { margin: 1 0; }
    #file-buttons { height: 3; align: center middle; }
    """
    BINDINGS = [('escape','close','Close')]
    def __init__(self, operation):
        super().__init__(); self.operation=operation
    def compose(self):
        titles={'browse':'Browse project files','code':'View source code','new':'Create a new file','import':'Import from computer / Android storage','export':'Export to computer / Android storage'}
        with Vertical(id='file-dialog'):
            yield Static(titles[self.operation])
            if self.operation=='browse':
                yield Static('Browse workspace files from the Files button. Select a path below to inspect its code.')
            else:
                yield Input(placeholder='Workspace-relative file path (e.g. src/main.py)',id='file-path')
                if self.operation in ('import','export'):
                    yield Input(placeholder='External absolute path (e.g. ~/Downloads/file.py or /sdcard/Download/file.py)',id='external-path')
            with Horizontal(id='file-buttons'):
                yield Button('Cancel',id='cancel')
                yield Button('Continue',id='confirm',variant='primary')
    def on_button_pressed(self,event):
        if event.button.id=='cancel':self.dismiss(None);return
        if self.operation=='browse':self.dismiss(('browse',));return
        path=self.query_one('#file-path',Input).value.strip()
        if not path:self.notify('Enter a file path',severity='warning');return
        if self.operation in ('import','export'):
            external=self.query_one('#external-path',Input).value.strip()
            if not external:self.notify('Enter an external path',severity='warning');return
            self.dismiss((self.operation,path,external))
        else:self.dismiss((self.operation,path))
    def action_close(self):self.dismiss(None)

class CodeUI(App):
    CSS='''
    Screen { background: #090909; color: #e8e8e8; }
    Header { background: #191919; color: #d9d9d9; }
    #banner { height: 8; padding: 0 1; background: #111111; color: #f5f5f5; }
    #info { height: 2; padding: 0 1; color: #bdbdbd; background: #101010; }
    #log { height: 1fr; border: solid #444444; background: #111111; padding: 0 1; }
    #live { height: auto; max-height: 28%; min-height: 2; border: solid #666666; padding: 0 1; background: #171717; color: #f4f4f4; }
    #prompt { height: 3; margin: 0 1; border: solid #888888; background: #1b1b1b; color: #ffffff; }
    #actions { height: 3; padding: 0 1; background: #151515; }
    #actions Button { min-width: 10; margin-right: 1; background: #303030; color: #f2f2f2; border: none; }
    Screen.narrow #actions Button { min-width: 7; margin-right: 0; }
    #hint { height: 1; padding: 0 1; color: #999999; }
    Footer { background: #191919; color: #d5d5d5; }
    Screen.narrow #banner { height: 3; }
    Screen.narrow #info { height: 1; }
    Screen.narrow #live { max-height: 35%; }
    Screen.narrow #actions { height: 3; }
    Screen.narrow #hint { display: none; }
    Screen.keyboard-open #banner { display: none; }
    Screen.keyboard-open #info { display: none; }
    Screen.keyboard-open Header { display: none; }
    Screen.keyboard-open Footer { display: none; }
    Screen.keyboard-open #live { max-height: 40%; }
    '''''
    BINDINGS=[('ctrl+q','quit','Quit'),('ctrl+l','clear','Clear'),('ctrl+c','cancel','Cancel'),('ctrl+k','keyboard','Keyboard layout'),('ctrl+r','resume','Resume')]
    def __init__(self,workspace='.',model='qwen2.5-coder:1.5b',host='http://127.0.0.1:11434',approval=None):
        super().__init__()
        self.agent=Agent(Workspace(workspace),model,host)
        if approval:self.agent.ws.settings.set('approval',approval)
        self.agent.ws.approve=lambda message:self.agent.ws.policy.decide(message,lambda:self._approve(message))
        self.agent.ws.preview=self._preview
        self.busy=False;self.streaming='';self._last_render='';self._keyboard=False
        self.transcript=[]
        self._activity_tick=0;self._activity_phase='Thinking';self._activity_start=0.0
        self.logfile=Path(self.agent.ws.root)/'.ollama-code'/'ui-errors.log'
    def compose(self)->ComposeResult:
        yield Header(show_clock=False)
        yield Static('',id='banner')
        yield Static('',id='info')
        yield RichLog(id='log',wrap=True,highlight=False,markup=False,auto_scroll=True)
        yield Static('Ready to code. Your response streams here.',id='live')
        with Horizontal(id='actions'):
            yield Button('Files',id='files',variant='primary')
            yield Button('Code',id='code')
            yield Button('New',id='new')
            yield Button('Import',id='import')
            yield Button('Export',id='export')
        yield Input(placeholder='> Ask Ollama Code anything · Enter to send',id='prompt')
        yield Static('Enter send  •  Ctrl+K mobile keyboard mode  •  Ctrl+R resume',id='hint')
        yield Footer()
    def on_mount(self):
        self._resize()
        self._status()
        self._write('OLLAMA CODE 18  |  Dark terminal edition\nType /help for commands, /resume for recovery, /code PATH to inspect source.')
        self.query_one('#prompt',Input).focus()
        self.set_interval(.12,self._refresh_stream)
        self.set_interval(.28,self._animate_activity)
    def on_resize(self,event):self._resize()
    def _resize(self):
        narrow=self.size.width<85
        self.screen.set_class(narrow,'narrow')
        if narrow:
            t=Text('██ OLLAMA CODE\n   LOCAL CODING AGENT',style='bold #f5f5f5')
        else:
            t=Text('  OLLAMA CODE\n'+BIG_LOGO+'\n  EXPLORE  /  PLAN  /  EDIT  /  VALIDATE  /  BUILD',style='bold #e9e9e9')
        self.query_one('#banner',Static).update(t)
    def _status(self):
        model=self.agent.model
        if self.size.width<85:model=model[:24]
        self.query_one('#info',Static).update(f'◆ {model}  ◇ {self.agent.ws.settings.values["approval"]}  ◆ {"THINKING" if self.busy and not self.streaming else "WRITING" if self.busy else "READY"}')
    def _write(self,message):
        self.query_one('#log',RichLog).write(message)
        if isinstance(message,str):
            self.transcript.append(message)
            if len(self.transcript)>3000:self.transcript=self.transcript[-3000:]
    def _save_transcript(self):
        import os
        folder=self.agent.ws.root/'.ollama-code'/'transcripts'
        folder.mkdir(parents=True,exist_ok=True)
        filename=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.md'
        target=folder/filename
        # Create exclusively; never overwrite a previous transcript.
        with target.open('x',encoding='utf-8') as handle:
            handle.write('# Ollama Code conversation\n\n')
            handle.write('\n\n'.join(self.transcript))
            handle.write('\n')
        self._write('Conversation saved: '+str(target.relative_to(self.agent.ws.root)))
    def _show_health(self):
        try:
            models=self.agent.models()
            self._write('Ollama server: connected\nModel: '+self.agent.model+'\nInstalled models: '+str(len(models)))
        except Exception as exc:
            self._write('Ollama server unavailable: '+str(exc)+'\nCheck that Ollama is running and the configured host is reachable.')

    def _preview(self,path,diff):self.call_from_thread(self._write,f'PROPOSED {path}\n{diff[:12000]}')
    def _approve(self,message):
        import concurrent.futures
        answer=concurrent.futures.Future()
        def show():self.push_screen(Approval(message),lambda result:answer.set_result(bool(result)))
        self.call_from_thread(show)
        return answer.result()
    def action_clear(self):self.query_one('#log',RichLog).clear()
    def action_cancel(self):self.agent.cancel.set();self._write('Cancellation requested. Session checkpoint retained.')
    def action_keyboard(self):
        self._keyboard=not self._keyboard
        self.screen.set_class(self._keyboard,'keyboard-open')
        self.query_one('#prompt',Input).focus()
    def action_resume(self):self._restore()
    def _restore(self):
        try:
            data=self.agent.session.load()
            if not data:self._write('No saved session.');return
            self.agent.history,self.agent.progress=data
            self._write(f'Restored session: {self.agent.progress.get("status","unknown")}. Use /continue to resume work.')
        except Exception as exc:self._write(f'Restore error: {exc}')
    def _animate_activity(self):
        """Animate while inference is active, including before the first token."""
        if not self.busy:
            return
        import time
        self._activity_tick += 1
        dots = ('.', '..', '...')[self._activity_tick % 3]
        spinner = ('◐', '◓', '◑', '◒')[self._activity_tick % 4]
        elapsed = int(time.monotonic() - self._activity_start)
        if self.streaming:
            label = 'Writing'
            # Keep recent output visible even when the model pauses.
            output = self.streaming[-4500:]
            self.query_one('#live',Static).update(f'{spinner} {label}{dots}  {elapsed}s\n{output}')
        else:
            self.query_one('#live',Static).update(f'{spinner} Thinking{dots}  {elapsed}s\nWaiting for model output…')
        self._status()

    def _refresh_stream(self):
        if self.streaming!=self._last_render:
            self._last_render=self.streaming
            # The activity timer draws the stream and its animated indicator.
    def _emit(self,chunk):
        # Called from worker thread. Rendering is throttled on UI timer.
        self.streaming+=chunk
        if len(self.streaming)>100000:self.streaming=self.streaming[-100000:]
    def on_button_pressed(self,event:Button.Pressed):
        if event.button.id in ('files','code','new','import','export'):
            operation='browse' if event.button.id=='files' else event.button.id
            self.push_screen(FileAction(operation),self._file_action)
    def _file_action(self,result):
        if result is None:return
        if result[0]=='browse':
            self._write('WORKSPACE FILES\n'+self.agent.ws.list_files());return
        if result[0]=='code':
            try:
                from rich.syntax import Syntax
                path=result[1];content=self.agent.ws.read_file(path)
                self._write(Syntax(content,self.agent.ws.path(path).suffix.lstrip('.') or 'text',line_numbers=True,word_wrap=True))
            except Exception as exc:self._write(f'Code preview error: {exc}')
            return
        if self.busy:self._write('Wait for the active task to finish before changing files.');return
        self.file_operation(result)
    @work(thread=True)
    def file_operation(self,result):
        op=result[0]
        try:
            ws=self.agent.ws
            if op=='new':message=ws.create_file(result[1],'')
            elif op=='import':message=ws.storage_import(result[2],result[1])
            elif op=='export':message=ws.storage_export(result[1],result[2])
            else:return
            self.call_from_thread(self._write,message)
        except Exception as exc:self.call_from_thread(self._write,f'{op.title()} error: {exc}')
    def on_input_submitted(self,event:Input.Submitted):
        prompt=event.value.strip();event.input.value=''
        if not prompt:return
        if prompt=='/help':self._write('/read FILE · /image IMAGE · /video VIDEO · /save · /health · /code PATH · /new PATH · /import SOURCE DEST · /export SOURCE DEST · /model NAME · /models · /settings · /approval MODE · /resume · /continue · /status · /keyboard · /files · /search TEXT · /clear · /quit');return
        if prompt.startswith(('/read ','/image ','/video ')):
            import shlex
            try:
                kind,raw=prompt[1:].split(' ',1)
                args=shlex.split(raw)
                if len(args)!=1:raise ValueError('Provide one quoted file path')
                self._write(self.agent.attachments.add(kind,args[0]))
            except Exception as exc:self._write(f'Attachment error: {exc}')
            return
        if prompt=='/keyboard':self.action_keyboard();return
        if prompt=='/save':
            try:self._save_transcript()
            except OSError as exc:self._write('Transcript save failed: '+str(exc))
            return
        if prompt=='/health':self.check_health();return
        if prompt=='/resume':self._restore();return
        if prompt=='/status':self._write(str(self.agent.progress));return
        if prompt.startswith('/model '):self.agent.model=prompt[7:].strip();self._status();return
        if prompt=='/models':self.list_models();return
        if prompt=='/settings':self._write(str(self.agent.ws.settings.values));return
        if prompt.startswith('/approval '):
            try:self.agent.ws.settings.set('approval',prompt.split(' ',1)[1]);self._status();self._write('Approval updated')
            except ValueError as exc:self._write(str(exc))
            return
        if prompt=='/vscode':
            from .vscode import install_workspace_config
            self._write(install_workspace_config(self.agent.ws.root,self.agent.ws.approve));return
        if prompt=='/clear':self.action_clear();self.agent.history=self.agent.history[:1];return
        if prompt=='/files':self._write(self.agent.ws.list_files());return
        if prompt.startswith('/code '):self._file_action(('code',prompt[6:].strip()));return
        if prompt.startswith('/new '):self._file_action(('new',prompt[5:].strip()));return
        if prompt.startswith('/import '):
            import shlex
            try:
                args=shlex.split(prompt[8:]);self._file_action(('import',args[1],args[0]))
            except (ValueError,IndexError):self._write('Usage: /import SOURCE DEST')
            return
        if prompt.startswith('/export '):
            import shlex
            try:
                args=shlex.split(prompt[8:]);self._file_action(('export',args[0],args[1]))
            except (ValueError,IndexError):self._write('Usage: /export SOURCE DEST')
            return
        if prompt.startswith('/search '):self._write(self.agent.ws.search_files(prompt[8:]));return
        if prompt in ('/quit','/exit'):self.exit();return
        if self.busy:self._write('Agent is working. Ctrl+C to cancel; wait before sending another message.');return
        if prompt=='/continue':
            if not self.agent.progress.get('goal'):
                self._restore()
            if not self.agent.progress.get('goal'):self._write('No task to continue.');return
            prompt='Continue the previous coding task from the saved state. Check current files and tests before making further changes. Goal: '+self.agent.progress['goal']
        self._write(Text('> '+prompt,style='bold #a6e36b'))
        import time
        self.streaming='';self._last_render='';self.busy=True
        self._activity_tick=0;self._activity_start=time.monotonic()
        self.query_one('#live',Static).update('◐ Thinking...\nWaiting for model output…')
        self._status()
        self.run_agent(prompt)
    @work(thread=True)
    def check_health(self):self.call_from_thread(self._show_health)
    @work(thread=True,exclusive=True)
    def list_models(self):
        try:self.call_from_thread(self._write,'\n'.join(self.agent.models()) or 'No models found')
        except Exception as exc:self.call_from_thread(self._write,str(exc))
    def _finish(self):
        self.busy=False
        if self.streaming:self._write(self.streaming[-30000:])
        self.streaming='';self._last_render=''
        self.query_one('#live',Static).update('Ready. Enter your next message.')
        self._status();self.query_one('#prompt',Input).focus()
    @work(thread=True,exclusive=True)
    def run_agent(self,prompt):
        try:self.agent.ask(prompt,emit=self._emit)
        except Exception as exc:
            try:
                self.logfile.parent.mkdir(parents=True,exist_ok=True)
                with self.logfile.open('a',encoding='utf-8') as f:
                    import traceback
                    f.write(traceback.format_exc()+'\n')
            except OSError:pass
            self._emit(f'\nAgent error: {type(exc).__name__}: {exc}\nSee .ollama-code/ui-errors.log. Use /resume or /continue.\n')
        finally:self.call_from_thread(self._finish)

def run(workspace,model,host,approval=None):CodeUI(workspace,model,host,approval).run()
