'''
Created on Feb 12, 2015

@author: strandha
'''

from PyQt4 import QtGui, QtCore

import lmfit

MODELS = {name: obj for name, obj in lmfit.models.__dict__.items()
          if name.endswith('Model') and name != 'Model'}


def generate_prefix(model, used_prefixes=[]):
    template = model.name.lstrip('Model').strip('()')[0] + '{0}_'

    i = 0

    while True:
        if template.format(i) not in used_prefixes:
            return template.format(i)

        i += 1


def update_prefix(model, prefix):
    old_prefix = model.prefix

    for param, hint in model.param_hints.items():
        try:
            expr = hint['expr']

            for name in model.param_names:
                if name in expr:
                    expr = expr.replace(name, prefix+name.lstrip(old_prefix))

            hint['expr'] = expr
        except KeyError:
            pass

    model.prefix = prefix


def add_models(model1, model2):
    if model1 is None:
        return model2

    clash_found = False
    # get list of used prefixes
    prefixes = [c.prefix for c in model1.components]

    # check if root parameter name clashes
    for c in model1.components:
        if not set(c._param_root_names).isdisjoint(model2._param_root_names):
            clash_found = True

            if c.prefix == '':
                prefix = generate_prefix(c, prefixes)
                update_prefix(c, prefix)
                prefixes.append(prefix)

    if clash_found:
        prefix = generate_prefix(model2, prefixes)
        update_prefix(model2, prefix)

    return model1 + model2


def remove_component(model, component):
    if component not in model.components:
        return model

    if len(model.components) == 1:
        return model

    component_list = model.components[:]
    component_list.remove(component)

    new_model = None

    for comp in component_list:
        new_model = add_models(new_model, comp)

    return new_model


class ModelWidget(QtGui.QDialog):
    '''
    Generate a fit model by adding predefined models from lmfit.
    '''

    _currentSelection = None

    def __init__(self, parent=None, model=None, name='MyModel'):
        self.model = model

        super(ModelWidget, self).__init__(parent=parent)

        self.setWindowTitle('Create Fit Model ...')

        layout = QtGui.QVBoxLayout()

        self.nameEdit = QtGui.QLineEdit(self)
        self.nameEdit.setText(name)
        layout.addWidget(self.nameEdit)

        modelCombo = QtGui.QComboBox(self)
        modelCombo.addItems(MODELS.keys())
        modelCombo.currentIndexChanged[QtCore.QString].connect(self.model_selected)
        modelCombo.currentIndexChanged[QtCore.QString].emit(modelCombo.currentText())

        addButton = QtGui.QPushButton('&Add')
        addButton.clicked.connect(self.add)

        modelLayout = QtGui.QHBoxLayout()
        modelLayout.addWidget(modelCombo, stretch=1)
        modelLayout.addWidget(addButton)
        layout.addItem(modelLayout)

        componentBox = QtGui.QGroupBox('Components')

        self.componentList = QtGui.QListWidget()

        self.removeButton = QtGui.QPushButton('&Remove')
        self.removeButton.clicked.connect(self.remove_component)
        self.removeButton.setEnabled(False)

        self.optButton = QtGui.QPushButton('&Options ...')
        self.optButton.clicked.connect(self.edit_options)
        self.optButton.setEnabled(False)

        self.componentList.itemClicked.connect(self.update_buttons)

        compButtonLayout = QtGui.QVBoxLayout()
        compButtonLayout.addStretch(1)
        compButtonLayout.addWidget(self.removeButton)
        compButtonLayout.addWidget(self.optButton)

        componentLayout = QtGui.QHBoxLayout()
        componentLayout.addWidget(self.componentList, stretch=1)
        componentLayout.addItem(compButtonLayout)

        componentBox.setLayout(componentLayout)
        layout.addWidget(componentBox)

        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addStretch(1)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.update_component_list()

    def add(self):
        if self._currentSelection is None:
            return

        selected_model = MODELS[self._currentSelection]()
        self.model = add_models(self.model, selected_model)
        self.update_component_list()

    def model_selected(self, model_name):
        self._currentSelection = str(model_name)

    def get_model(self):
        return str(self.nameEdit.text()), self.model

    def edit_options(self):
        raise NotImplementedError

    def remove_component(self):
        current_row = self.componentList.currentRow()
        selected_component = self.model.components[current_row]

        self.model = remove_component(self.model, selected_component)
        self.update_component_list()

    def update_component_list(self):
        self.componentList.clear()

        try:
            for comp in self.model.components:
                self.componentList.addItem(comp.name)
        except AttributeError:
            pass

    def update_buttons(self, item):
        self.removeButton.setEnabled(True)
