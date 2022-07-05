import os
import sys
from cudatext import *
import cudatext_keys as keys
import cudatext_cmd as cmds

from .terminal import Terminal

IS_WIN = os.name=='nt'
ENC = 'utf8'

TERMINALS_LIMIT = 4

opt_colors = False
#opt_floating = False
opt_esc_focuses_editor = False

def str_to_bool(s): return s=='1'
def bool_to_str(v): return '1' if v else '0'


#fn_icon = os.path.join(os.path.dirname(__file__), 'terminal.png')
fn_icon = os.path.join(os.path.dirname(__file__), 'icons8-console-30.png')
ini = os.path.join(app_path(APP_DIR_SETTINGS), 'plugins.ini')
section = 'exterminal'


class Command:
    def __init__(self):
        self.load_ops()
        self.terminal_id = 0
        self.terminals = []

    def load_ops(self):
#        try:
#            self.window_width =  int(ini_read(ini, section, 'window_width', '1400'))
#            self.window_height = int(ini_read(ini, section, 'window_height', '800'))
#        except:
#            pass
        global opt_colors
#        global opt_floating
        global opt_esc_focuses_editor
        opt_colors   = str_to_bool(ini_read(ini, section, 'colors',   '0'))
#        opt_floating = str_to_bool(ini_read(ini, section, 'floating', '0'))
        opt_esc_focuses_editor = str_to_bool(ini_read(ini, section, 'esc_focuses_editor', '0'))

    def save_ops(self, only_size=False):
#        if opt_floating:
#            ini_write(ini, section, 'window_width', str(self.window_width))
#            ini_write(ini, section, 'window_height', str(self.window_height))
#        if only_size:
#            return
        ini_write(ini, section, 'colors',   bool_to_str(opt_colors))
#        ini_write(ini, section, 'floating', bool_to_str(opt_floating))
        ini_write(ini, section, 'esc_focuses_editor', bool_to_str(opt_esc_focuses_editor))

    def config(self):
        self.save_ops()
        file_open(ini)

    def on_exit(self, ed_self):
        pass
        #self.save_ops(only_size=True)

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
#        t = Terminal("ExTerminal {}".format(self.terminal_id), self.window_width, self.window_height,
#            opt_floating, opt_esc_focuses_editor, fn_icon, opt_colors)
        t = Terminal("ExTerminal {}".format(self.terminal_id), 0, 0, 0, opt_esc_focuses_editor, fn_icon, opt_colors)
        t.open()
        if focus:
            t.memo.focus()
        self.terminals.append(t)

    def on_state(self, ed, state):
        return
#        if self.h_dlg and state == APPSTATE_THEME_UI:


