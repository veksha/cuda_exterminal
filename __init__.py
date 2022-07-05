import os
import sys
from cudatext import *
import cudatext_keys as keys
import cudatext_cmd as cmds

from .terminal import Terminal

TERMINALS_LIMIT = 4

SHELL_UNIX = 'bash'
SHELL_MAC = 'bash'
SHELL_WIN = 'cmd.exe'

IS_WIN = os.name=='nt'
IS_MAC = sys.platform=='darwin'

opt_colors = False
opt_esc_focuses_editor = False

def str_to_bool(s): return s=='1'
def bool_to_str(v): return '1' if v else '0'


fn_icon = os.path.join(os.path.dirname(__file__), 'icons8-console-30.png')
ini = os.path.join(app_path(APP_DIR_SETTINGS), 'plugins.ini')
section = 'exterminal'


class Command:
    def __init__(self):
        self.load_ops()
        self.terminal_id = 0
        self.terminals = []

    def load_ops(self):
        self.shell_unix = ini_read(ini, section, 'shell_unix', SHELL_UNIX)
        self.shell_mac = ini_read(ini, section, 'shell_macos', SHELL_MAC)
        self.shell_win = ini_read(ini, section, 'shell_windows', SHELL_WIN)
        if IS_WIN: self.shell_str = self.shell_win
        else: self.shell_str = self.shell_mac if IS_MAC else self.shell_unix

        global opt_colors
        global opt_esc_focuses_editor
        opt_colors   = str_to_bool(ini_read(ini, section, 'colors',   '0'))
        opt_esc_focuses_editor = str_to_bool(ini_read(ini, section, 'esc_focuses_editor', '0'))

    def save_ops(self, only_size=False):
        ini_write(ini, section, 'shell_windows', self.shell_win)
        ini_write(ini, section, 'shell_unix', self.shell_unix)
        ini_write(ini, section, 'shell_macos', self.shell_mac)
        ini_write(ini, section, 'colors',   bool_to_str(opt_colors))
        ini_write(ini, section, 'esc_focuses_editor', bool_to_str(opt_esc_focuses_editor))

    def config(self):
        self.save_ops()
        file_open(ini)

    def open(self):
        self.new_terminal_tab()

    def new(self):
        self.new_terminal_tab(focus=True)

    def close_all(self):
        for t in self.terminals:
            t.close()
            del t
        self.terminals = []
        ed.cmd(cmds.cmd_ShowPanelConsole)
        ed.focus()

    def new_terminal_tab(self,focus=False):
        if self.terminal_id >= TERMINALS_LIMIT:
            msg_box("More then {} terminals is not supported yet.".format(TERMINALS_LIMIT), MB_OK+MB_ICONINFO)
            return

        self.terminal_id += 1
        t = Terminal("ExTerminal {}".format(self.terminal_id), self.shell_str, opt_esc_focuses_editor, fn_icon, opt_colors)
        t.open()
        if focus:
            t.memo.focus()
        self.terminals.append(t)
