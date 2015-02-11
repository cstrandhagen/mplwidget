# -*- coding: utf-8 -*-
"""
Created on Wed Feb  1 11:35:48 2012

@author: strandha
"""
from matplotlib.patches import Rectangle
from matplotlib.transforms import blended_transform_factory
        
class AxisSpan(object):
    """
    Select a min/max range of the x or y axes for a matplotlib Axes

    Example usage::

        ax = subplot(111)
        ax.plot(x,y)

        def onselect(vmin, vmax):
            print vmin, vmax
        span = SpanSelector(ax, onselect, 'horizontal')

    *onmove_callback* is an optional callback that is called on mouse
      move within the span range

    """

    def __init__(self, ax, event, onselect, direction, minspan=None, useblit=False,
                 rectprops=None, onmove_callback=None,color='w',alpha=0.5,drawmode='normal'):
        """
        Create a span selector in *ax*.  When a selection is made, clear
        the span and call *onselect* with::

            onselect(vmin, vmax)

        and clear the span.

        *direction* must be 'horizontal' or 'vertical'

        If *minspan* is not ``None``, ignore events smaller than *minspan*

        The span rectangle is drawn with *rectprops*; default::
          rectprops = dict(facecolor='red', alpha=0.5)

        Set the visible attribute to ``False`` if you want to turn off
        the functionality of the span selector
        """
        rectprops = dict(facecolor=color, alpha=alpha)

        assert direction in ['horizontal', 'vertical'], 'Must choose horizontal or vertical for direction'
        self.direction = direction
        self.onselect = onselect
        self.onmove_callback = onmove_callback
        self.useblit = useblit
        self.minspan = minspan
        
        self.ax = ax
        self.canvas = ax.figure.canvas
        self.visible = True
        self.rectprops = rectprops
        self.drawmode = drawmode
        self.cids=[]
        self.cids.append(self.canvas.mpl_connect('motion_notify_event', self.onmove))
        self.cids.append(self.canvas.mpl_connect('button_release_event', self.release))
        self.cids.append(self.canvas.mpl_connect('draw_event', self.update_background))
        
        if self.direction == 'horizontal':
            trans = blended_transform_factory(self.ax.get_transform(), self.ax.transAxes)
            w,h = 0,1
            self.pressv = event.x
        else:
            trans = blended_transform_factory(self.ax.transAxes, self.ax.get_transform())
            w,h = 1,0
            self.pressv = event.y

        self.rect = Rectangle( (0,0), w, h,
                               transform=trans,
                               visible=self.visible,
                               **self.rectprops
                               )
        
        
            
        self.background = None
        
        if self.drawmode == 'inverted':
            self.rect2 = Rectangle( (0,0), w, h,
                               transform=trans,
                               visible=self.visible,
                               **self.rectprops
                               )
            if not self.useblit: self.ax.add_patch(self.rect2)
        
        if not self.useblit: self.ax.add_patch(self.rect)
        
        # Needed when dragging out of axes
        self.buttonDown = True
        self.prev = (0, 0)
    
    def update_background(self, event):
        'force an update of the background'
        if self.useblit:
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)

    def ignore(self, event):
        'return ``True`` if *event* should be ignored'
        return  not self.visible or event.button !=1

    def release(self, event):
        'on button release event'
        if self.pressv is None or (self.ignore(event) and not self.buttonDown): return
        self.buttonDown = False

        self.rect.set_visible(False)
        
        try:
            self.rect2.set_visible(False)
        except:
            pass
        
        self.canvas.draw()
        vmin = self.pressv
        if self.direction == 'horizontal':
            vmax = event.x or self.prev[0]
            vmin, vmax = [self.ax.transData.inverted().transform((v,0))[0] for v in [vmin,vmax]]
            mn,mx = self.ax.get_xlim()
        else:
            vmax = event.y or self.prev[1]
            vmin, vmax = [self.ax.transData.inverted().transform((0,v))[1] for v in [vmin,vmax]]
            mn,mx = self.ax.get_ylim()

        if vmin>vmax: vmin, vmax = vmax, vmin
        span = (vmax - vmin)/(mx-mn)
        
        if self.minspan is not None and span<self.minspan: return
        self.onselect(vmin, vmax)
        self.pressv = None
        
        for cid in self.cids:
            self.canvas.mpl_disconnect(cid)
        
        return False

    def update(self):
        """
        Draw using newfangled blit or oldfangled draw depending
        on *useblit*
        """
        if self.useblit:
            if self.background is not None:
                self.canvas.restore_region(self.background)
            self.ax.draw_artist(self.rect)
            if self.drawmode == 'inverted':
                self.ax.draw_artist(self.rect2)
            self.canvas.blit(self.ax.bbox)
        else:
            self.canvas.draw_idle()

        return False

    def onmove(self, event):
        'on motion notify event'
        if self.pressv is None or self.ignore(event): return
        x, y = event.x, event.y
        self.prev = x, y
        if self.direction == 'horizontal':
            v = x
        else:
            v = y

        minv, maxv = v, self.pressv
        
        if minv>maxv: minv, maxv = maxv, minv
        
        if self.drawmode == 'inverted':
            if self.direction == 'horizontal':
                self.rect.set_x(0)
                self.rect.set_width(minv)
                mx = self.ax.transData.transform((self.ax.get_xlim()[1],0))[0]
                self.rect2.set_x(maxv)
                self.rect2.set_width(mx-maxv)
            else:
                mx = self.ax.transData.transform((0,self.ax.get_ylim()[1]))[1]
                self.rect.set_y(0)
                self.rect.set_height(minv)
                self.rect2.set_y(maxv)
                self.rect2.set_height(mx-maxv)
        else:
            if self.direction == 'horizontal':
                self.rect.set_x(minv)
                self.rect.set_width(maxv-minv)
            else:
                self.rect.set_y(minv)
                self.rect.set_height(maxv-minv)
            
        
        
        if self.onmove_callback is not None:
            vmin = self.pressv
            if self.direction == 'horizontal':
                vmax = event.x or self.prev[0]
            else:
                vmax = event.y or self.prev[1]

            if vmin>vmax: vmin, vmax = vmax, vmin
            self.onmove_callback(vmin, vmax)

        self.update()
        return False