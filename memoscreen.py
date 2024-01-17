import sys
import time
from cudatext import *
import cudatext_cmd as cmds

from .pyte import *
from .pyte import control as ctrl
#from .pyte.screens import wcwidth
from collections import namedtuple
Margins = namedtuple("Margins", "top bottom")

from functools import partial

api_ver = app_api_version()

def BGRtoRGB(hex_string):
    def rev(s): return "" if not s else rev(s[2:]) + s[:2]
    return int(rev(hex_string),16)
    
def plot(data,sx=450,sy=130,offsetx=0):
#def plot(data,sx=100,sy=100,offsetx=0):
    n_list = [d[0] for d in data]
    min_n = min(n_list)
    max_n = max(n_list)
    diff_n = max_n - min_n
    
    time_list = [d[1] for d in data]
    min_t = min(time_list)
    max_t = max(time_list)
    diff_t = max_t - min_t

    canvas_proc(0, CANVAS_SET_BRUSH, color=0xdd552c)
    canvas_proc(0, CANVAS_RECT_FILL, x=offsetx,y=0,x2=offsetx+sx,y2=sy)
    
    canvas_proc(0, CANVAS_SET_PEN, color=0x555555, style=PEN_STYLE_DASH, size=3)
    canvas_proc(0, CANVAS_LINE, x=offsetx, y=sy, x2=offsetx+sx,y2=0)
    canvas_proc(0, CANVAS_SET_PEN, color=0xaaaaaa)
    canvas_proc(0, CANVAS_LINE, x=offsetx+1, y=sy+1, x2=offsetx+sx+1,y2=1)
    
    canvas_proc(0, CANVAS_SET_PEN, color=0xffffff, size=1)
    canvas_proc(0, CANVAS_LINE, x=offsetx, y=sy, x2=offsetx+sx,y2=sy)
    canvas_proc(0, CANVAS_LINE, x=offsetx+sx, y=sy, x2=offsetx+sx,y2=0)
    canvas_proc(0, CANVAS_LINE, x=offsetx+sx, y=0, x2=offsetx,y2=0)
    canvas_proc(0, CANVAS_LINE, x=offsetx, y=0, x2=offsetx,y2=sy)
    
    canvas_proc(0, CANVAS_SET_PEN, color=0x00ee88, size=5)
    
    px,py = None,None
    for i,(n,t) in enumerate(data):
        t = (t - min_t) * sy # scale
        n = (n - min_n) * sx # scale
        t = t // diff_t if diff_t != 0 else t
        n = n // diff_n if diff_n != 0 else n
        t, n = int(t), int(n) # to int
        
        if i == 0:
            px, py = n, sy-t  # remember first point coords
            continue # do not draw line yet, wait for second point
        else:
            x2, y2 = n, sy-t
            canvas_proc(0, CANVAS_LINE, x=px+offsetx, y=py, x2=x2+offsetx,y2=y2)
            px, py = x2, y2
            
            canvas_proc(0, CANVAS_SET_FONT, color=0xdddddd)
            h = canvas_proc(0, CANVAS_GET_TEXT_SIZE, 'text')[1]
            #canvas_proc(0, CANVAS_SET_BRUSH, style=BRUSH_CLEAR)
            t = "time: {}".format(round(data[-1][1]/1000, 6))
            n = "n: {}".format(data[-1][0])
            nn = "nn: {}".format(len(data))
            canvas_proc(0, CANVAS_TEXT, t, x=offsetx+5, y=2)
            canvas_proc(0, CANVAS_TEXT, n, x=offsetx+5, y=h)
            canvas_proc(0, CANVAS_TEXT, nn, x=offsetx+5, y=h*2)
            #app_idle()
            #sleep(0.1)
    #canvas_proc(0, CANVAS_TEXT, 'done', x=offsetx+5, y=h*2)


class MemoScreen(Screen):
    def __init__(self, memo: Editor, columns, lines, h_dlg, colored=0, draw_callback=None):
        self.memo = memo
        self.h_dlg = h_dlg
        self.no_ro = partial(self.memo.set_prop, PROP_RO, False)
        self.ro = partial(self.memo.set_prop, PROP_RO, True)

        self.top = 1
        self.colored = colored
        self.draw_callback = draw_callback
        self.dirty_prev = set()
        self.counter = 0
        self.time_data = []
        self.measured_line_time = time.perf_counter()*1000

        #super().__init__(columns, lines, sys.maxsize)
        #super().__init__(columns, lines, 1)
        super().__init__(columns, lines)

    def render(self,line):
#        is_wide_char = False
#        s = ''
#        line = self.buffer[line]
#        for x in range(self.columns):
#            if is_wide_char:  # Skip stub
#                is_wide_char = False
#                continue
#            char = line[x].data
#            assert sum(map(wcwidth, char[1:])) == 0
#            is_wide_char = wcwidth(char[0]) == 2
#            s += char
#        return s

        # TODO: test with wide chars
        s = ''.join( (self.buffer[line][char].data for char in range(self.columns)) )
        return s

    def pop_history_line(self):
        chars = self.history.top.popleft()
        text = ''.join( (chars[char].data for char in range(self.columns)) )
        return chars, text
        
    def erase_in_display(self, how=0, *args, **kwargs):
        """Overloaded to reset history state."""
        super().erase_in_display(how, *args, **kwargs)

        if how == 3:
            self._reset_history()
            self.top = 1
            self.no_ro()
            self.memo.set_text_all('')
            self.ro()
            self.cursor_position(0, 0)

    def set_title(self, param):
        super().set_title(param)
        dlg_proc(self.h_dlg, DLG_PROP_SET, name='form', prop={'cap': param})
        dlg_proc(self.h_dlg, DLG_CTL_PROP_SET, name='header', prop={'cap': param})

    def strip_trailing_whitespace(self, tag='', info=''):
        self.no_ro()
        # TODO: this is bad, i need something better
        #self.memo.set_text_all(self.memo.get_text_all().strip())
    
        # remove trailing empty lines
        for line in reversed(range(self.memo.get_line_count())):
            txt = self.memo.get_text_line(line)
            if txt is not None and txt.strip() == '':
                self.memo.replace_lines(line, line, [])
            else: break
    
        self.ro()

    def resize(self, lines=None, columns=None):
        super().resize(lines, columns)
        # try to strip white-space on terminal resize (will work on next resize, unfortunately)
        timer_proc(TIMER_START_ONE, self.strip_trailing_whitespace, 200)
        
        # commented out: see https://github.com/veksha/cuda_exterminal/issues/35
        # only for qt5 version this gives focus to terminal on app start (if window is maximized)
        #self.memo.focus() # handy, but can be annoying to some

    def refresh_caret(self):
        self.memo.set_caret(self.cursor.x, self.cursor.y + self.top - 1, options=CARET_OPTION_NO_SCROLL)
        
    def index(self):
        super().index()
        top, bottom = self.margins or Margins(0, self.lines - 1)
    
        
        if self.cursor.y == bottom:
            self.top += 1
            
            #canvas_proc(0, CANVAS_SET_BRUSH, color=0xa0ffa0)            
            #canvas_proc(0, CANVAS_RECT_FILL, x=0,y=0,x2=1000,y2=1000)
            #canvas_proc(0, CANVAS_TEXT, "lines: "+str(self.counter), x=500)
            #canvas_proc(0, CANVAS_TEXT, "fps: "+str(round(1/diff,1)), y=30)
            self.counter += 1
            
           # _time = time.perf_counter()*1000
           # diff = _time - self.measured_line_time
           # self.time_data.append(diff)
           # print("measured_line_time:", round(diff))
           # #canvas_proc(0, CANVAS_TEXT, "fps: "+str(round(1/diff,1)), y=30)
           # self.measured_line_time = _time
           # plot(self.time_data)
           # print("self.time_data:", self.time_data)
            
            #if self.draw_callback: self.draw_callback("MYTEXT")
            
            #self.memo_update()
            #self.refresh_caret()
            #self.memo.set_prop(PROP_SCROLL_VERT, self.top-1)
            #app_idle()

        
    def draw(self, data):
        super().draw(data)

        if len(self.dirty) == 1: # one line is drawing
            if self.dirty != self.dirty_prev: # not the same line as before
                if self.draw_callback: self.draw_callback("MYTEXT")
                
                #self.memo_update()

    #            self.refresh_caret()
    #            self.memo.set_prop(PROP_SCROLL_VERT, self.top-1)
    #            app_idle()
    #            #import time
    #            #time.sleep(0.001)        
    #    
    #    #while len(self.history.top) > 0:
    #    #    self.pop_history_line()
    #    #    self.top += 1
    #    
    #    #if len(self.dirty) == 1: # one line is drawing
    #    #    if self.dirty != self.dirty_prev: # not the same line as before
    #    #self.memo_update()

    ###

    def apply_url_markers(self, tag='', info=''):
        url_markers = [m for m in self.memo.attr(MARKERS_GET) if m[0] == -100] # url markers have tag -100
        for m in url_markers:
            for x in range(m[1], m[1]+m[3]): # sadly only non-multiline URLs will be colored/underlined
                self.memo.attr(MARKERS_ADD, 0, x, m[2], 1, m[4], m[5], m[6], border_down=m[12])


    def get_colors(self, x, y, chars):
        if not self.colored:
            return

        color_names = [chars[x].fg, chars[x].bg]
        reverse = chars[x].reverse

        bold = chars[x].bold
        intense_colors = bold

        colors = [0,0] # fg, bg

        for c in range(2):
            foreground = c == 0

            if color_names[c] == "default":
                colors[c] = colmap["foreground"] if foreground else colmap["background"]
            else:
                if color_names[c] in colmap.keys():
                    if foreground and intense_colors and not color_names[c].startswith("bright"):
                        color_names[c] = "bright" + color_names[c]
                    colors[c] = colmap[color_names[c]]
                else:
                    colors[c] = BGRtoRGB(color_names[c])

        fg, bg = colors
        if reverse: fg, bg = bg, fg

        # SLOW
        #try: # try new API, could be missing
            #self.memo.attr(MARKERS_DELETE_BY_POS, x=x, y=y)
        #except: pass

        return (x, y, fg, bg, bold)


colmap_default = { # https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
    'black': 0x36342e,
    'red': 0x0000cc,
    'green': 0x69a4e,
    'brown': 0x00a0c4,
    'blue': 0xa46534,
    'magenta': 0x7b5075,
    'cyan': 0x9a9806,
    'white': 0xcfd7d3,

    'brightblack': 0x535755,
    'brightred': 0x2929ef,
    'brightgreen': 0x34e28a,
    'brightbrown': 0x4fe9fc,
    'brightblue': 0xcf9f72,
    'brightmagenta': 0xa87fad,
    'brightcyan': 0xe2e234,
    'brightwhite': 0xeceeee,

    'background': 0x240a30,
    'foreground': 0xcfd7d3,
}
colmap = colmap_default
