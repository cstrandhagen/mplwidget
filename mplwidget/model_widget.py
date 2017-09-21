'''
Created on Feb 12, 2015

@author: strandha
'''

from matplotlib.backends.qt_compat import QtGui, QtCore

# needed for compatibility with PyQt5
try:
    from matplotlib.backends.qt_compat import QtWidgets
except ImportError:
    QtWidgets = QtGui

import inspect
import lmfit
from .models import model_dict


MODELS = {name: obj for name, obj in lmfit.models.__dict__.items()
          if name.endswith('Model') and name != 'Model'}

MODELS.update(model_dict)


def get_required_args(func):
    '''
    Get required arguments of a function by inspecting the signature.

    Parameters
    ----------
    func : function
        A python function.

    Returns
    -------
    required_args : list(str)
        Names of the required function arguments.
    '''
    argspec = inspect.getargspec(func)

    # argspec[0] gives a list of all arguments
    # this list includes optional arguments which are at the end of the list
    required_args = argspec[0]

    # argspec[3] is a list of default values
    # cutting of the last n arguments (where n is the number of default values)
    # leaves only the required arguments
    if argspec[3] is not None:
        required_args = required_args[:-len(argspec[3])]

    # for class methods 'self' is a required argument and has to be removed
    required_args.remove('self')

    return required_args


def generate_prefix(model, used_prefixes=[]):
    '''
    Generate a new model prefix from the model name.

    Model prefixes have the form of "L#_" where "L" is the first letter
    of the model name and "#" is a number starting from 0. To prevent
    duplicates a list of used prefixes can be supplied. Prefixes are
    created starting from 0 and if the prefix is already in that list,
    the number is increased by 1 until a unique prefix is found.
    '''
    template = model.name.lstrip('Model').strip('()')[0] + '{0}_'

    i = 0

    while True:
        if template.format(i) not in used_prefixes:
            return template.format(i)

        i += 1


def add_models(model1, model2):
    '''
    Add model2 to model1.

    Model1 may be a composite model, model2 must not be a composite model.

    Parameters
    ----------
    model1 : lmfit.Model
        lmfit fit model (may be composite)
    model2 : lmfit.Model
        lmfit fit model (must not be composite!)

    Returns
    -------
    model : lmfit.Model
        A composite lmfit fit model.
    '''
    if model1 is None:
        return model2

    # get list of already used prefixes, needed to create new prefixes
    prefixes = [comp.prefix for comp in model1.components]

    # extract root parameter names of model2 to check for duplicate names
    mod2_params = set(model2._param_root_names)

    # check if the root parameter names of model2 already occur in the
    # components of model1
    for comp in model1.components:
        if not mod2_params.isdisjoint(comp._param_root_names):
            # at least one of the parameter names exists in both models
            # create a new prefix for model2 and add it to the list of
            # already used prefixes
            prefix = generate_prefix(model2, prefixes)
            prefixes += [prefix]

            # since somehow the prefix of an existing model cannot be changed,
            # recreate a model of the same class with the new prefix
            model2 = model2.__class__(prefix=prefix)

            # no need to check additional components since we already now there
            # is a duplicate and the prefix is added to model2
            break

    # the goal is that all models with duplicate parameter names have a prefix
    # so we still need to check if all components of model1 with duplicate
    # parameter names already have a prefix and add one if this is not the case
    for comp in model1.components:
        # check if there are duplicate parameter names
        if not mod2_params.isdisjoint(comp._param_root_names):
            if comp.prefix == '':
                # the component does not have a prefix yet, so add one
                prefix = generate_prefix(comp, prefixes)
                prefixes += [prefix]
                comp = comp.__class__(prefix=prefix)

        model2 += comp

    return model2


def remove_component(model, component):
    '''
    Remove component from a composite lmfit model.

    Works by recreating the model by adding the individual
    components back together and omitting the component we
    want to remove.

    Parameters
    ----------
    model : lmfit.Model
        A (composite) lmfit fit model.
    component : lmfit.Model
        lmfit model component to remove.

    Returns
    -------
    model : lmfit.Model
        The original fit model without the component.
    '''
    if component not in model.components:
        return model

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
            print('DEBUG: no such result {0}'.format(name))
            pass


class ModelWidget(QtWidgets.QDialog):
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

        layout = QtWidgets.QVBoxLayout()

        nameEdit = QtWidgets.QLineEdit(self)
        nameEdit.textChanged.connect(self.model.set_name)
        nameEdit.setText(name)
        layout.addWidget(nameEdit)

        modelCombo = QtWidgets.QComboBox(self)
        modelCombo.setInsertPolicy(QtWidgets.QComboBox.InsertAlphabetically)
        modelCombo.addItems(sorted(MODELS.keys()))
        modelCombo.currentIndexChanged[str].connect(self.model_selected)
        modelCombo.currentIndexChanged[str].emit(modelCombo.currentText())

        addButton = QtWidgets.QPushButton('&Add')
        addButton.clicked.connect(self.add)

        modelLayout = QtWidgets.QHBoxLayout()
        modelLayout.addWidget(modelCombo, stretch=1)
        modelLayout.addWidget(addButton)
        layout.addItem(modelLayout)

        componentBox = QtWidgets.QGroupBox('Components')

        self.componentList = QtWidgets.QListWidget()

        self.removeButton = QtWidgets.QPushButton('&Remove')
        self.removeButton.clicked.connect(self.remove_component)
        self.removeButton.setEnabled(False)

        self.optButton = QtWidgets.QPushButton('&Options ...')
        self.optButton.clicked.connect(self.edit_options)
        self.optButton.setEnabled(False)

        self.componentList.itemClicked.connect(self.update_buttons)

        compButtonLayout = QtWidgets.QVBoxLayout()
        compButtonLayout.addStretch(1)
        compButtonLayout.addWidget(self.removeButton)
        compButtonLayout.addWidget(self.optButton)

        componentLayout = QtWidgets.QHBoxLayout()
        componentLayout.addWidget(self.componentList, stretch=1)
        componentLayout.addItem(compButtonLayout)

        componentBox.setLayout(componentLayout)
        layout.addWidget(componentBox)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
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
            text, ok = QtWidgets.QInputDialog.getText(self,
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

            QtWidgets.QMessageBox.critical(self, 'Ooops...', message)
            # self.add()

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
