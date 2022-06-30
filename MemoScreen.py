import sys
from cudatext import *
import cudatext_cmd as cmds

from .pyte import *
from .pyte import control as ctrl
#from .pyte.screens import wcwidth
from functools import partial


def BGRtoRGB(hex_string):
    def rev(s): return "" if not s else rev(s[2:]) + s[:2]
    return int(rev(hex_string),16)

class MemoScreen(HistoryScreen):
    def __init__(self, memo, columns, lines, screen_height, h_dlg, colored=0):
        self.memo = memo
        self.h_dlg = h_dlg
        self.no_ro = partial(self.memo.set_prop, PROP_RO, False)
        self.ro = partial(self.memo.set_prop, PROP_RO, True)

        self.top = 1
        self.screen_height = screen_height
        self.colored = colored

        super(MemoScreen, self).__init__(columns, lines, sys.maxsize)

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

    def set_title(self, param):
        super(MemoScreen, self).set_title(param)
        dlg_proc(self.h_dlg, DLG_PROP_SET, name='form', prop={'cap': param})

    def strip_trailing_whitespace(self):
        self.no_ro()
        self.memo.set_text_all(self.memo.get_text_all().strip())
        self.ro()

    def resize(self, lines=None, columns=None):
        super(MemoScreen, self).resize(lines, columns)
        # try to strip white-space on terminal resize (will work on next resize, unfortunately)
        self.strip_trailing_whitespace()

    def index(self):
        super(MemoScreen, self).index()

        self.no_ro()
        if self.memo.get_line_count()-1 < self.cursor.y:
            self.memo.set_text_line(-1, '')

        self.ro()

    def refresh_caret(self):
        self.memo.set_caret(self.cursor.x, self.cursor.y + self.top - 1, options=CARET_OPTION_NO_SCROLL)

    def cursor_position(self, line=None, column=None):
        super(MemoScreen, self).cursor_position(line, column)

        if line:
            self.no_ro()
            y = self.cursor.y
            while self.memo.get_line_count() < line:
                self.memo.set_text_line(-1, '')
            self.ro()

    def cursor_to_line(self, line=None):
        super(MemoScreen, self).cursor_to_line(line)

        self.no_ro()
        y = self.cursor.y
        while self.memo.get_line_count() < line:
            self.memo.set_text_line(-1, '')
        self.ro()

    def memo_update(self):
        self.no_ro()

        # draw history lines
        while len(self.history.top) > 0:
            self.memo.set_text_line(-1,'')
            chars, text = self.pop_history_line()
            self.memo.set_text_line(self.top-1,text)
            for x in range(self.columns): # apply colors to history lines
                self.apply_colors(x, self.top-1, chars)
            self.top += 1
            #print("top =",self.top)

        # draw screen dirty lines
        for y_buffer in self.dirty:
            y_memo = y_buffer + self.top - 1
            # add newlines as needed
            while self.memo.get_line_count()-1 < y_memo:
                self.memo.set_text_line(-1, '')
            # draw text
            text = self.render(y_buffer)
            self.memo.set_text_line(y_memo, text)
            # apply colors to dirty lines
            for x in range(self.columns):
                self.apply_colors(x, y_memo, self.buffer[y_buffer])

        self.dirty.clear()

        self.ro()

    def apply_colors(self, x, y, chars):
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
        self.memo.attr(MARKERS_DELETE_BY_POS, x=x, y=y)
        self.memo.attr(MARKERS_ADD, x=x, y=y, len=1, color_font=fg, color_bg=bg, font_bold=bold)


colmap = { # https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
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
