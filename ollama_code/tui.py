"""Responsive terminal chat UI for desktop and narrow mobile terminals."""
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog, Static, Button, TextArea
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual import work
from rich.text import Text
from .app import Agent, Workspace

COLORS=['#e8e8e8']
# Terminal-native dotted emblem inspired by Ollama's circular mark.
DOT_LOGO = ('   ⠤⠤⠤   \n'
            ' ⠿⠿⠿⠿⠿⠿⠿ \n'
            '⠿⠿⠿⠿⠿⠿⠿⠿⠿\n'
            '⠿⠿⠿⠿⠿⠿⠿⠿⠿\n'
            ' ⠿⠿⠿⠿⠿⠿⠿ \n'
            '   ⠤⠤⠤   ')
BIG_LOGO = ('██╗     ██╗      █████╗ ███╗   ███╗ █████╗      ██████╗ ██████╗ ██████╗ ███████╗\n'
'██║     ██║     ██╔══██╗████╗ ████║██╔══██╗    ██╔════╝██╔═══██╗██╔══██╗██╔════╝\n'
'██║     ██║     ███████║██╔████╔██║███████║    ██║     ██║   ██║██║  ██║█████╗  \n'
'██║     ██║     ██╔══██║██║╚██╔╝██║██╔══██║    ██║     ██║   ██║██║  ██║██╔══╝  \n'
'███████╗███████╗██║  ██║██║ ╚═╝ ██║██║  ██║    ╚██████╗╚██████╔╝██████╔╝███████╗\n'
'╚══════╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝')


class EditorScreen(ModalScreen[tuple | None]):
    """Full-screen editable buffer; saving only proposes a change, never writes directly."""
    CSS = """EditorScreen { align: center middle; background: #05070bcc; }
    #editor-dialog { width: 96%; height: 94%; background: #0d111b; border: solid #64748b; padding: 1; }
    #editor-title { height: 2; color: #93c5fd; text-style: bold; }
    #editor { height: 1fr; border: solid #334155; }
    #editor-actions { height: 3; align: right middle; }
    #editor-actions Button { margin-left: 1; }
    """
    BINDINGS = [('escape','cancel','Cancel'), ('ctrl+s','save','Save proposal')]
    def __init__(self, path, content):
        super().__init__(); self.path=path; self.content=content
    def compose(self):
        with Vertical(id='editor-dialog'):
            yield Static(f'EDITOR  ·  {self.path}  ·  Ctrl+S to review changes', id='editor-title')
            yield TextArea(self.content, id='editor', soft_wrap=False, show_line_numbers=True)
            with Horizontal(id='editor-actions'):
                yield Button('Cancel', id='editor-cancel')
                yield Button('Review diff', id='editor-save', variant='primary')
    def on_button_pressed(self, event):
        if event.button.id=='editor-save': self.action_save()
        elif event.button.id=='editor-cancel': self.dismiss(None)
    def action_save(self):
        self.dismiss((self.path, self.query_one('#editor', TextArea).text))
    def action_cancel(self): self.dismiss(None)

class Approval(ModalScreen[bool]):
    """Explicit approval modal with aligned before/after panes."""
    CSS="""Approval { align: center middle; background: #090909 85%; }
    #dialog { width: 96%; max-width: 120; height: 88%; background: #101522; border: solid #f59e0b; padding: 1; }
    #message { height: 2; color: #f8fafc; text-style: bold; }
    #diff-labels { height: 1; color: #93c5fd; }
    #diff-columns { height: 1fr; }
    .diff-pane { width: 1fr; height: 1fr; border: solid #334155; padding: 0 1; overflow-y: auto; }
    #buttons { height: 3; align: center middle; }
    #buttons Button { margin: 0 1; }
    """
    BINDINGS=[('escape','reject','Reject')]
    def __init__(self,message,diff=''):
        super().__init__();self.message=message;self.diff=diff
    def _panes(self):
        import difflib
        old=[];new=[]
        for line in self.diff.splitlines():
            if line.startswith(('---','+++','\\','@@')):continue
            if line.startswith('-'):old.append(line[1:])
            elif line.startswith('+'):new.append(line[1:])
            elif line.startswith(' '):old.append(line[1:]);new.append(line[1:])
        left=[];right=[]
        matcher=difflib.SequenceMatcher(a=old,b=new,autojunk=False)
        for tag,i1,i2,j1,j2 in matcher.get_opcodes():
            if tag=='equal':
                for a,b in zip(old[i1:i2],new[j1:j2]):left.append('  '+a);right.append('  '+b)
            elif tag in ('replace','delete'):
                before=old[i1:i2];after=new[j1:j2];height=max(len(before),len(after))
                left.extend(('− '+before[i] if i<len(before) else '') for i in range(height))
                right.extend(('+ '+after[i] if i<len(after) else '') for i in range(height))
            elif tag=='insert':
                for line in new[j1:j2]:left.append('');right.append('+ '+line)
        return ('\n'.join(left) or '(new file / no previous content)', '\n'.join(right) or '(deleted / empty content)')
    def compose(self):
        left,right=self._panes()
        with Vertical(id='dialog'):
            yield Static('HUMAN APPROVAL REQUIRED  ·  Review both panes before applying',id='message')
            yield Static(self.message, id='diff-labels')
            with Horizontal(id='diff-columns'):
                yield Static('BEFORE\n'+left, classes='diff-pane')
                yield Static('PROPOSED\n'+right, classes='diff-pane')
            with Horizontal(id='buttons'):
                yield Button('Reject (Esc)',id='reject',variant='error')
                yield Button('Approve & apply',id='approve',variant='success')
    def on_button_pressed(self,event):self.dismiss(event.button.id=='approve')
    def action_reject(self):self.dismiss(False)

class FileAction(ModalScreen[tuple | None]):
    """Touch-friendly form for local and shared-storage operations."""
    CSS = """FileAction { align: center middle; background: #090909 85%; }
    #file-dialog { width: 94%; max-width: 88; height: auto; max-height: 90%; background: #1a1a1a; border: solid #999999; padding: 1 2; }
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

class PromptBox(TextArea):
    """Multiline chat prompt: Enter sends, Shift+Enter adds a line.

    Priority bindings intentionally override TextArea's default Enter-to-newline
    behavior. Pasted multiline text remains in the editor as one prompt.
    Ctrl+Enter is also supported as an alternate send shortcut.
    """
    BINDINGS = [
        Binding("enter", "submit_prompt", "Send prompt", priority=True),
        Binding("shift+enter", "insert_newline", "New line", priority=True),
        Binding("ctrl+enter", "submit_prompt", "Send prompt", priority=True),
    ]

    def action_submit_prompt(self):
        prompt = self.text.strip()
        if not prompt:
            return
        # Clear first so the prompt is visibly accepted before work begins.
        self.text = ""
        self.app.handle_prompt(prompt)


class CodeUI(App):
    TITLE = 'OLLAMA CODE'
    CSS = """
    Screen { background: #090909; color: #f0f0f0; }
    Header, Footer { background: #111111; color: #aaaaaa; }
    #banner { height: 7; padding: 0 2; background: #080b12; color: #ffffff; border-bottom: solid #263249; overflow: hidden; }
    #banner Static { text-style: bold; }
    #info { height: 1; padding: 0 2; color: #a9bad5; background: #101725; border-bottom: solid #263249; }
    #log { height: 1fr; background: #090d14; padding: 1 2; border: none; }
    #plan { display: none; height: auto; max-height: 8; padding: 1 2; margin: 0 2; color: #cbd5e1; background: #111827; border: round #3b4c68; }
    Screen.task-running #plan { display: block; }
    #log:focus { border: none; }
    #activity { display: none; height: 1; padding: 0 2; background: #111521; color: #7dd3fc; }
    Screen.task-running #activity { display: block; }
    #live { display: none; height: auto; max-height: 28%; min-height: 2; padding: 1 2; background: #10131c; color: #e6edf8; border-top: solid #293248; overflow-y: auto; }
    Screen.task-running #live { display: block; }
    #prompt { height: 5; min-height: 3; margin: 1 2 0 2; border: solid #526789; background: #111827; color: #f8fafc; }
    #prompt:focus { border: solid #60a5fa; }
    #actions { display: none; height: 0; padding: 0; }
    #actions Button { display: none; }
    #hint { height: 1; padding: 0 2; color: #858585; }
    Screen.narrow #banner { height: 4; padding: 0 1; }
    Screen.narrow #info { height: 1; padding: 0 1; }
    Screen.narrow #plan { margin: 0 1; padding: 0 1; max-height: 6; }
    Screen.narrow #log { padding: 0 1; }
    Screen.narrow #prompt { margin: 1 1 0 1; height: 4; }
    Screen.narrow #live { max-height: 30%; padding: 0 1; }
    Screen.narrow #hint { display: none; }
    Screen.keyboard-open #banner, Screen.keyboard-open #info, Screen.keyboard-open Header, Screen.keyboard-open Footer { display: none; }
    Screen.keyboard-open #live { max-height: 35%; }
    """
    BINDINGS=[('ctrl+q','quit','Quit'),('ctrl+l','clear','Clear'),('ctrl+c','cancel','Cancel'),('ctrl+k','keyboard','Keyboard layout'),('ctrl+r','resume','Resume')]
    def __init__(self,workspace='.',model='qwen2.5-coder:1.5b',host='http://127.0.0.1:11434',approval=None,context=None):
        super().__init__()
        self.agent=Agent(Workspace(workspace),model,host)
        if context is not None:
            if not 4096 <= context <= 131072: raise ValueError('Context must be between 4096 and 131072 tokens')
            self.agent.ws.settings.set('context', context)
            self.agent.options['num_ctx'] = context
        if approval:self.agent.ws.settings.set('approval',approval)
        # The interactive TUI always asks a person before every write, even if CLI policy is permissive.
        self.agent.ws.approve=lambda message:self._approve(message)
        self.agent.ws.preview=self._preview
        self.busy=False;self.streaming='';self._last_render='';self._keyboard=False;self._pending_diff=''
        self._stream_lock=threading.Lock();self._stream_version=0;self._shown_version=-1
        self.transcript=[]
        self._activity_tick=0;self._activity_phase='ANALYZING';self._activity_start=0.0
        self._stage='ANALYZING';self._stage_detail='Inspecting the workspace and planning a safe approach'
        self.logfile=Path(self.agent.ws.root)/'.ollama-code'/'ui-errors.log'
    def compose(self)->ComposeResult:
        yield Header(show_clock=False)
        yield Static('',id='banner')
        yield Static('',id='info')
        yield RichLog(id='log',wrap=True,highlight=False,markup=False,auto_scroll=True)
        yield Static('',id='plan')
        yield Static('',id='activity')
        yield Static('',id='live')
        yield PromptBox('', id='prompt')
        yield Static('Enter send  •  Shift+Enter new line  •  Paste multi-line text  •  Ctrl+Enter also sends  •  /help',id='hint')
        yield Footer()
    def on_mount(self):
        self._resize()
        self._status()
        self._write('Type /help for commands · /files to browse · /view PATH to inspect source.')
        self.query_one('#prompt',PromptBox).focus()
        self.set_interval(.10,self._refresh_stream)
        self.set_interval(.20,self._animate_activity)
    def on_resize(self,event):self._resize()
    def _resize(self):
        narrow = self.size.width < 115
        self.screen.set_class(narrow, 'narrow')
        if narrow:
            t = Text()
            t.append('◆ ', style='bold #60a5fa')
            t.append('OLLAMA ', style='bold #93c5fd')
            t.append('CODE\n', style='bold #f0abfc')
            t.append('LOCAL-FIRST CODING AGENT · POWERED BY OLLAMA', style='dim #9aa8c4')
        else:
            # Place a large dotted Ollama-inspired mark beside the block wordmark.
            t = Text()
            base_lines = BIG_LOGO.splitlines()
            # Add a leading block O so the large wordmark reads OLLAMA CODE.
            leading_o = ['  █████╗ ', ' ██╔══██╗', ' ██║  ██║', ' ██║  ██║', ' ╚█████╔╝', '  ╚════╝ ']
            lines = [leading_o[i] + line for i, line in enumerate(base_lines)]
            dots = DOT_LOGO.splitlines()
            dot_width = max(map(len, dots)) + 2
            start_color, middle_color, end_color = (59, 130, 246), (139, 92, 246), (244, 114, 182)
            width = max(len(line) for line in lines)
            for row, line in enumerate(lines):
                t.append((dots[row] if row < len(dots) else '').ljust(dot_width), style='bold #7dd3fc')
                for column, char in enumerate(line):
                    ratio = column / max(1, width - 1)
                    if ratio < 0.5:
                        blend = ratio * 2
                        rgb = tuple(round(start_color[i] * (1 - blend) + middle_color[i] * blend) for i in range(3))
                    else:
                        blend = (ratio - 0.5) * 2
                        rgb = tuple(round(middle_color[i] * (1 - blend) + end_color[i] * blend) for i in range(3))
                    t.append(char, style=f'bold #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}')
                t.append('\n')
            # Keep the oversized wordmark as the sole title; secondary taglines waste vertical space.
        self.query_one('#banner', Static).update(t)
    def _status(self):
        model=self.agent.model
        if self.size.width<115:model=model[:24]
        state=self._stage if self.busy else 'IDLE'
        mode='ASK'
        self.query_one('#info',Static).update(f'MODEL  {model}    ·    MODE  {mode}    ·    STATE  {state}')

    def _update_plan(self):
        stages=[('ANALYZE','Understand request and inspect relevant files'),
                ('PLAN','Choose small, safe changes'),
                ('IMPLEMENT','Make focused edits after showing approval diffs'),
                ('VALIDATE','Check output and run relevant tests'),
                ('REVIEW','Summarize changes and any remaining issues')]
        current={'ANALYZING':0,'PLANNING':1,'IMPLEMENTING':2,'VALIDATING':3,'REVIEWING':4}.get(self._stage,0)
        lines=['TASK FLOW  ·  visible progress (not private reasoning)']
        for i,(name,desc) in enumerate(stages):
            marker='▶' if i==current else '✓' if i<current else '·'
            lines.append(f'{marker} {name:<10} {desc}')
        self.query_one('#plan',Static).update('\n'.join(lines))
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

    def _preview(self,path,diff):
        self._pending_diff=diff
        self.call_from_thread(self._write,f'PROPOSED {path}\n{diff[:12000]}')
    def _approve(self,message):
        import concurrent.futures
        answer=concurrent.futures.Future()
        def show():self.push_screen(Approval(message,self._pending_diff),lambda result:answer.set_result(bool(result)))
        self.call_from_thread(show)
        return answer.result()
    def action_clear(self):self.query_one('#log',RichLog).clear()
    def action_cancel(self):self.agent.cancel.set();self._write('Cancellation requested. Session checkpoint retained.')
    def action_keyboard(self):
        self._keyboard=not self._keyboard
        self.screen.set_class(self._keyboard,'keyboard-open')
        self.query_one('#prompt',PromptBox).focus()
    def action_resume(self):self._restore()
    def _restore(self):
        try:
            data=self.agent.session.load()
            if not data:self._write('No saved session.');return
            self.agent.history,self.agent.progress=data
            self._write(f'Restored session: {self.agent.progress.get("status","unknown")}. Use /continue to resume work.')
        except Exception as exc:self._write(f'Restore error: {exc}')
    def _animate_activity(self):
        """Animate four dots without repainting the response body."""
        if not self.busy:
            return
        import time
        self._activity_tick += 1
        # Exactly four dot positions; one brighter dot advances each frame.
        dots = ''.join('●' if i == self._activity_tick % 4 else '·' for i in range(4))
        elapsed = int(time.monotonic() - self._activity_start)
        with self._stream_lock:
            writing = bool(self.streaming)
        label = self._stage
        self.query_one('#activity', Static).update(f'{dots}  {label}  ·  {elapsed}s')
        if self._activity_tick % 5 == 0:
            self._status()

    def _refresh_stream(self):
        """Refresh visible output and a coarse, user-facing workflow stage."""
        if not self.busy:
            return
        with self._stream_lock:
            version = self._stream_version
            if version == self._shown_version:
                return
            output = self.streaming[-16000:]
        self._shown_version = version
        lowered = output.lower()
        if any(token in lowered for token in ('⚙ run_tests', '⚙ run_command', '⚙ validate', 'pytest', 'npm test', 'validation check')):
            self._stage = 'VALIDATING'
            self._stage_detail = 'Checking the result and looking for regressions'
        elif any(token in lowered for token in ('⚙ write_file', '⚙ apply_patch', '⚙ create_file', '⚙ edit_file', '⚙ replace_in_file')):
            self._stage = 'IMPLEMENTING'
            self._stage_detail = 'Applying focused changes; writes still require approval'
        elif output.strip() and self._stage == 'ANALYZING':
            self._stage = 'PLANNING'
            self._stage_detail = 'Organizing the task before making changes'
        self._update_plan()
        self._status()
        self.query_one('#live', Static).update(output or 'Inspecting the task…')

    def _emit(self, chunk):
        # Ollama callbacks run in a worker thread; synchronize shared text.
        with self._stream_lock:
            self.streaming += chunk
            if len(self.streaming) > 100000:
                self.streaming = self.streaming[-100000:]
            self._stream_version += 1
    def on_button_pressed(self,event:Button.Pressed):
        if event.button.id in ('files','code','new','import','export'):
            operation='browse' if event.button.id=='files' else event.button.id
            self.push_screen(FileAction(operation),self._file_action)
        elif event.button.id=='edit':
            self.push_screen(FileAction('code'),self._edit_path_selected)
        elif event.button.id=='undo':
            if not self.busy:self.rollback_last()
            else:self._write('Wait for the active task to finish before rolling back.')
    def _edit_path_selected(self,result):
        if not result or result[0]!='code':return
        path=result[1]
        try:
            content=self.agent.ws.read_file(path)
            self.push_screen(EditorScreen(path,content),self._editor_result)
        except Exception as exc:self._write(f'Editor error: {exc}')
    def _editor_result(self,result):
        if result is None:return
        if self.busy:self._write('Wait for the active task to finish before editing.');return
        self.apply_editor_content(result[0],result[1])
    @work(thread=True)
    def apply_editor_content(self,path,content):
        try:self.call_from_thread(self._write,self.agent.ws.write_file(path,content))
        except Exception as exc:self.call_from_thread(self._write,f'Edit failed: {exc}')
    @work(thread=True)
    def rollback_last(self):
        try:self.call_from_thread(self._write,self.agent.ws.rollback_last())
        except Exception as exc:self.call_from_thread(self._write,f'Rollback failed: {exc}')

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
    def handle_prompt(self, raw_prompt):
        prompt=raw_prompt.strip()

        if not prompt:return
        if prompt=='/help':self._write('FILES: /files · /view PATH [START END] · /editfile PATH · /history · /undo · /read PATH · /search TEXT · /new PATH · /import SOURCE DEST · /export SOURCE DEST\nAGENT: /edit PATH [change] (agent proposes edits; approval required) · /continue · /resume · /save\nMODEL: /model NAME · /models · /context TOKENS · /settings · /approval ask|edits|all · /health · /status\nMEDIA: /image PATH · /video PATH · /keyboard · /clear · /quit\nSafety: file writes show a diff and require approval by default. Files outside the selected workspace must be explicitly imported.');return
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
        if prompt.startswith('/model '):
            name=prompt[7:].strip()
            if not name:self._write('Usage: /model MODEL_NAME');return
            self.agent.model=name;self._status();self._write('Model set to '+name);return
        if prompt.startswith('/context '):
            try:
                value=int(prompt.split(None,1)[1])
                if not 4096 <= value <= 131072: raise ValueError('Use a context size between 4096 and 131072 tokens; available RAM/model support may limit practical sizes.')
                self.agent.ws.settings.set('context',value);self.agent.options['num_ctx']=value
                self._write(f'Context window set to {value:,} tokens. Larger windows use more RAM/VRAM and depend on model support.')
                self._status()
            except (ValueError,IndexError) as exc:self._write('Context not changed: '+str(exc))
            return
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
        if prompt=='/history':self._write(self.agent.ws.history());return
        if prompt=='/undo':
            if self.busy:self._write('Wait for the active task to finish before rolling back.')
            else:self.rollback_last()
            return
        if prompt.startswith('/editfile '):
            path=prompt[len('/editfile '):].strip().strip('\"')
            if not path:self._write('Usage: /editfile PATH');return
            self._edit_path_selected(('code',path));return
        if prompt.startswith(('/code ','/view ')):
            import shlex
            try:
                parts=shlex.split(prompt.split(' ',1)[1])
                if not 1 <= len(parts) <= 3: raise ValueError('Usage: /view PATH [START [END]]')
                path=parts[0]
                if len(parts)>1:
                    start=int(parts[1]);end=int(parts[2]) if len(parts)>2 else start+119
                    self._write(self.agent.ws.show_code(path,start,end))
                else:self._file_action(('code',path))
            except Exception as exc:self._write(f'View error: {exc}')
            return
        if prompt.startswith('/edit '):
            import shlex
            try:
                parts=shlex.split(prompt[6:])
                if not parts: raise ValueError('Usage: /edit PATH [what to change]')
                path=parts[0]
                instruction=' '.join(parts[1:]).strip()
                task=(f'The requested change is: {instruction}' if instruction else 'If I have not specified what to change, ask me what edit I want instead of guessing.')
                prompt=f'Please inspect {path} in the current workspace, explain the intended change briefly, then implement the requested edit using the available file tools. {task} Show a diff and obtain explicit human approval before writing any changes.'
            except ValueError as exc:
                self._write(str(exc));return
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
        self._shown_version=-1
        with self._stream_lock:self._stream_version+=1
        self._activity_tick=0;self._activity_start=time.monotonic()
        self._stage='ANALYZING';self._stage_detail='Inspecting the workspace and planning a safe approach'
        self.screen.set_class(True, 'task-running')
        self.query_one('#activity',Static).update('●···  ANALYZING  ·  0s')
        self.query_one('#live',Static).update('')
        self._update_plan()
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
        self._stage='IDLE'
        with self._stream_lock:final_text=self.streaming[-30000:]
        if final_text:self._write(final_text)
        self.streaming='';self._last_render=''
        self.screen.set_class(False, 'task-running')
        self.query_one('#activity',Static).update('')
        self.query_one('#live',Static).update('')
        self._status();self.query_one('#prompt',PromptBox).focus()
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

def clear_terminal_visible():
    """Clear the visible viewport only when attached to an interactive TTY.

    Intentionally preserves terminal scrollback (no CSI 3 J), shell history,
    files, and logs. Never runs a shell command; redirected output is untouched.
    """
    stream = sys.stdout
    if not getattr(stream, 'isatty', lambda: False)():
        return False
    if os.environ.get('TERM', '') in ('', 'dumb'):
        return False
    try:
        os.write(stream.fileno(), b'\x1b[2J\x1b[H')
        stream.flush()
        return True
    except (OSError, ValueError, AttributeError):
        return False


def run(workspace,model,host,approval=None,context=None):
    # Give the app a clean viewport, then clear its rendered screen on exit.
    clear_terminal_visible()
    try:
        CodeUI(workspace,model,host,approval,context).run()
    finally:
        clear_terminal_visible()
