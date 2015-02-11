from PyQt4 import QtGui
import os

def get_icon(name):
    path = os.path.dirname(__file__)
    fname = 'icons/%s.png' % name
    
    path = os.path.join(path,fname)
    
    if not os.path.exists(path):
        raise IOError('path does not exist %s' % path)
    
    return QtGui.QIcon(path)
