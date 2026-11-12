import os
import sys

base = getattr(sys, '_MEIPASS', None)
if base:
    os.environ.setdefault('TCL_LIBRARY', os.path.join(base, 'tcl', 'tcl8.6'))
    os.environ.setdefault('TK_LIBRARY', os.path.join(base, 'tcl', 'tk8.6'))
