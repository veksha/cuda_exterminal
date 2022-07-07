# ExTerminal

Advantages over Terminal+ plugin:
 - `ExTerminal` tries to mimic real interactive terminal behaviour.
 That means that you can use apps like nano/vim/htop/python inside it.
 - ...


# Commands:
- New terminal
- Close all terminals
- Run selection from editor
- Run current file
- Toggle focus terminal/editor

# Configuration file

Menu "Options / Settings-plugins / ExTerminal / Config", \[exterminal\] section.

Setting               | Possible values            | Description
----------------------|----------------------------|----------------------------
shell_*               | string                     | shell to execute, for example - "bash" or "cmd.exe"
colors                | 0,1                        | enable terminal colors. (slows down terminal. will be optimized in the future.)
esc_focuses_editor    | 0,1                        | focus editor by pressing ESC key instead of sending it to terminal. Disabled by default. <br> Hint: Ctrl+[ key sends ESC code to the terminal, you can use it instead of ESC key.

