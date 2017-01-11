'''
Created on Feb 9, 2015

@author: strandha
'''

import __main__
import numpy as np
from .axis_span import AxisSpan
from .model_widget import ModelWidget
from .parameter_widget import ParameterWidget
from .collabpsible_widget import CollapsibleWidget
from .result_widget import ResultWidget, ResultContainer

import matplotlib as mpl
from matplotlib.backends.qt_compat import QtGui


def store_in_namespace(result):
    try:
        fr = __main__.__getattribute__('FITRESULT')
    except AttributeError:
        fr = {}
        __main__.__setattr__('FITRESULT', fr)

    if type(fr) != dict:
        print('WARNING: overwriting FITRESULT in local namespace')
        fr = {}

    fr[result.name] = result.result


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


def get_line(axes, name):
    for line in axes.get_lines():
        if line.get_label() == name:
            return line

    raise AttributeError


def get_data(artist):
    if type(artist) == mpl.lines.Line2D:
        x, y = artist.get_data()
        weights = np.ones(len(x))
    elif type(artist) == mpl.container.BarContainer:
        x = np.array([p.get_x() for p in artist.patches])
        w = np.array([p.get_width() for p in artist.patches])
        x += w / 2.
        y = np.array([p.get_height() for p in artist.patches])

        # using sqrt(y) assuming this is a bar histogram
        weights = 1. / np.sqrt(y)
        weights[np.isinf(weights)] = 0
    elif type(artist) == mpl.patches.Polygon:
        x, y = zip(*artist.get_xy())
        x = np.array(x)
        y = np.array(y)

        # using sqrt(y) assuming this is a step histogram
        weights = 1. / np.sqrt(y)
    elif type(artist) == mpl.container.ErrorbarContainer:
        x, y = artist.lines[0].get_data()

        if artist.has_yerr:
            # taking only the positive error, assuming it is symmetric
            weights = 1. / (artist.lines[1][-1].get_ydata() - y)
            weights[np.isinf(weights)] = 0
        else:
            weights = np.ones(len(x))
    else:
        msg = 'get_data is not implemented for {0}'.format(type(artist))
        raise NotImplementedError(msg)

    return x, y, weights


def markup(string):
    return string.replace('[[', '<b>').replace(']]', '</b>').replace('\n', '<br>')


class FitWidget(QtGui.QDialog):
    '''
    classdocs
    '''

    def __init__(self, parent=None, artist=None):
        '''
        Constructor
        '''
        self.artist = artist
        self.model_dict = {}
        self.range_ = None

        super(FitWidget, self).__init__(parent=parent)

        self.setWindowTitle('Fit Tool')

        layout = QtGui.QVBoxLayout()

        self.modelCombo = QtGui.QComboBox(self)
        self.modelCombo.addItems(self.model_dict.keys())
        self.modelCombo.currentIndexChanged.connect(self.enable_edit)
        self.modelCombo.currentIndexChanged.connect(self.update_parwidget)
        self.modelCombo.currentIndexChanged.connect(self.update_resultwidget)

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

        self.parameter_widget = ParameterWidget(parameters={})
        self.parameter_widget.guessClicked.connect(self.guess)
        self.parameter_widget.valueChanged.connect(self.update_parameters)
        cw = CollapsibleWidget()
        cw.setTitle('Parameters')
        cw.setWidget(self.parameter_widget)

        layout.addWidget(cw, stretch=0)

        self.result_widget = ResultWidget(parent=self)

        cw = CollapsibleWidget()
        cw.setTitle('Results')
        cw.setWidget(self.result_widget)
        layout.addWidget(cw, stretch=0)

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
        layout.addWidget(self.textBox, stretch=1)

        closeButton = QtGui.QPushButton('&Close')
        closeButton.clicked.connect(self.close)

        cbLayout = QtGui.QHBoxLayout()
        cbLayout.addStretch()
        cbLayout.addWidget(closeButton)

        layout.addItem(cbLayout)

        self.setLayout(layout)

        self.print_text = self.textBox.append

    def guess(self):
        try:
            name = str(self.modelCombo.currentText())
            model = self.model_dict[name]
        except KeyError:
            QtGui.QMessageBox.warning(self, 'Ooops...',
                                      'Please create a model')
            return

        label = 'How should the start values be guessed?'
        choices = ['full range', 'global subrange']

        if len(model.get_components()) > 1:
            choices.append('component subrange')
        text, ok = QtGui.QInputDialog.getItem(self,
                                              'Choose how to guess ...',
                                              label,
                                              choices,
                                              0, False)

        if not ok:
            return

        text = str(text)
        x, y, w = get_data(self.artist)

        if text == 'full range':
            guess = model.parameters

            for comp in model.get_components():
                guess.update(comp.guess(y, x=x))

            model.parameters = guess
            self.update_parwidget(0)

        elif text == 'global subrange':
            dlg = RangeSelector(get_axes(self.artist), parent=self)

            def cb():
                sel = (x > dlg.xmin) & (x < dlg.xmax)
                guess = model.get_parameters()

                for comp in model.get_components():
                    guess.update(comp.guess(y[sel], x=x[sel]))

                model.parameters = guess
                self.update_parwidget(0)

            dlg.accepted.connect(cb)
            dlg.show()

        elif text == 'component subrange':
            guess = model.get_parameters()

            comp_iter = iter(model.get_components())

            def call_next():
                comp = comp_iter.next()
                msg = '''Click and drag in plot window to select data range
                         for guess of component {0}
                      '''.format(comp.name)

                dlg = RangeSelector(get_axes(self.artist),
                                    parent=self, msg=msg)

                def cb():
                    sel = (x > dlg.xmin) & (x < dlg.xmax)
                    guess.update(comp.guess(y[sel], x=x[sel]))

                    try:
                        call_next()
                    except StopIteration:
                        model.set_parameters(guess)
                        self.model_dict[model.name] = model
                        self.update_parwidget(0)

                dlg.accepted.connect(cb)
                dlg.setModal(True)
                dlg.show()

            call_next()

        else:
            print('this should never happen')
            return

    def enable_edit(self, idx):
        self.editButton.setEnabled(True)

    def update_parameters(self):
        try:
            name = str(self.modelCombo.currentText())
            model = self.model_dict[name]
        except KeyError:
            QtGui.QMessageBox.warning(self, 'Ooops...',
                                      'Please create a model')

        model.update_parameters(self.parameter_widget.getValues())

    def update_parwidget(self, *args):
        try:
            name = str(self.modelCombo.currentText())
            model = self.model_dict[name]
        except KeyError:
            return

        pars = model.get_parameters()
        self.parameter_widget.updateParameters(pars)

    def update_resultwidget(self, *args):
        try:
            name = str(self.modelCombo.currentText())
            model = self.model_dict[name]
            self.result_widget.set_model(model)
        except KeyError:
            return

    def new_model(self):
        dlg = ModelWidget(parent=self)
        result = dlg.exec_()

        if result == QtGui.QDialog.Accepted:
            model = dlg.get_model()
            self.model_dict[model.name] = model
            self.modelCombo.clear()
            self.modelCombo.addItems(self.model_dict.keys())

    def edit_model(self):
        name = str(self.modelCombo.currentText())
        model = self.model_dict[name]

        dlg = ModelWidget(parent=self, model=model, name=model.name)
        result = dlg.exec_()

        if result == QtGui.QDialog.Accepted:
            model = dlg.get_model()
            self.model_dict[model.name] = model
            self.modelCombo.clear()
            self.modelCombo.addItems(self.model_dict.keys())

    def fit(self):
        model_name = str(self.modelCombo.currentText())

        try:
            model = self.model_dict[model_name]
            self.print_text('{0} selected'.format(model.name))
        except KeyError:
            QtGui.QMessageBox.warning(self, 'Ooops...',
                                      'Please create a model')
            return

        if self.artist is None:
            QtGui.QMessageBox.warning(self, 'Ooops...',
                                      'No data selected')
            return

        x, y, w = get_data(self.artist)

        if self.range_ is not None:
            sel = (x > self.range_.xmin) & (x < self.range_.xmax)
        else:
            sel = None

        result = self._perform_fit(model, x, y, w, sel)
        self._store_fit_result(model, result)
        self._plot_fit_result(result, x)

    def _perform_fit(self, model, x, y, w, sel=None):
        if sel is None:
            result = model.fit(y, x=x, weights=w,
                               params=model.get_parameters())
        else:
            result = model.fit(y[sel], x=x[sel], weights=w[sel],
                               params=model.get_parameters())

        self.print_text(result.fit_report())

        return ResultContainer(result)

    def _plot_fit_result(self, result, x, show_components=True):
        axes = get_axes(self.artist)

        hold_state = axes._hold
        axes.hold(True)
        lines = axes.plot(x, result.eval(x=x), label=result.name, lw=2)
        result.set_plot(lines[0])

        if result.get_ncomponents() > 1:
            for data in result.eval_components(x=x).values():
                line = axes.plot(x, data, '--', color=result.plot.get_color(),
                                 lw=2, label='_nolegend_')[0]

                result.add_component_plot(line)
                line.set_visible(show_components)

        axes.hold(hold_state)
        self.parent().draw()

    def _store_fit_result(self, model, result, name=None):
        if name is None:
            name = model.name + '_{0}'

        i = 0

        while True:
            if name.format(i) not in model.results:
                name = name.format(i)
                break

            i += 1

        result.name = name
        model.add_result(name, result)
        self.update_resultwidget()
        store_in_namespace(result)

    def get_range(self):
        dlg = RangeSelector(get_axes(self.artist), parent=self)

        def cb():
            self.range_ = Range(dlg.xmin, dlg.xmax)

        dlg.accepted.connect(cb)
        dlg.setModal(True)
        dlg.show()


class Range(object):
    def __init__(self, xmin, xmax):
        self.xmin = xmin
        self.xmax = xmax


class RangeSelector(QtGui.QDialog):
    def __init__(self, axes, parent=None, msg=None):
        self.ax = axes
        self.xmin = -np.inf
        self.xmax = np.inf

        super(RangeSelector, self).__init__(parent=parent)

        layout = QtGui.QVBoxLayout()

        if msg is None:
            msg = 'Click and drag in plot window to select data range'

        layout.addWidget(QtGui.QLabel(msg))
        self.setWindowTitle('Select Data Range...')

        buttonBox = QtGui.QHBoxLayout()
        buttonBox.addStretch(1)

        okButton = QtGui.QPushButton('&Ok')
        okButton.clicked.connect(self.accept)
        buttonBox.addWidget(okButton)

        cancelButton = QtGui.QPushButton('&Cancel')
        cancelButton.clicked.connect(self.reject)
        buttonBox.addWidget(cancelButton)

        buttonBox.addStretch(1)
        layout.addItem(buttonBox)
        self.setLayout(layout)

        self.connect = self.ax.figure.canvas.mpl_connect
        self.disconnect = self.ax.figure.canvas.mpl_disconnect

    def on_click(self, event):
        def onselect(xmin, xmax):
            self.disconnect(self.cid)
            self.xmin, self.xmax = xmin, xmax
            self.parent().print_text('range selected for fit: {0:7.2g} ... {1:7.2g}'.format(xmin, xmax))

            super(RangeSelector, self).accept()

        self.span = AxisSpan(self.ax,
                             event,
                             onselect,
                             'horizontal',
                             color='black',
                             alpha=.7,
                             drawmode='inverted')

    def accept(self):
        self.setModal(False)
        self.cid = self.connect('button_press_event', self.on_click)
        self.hide()
