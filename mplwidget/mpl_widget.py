# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License

"""
MatplotlibWidget
================

Example of matplotlib widget for PyQt4

Copyright © 2009 Pierre Raybaut
This software is licensed under the terms of the MIT License

Derived from 'embedding_in_pyqt4.py':
Copyright © 2005 Florent Rougon, 2006 Darren Dale
"""

__version__ = "1.0.0"

from PyQt4 import QtCore,QtGui

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from navtoolbar import NavigationToolbar

def axis_labels_overlap(axis):
    bb = [t.label.get_window_extent() for t in axis.get_major_ticks()]
    print 'overlap', len(bb), bb[0].count_overlaps(bb[1:])
    return bool(bb[0].count_overlaps(bb[1:]))

def reduce_number_of_axis_labels(axis):
    n = len(axis.get_major_ticks())
    
    while axis_labels_overlap(axis) and n > 3:
        print n
        n -= 1
        axis.set_major_locator(MaxNLocator(n))

def increase_number_of_axis_labels(axis):
    n = len(axis.get_major_ticks())
    
    while not axis_labels_overlap(axis):
        print n
        n *= 2
        axis.set_major_locator(MaxNLocator(n))
    
    reduce_number_of_axis_labels(axis)

def adjust_axis_labels(axes):
    for axis in [axes.yaxis,axes.xaxis]:
        print axis
        if axis_labels_overlap(axis):
            print 'reducing'
            reduce_number_of_axis_labels(axis)
        #else:
        #    print 'increasing'
        #    increase_number_of_axis_labels(axis)

class MatplotlibWidget(Canvas):
    """
    MatplotlibWidget inherits PyQt4.QtGui.QWidget
    and matplotlib.backend_bases.FigureCanvasBase
   
    Options: option_name (default_value)
    -------    
    parent (None): parent widget
    title (''): figure title
    xlabel (''): X-axis label
    ylabel (''): Y-axis label
    xlim (None): X-axis limits ([min, max])
    ylim (None): Y-axis limits ([min, max])
    xscale ('linear'): X-axis scale
    yscale ('linear'): Y-axis scale
    width (4): width in inches
    height (3): height in inches
    dpi (100): resolution in dpi
    hold (False): if False, figure will be cleared each time plot is called
   
    Widget attributes:
    -----------------
    figure: instance of matplotlib.figure.Figure
    axes: figure axes
   
    Example:
    -------
    self.widget = MatplotlibWidget(self, yscale='log', hold=True)
    from numpy import linspace
    x = linspace(-10, 10)
    self.widget.axes.plot(x, x**2)
    self.wdiget.axes.plot(x, x**3)
    """
    canvasUpdated = QtCore.pyqtSignal()
    
    def __init__(self, parent=None, title='', xlabel='', ylabel='',
                 xlim=None, ylim=None, xscale='linear', yscale='linear',
                 width=4, height=3, dpi=100, hold=False):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        if xscale is not None:
            self.axes.set_xscale(xscale)
        if yscale is not None:
            self.axes.set_yscale(yscale)
        if xlim is not None:
            self.axes.set_xlim(*xlim)
        if ylim is not None:
            self.axes.set_ylim(*ylim)
        self.axes.hold(hold)

        Canvas.__init__(self, self.figure)
        self.setParent(parent)

        Canvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, 
                             QtGui.QSizePolicy.Expanding)
        Canvas.updateGeometry(self)
        
        self.toolbar = NavigationToolbar(self,self)
        
    def sizeHint(self):
        w, h = self.get_width_height()
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        return QtCore.QSize(10, 10)
    
    @QtCore.pyqtSlot()
    def draw(self):
        super(MatplotlibWidget,self).draw()
        #adjust_axis_labels(self.axes)
        self.canvasUpdated.emit()


#===============================================================================
#   Example
#===============================================================================
if __name__ == '__main__':
    import sys
    from PyQt4.QtGui import QMainWindow, QApplication
    from numpy import linspace
   
    class ApplicationWindow(QMainWindow):
        def __init__(self):
            QMainWindow.__init__(self)
            self.mplwidget = MatplotlibWidget(self, title='Example',
                                              xlabel='Linear scale',
                                              ylabel='Log scale',
                                              hold=True)
            self.mplwidget.setFocus()
            self.setCentralWidget(self.mplwidget)
            self.plot(self.mplwidget.axes)
           
        def plot(self, axes):
            x = linspace(-10, 10)
            axes.plot(x, x**2)
            axes.plot(x, x**3)
       
    app = QApplication(sys.argv)
    win = ApplicationWindow()
    win.show()
    sys.exit(app.exec_())
