from qtools.qtpy.QtCore import Qt 
from qtools.qtpy import QtGui, QT_BINDING, QT_BINDING_VERSION
import os

__all__ = ['get_cursor']

getpath = lambda file: os.path.join(os.path.dirname(__file__), file)

if QT_BINDING == 'pyside' and QT_BINDING_VERSION <= '1.1.1':
    def get_cursor(name):
        return None
else:
    def get_cursor(name):
        if name is None:
            name = 'ArrowCursor'
        if name == 'MagnifyingGlassCursor':
            MagnifyingGlassPixmap = QtGui.QPixmap(getpath("cursors/magnifyingglass2.png"))
            MagnifyingGlassPixmap.setMask(QtGui.QBitmap(\
                                          QtGui.QPixmap(getpath("cursors/magnifyingglass1.png"))))
            MagnifyingGlassCursor = QtGui.QCursor(MagnifyingGlassPixmap)
            return MagnifyingGlassCursor
        else:
            return QtGui.QCursor(getattr(Qt, name))
        