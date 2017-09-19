'''
Created on Feb 16, 2015

@author: strandha
'''

from matplotlib.backends.qt_compat import QtCore, QtGui
import numpy as np

# needed for compatibility with PyQt5
try:
    from matplotlib.backends.qt_compat import QtWidgets
except ImportError:
    QtWidgets = QtGui


class ParameterGrid(QtWidgets.QWidget):
    updatedPars = QtCore.Signal()

    def __init__(self, parameters, parent=None):
        super(ParameterGrid, self).__init__(parent=parent)

        self.parameters = parameters

        layout = self.createLayout()

        self.setLayout(layout)

    def createLayout(self):
        layout = QtWidgets.QGridLayout()

        # header row
        layout.addWidget(QtWidgets.QLabel('<b>Parameter Name</b>'), 0, 0)
        layout.addWidget(QtWidgets.QLabel('<b>Value</b>'), 0, 1)
        layout.addWidget(QtWidgets.QLabel('<b>Lower</b>'), 0, 2)
        layout.addWidget(QtWidgets.QLabel('<b>Upper</b>'), 0, 3)
        layout.addWidget(QtWidgets.QLabel('<b>Fixed</b>'), 0, 4)
        layout.itemAt(0).widget().setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                                QtWidgets.QSizePolicy.Fixed)

        for name, par in sorted(self.parameters.items()):
            self._addRow(layout, par)

        return layout

    def _addRow(self, layout, parameter):
        row = layout.rowCount()

        layout.addWidget(QtWidgets.QLabel(parameter.name), row, 0,
                         QtCore.Qt.AlignRight)

        sb = QtWidgets.QDoubleSpinBox()
        sb.valueChanged.connect(self.updatedPars.emit)
        sb.setRange(-np.inf, np.inf)
        if parameter.value is not None:
            sb.setValue(parameter.value)

        layout.addWidget(sb, row, 1)

        sb = QtWidgets.QDoubleSpinBox()
        sb.valueChanged.connect(self.updatedPars.emit)
        sb.setRange(-np.inf, np.inf)
        if parameter.min is not None:
            sb.setValue(parameter.min)

        layout.addWidget(sb, row, 2)

        sb = QtWidgets.QDoubleSpinBox()
        sb.valueChanged.connect(self.updatedPars.emit)
        sb.setRange(-np.inf, np.inf)
        if parameter.max is not None:
            sb.setValue(parameter.max)

        layout.addWidget(sb, row, 3)

        cb = QtWidgets.QCheckBox()
        cb.stateChanged.connect(self.updatedPars.emit)
        cb.setChecked(not parameter.vary)
        layout.addWidget(cb, row, 4, QtCore.Qt.AlignCenter)

    def getValues(self):
        layout = self.layout()
        values = {}

        for i in xrange(1, layout.rowCount()):
            name = str(layout.itemAtPosition(i, 0).widget().text())
            values[name] = {}
            value = layout.itemAtPosition(i, 1).widget().value()
            values[name]['value'] = value
            lower = layout.itemAtPosition(i, 2).widget().value()
            values[name]['lower'] = lower
            upper = layout.itemAtPosition(i, 3).widget().value()
            values[name]['upper'] = upper
            fixed = layout.itemAtPosition(i, 4).widget().isChecked()
            values[name]['fixed'] = fixed

        return values


class ParameterWidget(QtWidgets.QWidget):
    guessClicked = QtCore.Signal()
    valueChanged = QtCore.Signal()

    def __init__(self, parameters, parent=None):
        super(ParameterWidget, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout()

        self.parGrid = ParameterGrid(parameters, parent=self)
        self.parGrid.updatedPars.connect(self.valueChanged.emit)
        self.parGrid.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                   QtWidgets.QSizePolicy.MinimumExpanding)
        layout.addWidget(self.parGrid)

        guessButton = QtWidgets.QPushButton('&Guess')
        guessButton.clicked.connect(self.guessClicked.emit)
        buttonBox = QtWidgets.QHBoxLayout()
        buttonBox.addStretch(1)
        buttonBox.addWidget(guessButton)

        layout.addItem(buttonBox)

        self.setLayout(layout)

    def updateParameters(self, parameters):
        idx = self.children().index(self.parGrid)
        self.layout().removeWidget(self.parGrid)
        self.parGrid = ParameterGrid(parameters)
        self.parGrid.updatedPars.connect(self.valueChanged.emit)
        self.parGrid.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                   QtWidgets.QSizePolicy.MinimumExpanding)
        self.layout().insertWidget(0, self.parGrid)
        self.children()[idx].setParent(None)

    def getValues(self):
        return self.parGrid.getValues()
