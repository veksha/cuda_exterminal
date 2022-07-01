SHELL_WIN = 'cmd.exe'
SHELL_UNIX = '/bin/bash'
TERM = "xterm-256color"

DEBUG = 0
DEBUG_FEED = 0
DEBUG_READ = 0

import os
import sys
from time import sleep
from subprocess import Popen
from threading import Thread, Lock

from cudatext import *
import cudatext_keys as keys

IS_WIN = os.name=='nt'
ENC = 'utf8'

from .memoscreen import MemoScreen, DebugScreen, ctrl, colmap
if IS_WIN:
    from .conpty.conpty import ConPty
else:
    import pty, array, termios, fcntl

opt_colors = False
opt_floating = False

def str_to_bool(s): return s=='1'
def bool_to_str(v): return '1' if v else '0'


ini = os.path.join(app_path(APP_DIR_SETTINGS), 'cuda_example_terminal.ini')
fn_icon = os.path.join(os.path.dirname(__file__), 'terminal.png')

class Command:
    def __init__(self):
        self.load_ops()

        self.visible_columns = 0
        self.visible_lines = 0
        self.shell = None

        if DEBUG:
            self.dbg_pos = 0
#            self.dbg_data = '\x1b[?2004h\x1b]0;lubuntu@lubuntu2204: ~/.config/cudatext/py/cuda_example_terminal\x07\x1b[01;32mlubuntu@lubuntu2204\x1b[00m:\x1b[01;34m~/.config/cudatext/py/cuda_example_terminal\x1b[00m$ env\r\n\x1b[?2004l\rSHELL=/bin/bash\r\nQT_ACCESSIBILITY=1\r\nXDG_CONFIG_DIRS=/etc/xdg/xdg-Lubuntu:/etc/xdg:/etc:/usr/share\r\n'
            #self.dbg_data = '\x1b[1;1H\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\x1b[1;205H\x1b[?2004l\x1b[?1006l\x1b[?1002l\x1b[?1001r\x1b[?1l\x1b>\x1b[18;1H\x1b(B\x1b[m\x1b[39;49m\r\x1b[K\r\x1b[?1049l\x1b[23;0;0t\x1b[39;49m\r\n\x1b[?2004h\x1b]0;lubuntu@lubuntu2204: ~/.config/cudatext/py/cuda_example_terminal\x07\x1b[01;32mlubuntu@lubuntu2204\x1b[00m:\x1b[01;34m~/.config/cudatext/py/cuda_example_terminal\x1b[00m$ '
            self.dbg_data = '\x1b[1;205H\x1b[?2004l\x1b[?1006l\x1b[?1002l\x1b[?1001r\x1b[?1l\x1b>\x1b[18;1H\x1b(B\x1b[m\x1b[39;49m\r\x1b[K\r\x1b[?1049l\x1b[23;0;0t\x1b[39;49m\r\n\x1b[?2004h\x1b]0;lubuntu@lubuntu2204: ~/.config/cudatext/py/cuda_example_terminal\x07\x1b[01;32mlubuntu@lubuntu2204\x1b[00m:\x1b[01;34m~/.config/cudatext/py/cuda_example_terminal\x1b[00m$ '

        h = dlg_proc(0, DLG_CREATE)
        dlg_proc(h, DLG_PROP_SET, prop={
            'name':'form','border': DBORDER_SIZE,'w': self.window_width,'h': self.window_height,
            'cap':'Console',
            'topmost': True,
            'keypreview': True,
            'on_key_press': self.form_key_press,
            'on_key_down': self.form_key_down,
            'on_resize': self.form_resize,
            'on_close': self.form_close,
        })
        n = dlg_proc(h, DLG_CTL_ADD, 'editor')
        dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={
            'name': 'memo',
            'a_r': ('', ']'), 'a_b': ('', ']'),
            'font_size': 11,
            'on_click': self.memo_on_click,
            'on_click_link': self.memo_on_click_link,
        })

        self.h_dlg = h
        self.memo = Editor(dlg_proc(h, DLG_CTL_HANDLE, index=n))

#        self.memo.set_prop(PROP_WRAP, WRAP_ON_WINDOW)
        self.memo.set_prop(PROP_RO, True)
        self.memo.set_prop(PROP_CARET_VIRTUAL, True)
        self.memo.set_prop(PROP_GUTTER_ALL, False)
#        self.memo.set_prop(PROP_GUTTER_STATES, False)
        self.memo.set_prop(PROP_MINIMAP, False)
        self.memo.set_prop(PROP_MICROMAP, False)
#        self.memo.set_prop(PROP_HILITE_CUR_LINE, True)
        self.memo.set_prop(PROP_CARET_STOP_UNFOCUSED, True)
        self.memo.set_prop(PROP_SCROLLSTYLE_HORZ, SCROLLSTYLE_HIDE)


        self.memo.set_prop(PROP_CARET_VIEW, (-100, 3, False))
        self.memo.set_prop(PROP_CARET_VIEW_RO, self.memo.get_prop(PROP_CARET_VIEW))

        self.memo.set_prop(PROP_THEMED, False)
        self.memo.set_prop(PROP_COLOR, (COLOR_ID_TextFont, colmap['foreground']))
        self.memo.set_prop(PROP_COLOR, (COLOR_ID_TextBg,   colmap['background']))
        #if not opt_colors:
            #self.memo.action(EDACTION_APPLY_THEME)

    def load_ops(self):
        try:
            self.window_width =  int(ini_read(ini, 'op', 'window_width', '1400'))
            self.window_height = int(ini_read(ini, 'op', 'window_height', '800'))
        except:
            pass
        global opt_colors
        global opt_floating
        opt_colors   = str_to_bool(ini_read(ini, 'op', 'colors',   '0'))
        opt_floating = str_to_bool(ini_read(ini, 'op', 'floating', '0'))

    def save_ops(self, only_size=False):
        if opt_floating:
            ini_write(ini, 'op', 'window_width', str(self.window_width))
            ini_write(ini, 'op', 'window_height', str(self.window_height))
        if only_size:
            return
        ini_write(ini, 'op', 'colors',   bool_to_str(opt_colors))
        ini_write(ini, 'op', 'floating', bool_to_str(opt_floating))

    def config(self):
        self.save_ops()
        file_open(ini)

    def on_exit(self, ed_self):
        print('exit')
        self.save_ops(only_size=True)

    def open(self):
        timer_proc(TIMER_START, self.timer_update, 20, tag='')

        if opt_floating:
            dlg_proc(self.h_dlg, DLG_SHOW_NONMODAL)
        else:
            #add as dock panel
            app_proc(PROC_BOTTOMPANEL_ADD_DIALOG, ('Example Terminal', self.h_dlg, fn_icon))
            app_proc(PROC_BOTTOMPANEL_ACTIVATE, 'Example Terminal')

    def on_state(self, ed, state):
        return
#        if self.h_dlg and state == APPSTATE_THEME_UI:

    def memo_on_click(self, id_dlg, id_ctl, data='', info=''):
        self.screen.refresh_caret()
        self.memo.action(EDACTION_UPDATE)

    def memo_on_click_link(self, id_dlg, id_ctl, data='', info=''):
        import webbrowser
        webbrowser.open(data) # crash?!

    def debug(self, *args, **kwargs):
        print('Unrecognized sequence:',*args)

    def create_screen(self):
        d = DebugScreen(sys.stdout)
        self.dstream = pyte.Stream()
        self.dstream.attach(d)

        self.screen_height = self.visible_lines
#        self.screen_height = 25
        self.screen_width = self.visible_columns-3

        self.screen = MemoScreen(self.memo, self.screen_width, self.screen_height, self.h_dlg, colored=opt_colors)
        self.screen.write_process_input = self.write
        if DEBUG:
            self.screen.debug = self.debug

#        self.screen.set_mode(pyte.modes.LNM)

        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

    def execute_shell(self):
        cwd = os.path.dirname(ed.get_filename())
        if not os.path.isdir(cwd):
            cwd = None
        all_env = dict(os.environ)

        env = {"TERM":TERM}
        all_env.update(env)

        try:
            if IS_WIN:
                SHELL = SHELL_WIN
                self.shell = ConPty(SHELL, self.screen_width, self.screen_height, env=all_env, cwd=cwd)
            else:
                SHELL = SHELL_UNIX
                all_env.update({
                    #"COLORTERM":"truecolor",
                })
                self.master, self.slave = pty.openpty()
                self.shell = Popen([SHELL], preexec_fn=os.setsid, stdin=self.slave, stdout=self.slave, stderr=self.slave,
                                    universal_newlines=True, env=all_env, cwd=cwd)
                self.send_winsize(self.screen_height, self.screen_width)

        except Exception as e:
            print('NOTE:',e,SHELL)
            self.memo.set_prop(PROP_RO, False)
            self.memo.set_text_all('{}\n{}'.format(e,SHELL))
            self.memo.set_prop(PROP_RO, True)
            return False

        self.stop_t = False
        self.btext = b''
        self.btextchanged = False
        self.block = Lock()
        self.block.acquire()

        self.CtlTh = ControlTh(self)
        self.CtlTh.start()
        return True

    def timer_update(self, tag='', info=''):
        if self.shell is None:
            self.visible_columns = self.memo.get_prop(PROP_VISIBLE_COLUMNS)
            self.visible_lines   = self.memo.get_prop(PROP_VISIBLE_LINES)
            if self.visible_columns > 0 and self.visible_lines > 0:
                self.create_screen()
                if DEBUG:
                    timer_proc(TIMER_STOP, self.timer_update, 20, tag='')
                    return
                else:
                    if not self.execute_shell():
                        timer_proc(TIMER_STOP, self.timer_update, 20, tag='')
                        return
            # return until memo will initialize its PROP_VISIBLE_LINES/PROP_VISIBLE_COLUMNS props
            else: return

        self.btextchanged = False
        if self.block.locked():
            self.block.release()
        sleep(0.01)
        self.block.acquire()

        if self.btextchanged:
            self.stream.feed(self.btext.decode(ENC, errors='replace'))

            self.screen.memo_update()
            self.screen.refresh_caret()

            self.memo.set_prop(PROP_SCROLL_VERT, self.screen.top-1)

            if not IS_WIN: # on Linux memo is not immediately repainted for some reason
                #self.memo.action(EDACTION_UPDATE) # doesn't repaint
                #app_idle() # does repaint but is heavy
                pass

            pass;               DEBUG_FEED and self.dstream.feed(self.btext.decode(ENC, errors='replace'))
            self.btext = b''

    def write(self, text):
        if self.shell:
            if IS_WIN:
                self.shell.write(text)
    #            print('writing:',bytes(text,'utf8'))
            else:
                os.write(self.master, bytes(text,'utf8'))

    def form_key_press(self, id_dlg, id_ctl, data='', info=''):
        key = id_ctl

        if DEBUG:
            STEP = 0
            if 0:pass
            elif key == ord('1'): STEP = 1
            elif key == ord('2'): STEP = 25
            elif key == ord('3'): STEP = 75
            elif key == ord('4'): STEP = 999999

            p = self.dbg_pos
            if p < len(self.dbg_data):
                print('feeding:',self.dbg_data[p:p+STEP])
                self.stream.feed(self.dbg_data[p:p+STEP])
                pass;               DEBUG_FEED and self.dstream.feed(self.dbg_data[p:p+STEP])
                self.screen.memo_update()
                self.screen.refresh_caret()
                p += STEP
                self.dbg_pos = min(p, len(self.dbg_data))
                dlg_proc(self.h_dlg, DLG_PROP_SET, name='form', prop={'cap': str(self.dbg_pos)})
            return False
        else:
#            print('key_press',key)
            self.write(chr(key))
        return True


    def form_key_down(self, id_dlg, id_ctl, data='', info=''):
        key = id_ctl
        if DEBUG:
            pass
#            print(key)
        else:
            if 0:pass
            elif data == 'c':
                if 0:pass # ctrl + key
                elif 65 <= key <= 90:
                    self.write(chr(key-64))
                    return False
                elif key == keys.VK_BACKSPACE:
                    self.write(ctrl.BS)
                    return False
                elif key == keys.VK_HOME:
                    self.write(ctrl.ESC+'[1;5H')
                    return False
                elif key == keys.VK_END:
                    self.write(ctrl.ESC+'[1;5F')
                    return False
                elif key == 191: # '/' slash key
                    self.write('\x1F') # Unit Separator
                    return False
    #            elif 47+144 <= key <= 47+144: # 47+144 = 191 '/' slash key
    #                print('ctrl+key-144',key-144)
    #                self.write(chr(key-144-16))
    #                return False
            elif data == 'a':
                if 0:pass # alt + key
                elif 65 <= key <= 90:
                    self.write(ctrl.ESC+chr(key))
                    return False
                elif 92+128 <= key <= 92+128:
                    self.write(ctrl.ESC+chr(key-128))
                    return False
                elif 43+144 <= key <= 90+144:
                    self.write(ctrl.ESC+chr(key-144))
                    return False
                elif key == keys.VK_BACKSPACE:
                    self.write(ctrl.ESC+ctrl.BS)
                    return False
            elif data == 's':
                if 0:pass # shift + key
                elif key == keys.VK_INSERT:
                    self.write(app_proc(PROC_GET_CLIP, ''))
                    return False
            elif len(data) == 2 and 'c' in data and 'a' in data:
                if 0:pass # ctrl + alt + key
                elif key == keys.VK_PAGEUP:
                    self.write(ctrl.ESC+'[5;7~')
                    return False

            elif data == '': # # key without combination, this must be the last
                if 0:pass
                elif key == keys.VK_ESCAPE:
                    self.write(ctrl.ESC)
                    return False
                elif key == keys.VK_ENTER:
                    self.write('\r')
                elif key == keys.VK_TAB:
                    self.write('\t')
                elif key == keys.VK_DELETE:
                    self.write(ctrl.ESC+'[3~')
                elif key == keys.VK_BACKSPACE:
                    self.write(ctrl.DEL)
                elif key == keys.VK_UP:
                    self.write(ctrl.ESC+'OA')
                    return False
                elif key == keys.VK_DOWN:
    #                print('markers',len(self.memo.attr(MARKERS_GET)))
    #                print('markers',self.memo.attr(MARKERS_GET))
                    self.write(ctrl.ESC+'OB')
                    return False
                elif key == keys.VK_RIGHT:
                    self.write(ctrl.ESC+'OC')
                    return False
                elif key == keys.VK_LEFT:
                    self.write(ctrl.ESC+'OD')
                    return False
                elif key == keys.VK_PAGEUP:
                    self.write(ctrl.ESC+'[5~')
                    return False
                elif key == keys.VK_PAGEDOWN:
                    self.write(ctrl.ESC+'[6~')
                    return False
                elif key == keys.VK_HOME:
                    self.write(ctrl.ESC+'OH')
                    return False
                elif key == keys.VK_END:
                    self.write(ctrl.ESC+'OF')
                    return False
                elif key == keys.VK_F1:
                    self.write(ctrl.ESC+'OP')
                    return False
                elif key == keys.VK_F2:
                    self.write(ctrl.ESC+'OQ')
                    return False
                elif key == keys.VK_F3:
                    self.write(ctrl.ESC+'OR')
                    return False
                elif key == keys.VK_F4:
                    self.write(ctrl.ESC+'OS')
                    return False
                elif key == keys.VK_F5:
                    self.write(ctrl.ESC+'[15~')
                    return False
                elif key == keys.VK_F6:
                    self.write(ctrl.ESC+'[17~')
                    return False
                elif key == keys.VK_F7:
                    self.write(ctrl.ESC+'[18~')
                    return False
                elif key == keys.VK_F8:
                    self.write(ctrl.ESC+'[19~')
                    return False
                elif key == keys.VK_F9:
                    self.write(ctrl.ESC+'[20~')
                    return False
                elif key == keys.VK_F10:
                    self.write(ctrl.ESC+'[21~')
                    return False
                elif key == keys.VK_F11:
                    self.write(ctrl.ESC+'[23~')
                    return False
                elif key == keys.VK_F12:
                    self.write(ctrl.ESC+'[24~')
                    return False
        return True

    def send_winsize(self, h, w):
        if IS_WIN:
            self.write("\x1b[8;{};{}t".format(h, w))
        else:
            winsize = array.array("h", [h,w,0,0,])
            # Send winsize to target terminal.
            fcntl.ioctl(self.master, termios.TIOCSWINSZ, winsize)

    def terminal_resize(self, tag='', info=''):
        self.visible_columns = self.memo.get_prop(PROP_VISIBLE_COLUMNS)
        self.visible_lines   = self.memo.get_prop(PROP_VISIBLE_LINES)
        if self.visible_columns > 0 and self.visible_lines > 0:
            self.screen.resize(self.visible_lines,self.visible_columns-3)
            self.screen.ensure_vbounds()
            self.send_winsize(self.visible_lines, self.visible_columns-3)

    def form_resize(self, ag, aid='', data=''):
        prop = dlg_proc(self.h_dlg, DLG_PROP_GET)
        if prop:
#            x = prop['x']
#            y = prop['y']
            self.window_width  = prop['w']
            self.window_height = prop['h']

        # delay terminal_resize because memo is not resized yet
        timer_proc(TIMER_START_ONE, self.terminal_resize, 200)

    def form_close(self, id_dlg, id_ctl, data='', info=''):
        pass
#        timer_proc(TIMER_STOP, self.timer_update, 20, tag='')
#        self.stop_t = True


class ControlTh(Thread):
    def __init__(self, Cmd):
        Thread.__init__(self, daemon=True)
        self.Cmd = Cmd

    def add_buf(self, s):
        self.Cmd.block.acquire()

        self.Cmd.btextchanged = True
        self.Cmd.btext += s

        self.Cmd.block.release()

    def run(self):
        while True:
            if self.Cmd.stop_t: return

            if IS_WIN:
                s = self.Cmd.shell.read()
            else:
                s = os.read(self.Cmd.master,2048)

            if s:
                pass;    DEBUG_READ and print(s)
                self.add_buf(s)
