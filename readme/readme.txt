Plugin for CudaText.

Advantages over Terminal+ plugin:

- ExTerminal tries to mimic real interactive terminal behaviour.
  That means that you can use apps like nano/vim/htop/python inside it.

To configure, call menu item "Options / Settings-plugins / ExTerminal / Config".
This will open plugins.ini config file, scroll to [exterminal] section.
Options that are boolean must have value 0 or 1.

Commands:
- New terminal
- Close all terminals

Options:
- shell_*: shell to execute, for example - "bash" or "cmd.exe".
- colors: display colors in terminal. Working slow as for now. Disabled by default.
- esc_focuses_editor: focus editor by pressing ESC key instead of sending it to terminal.
    Disabled by default.
    Hint: Ctrl+[ key sends ESC code to the terminal, you can use it instead of ESC key.


About
-----
Author: veksha (https://github.com/veksha)
License: MIT
