'''
Created on Feb 16, 2015

@author: strandha
'''

from matplotlib.backends.qt_compat import QtGui, QtCore

# needed for compatibility with PyQt5
try:
    from matplotlib.backends.qt_compat import QtWidgets
except ImportError:
    QtWidgets = QtGui


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(ClickableLabel, self).__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        self.clicked.emit()


class CollapsibleWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(CollapsibleWidget, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout()

        self.label = ClickableLabel()
        self.label.clicked.connect(self.toggle)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                 QtWidgets.QSizePolicy.MinimumExpanding)
        layout.addWidget(self.label, stretch=0)

        self.widget = QtWidgets.QWidget()
        layout.addWidget(self.widget, stretch=1)

        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.MinimumExpanding)

    def setTitle(self, text):
        self.label.setText('<b>' + text + '</b>')

    def toggle(self):
        self.widget.setVisible(not self.widget.isVisible())

    def setWidget(self, widget):
        idx = self.children().index(self.widget)
        self.layout().removeWidget(self.widget)
        self.widget = widget
        self.layout().addWidget(self.widget, stretch=1)
        self.children()[idx].setParent(None)
