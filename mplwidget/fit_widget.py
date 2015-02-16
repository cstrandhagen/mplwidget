'''
Created on Feb 9, 2015

@author: strandha
'''

import numpy as np
from .axis_span import AxisSpan
from .model_widget import ModelWidget

import matplotlib as mpl
from matplotlib.backends.qt_compat import QtGui


def get_axes(artist):
    if hasattr(artist, 'get_axes'):
        axes = artist.get_axes()
    elif type(artist) == mpl.container.BarContainer:
        axes = artist.patches[0].axes
    elif type(artist) == mpl.container.ErrorbarContainer:
        axes = artist.lines[0].get_axes()
    else:
        msg = 'get_axes is not implemented for {0}'.format(type(artist))
        raise NotImplementedError(msg)

    return axes


def get_data(artist):
    if type(artist) == mpl.lines.Line2D:
        x, y = artist.get_data()
        weights = np.ones(len(x))
    elif type(artist) == mpl.container.BarContainer:
        x = np.array([p.get_x() for p in artist.patches])
        w = np.array([p.get_width() for p in artist.patches])
        x += w/2.
        y = np.array([p.get_height() for p in artist.patches])
        # using sqrt(y) assuming this is a bar histogram
        weights = 1./np.sqrt(y)
        weights[np.isinf(weights)] = 0
    elif type(artist) == mpl.patches.Polygon:
        x, y = zip(*artist.get_xy())
        x = np.array(x)
        y = np.array(y)
        # using sqrt(y) assuming this is a step histogram
        weights = np.sqrt(y)
    elif type(artist) == mpl.container.ErrorbarContainer:
        x, y = artist.lines[0].get_data()

        if artist.has_yerr:
            # taking only the positive error, assuming it is symmetric
            weights = 1./(artist.lines[1][-1].get_ydata() - y)
            weights[np.isinf(weights)] = 0
        else:
            weights = np.ones(len(x))
    else:
        msg = 'get_data is not implemented for {0}'.format(type(artist))
        raise NotImplementedError(msg)

    return x, y, weights


class FitWidget(QtGui.QDialog):
    '''
    classdocs
    '''
    model = None
    model_dict = {}
    range_ = None

    def __init__(self, parent=None, artist=None):
        '''
        Constructor
        '''
        self.artist = artist

        super(FitWidget, self).__init__(parent=parent)

        self.setWindowTitle('Fit Tool')

        layout = QtGui.QVBoxLayout()

        self.modelCombo = QtGui.QComboBox(self)
        self.modelCombo.addItems(self.model_dict.keys())
        self.modelCombo.currentIndexChanged.connect(self.enable_edit)

        newButton = QtGui.QPushButton('&New')
        newButton.clicked.connect(self.new_model)

        self.editButton = QtGui.QPushButton('&Edit')
        self.editButton.clicked.connect(self.edit_model)
        self.editButton.setEnabled(False)

        modelLayout = QtGui.QHBoxLayout()
        modelLayout.addWidget(self.modelCombo, stretch=1)
        modelLayout.addWidget(newButton, stretch=0)
        modelLayout.addWidget(self.editButton)

        layout.addItem(modelLayout)

        fitButton = QtGui.QPushButton('&Fit', self)
        fitButton.clicked.connect(self.fit)

        rngButton = QtGui.QPushButton('Select &Range')
        rngButton.clicked.connect(self.get_range)

        fbLayout = QtGui.QHBoxLayout()
        fbLayout.addStretch()
        fbLayout.addWidget(rngButton)
        fbLayout.addWidget(fitButton)

        layout.addItem(fbLayout)

        self.textBox = QtGui.QTextEdit(self)
        self.textBox.setReadOnly(True)
        layout.addWidget(self.textBox)

        closeButton = QtGui.QPushButton('&Close')
        closeButton.clicked.connect(self.close)

        cbLayout = QtGui.QHBoxLayout()
        cbLayout.addStretch()
        cbLayout.addWidget(closeButton)

        layout.addItem(cbLayout)

        self.setLayout(layout)

        self.print_text = self.textBox.append

    def enable_edit(self, idx):
        self.editButton.setEnabled(True)

    def new_model(self):
        dlg = ModelWidget()
        result = dlg.exec_()

        if result == QtGui.QDialog.Accepted:
            name, model = dlg.get_model()
            self.model_dict[name] = model
            self.modelCombo.clear()
            self.modelCombo.addItems(self.model_dict.keys())

    def edit_model(self):
        name = str(self.modelCombo.currentText())
        model = self.model_dict[name]

        dlg = ModelWidget(model=model, name=name)
        result = dlg.exec_()

        if result == QtGui.QDialog.Accepted:
            name, model = dlg.get_model()
            self.model_dict[name] = model
            self.modelCombo.clear()
            self.modelCombo.addItems(self.model_dict.keys())

    def fit(self):
        model_name = str(self.modelCombo.currentText())

        try:
            model = self.model_dict[model_name]
            self.print_text('{0} selected'.format(model_name))
        except KeyError:
            self.print_text('please select a model\n')
            return

        if self.artist is None:
            self.print_text('no data passed\n')
            return

        x, y, w = get_data(self.artist)

        guess = model.make_params()

        if self.range_ is not None:
            sel = (x > self.range_.xmin) & (x < self.range_.xmax)

            for comp in model.components:
                guess.update(comp.guess(y[sel], x=x[sel]))

            result = model.fit(y[sel], x=x[sel], weights=w[sel], params=guess)
        else:
            for comp in model.components:
                guess.update(comp.guess(y, x=x))

            result = model.fit(y, x=x, weights=w, params=guess)

        self.print_text(result.fit_report())

        axes = get_axes(self.artist)

        hold_state = axes._hold
        axes.hold(True)
        axes.plot(x, result.eval(x=x), label='fit_result', color='b')
        axes.hold(hold_state)

        self.parent().draw()

    def get_range(self):
        axes = get_axes(self.artist)

        if self.range_ is not None:
            del self.range_

        self.range_ = RangeSelector(self, axes)


class RangeSelector(object):
    def __init__(self, parent, axes):
        self.xmin = None
        self.xmax = None

        self.ax = axes
        self.parent = parent

        self.connect = self.ax.figure.canvas.mpl_connect
        self.disconnect = self.ax.figure.canvas.mpl_disconnect

        self.cid = self.connect('button_press_event', self.on_click)

    def on_click(self, event):
        def onselect(xmin, xmax):
            self.disconnect(self.cid)
            self.xmin, self.xmax = xmin, xmax
            self.parent.print_text('range selected for fit: {0:7.2g} ... {1:7.2g}'.format(xmin, xmax))

        self.span = AxisSpan(self.ax,
                             event,
                             onselect,
                             'horizontal',
                             color='black',
                             alpha=.7,
                             drawmode='inverted')
