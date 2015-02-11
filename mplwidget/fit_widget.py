'''
Created on Feb 9, 2015

@author: strandha
'''

import lmfit
import matplotlib as mpl
import numpy as np
from .axis_span import AxisSpan

from PyQt4 import QtCore,QtGui

MODELS = {'Gaussian':lmfit.models.GaussianModel,
          'Lorentzian':lmfit.models.LorentzianModel}

def get_axes(artist):
    if type(artist) == mpl.lines.Line2D:
        axes = artist.axes
    elif type(artist) == mpl.container.BarContainer:
        axes = artist.patches[0].axes
    else:
        raise NotImplementedError
    
    return axes

def get_data(artist):
    if type(artist) == mpl.lines.Line2D:
        x,y = artist.get_data()
    elif type(artist) == mpl.container.BarContainer:
        x = np.array([p.get_x() for p in artist.patches])
        w = np.array([p.get_width() for p in artist.patches])
        x += w/2.
        y = np.array([p.get_height() for p in artist.patches])
    else:
        raise NotImplementedError
    
    return x,y

class FitWidget(QtGui.QDialog):
    '''
    classdocs
    '''
    model = None
    range = None
    

    def __init__(self, parent = None, artist = None):
        '''
        Constructor
        '''
        self.artist = artist
        
        super(FitWidget,self).__init__(parent=parent)
        
        layout = QtGui.QVBoxLayout()
        
        modelCombo = QtGui.QComboBox(self)
        modelCombo.addItems(MODELS.keys())
        modelCombo.currentIndexChanged[QtCore.QString].connect(self.modelSelected)
        
        layout.addWidget(modelCombo)
        
        fitButton = QtGui.QPushButton('&Fit',self)
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
    
    def modelSelected(self,model_name):
        self.print_text('selected model {0}\n'.format(model_name))
        self.model = MODELS[str(model_name)]
    
    def fit(self):
        if self.model is None:
            self.print_text('please select a model\n')
        elif self.artist is None:
            self.print_text('no data passed\n')
        else:
            x,y = get_data(self.artist)
            
            model = self.model()
            
            if self.range is not None:
                sel = (x>self.range.xmin)&(x<self.range.xmax)
                self.res = model.fit(y[sel],x=x[sel],params=model.guess(y[sel],x=x[sel]))
            else:
                self.res = model.fit(y,x=x,params=model.guess(y,x=x))
            
            
            self.print_text(self.res.fit_report())
            
            axes = get_axes(self.artist)
            
            hold_state = axes._hold
            axes.hold(True)
            axes.plot(x,self.res.eval(x=x),label='fit_result',color='b')
            axes.hold(hold_state)
            
            self.parent().draw()
    
    def get_range(self):
        axes = get_axes(self.artist)
        
        if self.range is not None:
            del self.range
        
        self.range = RangeSelector(self,axes)  

class RangeSelector(object):
    def __init__(self,parent,axes):
        self.xmin = None
        self.xmax = None
        
        self.ax = axes
        self.parent = parent
        
        self.connect = self.ax.figure.canvas.mpl_connect
        self.disconnect = self.ax.figure.canvas.mpl_disconnect

        self.cid = self.connect('button_press_event',self.on_click)
        
    
    def on_click(self,event):
        def onselect(xmin,xmax):
            self.disconnect(self.cid)
            self.xmin,self.xmax = xmin,xmax
            self.parent.print_text('range selected for fit: {0:7.2g} ... {1:7.2g}'.format(xmin,xmax))
        
        self.span = AxisSpan(self.ax,event,onselect,'horizontal',color='black',alpha=.7,drawmode='inverted')
             
    
        
        