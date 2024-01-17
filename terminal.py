TERM = "xterm-256color"

TIMER_INTERVAL = 70

DEBUG = 0
DEBUG_FEED = 0
DEBUG_READ = 0

import os
import sys
from time import perf_counter, sleep
from subprocess import Popen
from threading import Thread, Lock

from cudatext import *
import cudatext_keys as keys
import cudatext_cmd as cmds

from cudax_lib import get_translation
_ = get_translation(__file__)  # I18N


IS_WIN = os.name=='nt'
ENC = 'utf8'

api_ver = app_api_version()

from .memoscreen import MemoScreen, DebugScreen, ctrl, colmap, Stream, plot
if IS_WIN:
    from .conpty.conpty import ConPty
else:
    import pty, array, termios, fcntl

key_map = {
    keys.VK_ENTER: '\r',
    keys.VK_TAB: '\t',
    keys.VK_DELETE: ctrl.ESC+'[3~',
    keys.VK_BACKSPACE: ctrl.DEL,
    keys.VK_UP: ctrl.ESC+'[A',
    keys.VK_DOWN: ctrl.ESC+'[B',
    keys.VK_RIGHT: ctrl.ESC+'[C',
    keys.VK_LEFT: ctrl.ESC+'[D',
    keys.VK_PAGEUP: ctrl.ESC+'[5~',
    keys.VK_PAGEDOWN: ctrl.ESC+'[6~',
    keys.VK_HOME: ctrl.ESC+'OH',
    keys.VK_END: ctrl.ESC+'OF',
    keys.VK_F1: ctrl.ESC+'OP',
    keys.VK_F2: ctrl.ESC+'OQ',
    keys.VK_F3: ctrl.ESC+'OR',
    keys.VK_F4: ctrl.ESC+'OS',
    keys.VK_F5: ctrl.ESC+'[15~',
    keys.VK_F6: ctrl.ESC+'[17~',
    keys.VK_F7: ctrl.ESC+'[18~',
    keys.VK_F8: ctrl.ESC+'[19~',
    keys.VK_F9: ctrl.ESC+'[20~',
    keys.VK_F10: ctrl.ESC+'[21~',
    keys.VK_F11: ctrl.ESC+'[23~',
    keys.VK_F12: ctrl.ESC+'[24~'
}

class Terminal:
    themed = False
    font_size = 11
    def __init__(self, name, shell_str, esc_focuses_editor, fn_icon, colors, show_caption):
        self.name = name
        self.opt_esc_focuses_editor = esc_focuses_editor
        self.fn_icon = fn_icon
        self.opt_colors = colors
        self.opt_show_caption = show_caption

        self.visible_columns = 0
        self.visible_lines = 0
        self.shell = None
        self.screen = None
        self.shell_str = shell_str
        theme_colors = app_proc(PROC_THEME_UI_DICT_GET, '')
        
        self.measured_timer_time = perf_counter()*1000
        self.timer_took_too_long = False
        self.measured_line_time = perf_counter()*1000
        self.time_data = []

        if DEBUG:
            self.dbg_pos = 0
            #self.dbg_data = '\x1b[?2004h\x1b]0;lubuntu@lubuntu2204:'

        h = dlg_proc(0, DLG_CREATE)
        dlg_proc(h, DLG_PROP_SET, prop={
            'name':'form','border': DBORDER_SIZE,
            'cap':_('Console'),
            'keypreview': True,
            'on_key_press': self.form_key_press,
            'on_key_down': self.form_key_down,
            'on_resize': self.form_resize,
            'on_close': self.form_close,
            'on_show': self.form_show,
            'color': theme_colors['TabBg']['color'],
        })
        n = dlg_proc(h, DLG_CTL_ADD, 'label')
        dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={
            'name': 'header',
            'font_size': 10,
            'cap': _('ExTerminal'),
            'align': ALIGN_TOP,
            #'sp_a': 1,
            'sp_l': 3,
            'font_color': theme_colors['TabFont']['color'],
            'vis': self.opt_show_caption,
        })
        n = dlg_proc(h, DLG_CTL_ADD, 'editor')
        dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={
            'name': 'memo',
            'font_size': Terminal.font_size,
            'on_click': self.memo_on_click,
            'on_click_link': self.memo_on_click_link,
            'align': ALIGN_CLIENT,
        })

        self.h_dlg = h
        self.memo = Editor(dlg_proc(h, DLG_CTL_HANDLE, index=n))

        self.memo.set_prop(PROP_UNDO_LIMIT, 0) # disable UNDO info
        #self.memo.set_prop(PROP_WRAP, WRAP_ON_WINDOW)
        self.memo.set_prop(PROP_RO, True)
        self.memo.set_prop(PROP_CARET_VIRTUAL, True)
        #self.memo.set_prop(PROP_GUTTER_ALL, False)
        self.memo.set_prop(PROP_GUTTER_STATES, False)
        self.memo.set_prop(PROP_GUTTER_BM, False)
        self.memo.set_prop(PROP_GUTTER_FOLD, False)
        self.memo.set_prop(PROP_GUTTER_NUM, False)
        self.memo.set_prop(PROP_MINIMAP, False)
        self.memo.set_prop(PROP_MICROMAP, False)
        #self.memo.set_prop(PROP_HILITE_CUR_LINE, True)
        self.memo.set_prop(PROP_CARET_STOP_UNFOCUSED, True)
        self.memo.set_prop(PROP_SCROLLSTYLE_HORZ, SCROLLSTYLE_HIDE)
        self.memo.set_prop(PROP_UNPRINTED_SHOW, False)
        self.memo.set_prop(PROP_MARGIN, 2000)
        
        # new api!
        if api_ver >= '1.0.425':
            self.memo.attr(MARKERS_SET_DUPS, tag=0) # 0 means disallow marker dups
        if api_ver >= '1.0.426':
            self.memo.set_prop(PROP_WHEEL_ZOOMS, False)

        self.memo.set_prop(PROP_CARET_VIEW, (-100, 3, False))
        self.memo.set_prop(PROP_CARET_VIEW_RO, self.memo.get_prop(PROP_CARET_VIEW))

        self.set_theme_colors()

    def set_theme_colors(self):
        self.memo.set_prop(PROP_THEMED, Terminal.themed)
        if Terminal.themed:
            theme_colors = app_proc(PROC_THEME_UI_DICT_GET, '')
            # header color
            dlg_proc(self.h_dlg, DLG_PROP_SET, name='form', prop={ 'color': theme_colors['TabBg']['color'] } )
            dlg_proc(self.h_dlg, DLG_CTL_PROP_SET, name='header', prop={ 'font_color': theme_colors['TabFont']['color'] } )
            # memo color
            theme_textfont = theme_colors[COLOR_ID_TextFont]['color']
            theme_textbg   = theme_colors[COLOR_ID_TextBg]['color']
            colmap['foreground'] = theme_textfont
            colmap['background'] = theme_textbg
            #self.memo.action(EDACTION_APPLY_THEME)
        self.memo.set_prop(PROP_COLOR, (COLOR_ID_TextFont, colmap['foreground']))
        self.memo.set_prop(PROP_COLOR, (COLOR_ID_TextBg,   colmap['background']))
        if self.screen:
            self.screen.dirty = set(range(self.screen.lines))
            self.memo_update()

    def open(self):
        timer_proc(TIMER_START, self.timer_update, TIMER_INTERVAL, tag='')

        app_proc(PROC_BOTTOMPANEL_ADD_DIALOG, (self.name, self.h_dlg, self.fn_icon))
        app_proc(PROC_BOTTOMPANEL_ACTIVATE, self.name)

    def memo_on_click(self, id_dlg, id_ctl, data='', info=''):
        text = self.memo.get_text_sel()
        if text:
            text = '\n'.join([line.rstrip() for line in text.splitlines()])
            app_proc(PROC_SET_CLIP, text)
            msg_status(_("Text was copied to clipboard!"))
        
        self.screen.refresh_caret()
        self.memo.action(EDACTION_UPDATE)

    def memo_on_click_link(self, id_dlg, id_ctl, data='', info=''):
        if IS_WIN:
            Popen(['start', '', data], shell=True)
        else:
            import webbrowser
            webbrowser.open(data)

    def debug(self, *args, **kwargs):
        print(_('Unrecognized sequence:'),*args)

    def create_screen(self):
        d = DebugScreen(sys.stdout)
        self.dstream = Stream()
        self.dstream.attach(d)

        self.screen_height = self.visible_lines
        self.screen_width = self.visible_columns-3

        def draw_callback(text):
            pass
            self.memo_update()
        
        self.screen = MemoScreen(self.memo, self.screen_width, self.screen_height, self.h_dlg, self.opt_colors, draw_callback)
        self.screen.write_process_input = self.write
        if DEBUG:
            self.screen.debug = self.debug

        #self.screen.set_mode(pyte.modes.LNM)

        self.stream = Stream()
        self.stream.attach(self.screen)

    def execute_shell(self):
        cwd = os.path.dirname(ed.get_filename())
        if not os.path.isdir(cwd):
            cwd = None
        all_env = dict(os.environ)

        env = {"TERM":TERM}
        all_env.update(env)

        self.memo.set_prop(PROP_RO, False)
        self.memo.set_text_all('')
        self.memo.set_prop(PROP_RO, True)

        try:
            if IS_WIN:
                self.shell = ConPty(self.shell_str, self.screen_width, self.screen_height, env=all_env, cwd=cwd)
            else:
                all_env.update({
                    #"COLORTERM":"truecolor",
                })
                self.master, self.slave = pty.openpty()
                self.shell = Popen([self.shell_str], preexec_fn=os.setsid, stdin=self.slave, stdout=self.slave, stderr=self.slave,
                                    universal_newlines=True, env=all_env, cwd=cwd)
                self.send_winsize(self.screen_height, self.screen_width)

        except Exception as e:
            print('NOTE:',e,self.shell_str)
            self.memo.set_prop(PROP_RO, False)
            self.memo.set_text_all('{}\n{}'.format(e,self.shell_str))
            self.memo.set_prop(PROP_RO, True)
            self.shell = False # flag "False" means: error while executing shell
            return False

        self.stop_t = False
        self.btext = b''
        self.btextchanged = False
        self.block = Lock()
        self.block.acquire()

        self.CtlTh = ControlTh(self)
        self.CtlTh.start()
        return True

    def memo_update(self):
        self.memo.set_prop(PROP_RO, False)

        markers = [] # list of tuples: (x, y, fg, bg, bold)

        # draw history lines
        #print("self.history.top:", len(self.history.top))
        #while len(self.history.top) > 0:
        #    chars, text = self.pop_history_line()
        #    
        #    # == use this only if there is no "memo_update" call in "draw" func above
        #    # == and history size is configured > 1
        #    # == (this is obsolete/backup)
        #    #self.memo.set_text_line(-1,'')
        #    #self.memo.set_text_line(self.top-1,text)
        #    #for x in range(self.columns): # apply colors to history line
        #    #    colors = self.get_colors(x, self.top-1, chars)
        #    #    if colors:
        #    #        markers.append(colors)
        #    
        #    self.top += 1

        # draw screen dirty lines
        whitespace_passed = False
        #memo_line_count = self.memo.get_line_count()
        #print("self.screen.top:", self.screen.top)
        #print("memo_line_count:", memo_line_count)
        #
        #if self.screen.top > memo_line_count - self.screen.lines:
        #    self.screen.top = memo_line_count
            
        for y_buffer in reversed(sorted(self.screen.dirty)):
            y_memo = y_buffer + self.screen.top - 1
            #print(y_memo)
            # get text
            text = self.screen.render(y_buffer)
            # process empty lines but try not to add newlines
            if not whitespace_passed and text.strip() == '':
                self.memo.set_text_line(y_memo, '')
                continue
            else: whitespace_passed = True

            # add newlines as needed
            while self.memo.get_line_count()-1 < y_memo:
                self.memo.set_text_line(-1, '')

            #print(y_memo,text)
            self.memo.set_text_line(y_memo, text)
            # apply colors to dirty line
            for x in range(self.screen.columns):
                colors = self.screen.get_colors(x, y_memo, self.screen.buffer[y_buffer])
                if colors:
                    markers.append(colors)

        # add markers
        if markers and api_ver >= '1.0.425':
            m = list(zip(*markers))
            self.memo.attr(MARKERS_ADD_MANY, x=m[0], y=m[1], len=[1]*len(markers), color_font=m[2], color_bg=m[3], font_bold=m[4])
        
        # URL markers
        # we must wait 10ms for url markers, they are not present yet
        timer_proc(TIMER_START_ONE, self.screen.apply_url_markers, 10)
        
        # show marker count in terminal header
        #dlg_proc(self.h_dlg, DLG_CTL_PROP_SET, name='header', prop={
            #'cap': '{} markers'.format(len(self.memo.attr(MARKERS_GET)))
        #})

        self.screen.dirty.clear()
        self.memo.set_prop(PROP_RO, True)

    def timer_update(self, tag='', info=''):
        # measure timer time
        _time = perf_counter()*1000
        diff = _time - self.measured_timer_time
        #print("timer_update, diff:", round(diff))
        self.measured_timer_time = _time
        self.timer_took_too_long = diff > 1000

        if self.shell is None:
            self.visible_columns = self.memo.get_prop(PROP_VISIBLE_COLUMNS)
            self.visible_lines   = self.memo.get_prop(PROP_VISIBLE_LINES)
            if self.visible_columns > 0 and self.visible_lines > 0:
                self.create_screen()
                if DEBUG:
                    timer_proc(TIMER_STOP, self.timer_update, TIMER_INTERVAL, tag='')
                    return
                else:
                    if not self.execute_shell():
                        timer_proc(TIMER_STOP, self.timer_update, TIMER_INTERVAL, tag='')
                        return
            # return until memo will initialize its PROP_VISIBLE_LINES/PROP_VISIBLE_COLUMNS props
            else: return

        self.btextchanged = False
        if self.block.locked():
            self.block.release()
        sleep(0.01) # let terminal thread work fast
        self.block.acquire()

        if self.btextchanged or self.btext:
            _time = perf_counter()*1000
            diff = _time - self.measured_line_time
            #canvas_proc(0, CANVAS_TEXT, "fps: "+str(round(1/diff,1)), y=30)
            self.measured_line_time = _time
            #if len(self.time_data) > 50:
            #    self.time_data = self.time_data[1:]
            if diff > 1000: diff = 1000
            self.time_data.append([self.memo.get_line_count(), diff])
            plot(self.time_data)
            
            chunk_len = len(self.btext)
            chunk_len = chunk_len if chunk_len < 2500 else 2500
            self.stream.feed(self.btext[:chunk_len].decode(ENC, errors='replace'))

            self.memo_update()
            self.screen.refresh_caret()

            self.memo.set_prop(PROP_SCROLL_VERT, self.screen.top-1)

            if not IS_WIN: # on Linux memo is not immediately repainted for some reason
                #self.memo.action(EDACTION_UPDATE) # doesn't repaint
                #app_idle() # does repaint but is heavy
                pass

            pass;               DEBUG_FEED and self.dstream.feed(self.btext.decode(ENC, errors='replace'))
            #self.btext = b''
            self.btext = self.btext[chunk_len:]

    def write(self, text):
        if self.shell:
            if IS_WIN:
                self.shell.write(text)
                #print('writing:',bytes(text,'utf8'))
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
            #print('key_press',key)
            self.write(chr(key))
        return True

    def form_key_down(self, id_dlg, id_ctl, data='', info=''):
        key = id_ctl

        if is_toggle_focus_hotkey(key, data):
            #return True # doesn't work?
            ed.focus()
            return False

        if DEBUG:
            pass
            #print(key)
        else:
            if 0:pass
            elif data == 'c':
                if 0:pass # ctrl + key
                elif 65 <= key <= 90:
                    self.write(chr(key-64))
                    return False
                elif key == keys.VK_LEFT:
                    self.write(ctrl.ESC+'[1;5D')
                    return False
                elif key == keys.VK_RIGHT:
                    self.write(ctrl.ESC+'[1;5C')
                    return False
                elif key == keys.VK_BACKSPACE:
                    self.write(ctrl.BS)
                    return False
                elif key == keys.VK_DELETE:
                    self.write(ctrl.ESC+'[3;5~')
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
                elif key == 219: # '[' left square bracket
                    self.write(ctrl.ESC)
                    return False
                #elif 47+144 <= key <= 47+144: # 47+144 = 191 '/' slash key
                    #print('ctrl+key-144',key-144)
                    #self.write(chr(key-144-16))
                    #return False
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
                elif key == keys.VK_DELETE:
                    self.write(ctrl.ESC+'[3;3~')
                    return False
            elif data == 's':
                if 0:pass # shift + key
                elif key == keys.VK_INSERT:
                    self.write(app_proc(PROC_GET_CLIP, ''))
                    return False
                elif key == keys.VK_TAB:
                    self.write(ctrl.ESC+'[Z')
                    return False
            elif len(data) == 2 and 'c' in data and 'a' in data:
                if 0:pass # ctrl + alt + key
                elif key == keys.VK_PAGEUP:
                    self.write(ctrl.ESC+'[5;7~')
                    return False

            elif data == '': # # key without combination, this must be the last
                if key == keys.VK_ESCAPE:
                    if self.opt_esc_focuses_editor:
                        ed.cmd(cmds.cmd_FocusEditor)
                    else:
                        self.write(ctrl.ESC)
                    return False
                elif key in key_map:
                    self.write(key_map.get(key, ''))
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
        # delay terminal_resize because memo is not resized yet
        timer_proc(TIMER_START_ONE, self.terminal_resize, 200)

    def form_close(self, id_dlg, id_ctl, data='', info=''):
        pass
        #timer_proc(TIMER_STOP, self.timer_update, 20, tag='')
        #self.stop_t = True

    def form_show(self, id_dlg, id_ctl, data='', info=''):
        if self.form_show_callback:
            self.form_show_callback(self)

    def close(self):
        timer_proc(TIMER_STOP, self.timer_update, 20, tag='')
        self.stop_t = True
        app_proc(PROC_BOTTOMPANEL_REMOVE, self.name)
        dlg_proc(self.h_dlg, DLG_FREE)


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
                if not self.Cmd.shell.is_alive:
                    # shell will be restarted automatically
                    self.Cmd.shell = None
                    return
                s = self.Cmd.shell.read()
            else:
                if self.Cmd.shell.poll() is not None:
                    # shell will be restarted automatically
                    self.Cmd.shell = None
                    return
                # for a lot of output text - 10000 value seems ok.
                # output speed is at least tolerable
                s = os.read(self.Cmd.master,10000)
                
            
            #if self.Cmd.timer_took_too_long:
            #    print("sleeping 1 sec")
            #    #sleep(TIMER_INTERVAL*2/1000)
            #    sleep(1)
            sleep(0.01) # let MainThread draw something very fast
            
            # TODO: asciinema play https://asciinema.org/a/439918

            if s:
                pass;    DEBUG_READ and print(s)
                self.add_buf(s)
            else:
                sleep(0.05) # reduces CPU usage while doing nothing!

def get_hotkeys(plugcmd):
    lcmds   = app_proc(PROC_GET_COMMANDS, '')
    try:
        cfg_keys= [(cmd['key1'], cmd['key2'])
                    for cmd in lcmds
                    if cmd['type']=='plugin' and cmd['p_module']=='cuda_exterminal' and cmd['p_method']==plugcmd][0]
    except:
        return ()
    return cfg_keys

def is_toggle_focus_hotkey(key, data):
    str_key =\
    ('Meta+' if 'm' in data else '')+\
    ('Shift+' if 's' in data else '')+\
    ('Ctrl+' if 'c' in data else '')+\
    ('Alt+' if 'a' in data else '')+\
    app_proc(PROC_HOTKEY_INT_TO_STR, key)

    for hotkey in get_hotkeys('toggle_focus'):
        if hotkey and str_key == hotkey:
            return True
    return False
