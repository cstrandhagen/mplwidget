'''
Created on Feb 18, 2015

@author: strandha
'''

from matplotlib.backends.qt_compat import QtCore, QtGui


class ResultContainer(object):
    def __init__(self, result, name='', plot=None, component_plots=None):
        self.result = result
        self.plot = plot
        self.name = name

        if component_plots is None:
            component_plots = []

        self.component_plots = component_plots

    def set_plot(self, line):
        self.plot = line

    def add_component_plot(self, line):
        self.component_plots.append(line)

    def get_ncomponents(self):
        return len(self.result.components)

    def toggle_plot(self, show=None):
        if self.plot is None:
            return

        if show is None:
            show = not self.plot.get_visible()

        self.plot.set_visible(show)
        self.plot.figure.canvas.draw()

    def toggle_components(self, show=None):
        if len(self.component_plots) == 0:
            return

        if show is None:
            show = not self.component_plots[0].get_visible()

        for line in self.component_plots:
            line.set_visible(show)

        line.figure.canvas.draw()

    def has_components(self):
        return bool(len(self.component_plots))

    def eval(self, *args, **kwargs):
        return self.result.eval(*args, **kwargs)

    def eval_components(self, *args, **kwargs):
        return self.result.eval_components(*args, **kwargs)


class ResultWidget(QtGui.QWidget):
    componentsToggled = QtCore.Signal(bool)
    removed = QtCore.Signal(str)

    def __init__(self, parent=None, model=None):
        self.model = model

        super(ResultWidget, self).__init__(parent=parent)

        layout = QtGui.QHBoxLayout()

        self.resultList = QtGui.QListWidget()
        self.resultList.itemClicked.connect(self.update_buttons)
        layout.addWidget(self.resultList, stretch=1)

        buttonBox = QtGui.QVBoxLayout()
        buttonBox.addStretch(1)

        self.compCheck = QtGui.QCheckBox()
        self.compCheck.setText('Show components')
        self.compCheck.setEnabled(False)
        self.compCheck.toggled.connect(self.toggle_components)
        buttonBox.addWidget(self.compCheck)

        self.removeButton = QtGui.QPushButton('&Remove')
        self.removeButton.setEnabled(False)
        self.removeButton.clicked.connect(self.remove_result)
        buttonBox.addWidget(self.removeButton)

        self.showButton = QtGui.QPushButton('Show/Hide')
        self.showButton.setEnabled(False)
        self.showButton.clicked.connect(self.toggle_plot)
        buttonBox.addWidget(self.showButton)

        layout.addItem(buttonBox)

        self.setLayout(layout)

        self.update_result_list()

    def update_buttons(self, *args):
        result = self._get_current_result()

        if self.resultList.count() > 0:
            self.compCheck.setEnabled(True)
            self.removeButton.setEnabled(True)
            self.showButton.setEnabled(True)
        else:
            self.compCheck.setEnabled(False)
            self.removeButton.setEnabled(False)
            self.showButton.setEnabled(False)

        if not result.has_components():
            self.compCheck.setEnabled(False)
        else:
            visible = result.component_plots[0].get_visible()
            self.compCheck.setChecked(visible)

    def update_result_list(self):
        self.resultList.clear()

        try:
            for result_name in sorted(self.model.results.keys()):
                self.resultList.addItem(result_name)
        except AttributeError:
            pass

    def set_model(self, model):
        self.model = model
        self.update_result_list()

    def remove_result(self):
        name = str(self.resultList.currentItem().text())
        self.model.remove_result(name)
        self.removed.emit(name)
        self.update_result_list()
        self.update_buttons()

    def toggle_plot(self):
        result = self._get_current_result()
        result.toggle_plot()

    def toggle_components(self):
        result = self._get_current_result()
        result.toggle_components()

    def _get_current_result(self):
        name = str(self.resultList.currentItem().text())
        return self.model.results[name]
