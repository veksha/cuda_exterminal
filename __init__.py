#import sys
#sys.path.insert(0,'F:\\MySSDPrograms\\PyCharm 2020.1\\plugins\\python\\helpers\\pydev')
#
#import pydevd_pycharm
#try:
#    pydevd_pycharm.settrace('localhost', port=1530, stdoutToServer=True, stderrToServer=True)
#except: pass

import os
import sys
from time import sleep, time
from subprocess import Popen, PIPE, STDOUT, call
from cudatext import *
import cudatext_cmd as cmds
import cudatext_keys as keys
from threading import Thread, Lock

from .pyte import *
from functools import partial

ENC = 'cp866' # or utf8
MAX_BUFFER = 100*1000

DEBUG = 0

class Command:
    def run(self):
        h = dlg_proc(0, DLG_CREATE)
        dlg_proc(h, DLG_PROP_SET, prop={'border': DBORDER_SIZE,'w': 800,'h': 600, 'keypreview': True,
        'on_key_press': self.form_key_press,
        'on_key_down': self.form_key_down,
        })
        n = dlg_proc(h, DLG_CTL_ADD, 'editor')
        dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={'name': 'memo','a_r': ('', ']'), 'a_b': ('', ']'), 'font_size': 11})

        self.memo = Editor(dlg_proc(h, DLG_CTL_HANDLE, index=n))
#        self.memo.set_prop(PROP_WRAP, WRAP_ON_WINDOW) # 1. this line is needed to reproduce

        self.memo.set_prop(PROP_RO, True)
        self.memo.set_prop(PROP_CARET_VIRTUAL, False)
        self.memo.set_prop(PROP_MINIMAP, False)

        if DEBUG:
            d = DebugScreen(sys.stdout)
            self.dstream = pyte.Stream()
            self.dstream.attach(d)
    #        self.dstream.feed('\n')

        self.screen = MemoScreen(self.memo, 80, 9000)
        self.screen.set_mode(pyte.modes.LNM)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

        self.p = Popen(
            os.path.expandvars('cmd.exe'), #TODO Windows: use shell arguments
            stdin = PIPE,
            stdout = PIPE,
            stderr = STDOUT,
            shell = True,
            bufsize = 0,
            env = os.environ,
            cwd = os.path.dirname(ed.get_filename()),
            )

        self.stop_t = False
        self.btext = b''
        self.btextchanged = False
        self.block = Lock()
        self.block.acquire()
        self.CtlTh = ControlTh(self)
        self.CtlTh.start()
        timer_proc(TIMER_START, self.timer_update, 200, tag='')

        dlg_proc(h, DLG_SHOW_NONMODAL)

    def timer_update(self, tag='', info=''):
        self.btextchanged = False
        if self.block.locked():
            self.block.release()
        sleep(0.03)
        self.block.acquire()
        if self.btextchanged:
            self.stream.feed(self.btext.decode(ENC))
            pass;               DEBUG and self.dstream.feed(self.btext.decode(ENC))
            self.btext = b''

    def _exec(self, s):
        if self.p:
            s = s + '\n'
            self.p.stdin.write((s).encode(ENC))
            self.p.stdin.flush()

    def form_key_press(self, id_dlg, id_ctl, data='', info=''):
        key = id_ctl
        self.screen.command_line += chr(key)
        self.stream.feed(chr(key))

    def form_key_down(self, id_dlg, id_ctl, data='', info=''):
        key = id_ctl
        if 0:pass
        elif key == keys.VK_ENTER:
#            self.stream.feed(pyte.control.CR+pyte.control.LF)
#            self._exec('dir')
            self._exec(self.screen.command_line)
            self.screen.command_line = ''
        elif key == keys.VK_BACKSPACE:
            self.stream.feed(pyte.control.BS)
#        elif key == keys.VK_TAB:
#            self.stream.feed(pyte.control.HT)


class MemoScreen(Screen):
    def __init__(self, memo, columns, lines):
        super(MemoScreen, self).__init__(columns, lines)

        self.memo = memo
        self.no_ro = partial(self.memo.set_prop, PROP_RO, False)
        self.ro = partial(self.memo.set_prop, PROP_RO, True)

        self.command_line = ''

    def cl_offset(self):
        carets = self.memo.get_carets()
        x, y, _, _ = carets[0]
        return self.memo.convert(CONVERT_CARET_TO_OFFSET, x, y)

    def set_title(self, param):
        super(MemoScreen, self).set_title(param)
        print('TITLE:',param)

    def refresh_caret(self):
        self.memo.set_caret(self.cursor.x, self.cursor.y)

    def backspace(self):
        super(MemoScreen, self).backspace()
        self.refresh_caret()

    def carriage_return(self):
        super(MemoScreen, self).carriage_return()
        self.refresh_caret()
#        print('cr',self.cursor.x,self.cursor.y)

    def linefeed(self):
        self.no_ro()
        self.memo.insert(len(self.buffer[self.cursor.y]), self.cursor.y, '\n')
        self.ro()
        super(MemoScreen, self).linefeed()
        self.refresh_caret()
#        print('lf',self.cursor.x,self.cursor.y)
#        if len(self.buffer) == 24:
#            raise NotImplementedError

    def draw(self, data):
        self.no_ro()
        self.memo.insert(self.cursor.x, self.cursor.y, data)
        self.ro()
        super(MemoScreen, self).draw(data)
        self.refresh_caret()
#        print('draw',self.cursor.x,self.cursor.y)


class ControlTh(Thread):
    def __init__(self, Cmd):
        Thread.__init__(self, daemon = True)
        self.Cmd = Cmd

    def add_buf(self, s, clear):
        self.Cmd.block.acquire()

        ### main thread is stopped here
        self.Cmd.btextchanged = True
        # limit the buffer size!
        self.Cmd.btext = (self.Cmd.btext+s)[-MAX_BUFFER:]
        if clear:

            if self.Cmd.ch_out and self.Cmd.ch_pid > 0:
                try:
                    os.waitpid(self.Cmd.ch_pid, os.WNOHANG) # check if current child terminal process exists
                except ChildProcessError:
                    # child process is gone, close stuff  (terminal exited by itself)
                    ch_out = self.Cmd.ch_out
                    self.Cmd.ch_out = None
                    self.Cmd.ch_pid = -1

                    if ch_out:
                        ch_out.close()
                else:
                    # child exists, continue reading  (shell process got restarted by Terminal())
                    pass

            self.Cmd.p=None
        self.Cmd.block.release()

    def run(self):
        while True:
            if self.Cmd.stop_t: return
            if not self.Cmd.p:
                sleep(0.5)
                continue
            pp1 = self.Cmd.p.stdout.tell()
            self.Cmd.p.stdout.seek(0, 2)
            pp2 = self.Cmd.p.stdout.tell()
            self.Cmd.p.stdout.seek(pp1)
            if self.Cmd.p.poll() is not None:
                s = MSG_ENDED.encode(ENC)
                self.add_buf(s, True)
            # don't break, shell will be restarted
            elif pp2!=pp1:
                s = self.Cmd.p.stdout.read(pp2-pp1)
                pass;               DEBUG and print('s',s)
                self.add_buf(s, False)
            sleep(0.02)
