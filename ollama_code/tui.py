"""Full-screen terminal UI with native, blocking approval dialogs."""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, Button
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual import work
from rich.text import Text
from .app import Agent, Workspace

BANNER = [
' ██████╗ ██╗     ██╗      █████╗ ███╗   ███╗ █████╗      ██████╗ ██████╗ ██████╗ ███████╗',
'██╔═══██╗██║     ██║     ██╔══██╗████╗ ████║██╔══██╗    ██╔════╝██╔═══██╗██╔══██╗██╔════╝',
'██║   ██║██║     ██║     ███████║██╔████╔██║███████║    ██║     ██║   ██║██║  ██║█████╗',
'██║   ██║██║     ██║     ██╔══██║██║╚██╔╝██║██╔══██║    ██║     ██║   ██║██║  ██║██╔══╝',
'╚██████╔╝███████╗███████╗██║  ██║██║ ╚═╝ ██║██║  ██║    ╚██████╗╚██████╔╝██████╔╝███████╗',
' ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝'
]
COLORS=['#ffdb47','#ffb454','#f48b91','#c58ff0','#7aafff','#5ad6c9','#a9e66d']

class Approval(ModalScreen[bool]):
    CSS='''Approval { align: center middle; background: #120617 80%; } #dialog { width: 82%; height: auto; max-height: 75%; background: #310d31; border: heavy #f5c95b; padding: 2; } #message { margin-bottom: 2; color: #fff0b4; } #buttons { height: 3; align: center middle; } Button { margin: 0 2; }'''
    BINDINGS=[('escape','reject','Reject')]
    def __init__(self,message): super().__init__();self.message=message
    def compose(self):
        with Vertical(id='dialog'):
            yield Static('⚠  APPROVAL REQUIRED',classes='heading')
            yield Static(self.message,id='message')
            with Horizontal(id='buttons'):
                yield Button('Reject',id='reject',variant='error')
                yield Button('Approve',id='approve',variant='success')
    def on_button_pressed(self,event):self.dismiss(event.button.id=='approve')
    def action_reject(self):self.dismiss(False)

class CodeUI(App):
    CSS='''Screen { background: #21051e; color: #f7e8f4; } #banner { height: 8; padding: 0 1; background: #300a2b; overflow-x: auto; } #info { height: 3; padding: 1 2; color: #ffe066; } #log { border: round #ad6cc4; background: #230720; padding: 1 2; } #prompt { dock: bottom; margin: 1 1; border: round #ffe066; background: #320c2e; } Footer { background: #3c1036; }'''
    BINDINGS=[('ctrl+q','quit','Quit'),('ctrl+l','clear','Clear'),('ctrl+c','cancel','Cancel agent')]
    def __init__(self,workspace='.',model='qwen2.5-coder:1.5b',host='http://127.0.0.1:11434',approval=None):
        super().__init__();self.agent=Agent(Workspace(workspace),model,host)
        if approval:self.agent.ws.settings.set('approval',approval)
        self.agent.ws.approve=lambda message:self.agent.ws.policy.decide(message,lambda:self._approve(message))
        self.agent.ws.preview=self._preview
    def compose(self)->ComposeResult:
        yield Header(show_clock=True)
        yield Static('',id='banner')
        yield Static('',id='info')
        yield RichLog(id='log',wrap=True,highlight=True,markup=False)
        yield Input(placeholder='❯ Ask to build, debug, refactor, test, or search...',id='prompt')
        yield Footer()
    def on_mount(self):
        t=Text()
        for i,line in enumerate(BANNER):
            for j,ch in enumerate(line):t.append(ch,style=COLORS[(j//12+i)%len(COLORS)])
            t.append('\n')
        self.query_one('#banner',Static).update(t)
        self._status()
        self.query_one('#log',RichLog).write('OLLAMA CODE • Live agent • File and command approvals enabled\nType /help for commands. Ctrl+C cancels agent execution.')
        self.query_one('#prompt',Input).focus()
    def _status(self):self.query_one('#info',Static).update(f'◆ {self.agent.model}    ◇ {self.agent.ws.root}    ◆ Approval: {self.agent.ws.settings.values["approval"]}')
    def _write(self,message):self.query_one('#log',RichLog).write(message)
    def _preview(self,path,diff):self.call_from_thread(self._write,f'\nPROPOSED: {path}\n{diff[:12000]}')
    def _approve(self,message):
        import concurrent.futures
        answer=concurrent.futures.Future()
        def show():self.push_screen(Approval(message),lambda result:answer.set_result(bool(result)))
        self.call_from_thread(show)
        return answer.result()
    def action_clear(self):self.query_one('#log',RichLog).clear()
    def action_cancel(self):self.agent.cancel.set();self._write('Cancellation requested.')
    def on_input_submitted(self,event:Input.Submitted):
        prompt=event.value.strip();event.input.value=''
        if not prompt:return
        if prompt.startswith('/model '):self.agent.model=prompt[7:].strip();self._status();return
        if prompt=='/models':self.list_models();return
        if prompt=='/settings':self._write(str(self.agent.ws.settings.values));return
        if prompt.startswith('/approval '):
            try:self.agent.ws.settings.set('approval',prompt.split(' ',1)[1]);self._status();self._write('Approval policy updated')
            except ValueError as e:self._write(str(e))
            return
        if prompt=='/vscode':
            from .vscode import install_workspace_config
            self._write(install_workspace_config(self.agent.ws.root,self.agent.ws.approve));return
        if prompt=='/clear':self.action_clear();self.agent.history=self.agent.history[:1];return
        if prompt=='/help':self._write('/settings · /approval ask|edits|all · /vscode · /models · /model NAME · /files · /search TEXT · /clear · /quit');return
        if prompt=='/files':self._write(self.agent.ws.list_files());return
        if prompt.startswith('/search '):self._write(self.agent.ws.search_files(prompt[8:]));return
        if prompt in ('/quit','/exit'):self.exit();return
        self._write(Text('❯ '+prompt,style='bold #ffe066'))
        self.run_agent(prompt)
    @work(thread=True,exclusive=True)
    def list_models(self):
        try:self.call_from_thread(self._write,'\n'.join(self.agent.models()) or 'No models found')
        except Exception as e:self.call_from_thread(self._write,str(e))
    @work(thread=True,exclusive=True)
    def run_agent(self,prompt):
        try:self.agent.ask(prompt,emit=lambda chunk:self.call_from_thread(self._write,chunk))
        except Exception as e:self.call_from_thread(self._write,f'Agent error: {e}')

def run(workspace,model,host,approval=None):CodeUI(workspace,model,host,approval).run()
