'''
Created on Feb 12, 2015

@author: strandha
'''

from matplotlib.backends.qt_compat import QtGui, QtCore

import inspect
import lmfit
from .models import model_dict

MODELS = {name: obj for name, obj in lmfit.models.__dict__.items()
          if name.endswith('Model') and name != 'Model'}

MODELS.update(model_dict)


def get_required_args(func):
    argspec = inspect.getargspec(func)

    required_args = argspec[0]
    if argspec[3] is not None:
        required_args = required_args[:len(argspec[3])]

    required_args.remove('self')

    return required_args


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
                    expr = expr.replace(name, prefix + name.lstrip(old_prefix))

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
        return None

    component_list = model.components[:]
    component_list.remove(component)

    new_model = None

    for comp in component_list:
        new_model = add_models(new_model, comp)

    return new_model


class ModelContainer(object):
    def __init__(self, name='', model=None, parameters=None, results=None):
        self.name = name
        self.model = model
        self.parameters = parameters

        if results is None:
            results = {}

        self.results = results

    def add_component(self, component):
        self.model = add_models(self.model, component)

    def remove_component(self, idx):
        selected_component = self.model.components[idx]
        self.model = remove_component(self.model, selected_component)

    def set_name(self, name):
        self.name = str(name)

    def get_components(self):
        return self.model.components

    def get_parameters(self):
        if self.parameters is None:
            self.parameters = self.model.make_params()

        if set(self.parameters.keys()) != set(self.model.make_params().keys()):
            self.parameters = self.model.make_params()

        return self.parameters

    def set_parameters(self, parameters):
        self.parameters = parameters

    def fit(self, *args, **kwargs):
        return self.model.fit(*args, **kwargs)

    def update_parameters(self, value_dict):
        for par in self.parameters.values():
            v = value_dict[par.name]
            par.value = v['value']
            par.min = v['lower']
            par.max = v['upper']
            par.vary = not v['fixed']

    def add_result(self, name, result):
        self.results[name] = result

    def remove_result(self, name):
        try:
            self.results.pop(name)
        except KeyError:
            print 'DEBUG: no such result ', name
            pass


class ModelWidget(QtGui.QDialog):
    '''
    Generate a fit model by adding predefined models from lmfit.
    '''
    def __init__(self, parent=None, model=None, name='MyModel'):
        if model is None:
            model = ModelContainer()

        self.model = model
        self._currentSelection = None

        super(ModelWidget, self).__init__(parent=parent)

        self.setWindowTitle('Create Fit Model ...')

        layout = QtGui.QVBoxLayout()

        nameEdit = QtGui.QLineEdit(self)
        nameEdit.textChanged.connect(self.model.set_name)
        nameEdit.setText(name)
        layout.addWidget(nameEdit)

        modelCombo = QtGui.QComboBox(self)
        modelCombo.setInsertPolicy(QtGui.QComboBox.InsertAlphabetically)
        modelCombo.addItems(sorted(MODELS.keys()))
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

        selected_model = MODELS[self._currentSelection]
        required_args = get_required_args(selected_model.__init__)

        args = []

        for argname in required_args:
            text, ok = QtGui.QInputDialog.getText(self,
                                                  'Set Required Parameter',
                                                  argname)

            if ok is False:
                return

            text = str(text)

            if text.replace('.', '').isdigit():
                if '.' in text:
                    args.append(float(text))
                else:
                    args.append(int(text))
            else:
                args.append(text)

        try:
            self.model.add_component(selected_model(*args))
            self.update_component_list()
        except Exception as exc:
            message = '<b>{0}</b><br><br>{1}'.format(type(exc).__name__,
                                                     exc.message)

            QtGui.QMessageBox.critical(self, 'Ooops...', message)
            self.add()

    def model_selected(self, model_name):
        self._currentSelection = str(model_name)

    def get_model(self):
        return self.model

    def edit_options(self):
        raise NotImplementedError

    def remove_component(self):
        idx = self.componentList.currentRow()
        self.model.remove_component(idx)
        self.update_component_list()

    def update_component_list(self):
        self.componentList.clear()

        try:
            for comp in self.model.get_components():
                self.componentList.addItem(comp.name)
        except AttributeError:
            pass

    def update_buttons(self, item):
        self.removeButton.setEnabled(True)
