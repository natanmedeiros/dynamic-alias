import shlex
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from .resolver import DataResolver
from .executor import CommandExecutor
from .completer import DynamicAliasCompleter

class InteractiveShell:
    def __init__(self, resolver: DataResolver, executor: CommandExecutor):
        self.resolver = resolver
        self.executor = executor

    def run(self):
        completer = DynamicAliasCompleter(self.resolver, self.executor)
        
        style = Style.from_dict({
            'completion-menu.completion': 'bg:#008888 #ffffff',
            'completion-menu.completion.current': 'bg:#00aaaa #000000',
            'scrollbar.background': 'bg:#88aaaa',
            'scrollbar.button': 'bg:#222222',
        })

        bindings = KeyBindings()

        @bindings.add('enter')
        def _(event):
            b = event.current_buffer
            if b.complete_state:
                if b.complete_state.current_completion:
                    b.apply_completion(b.complete_state.current_completion)
                elif b.complete_state.completions:
                    b.apply_completion(b.complete_state.completions[0])
            else:
                b.validate_and_handle()
        
        session = PromptSession(
            completer=completer,
            style=style,
            complete_while_typing=True,
            key_bindings=bindings
        )

        while True:
            try:
                text = session.prompt('dya > ', placeholder=HTML('<style color="gray">(tab for menu)</style>'))
                text = text.strip()
                if not text:
                    continue
                if text in ['exit', 'quit']:
                    break
                    
                import shlex
                try:
                    parts = shlex.split(text)
                except ValueError:
                    print("Error: Invalid quotes")
                    continue
                    
                result = self.executor.find_command(parts)
                
                if result:
                    cmd, vars = result
                    self.executor.execute(cmd, vars)
                    self.resolver.cache.save()
                else:
                    print("Invalid command.")

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")
