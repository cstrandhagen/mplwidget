# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 15:50:25 2012

@author: strandha
"""
from functools import partial
import numpy as np

from matplotlib.cbook import Stack
from matplotlib.font_manager import FontProperties

from matplotlib.backends.qt_compat import QtCore, QtGui

from .axis_span import AxisSpan
from .axis_pan import AxisPan
from .icons import get_icon
from .fit_widget import FitWidget


def gauss_function(x, a, x0, sigma):
    return a / (sigma * np.sqrt(2 * np.pi)) * np.exp(-((x - x0))**2 / (2 * sigma**2))


class NavigationToolbar(QtGui.QToolBar):
    """
    Toolbar which replaces the one which is shipped with matplotlib.
    Currently supports:
        - view history

    This class also defines the default mouse behaviour when nothing is selected:
        - scroll wheel zooms in/out (self._on_scroll)
        - right click -> context menu (self._on_click)
        - left click on axis -> zoom along axis (self._on_click)
        - click on scroll wheel -> pan plot (self._on_middle_click)
    """
    message = QtCore.Signal(str)

    def __init__(self, canvas, parent, coordinates=False):
        super(NavigationToolbar, self).__init__(parent)
        self.canvas = canvas
        canvas.toolbar = self
        self._views = Stack()

        self.homeAction = self.addAction(get_icon('home'), 'Home', self.home)
        self.homeAction.setToolTip('restore initial view')
        self.backAction = self.addAction(get_icon('arrow_left'),
                                         'Back',
                                         self.back)
        self.backAction.setToolTip('restore last view')
        self.forwardAction = self.addAction(get_icon('arrow_right'),
                                            'Forward',
                                            self.forward)
        self.forwardAction.setToolTip('go to next view')

        # register default mouse behaviour
        self._idPress = self.canvas.mpl_connect('button_press_event',
                                                self._on_click)
        self._idScroll = self.canvas.mpl_connect('scroll_event',
                                                 self._on_scroll)

        # needed to keep as a reference for things created in a SubMenu
        self._fitWidget = None

        self.set_history_buttons()

    def scroll_zoom(self, axes, steps, location=None, stepsize=0.1):
        xmin, xmax = axes.get_xlim()
        xmin += (location[0] - xmin) * steps * stepsize
        xmax += (location[0] - xmax) * steps * stepsize
        axes.set_xlim(xmin, xmax)
        ymin, ymax = axes.get_ylim()
        ymin += (location[1] - ymin) * steps * stepsize
        ymax += (location[1] - ymax) * steps * stepsize
        axes.set_ylim(ymin, ymax)
        self.push_current()
        self.dynamic_update()

    def _on_scroll(self, event):
        if event.inaxes is None:
            return

        if self._views.empty():
            self.push_current()

        self.scroll_zoom(event.inaxes, event.step,
                         location=(event.xdata, event.ydata))

    def _on_click(self, event):
        if event.button == 3:
            self._right_click(event)
        elif event.button == 1:
            self._left_click(event)
        elif event.button == 2:
            self._middle_click(event)
        else:
            pass

    def _middle_click(self, event):
        """activate pan mode"""
        if event.inaxes is not None:
            self._idRelease = self.canvas.mpl_connect('button_release_event',
                                                      self.release_pan)
            self._idDrag = self.canvas.mpl_connect('mouse_move_event',
                                                   self.drag_pan)
            x, y = event.x, event.y

            # push the current view to define home if stack is empty
            if self._views.empty():
                self.push_current()

            self._xypress = []

            for i, a in enumerate(self.canvas.figure.get_axes()):
                if (x is not None and y is not None and a.in_axes(event) and
                        a.get_navigate() and a.can_pan()):
                    pan = AxisPan(a, event)
                    self._xypress.append((pan, i))
                    self.canvas.mpl_disconnect(self._idDrag)
                    self._idDrag = self.canvas.mpl_connect('motion_notify_event',
                                                           self.drag_pan)

    def drag_pan(self, event):
        """drag callback in pan mode"""
        for a, ind in self._xypress:
            a.drag(event)

        self.dynamic_update()

    def release_pan(self, event):
        """the release mouse button callback in pan mode"""

        self.canvas.mpl_disconnect(self._idDrag)

        for a, ind in self._xypress:
            del a

        if not self._xypress:
            return

        self._xypress = []
        self.push_current()

        self.draw()

    def _left_click(self, event):
        ax = self.canvas.figure.gca()
        if ax.get_xaxis().contains(event)[0]:
            def zoom(xmin, xmax):
                if self._views.empty():
                    self.push_current()

                ax.set_xlim(xmin, xmax)
                self.push_current()
                self.dynamic_update()

            self.axzoom = AxisSpan(ax, event, zoom, 'horizontal',
                                   minspan=0.001, color='w')
        if ax.get_yaxis().contains(event)[0]:
            def zoom(ymin, ymax):
                if self._views.empty():
                    self.push_current()

                ax.set_ylim(ymin, ymax)
                self.push_current()
                self.dynamic_update()

            self.axzoom = AxisSpan(ax, event, zoom, 'vertical',
                                   minspan=0.001, color='w')

    def _right_click(self, event):
        menu = QtGui.QMenu()
        sub_menus = []
        add_these = []

        # check which artists have been clicked
        for artist in self.canvas.figure.gca().get_children():
            picked, props = artist.contains(event)
            if picked:
                # check if artist is part of bar graph
                for container in self.canvas.figure.gca().containers:
                    if artist in container.get_children():
                        if container not in add_these:
                            add_these.append(container)
                        break
                else:
                    if not str(artist).startswith("Rectangle(0,0"):
                        sub_menus.append(SubMenu(artist, parent=self))

        for artist in [self.canvas.figure.gca().xaxis.label,
                       self.canvas.figure.gca().yaxis.label]:

            picked, props = artist.contains(event)
            if picked:
                sub_menus.append(SubMenu(artist, parent=self))

        for container in add_these:
            sub_menus.append(SubMenu(container, parent=self))

        for sub_menu in sub_menus:
            menu.addMenu(sub_menu)

        point = QtCore.QPoint(event.x, self.canvas.height() - event.y)
        menu.exec_(self.canvas.mapToGlobal(point))

    def back(self, *args):
        """move back up the view lim stack"""
        self._views.back()
        self.set_history_buttons()
        self._update_view()

    def dynamic_update(self):
        self.canvas.draw()

    def forward(self, *args):
        """Move forward in the view lim stack"""
        self._views.forward()
        self.set_history_buttons()
        self._update_view()

    def home(self, *args):
        """Restore the original view"""
        view = self._views.home()
        self._views.clear()
        self._views.push(view)
        self.set_history_buttons()
        self._update_view()

    def set_history_buttons(self):
        """Activate/Deactivate history buttons according to their availability"""
        n = len(self._views)
        p = self._views._pos
        if n < 2:
            self.homeAction.setEnabled(False)
            self.forwardAction.setEnabled(False)
            self.backAction.setEnabled(False)
        else:
            self.homeAction.setEnabled(True)
            self.forwardAction.setEnabled(True)
            self.backAction.setEnabled(True)

            if p == 0:
                self.backAction.setEnabled(False)
            if p == n - 1:
                self.forwardAction.setEnabled(False)

    def push_current(self):
        """push the current view limits onto the stack"""
        lims = []
        for a in self.canvas.figure.get_axes():
            xmin, xmax = a.get_xlim()
            ymin, ymax = a.get_ylim()
            lims.append((xmin, xmax, ymin, ymax))

        self._views.push(lims)
        self.set_history_buttons()

    def draw(self):
        """Redraw the canvases, update the locators"""
        for a in self.canvas.figure.get_axes():
            xaxis = getattr(a, 'xaxis', None)
            yaxis = getattr(a, 'yaxis', None)
            locators = []
            if xaxis is not None:
                locators.append(xaxis.get_major_locator())
                locators.append(xaxis.get_minor_locator())
            if yaxis is not None:
                locators.append(yaxis.get_major_locator())
                locators.append(yaxis.get_minor_locator())

            for loc in locators:
                loc.refresh()
        self.canvas.draw()

    def _update_view(self):
        """Update the viewlim and position from the view and
        position stack for each axes
        """

        lims = self._views()
        if lims is None:
            return

        for i, a in enumerate(self.canvas.figure.get_axes()):
            xmin, xmax, ymin, ymax = lims[i]
            a.set_xlim((xmin, xmax))
            a.set_ylim((ymin, ymax))

        self.draw()

    def fit(self, artist):
        if self._fitWidget is None:
            self._fitWidget = FitWidget(self, artist)
        else:
            self._fitWidget.artist = artist

        self._fitWidget.show()


class SubMenu(QtGui.QMenu):
    def __init__(self, artist, parent=None, *args, **kw):
        self.artist = artist
        self.parent = parent
        super(SubMenu, self).__init__(*args, **kw)

        self.setTitle(self._title())
        self.create_menu()

    def create_menu(self):
        if hasattr(self.artist, '__name__'):
            if self.artist.__name__ in ['xaxis', 'yaxis']:
                a = self.addAction('edit axis label',
                                   partial(self.edit_text,
                                           self.artist.get_label_text,
                                           self.artist.set_label_text))

                a = self.addAction('logscale', self.logscale)
                a.setCheckable(True)
                a = self.addAction('show grid', self.grid)
                a.setCheckable(True)
                self.addSeparator()

        if hasattr(self.artist, 'set_text'):
            a = self.addAction('edit text',
                               partial(self.edit_text,
                                       self.artist.get_text,
                                       self.artist.set_text))

        if hasattr(self.artist, 'set_fontproperties'):
            a = self.addAction('Font ...', self.font)
        if hasattr(self.artist, 'set_color'):
            a = self.addAction('Color ...', self.color)

        self.addSeparator()
        a = self.addAction('hide', self.hide)
        a = self.addAction('fit', self.fit)

    def _title(self):
        if hasattr(self.artist, '__name__'):
            return self.artist.__name__
        elif hasattr(self.artist, 'get_label'):
            return self.artist.get_label()
        else:
            return str(self.artist)

    def fit(self):
        self.parent.fit(self.artist)

    def hide(self):
        try:
            self.artist.set_visible(False)
        except AttributeError:
            try:
                for child in self.artist.get_children():
                    child.set_visible(False)
            except:
                print('unexpected error')

        self.parent.canvas.draw()

    def edit_text(self, getter, setter):
        text, ok = QtGui.QInputDialog.getText(self, 'Edit Text', 'Text:',
                                              text=getter())
        if ok:
            setter(text)
            self.parent.canvas.draw()

    def grid(self):
        self.artist.grid()
        self.parent.canvas.draw()

    def logscale(self):
        if self.artist.get_scale() == 'linear':
            self.artist.set_scale('log')
        else:
            self.artist.set_scale('linear')

        self.parent.canvas.draw()

    def font(self):
        font, ok = QtGui.QFontDialog.getFont(_convert_font_toQT(self.artist.get_fontproperties()), self)

        if ok:
            self.artist.set_fontproperties(_convert_font_fromQT(font))
            self.parent.canvas.draw()

    def color(self):
        from matplotlib.colors import colorConverter
        rgbf = colorConverter.to_rgba(self.artist.get_color())
        initial = QtGui.QColor.fromRgbF(rgbf[0], rgbf[1], rgbf[2], rgbf[3])
        color = QtGui.QColorDialog().getColor(initial)

        if color.isValid():
            self.artist.set_color(color.getRgbF())
            if hasattr(self.artist, 'set_markeredgecolor'):
                self.artist.set_markeredgecolor(color.getRgbF())
                self.artist.set_markerfacecolor(color.getRgbF())

        self.parent.canvas.draw()

    def pop_up(self):
        point = QtCore.QPoint(self.event.mouseevent.x,
                              self.parent.height() - self.event.mouseevent.y)

        self.exec_(self.parent.canvas.mapToGlobal(point))


def _convert_font_fromQT(font):
    family = str(font.family())
    size = font.pointSize()

    style_enum = ['normal', 'italic', 'oblique']
    style = style_enum[font.style()]

    weight_dict = {25: 'light',
                   50: 'normal',
                   63: 'demibold',
                   75: 'bold',
                   87: 'black'}

    weight = weight_dict[font.weight()]

    if font.capitalization == 3:
        variant = 'small_caps'
    else:
        variant = 'normal'

    return FontProperties(family, style, variant, weight, size=size)


def _convert_font_toQT(font):
    fontQT = QtGui.QFont()
    fontQT.setFamily(font.get_family()[0])
    fontQT.setPointSize(round(font.get_size_in_points()))
    style_enum = ['normal', 'italic', 'oblique']
    fontQT.setStyle(style_enum.index(font.get_style()))
    weight_dict = {'light': 25,
                   'normal': 50,
                   'demibold': 63,
                   'bold': 75,
                   'black': 87}

    fontQT.setWeight(weight_dict[font.get_weight()])
    if font.get_variant() == 'small-caps':
        fontQT.setCapitalization(3)
    else:
        fontQT.setCapitalization(0)

    return fontQT
