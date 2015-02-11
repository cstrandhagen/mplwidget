# -*- coding: utf-8 -*-
"""
Created on Wed Feb  1 11:35:48 2012

@author: strandha
"""
        
class AxisPan(object):
    def __init__(self,axes,event):
        self.lim           = axes.viewLim.frozen()
        self.trans         = axes.transData.frozen()
        self.trans_inverse = axes.transData.inverted().frozen()
        self.bbox          = axes.bbox.frozen()
        self.x             = event.x
        self.y             = event.y
        self.button        = event.button
        self.axes          = axes
    
    def drag(self,event):
        key = event.key
        def format_deltas(key, dx, dy):
            if key=='control':
                if(abs(dx)>abs(dy)):
                    dy = dx
                else:
                    dx = dy
            elif key=='x':
                dy = 0
            elif key=='y':
                dx = 0
            elif key=='shift':
                if 2*abs(dx) < abs(dy):
                    dx=0
                elif 2*abs(dy) < abs(dx):
                    dy=0
                elif(abs(dx)>abs(dy)):
                    dy=dy/abs(dy)*abs(dx)
                else:
                    dx=dx/abs(dx)*abs(dy)
            return (dx,dy)

        dx = event.x - self.x
        dy = event.y - self.y
        
        if dx == 0 and dy == 0:
            return
        
        dx, dy = format_deltas(key, dx, dy)
        result = self.bbox.translated(-dx, -dy).transformed(self.trans_inverse)
        
        self.axes.set_xlim(*result.intervalx)
        self.axes.set_ylim(*result.intervaly)