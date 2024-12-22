#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Written in 2024 by Mikhail Gribkov ( https://github.com/youzhick )
# Distributed 'as is' with no license limitations.

import curses
from datetime import datetime
import os
import sys

KEY_UP = 259
KEY_DOWN = 258
KEY_LEFT = 260
KEY_RIGHT = 261
KEY_ENTER = 10
KEY_PADENTER = 459
KEY_ESC = 27
KEY_TAB = 9
KEY_RESIZE = 546
KEY_HOME = 262
KEY_END = 360
KEY_PGUP = 339
KEY_PGDOWN = 338

KEY_CTRL_SHIFT = -96

KEYS_ENTER = [KEY_ENTER, KEY_PADENTER, 13, 343]
KEYS_QUIT = [KEY_ESC, ord('c') + KEY_CTRL_SHIFT, ord('x') + KEY_CTRL_SHIFT, ord('q') + KEY_CTRL_SHIFT]
SYMBOLS = [ord('_'), ord('-'), ord('+')]

libNames = []
includedLibs = []

libs_shared = ''
libs_session = ''
libs_local = ''

lastFile = '~/.pglib.last'

PGDATA = None
PGINSTALL = None
PGCONFIG = None
pg_config = None
postgresql_conf = None
postgresql_auto_conf = None
libdir = None
sharedir = None

APP_VERSION = '1.0'
# *************************************************************************
# Returns timestamp in float seconds
def getTimestamp():
    return datetime.now().timestamp()
# *************************************************************************
class PadComponent:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.colPair = 0

    def setColorPair(self, cPairInd):
        self.colPair = cPairInd
# *************************************************************************
# Constants:
# shared_preload_libraries
# session_preload_libraries
# local_preload_libraries
class LinesSelectionPad(PadComponent):
    def __init__(self, stdscr, x, y, w):
        super(LinesSelectionPad, self).__init__(stdscr)
        global libs_shared
        global libs_session
        global libs_local
    
        self.contents_shared = libs_shared
        self.contents_session = libs_session
        self.contents_local = libs_local
        self.selected = 0
        self.updateSelectedList()
        self.relayout(x, y, w)
        self.repaint()
        
    def getCurLine(self):
        if self.selected == 0:
            return self.contents_shared
        elif self.selected == 1:
            return self.contents_session
        return self.contents_local

    def setCurLine(self, newVal):
        if self.selected == 0:
            self.contents_shared = newVal
        elif self.selected == 1:
            self.contents_session = newVal
        else:
            self.contents_local = newVal

    def relayout(self, x, y, w):
        self.width = w
        self.x = x
        self.y = y
        self.win = curses.newwin(3, w, y, x)
        
    def setSelectedInd(self, ind):
        self.selected = ind

    def incSelected(self):
        self.setSelectedInd((self.selected + 1) % 3)

    def repaint(self):
        self.win.clear()
        self.win.bkgd(' ', curses.color_pair(self.colPair))
        self.win.addnstr(0, 0, ('==> ' if self.selected == 0 else '    ') + 'shared_preload_libraries\t= \'' + self.contents_shared + '\'', self.width-1, curses.color_pair(self.colPair))
        self.win.addnstr(1, 0, ('==> ' if self.selected == 1 else '    ') + 'session_preload_libraries\t= \'' + self.contents_session + '\'', self.width-1, curses.color_pair(self.colPair))
        self.win.addnstr(2, 0, ('==> ' if self.selected == 2 else '    ') + 'local_preload_libraries\t= \'' + self.contents_local + '\'', self.width-1, curses.color_pair(self.colPair))
        self.win.refresh()
    
    def reset(self):
        global includedLibs
        self.contents_shared = ''
        self.contents_session = ''
        self.contents_local = ''

        for i in range(len(includedLibs)):
            includedLibs[i] = False
        
    def updateLine(self, ind):
        global libNames
        global includedLibs
        
        if len(includedLibs) < 1:
            return

        ln = self.getCurLine()

        if includedLibs[ind]:
            # Add lib. It's simple
            self.setCurLine(libNames[ind] if len(ln) == 0 else (ln + ', ' + libNames[ind]))
            return
        
        # Remove lib
        tokens = [l.strip() for l in ln.split(',')]
        ln = ''
        for t in tokens:
            if t != libNames[ind]:
                ln = ln + (t if len(ln) == 0 else (', ' + t))
        
        self.setCurLine(ln)
        
    def updateSelectedList(self):
        global libNames
        global includedLibs
        
        ln = self.getCurLine()
        tokens = [l.strip() for l in ln.split(',')]
        
        for i, l in enumerate(libNames):
            includedLibs[i] = l in tokens
            
    def saveFiles(self):
        global libs_shared
        global libs_session
        global libs_local
        
        libs_shared = self.contents_shared
        libs_session = self.contents_session
        libs_local = self.contents_local

        saveCurrentConfigs()
# *************************************************************************
class LibsPad(PadComponent):
    def __init__(self, stdscr, x, y, w, h):
        super(LibsPad, self).__init__(stdscr)
        self.selColPair = 0
        self.selected = 0
        self.savedSelected = 0
        self.relayout(x, y, w, h)
        self.repaint()
    
    def setSelColorPair(self, cPairInd):
        self.selColPair = cPairInd

    def relayout(self, x, y, w, h):
        global libNames
        
        #--- Settings ---
        spacer = 2
        padding = 0
        #---
        
        self.coords = []
        libsCnt = len(libNames)

        if libsCnt > 0:
            self.maxLen = max([len(ln) for ln in libNames]) + spacer + len('[ ]')
            
            maxOnScreen = max(max(int((w - padding*2)/self.maxLen), 1)*h, 1)
            
            if maxOnScreen >= libsCnt:
                # Orient in columns first
                xx = padding
                yy = 0
                for ln in libNames:
                    self.coords.append((xx, yy))
                    yy += 1
                    if yy >= h:
                        yy = 0
                        xx += self.maxLen
            else:
                # @TODO: Add scrollable layout
                pass

        self.width = w
        self.height = h
        self.x = x
        self.y = y
        self.win = curses.newwin(h, w, y, x)

    def repaint(self):
        global libNames
        global includedLibs

        self.win.clear()
        self.win.bkgd(' ', curses.color_pair(self.colPair))
        for i, c in enumerate(self.coords):
            self.win.addnstr(c[1], c[0], '[' + ('X' if includedLibs[i] else ' ') + ']' + libNames[i], self.width-1 - c[0], curses.color_pair(self.selColPair if i == self.selected else self.colPair))
            
        self.win.refresh()
        
    def moveSelection(self, dx, dy):
        global libNames
        libsCnt = len(libNames)

        if libsCnt > 0:
            self.selected += dy + dx*self.height
            
            if self.selected < 0:
                self.selected = 0
            elif self.selected >= libsCnt:
                self.selected = libsCnt - 1
                
    def switchInclusion(self):
        global includedLibs

        if len(includedLibs) > self.selected:
            includedLibs[self.selected] = not includedLibs[self.selected]

    def initQFind(self):
        self.savedSelected = self.selected
        
    def findSelection(self, qsStr):
        global libNames

        libsCnt = len(libNames)

        if libsCnt > 0:
            for i in range(libsCnt):
                realI = (i + self.savedSelected + 1) % libsCnt
                s = libNames[realI].lower()
                if s.find(qsStr) >= 0:
                    self.selected = realI
                    break
        

# *************************************************************************
class LabelPad(PadComponent):
    def __init__(self, stdscr, x, y, w, isCentered=False, bgChar=' '):
        super(LabelPad, self).__init__(stdscr)
        self.text = ''
        self.isCentered = isCentered
        self.bgChar = bgChar
        self.relayout(x, y, w)
        self.repaint()
        
    def relayout(self, x, y, w):
        self.width = w + 1
        self.x = x
        self.y = y
        self.win = curses.newwin(1, self.width, y, x)

    def repaint(self):
        self.win.clear()
        self.win.bkgd(self.bgChar, curses.color_pair(self.colPair))
        xPos = 0 if not self.isCentered else int((self.width - len(self.text))/2)
        if xPos < 0:
            xPos = 0
        self.win.addnstr(0, xPos, self.text, self.width-1, curses.color_pair(self.colPair))
        self.win.refresh()

    def setText(self, txt, instantRepaint=True):
        self.text = txt
        if instantRepaint:
            self.repaint()
# *************************************************************************
def win_main(stdscr):
    global libNames

    curses.init_color(curses.COLOR_YELLOW, 1000, 1000, 0)
    
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_GREEN)

    stdscr.clear()
    h,w  = stdscr.getmaxyx()
    stdscr.refresh()

    savedStr = '--== Saved ==--'
    lbSaved = LabelPad(stdscr, w - 3 - len(savedStr), h - 4, len(savedStr), isCentered=True, bgChar=' ')
    lbSaved.setColorPair(4)
    lbSaved.setText(savedStr)

    lbHeadConstants = LabelPad(stdscr, 0, 0, w, isCentered=True, bgChar='=')
    lbHeadConstants.setColorPair(1)
    lbHeadConstants.setText('_Constants_')
    lbHeadConstants.repaint()
    
    selConsts = LinesSelectionPad(stdscr, 0, 1, w)
    selConsts.setColorPair(2)
    selConsts.repaint()

    lbHeadLibs = LabelPad(stdscr, 0, 4, w, isCentered=True, bgChar='=')
    lbHeadLibs.setColorPair(1)
    lbHeadLibs.setText('_Libraries_')
    lbHeadLibs.repaint()

    libsPad = LibsPad(stdscr, 0, 5, w, h - 6)
    libsPad.setColorPair(2)
    libsPad.setSelColorPair(3)
    libsPad.repaint()

    lbHelp = LabelPad(stdscr, 0, h-1, w, isCentered=False, bgChar=' ')
    lbHelp.setColorPair(1)
    lbHelp.setText('^S: Save    ^Q/^X: Quit    ^R: Reset    ENTER/SPACE: Select    TAB: Switch Constant    Arrows: Move cursor')
    lbHelp.repaint()

    stdscr.nodelay(True)
    needRepaint = False
    savedTimeEnd = -1.
    quickSearchTypeEnd = -1.
    lastTimeRepaint = -1.
    quickSearchStr = ''
    
    while True:
        c = stdscr.getch()

        if c in KEYS_QUIT:
            break
        elif c == KEY_TAB:
            selConsts.incSelected()
            selConsts.updateSelectedList()
            needRepaint = True
        elif c == KEY_UP:
            libsPad.moveSelection(0, -1)
            needRepaint = True
        elif c == KEY_DOWN:
            libsPad.moveSelection(0, 1)
            needRepaint = True
        elif c == KEY_LEFT:
            libsPad.moveSelection(-1, 0)
            needRepaint = True
        elif c == KEY_RIGHT:
            libsPad.moveSelection(1, 0)
            needRepaint = True
        elif c in KEYS_ENTER or c == ord(' '):
            libsPad.switchInclusion()
            selConsts.updateLine(libsPad.selected)
            needRepaint = True
        elif c == ord('r') + KEY_CTRL_SHIFT:
            selConsts.reset()
            needRepaint = True
        elif c == KEY_HOME:
            libsPad.selected = 0
            needRepaint = True
        elif c == KEY_END and len(libNames) > 0:
            libsPad.selected = len(libNames) - 1
            needRepaint = True
        elif c == KEY_PGDOWN and len(libNames) > 0:
            libsPad.selected = (libsPad.selected + int(libsPad.height/4)) % len(libNames)
            needRepaint = True
        elif c == KEY_PGUP and len(libNames) > 0:
            libsPad.selected = (libsPad.selected - int(libsPad.height/4)) % len(libNames)
            needRepaint = True
        elif c == ord('s') + KEY_CTRL_SHIFT:
            selConsts.saveFiles()
            savedTimeEnd = getTimestamp() + 1. # 1 sec display of "Saved" message
            lastTimeRepaint = -1.
            lbSaved.setText(savedStr, False)
        elif (c >= ord('a') and c <= ord('z')) or (c >= ord('A') and c <= ord('Z')) or (c >= ord('0') and c <= ord('9')) or (c in SYMBOLS):
            # quick search
            if len(quickSearchStr) == 0:
                libsPad.initQFind()
            quickSearchStr += chr(c).lower()
            quickSearchTypeEnd = getTimestamp() + 1.5 # 1.5 secs waiting for the new type
            lastTimeRepaint = -1.
            needRepaint = True
            lbSaved.setText(quickSearchStr, False)
            libsPad.findSelection(quickSearchStr)
        elif needRepaint or c == KEY_RESIZE or c == curses.KEY_RESIZE or ((savedTimeEnd > 0 or quickSearchTypeEnd > 0) and getTimestamp() - lastTimeRepaint > 0.5):
            try:
                stdscr.clear()
                h,w  = stdscr.getmaxyx()
    
                stdscr.refresh()
                
                lbHeadConstants.relayout(0, 0, w)
                lbHeadConstants.repaint()
            
                selConsts.relayout(0, 1, w)
                selConsts.repaint()
                
                lbHeadLibs.relayout(0, 4, w)
                lbHeadLibs.repaint()

                libsPad.relayout(0, 5, w, h - 6)
                libsPad.repaint()
    
                lbHelp.relayout(0, h-1, w)
                lbHelp.repaint()
                                
                needRepaint = False

                if savedTimeEnd > 0:
                    if getTimestamp() > savedTimeEnd:
                        savedTimeEnd = -1.
                        lastTimeRepaint = -1.
                        needRepaint = True
                    else:
                        lbSaved.relayout(w - 3 - len(savedStr), h - 4, len(savedStr))
                        lbSaved.repaint()
                        lastTimeRepaint = getTimestamp()
                if quickSearchTypeEnd > 0:
                    if getTimestamp() > quickSearchTypeEnd:
                        quickSearchStr = ''
                        quickSearchTypeEnd = -1.
                        lastTimeRepaint = -1.
                        needRepaint = True
                    else:
                        lbSaved.relayout(w - 3 - len(quickSearchStr), h - 4, len(quickSearchStr))
                        lbSaved.repaint()
                        lastTimeRepaint = getTimestamp()

            except:
                needRepaint = True

# *************************************************************************
def saveCurrentConfigs():
    data = []
    with open(postgresql_auto_conf, 'r') as f:
        for l in f.readlines():
            ls = l.strip()
            if not ls.startswith('shared_preload_libraries') and not ls.startswith('session_preload_libraries') and not ls.startswith('local_preload_libraries'):
                data.append(l)
                
    data.append('shared_preload_libraries = \'' + libs_shared + '\'\n')
    data.append('session_preload_libraries = \'' + libs_session + '\'\n')
    data.append('local_preload_libraries = \'' + libs_local + '\'\n')

    with open(postgresql_auto_conf, 'w') as f:
        f.writelines(data)
    
    # Save last call
    with open(os.path.expanduser(lastFile), 'w') as f:
        f.write(postgresql_auto_conf + '\n')
        f.write('shared_preload_libraries = \'' + libs_shared + '\'\n')
        f.write('session_preload_libraries = \'' + libs_session + '\'\n')
        f.write('local_preload_libraries = \'' + libs_local + '\'\n')
# *************************************************************************
def readConstsFromConfig(fname):
    if not os.path.isfile(fname):
        return
    
    global libs_shared
    global libs_session
    global libs_local

    with open(fname, 'r') as f:
        for ln in f.readlines():
            commPos = ln.find('#')
            l = ln[:commPos].strip() if commPos >= 0 else ln.strip()
            tokens = l.split('=')
            if len(tokens) != 2:
                continue
            
            name = tokens[0].strip()
            value = tokens[1].strip(' \'')
            
            if name == 'shared_preload_libraries':
                libs_shared = value
            elif name == 'session_preload_libraries':
                libs_session = value
            elif name == 'local_preload_libraries':
                libs_local = value
# *************************************************************************
def readFiles():
    global libNames
    global includedLibs
    libNames = []
    includedLibs = []
    
    # Get libs list
    sosList = [os.path.split(l.strip())[1] for l in os.popen('ls ' + libdir + '/*.so').readlines()]
    for ln in os.popen('ls ' + sharedir + '/extension/*.control').readlines():
        l = os.path.split(ln.strip())[1]
        libName = l[:l.rfind('.')]
        if libName + '.so' in sosList:
            libNames.append(libName)
            includedLibs.append(False)
    
    # Read config files
    global libs_shared
    global libs_session
    global libs_local

    libs_shared = ''
    libs_session = ''
    libs_local = ''

    readConstsFromConfig(postgresql_conf)
    readConstsFromConfig(postgresql_auto_conf)
    
    return True
# *************************************************************************
def doSaveLast():
    print('Saving last config...')
    confname = os.path.expanduser(lastFile)
    if not os.path.exists(confname):
        print('Cannot find the last config save file (' + confname + ')')
        return

    with open(confname, 'r') as f:
        lastConfig = f.readlines()
        data = []
        if os.path.exists(lastConfig[0].strip()):
            with open(lastConfig[0].strip(), 'r') as ff:
                for l in ff.readlines():
                    ls = l.strip()
                    if not ls.startswith('shared_preload_libraries') and not ls.startswith('session_preload_libraries') and not ls.startswith('local_preload_libraries'):
                        data.append(l)

        for l in lastConfig[1:]:
            data.append(l)
            print(l.strip())

        with open(lastConfig[0].strip(), 'w') as ff:
            ff.writelines(data)
    
    print('Done')

# *************************************************************************
def firstNonNone(lst):
    for l in lst:
        if l is not None:
            return l
    return None
# *************************************************************************
def gatherSystemInfo(verbose=False):
    if verbose:
        print('Analyzing environment...')
    
    global PGDATA
    global PGINSTALL
    global PGCONFIG
    global pg_config
    global postgresql_conf
    global postgresql_auto_conf
    global libdir
    global sharedir

    if verbose:
        print('\nCall parameters:')
        print('$PGDATA    is ' + (('set to \'' + PGDATA + '\' (' + ('exists' if os.path.isdir(PGDATA) else 'does not exist') + ')') if PGDATA is not None else ('not set')))
        print('$PGINSTALL is ' + (('set to \'' + PGINSTALL + '\' (' + ('exists' if os.path.isdir(PGINSTALL) else 'does not exist') + ')') if PGINSTALL is not None else ('not set')))
        print('$PGCONFIG  is ' + (('set to \'' + PGCONFIG + '\' (' + ('exists' if os.path.isdir(PGCONFIG) else 'does not exist') + ')') if PGCONFIG is not None else ('not set')))
    
    if PGDATA is not None and not os.path.isdir(PGDATA):
        PGDATA = None
    if PGINSTALL is not None and not os.path.isdir(PGINSTALL):
        PGINSTALL = None
    if PGCONFIG is not None and not os.path.isdir(PGCONFIG):
        PGCONFIG = None
    
    PGDATA_env = os.environ['PGDATA'] if 'PGDATA' in os.environ else None
    PGINSTALL_env = os.environ['PGINSTALL'] if 'PGINSTALL' in os.environ else None
    PGCONFIG_env = os.environ['PGCONFIG'] if 'PGCONFIG' in os.environ else None
    
    if verbose:
        print('\nEnvironment variables:')
        print('$PGDATA    is ' + (('set to \'' + PGDATA_env + '\' (' + ('exists' if os.path.isdir(PGDATA_env) else 'does not exist') + ')') if PGDATA_env is not None else ('not set')))
        print('$PGINSTALL is ' + (('set to \'' + PGINSTALL_env + '\' (' + ('exists' if os.path.isdir(PGINSTALL_env) else 'does not exist') + ')') if PGINSTALL_env is not None else ('not set')))
        print('$PGCONFIG  is ' + (('set to \'' + PGCONFIG_env + '\' (' + ('exists' if os.path.isdir(PGCONFIG_env) else 'does not exist') + ')') if PGCONFIG_env is not None else ('not set')))

    if PGDATA_env is not None and not os.path.isdir(PGDATA_env):
        PGDATA_env = None
    if PGINSTALL_env is not None and not os.path.isdir(PGINSTALL_env):
        PGINSTALL_env = None
    if PGCONFIG_env is not None and not os.path.isdir(PGCONFIG_env):
        PGCONFIG_env = None

    if verbose:
        print('\nSearching for pg_config:')
    pg_config_arg = None if PGINSTALL is None else os.path.join(PGINSTALL, 'bin/pg_config')
    if pg_config_arg is not None and not os.path.exists(pg_config_arg):
        pg_config_arg = None
    
    pg_config_env = None if PGINSTALL_env is None else os.path.join(PGINSTALL_env, 'bin/pg_config')
    if pg_config_env is not None and not os.path.exists(pg_config_env):
        pg_config_env = None
        
    pg_config_path = os.popen('which pg_config').read().strip()
    if pg_config_path is not None and not os.path.exists(pg_config_path):
        pg_config_path = None

    if verbose:
        print('Via argument: ' + ('Found' if pg_config_arg is not None else 'Not found'))
        print('Via env var:  ' + ('Found' if pg_config_env is not None  else 'Not found'))
        print('Via $PATH:    ' + ('Found' if pg_config_path is not None else 'Not found'))
        
        print('\nChecking data_directory in PGCONFIG/postgresql.conf:')
    PGDATA_conf_arg = None
    conf_file_arg = None if PGCONFIG is None else os.path.join(PGCONFIG, 'postgresql.conf')
    if conf_file_arg is not None and not os.path.isfile(conf_file_arg):
        conf_file_arg = None
    if conf_file_arg is not None:
        with open(conf_file_arg, 'r') as f:
            for ln in f.readlines():
                commPos = ln.find('#')
                l = ln[:commPos].strip() if commPos >= 0 else ln.strip()
                tokens = l.split('=')
                if len(tokens) != 2:
                    continue
                
                name = tokens[0].strip()
                value = tokens[1].strip(' \'')
                
                if name == 'data_directory':
                    PGDATA_conf_arg = value
    PGDATA_conf_env = None
    conf_file_env = None if PGCONFIG_env is None else os.path.join(PGCONFIG_env, 'postgresql.conf')
    if conf_file_env is not None and not os.path.isfile(conf_file_env):
        conf_file_env = None
    if conf_file_env is not None:
        with open(conf_file_env, 'r') as f:
            for ln in f.readlines():
                commPos = ln.find('#')
                l = ln[:commPos].strip() if commPos >= 0 else ln.strip()
                tokens = l.split('=')
                if len(tokens) != 2:
                    continue
                
                name = tokens[0].strip()
                value = tokens[1].strip(' \'')
                
                if name == 'data_directory':
                    PGDATA_conf_env = value

    if PGDATA_conf_arg is not None and not os.path.isdir(PGDATA_conf_arg):
        PGDATA_conf_arg = None
    if PGDATA_conf_env is not None and not os.path.isdir(PGDATA_conf_env):
        PGDATA_conf_env = None

    if verbose:
        print('Via argument: ' + ('Not found' if PGDATA_conf_arg is None else 'Found'))
        print('Via env var:  ' + ('Not found' if PGDATA_conf_env is None else 'Found'))

    pg_config = firstNonNone([pg_config_arg, pg_config_env, pg_config_path])
    if conf_file_arg is not None:
        PGDATA = firstNonNone([PGDATA, PGDATA_conf_arg, PGDATA_env])
        postgresql_conf = conf_file_arg
    elif conf_file_env is not None:
        PGDATA = firstNonNone([PGDATA, PGDATA_conf_env, PGDATA_env])
        postgresql_conf = conf_file_env
    else:
        PGDATA = firstNonNone([PGDATA, PGDATA_env])
        postgresql_conf = None if PGDATA is None else os.path.join(PGDATA, 'postgresql.conf')
        if postgresql_conf is not None and not os.path.isfile(postgresql_conf):
            postgresql_conf = None
        
    postgresql_auto_conf = None if PGDATA is None else os.path.join(PGDATA, 'postgresql.auto.conf')
    if postgresql_auto_conf is not None and not os.path.isfile(postgresql_auto_conf):
        postgresql_auto_conf = None

    libdir = None if pg_config is None else os.popen(pg_config + ' --libdir').read().strip()
    sharedir = None if pg_config is None else os.popen(pg_config + ' --sharedir').read().strip()
    if libdir is not None and not os.path.isdir(libdir):
        libdir = None
    if sharedir is not None and not os.path.isdir(sharedir):
        sharedir = None

    if verbose:
        print('\nFinal setting:')
        print('$PGDATA:             ', 'Not found' if PGDATA is None else PGDATA)
        print('pg_config:           ', 'Not found' if pg_config is None else pg_config)
        print('--libdir:            ', 'Not found' if libdir is None else libdir)
        print('--sharedir:          ', 'Not found' if sharedir is None else sharedir)
        print('postgresql.conf:     ', 'Not found' if postgresql_conf is None else postgresql_conf)
        print('postgresql.auto.conf:', 'Not found' if postgresql_auto_conf is None else postgresql_auto_conf)
    
    if libdir is None or sharedir is None or postgresql_auto_conf is None:
        if verbose:
            print('')
        print('Can\'t proceed, insufficient info: need to find at least lib/share dirs and postgresql.auto.conf')
        exit()
    elif verbose:
        print('\nNecessary data found, it\'s OK to proceed.')

# *************************************************************************
def printHelp():
    fname = os.path.basename(__file__)
    print('Usage:')
    print('\t' + fname + ' [<option>] [--pgdata=<PGDATA>] [--pginstall=<PGINSTALL>] [--pgconfig=<PGCONFIG>]')
    print('Options:')
    print('\t --help       : Print this help.')
    print('\t --last       : Rewrite last saved config. No UI.')
    print('\t --info       : Gather info about system, print it and exit.')
    print('\t                Use it as diagnostics in case of problems.')
    print('\t --version    : Print program version.')
    print('\nDisplays installed extensions for existing PostgreSQL instance and allows to\n'
          'select them for (shared/session/local)_preload_libraries. The resulting constants\n'
          'are saved to postgresql.auto.conf.')
    print('\nThe program uses three parameter constants for finding postgres instance parts:')
    print('PGDATA:     Same as the traditional value: the directory containing cluster files.\n'
          '            postgresql.auto.conf is supposed to be there already. And this is one\n'
          '            of the places to search for postgresql.conf.')
    print('PGINSTALL:  The directory containing postgres binaries. The program will search for\n'
          '            pg_config in PGINSTALL/bin (or in $PATH if PGINSTALL isn\'t set).')
    print('PGCONFIG:   Additional directory to search for postgresql.conf in case it\'s not\n'
          '            located in PGDATA. You can acquire the file location via \'SHOW config_file\'\n'
          '            request to your DB.')
    print('Each parameter can be set either as an environment variable or via command line\n'
          'parameter. None of them are required, but these help to find the required data.')
    print('What is really required:')
    print('1. postgresql.auto.conf file. We will rewrite it, but it should be there, otherwise\n'
          '   something is wrong with the system setup. The file is expected to be in PGDATA.\n'
          '   PGDATA is read either from the corresponding parameter/environment constant or\n'
          '   from the data_directory value of postgresql.conf file if PGCONFIG is given.')
    print('2. lib/share directories. These are requested from pg_config which is expected to\n'
          '   be found either in PGINSTALL/bin or somewhere in the system $PATH.')
    print('Use --info option to see which paths will be used for your system.')
# *************************************************************************
def parseArgs(args):
    doPrintInfo = False
    
    if args[0].lower() == '--last':
        doSaveLast()
        exit()
    
    if args[0].lower() == '--help':
        printHelp()
        exit()
    
    if args[0].lower() == '--version':
        global APP_VERSION
        print(APP_VERSION)
        exit()
    
    if args[0].lower() == '--info':
        doPrintInfo = True

    for arg in args:
        splitP = arg.find('=')
        if splitP <= 0:
            continue
        name = arg[:splitP].lower()
        value = arg[splitP + 1:]
        
        if name == '--pgdata':
            global PGDATA
            PGDATA = value
        elif name == '--pginstall':
            global PGINSTALL
            PGINSTALL = value            
        elif name == '--pgconfig':
            global PGCONFIG
            PGCONFIG = value            
    
    if doPrintInfo:
        gatherSystemInfo(True)
        exit()
# *************************************************************************
if __name__ == '__main__':
    if len(sys.argv) > 1:
        parseArgs(sys.argv[1:])
    
    gatherSystemInfo()
        
    if not readFiles():
        exit(1)
    
    stdscr = curses.initscr()
    
    curses.raw(True)
    curses.wrapper(win_main)
    
    curses.reset_shell_mode()
    