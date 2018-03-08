#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("folder", help="folder/file to browse (defaults to current folder)", nargs="?", default=None)
parser.add_argument("-e", "--ext", help="file extension (defaults to \"npy\")", default="npy")
clargs = parser.parse_args()


def normalizeFileExt(fileext):
    if not fileext.startswith("."):
        fileext = "." + fileext
    return fileext

FILEEXT = normalizeFileExt(clargs.ext)


import os

def getFolder(folder):
    if folder:
        return os.path.realpath(folder)
    else:
        return os.getcwd()

def getFirstFile(folder, fileext=FILEEXT):
    for root, dirs, files in os.walk(folder):
        for fn in files:
            if fn.endswith(fileext):
                return os.path.join(root, fn)
    return folder

FOLDER = getFirstFile(getFolder(clargs.folder))


import numpy as np


## something is broken when using wx3.0, hence
#import wxversion
#wxversion.select('2.8')

import wx

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import (
    FigureCanvasWxAgg as FigureCanvas,
    NavigationToolbar2WxAgg as NavigationToolbar
)
#from matplotlib.backends.backend_wx import (
#    FigureCanvasWx as FigureCanvas,
#    NavigationToolbar2Wx as NavigationToolbar
#)
from matplotlib.colors import LogNorm


class NavigationToolbarX(NavigationToolbar):

    ID_TOGGLE_LOG = wx.NewId()
    ID_TOGGLE_COLORBAR = wx.NewId()
    CALL_DEFAULT_CALLBACK = [ID_TOGGLE_LOG, ID_TOGGLE_COLORBAR]

    def __init__(self, *args, **kwargs):
        NavigationToolbar.__init__(self, *args, **kwargs)
        self.AddSeparator()
        self.AddSimpleTool(self.ID_TOGGLE_LOG, wx.ArtProvider.GetBitmap("gtk-zoom-fit"), 'Log', 'Logarithmic plot', isToggle=True)
        self.AddSimpleTool(self.ID_TOGGLE_COLORBAR, wx.ArtProvider.GetBitmap("gtk-select-color"), 'Colorbar', 'Show colorbar', isToggle=True)
        self.ToggleTool(self.ID_TOGGLE_COLORBAR, True)

    def set_default_callback(self, function):
        for i in self.CALL_DEFAULT_CALLBACK:
            wx.EVT_TOOL(self, i, function)

    def get_state_log(self):
        return self.GetToolState(self.ID_TOGGLE_LOG)

    def get_state_colorbar(self):
        return self.GetToolState(self.ID_TOGGLE_COLORBAR)


class PlotPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizerAndFit(self.sizer)

        self.add_canvas()
        self.add_toolbar()


    def add_canvas(self):
        self.figure = figure = Figure()
        self.axes = self.make_axes()
        self.canvas = FigureCanvas(self, wx.ID_ANY, figure)
        self.sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.EXPAND)

    def add_toolbar(self):
        self.toolbar = toolbar = NavigationToolbarX(self.canvas)
        toolbar.Realize()
        toolbar.update()
        self.sizer.Add(toolbar, 0, wx.LEFT|wx.EXPAND)

    def __getattr__(self, name):
        if name == "plot":
            state_log = self.toolbar.get_state_log()
            if state_log:
                self.axes.set_yscale('log')
            else:
                self.axes.set_yscale('linear')

        return getattr(self.axes, name)

    def make_axes(self):
        return self.figure.add_subplot(111)

    def reset(self):
        self.figure.clear()
        self.axes = self.make_axes()

    def draw(self):
        self.figure.tight_layout()
        try: #TODO
            self.canvas.draw()
        except:
            pass
        self.canvas.flush_events()


class ListPanel(wx.Panel):

    def __init__(self, parent, folder=FOLDER, fileext=FILEEXT):
        wx.Panel.__init__(self, parent)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(hbox)

        self.dirctrl = wx.GenericDirCtrl(self, wx.ID_ANY, dir=folder, filter="*" + fileext)
        hbox.Add(self.dirctrl, 1, wx.EXPAND|wx.ALL, 1)


    def getSelectedText(self):
        return self.dirctrl.GetPath()

    def reloadFileList(self):
        p = self.dirctrl.GetPath()
        res = self.dirctrl.ReCreateTree()
        self.dirctrl.SetPath(p)
        return res



class PlotListFrame(wx.Frame):

    def __init__(self, fileext=FILEEXT):
        wx.Frame.__init__(self, None, title=fileext + " browser++", size=(1000, 600))

        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        self.pltpan = PlotPanel(self.splitter)
        self.lstpan = ListPanel(self.splitter)

        self.splitter.SplitVertically(self.pltpan, self.lstpan, 600)
        self.splitter.SetSashGravity(0.75)

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.update)
        self.pltpan.toolbar.set_default_callback(self.update)

        self.add_statusbar()
        self.add_icon()

        self.Show()
        self.update(None)


    def update(self, event):
        self.update_list()
        self.update_plot()


    def update_list(self):
        self.Bind(wx.EVT_TREE_SEL_CHANGED, None)
        self.reloadFileList()
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.update)


    def update_plot(self):
        text = self.getSelectedText()

        try:
            A = np.load(text)
        except IOError as e:
#            print "IOError:", e, "for", text
            return

        self.statbar.SetStatusText("shape = {}, dtype = {}".format(A.shape, A.dtype), 3)

        self.pltpan.reset()
        self.pltpan.set_title(os.path.splitext(os.path.basename(text))[0])

        if A.ndim == 1:
            self.pltpan.plot(A)
        elif A.ndim == 2:
            if A.shape[0] == 2:
                self.pltpan.plot(*A)
            elif A.shape[1] == 2:
                self.pltpan.plot(*A.T)
            else:
                state_log = self.pltpan.toolbar.get_state_log()
                norm = LogNorm() if state_log else None

                img = self.pltpan.imshow(A, interpolation="none", norm=norm)
#                img = self.pltpan.pcolormesh(A, norm=norm)

                state_colorbar = self.pltpan.toolbar.get_state_colorbar()
                if state_colorbar:
                    with np.errstate(all='ignore'):
                        self.pltpan.figure.colorbar(img)
        else:
            return

        self.pltpan.draw()


    def add_statusbar(self):
#        self.statbar = wx.StatusBar(self, wx.ID_ANY)
        self.statbar = self.CreateStatusBar(4)
        self.SetStatusBar(self.statbar)
        self.pltpan.canvas.mpl_connect('motion_notify_event', self.update_statusbar_coord)
        self.Bind(wx.EVT_TOOL_ENTER, self.update_statusbar_help)

    def update_statusbar_coord(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
            self.statbar.SetStatusText("x = {}".format(x), 1)
            self.statbar.SetStatusText("y = {}".format(y), 2)

    def update_statusbar_help(self, event):
        tool_id = event.GetSelection()
        help = self.pltpan.toolbar.GetToolLongHelp(tool_id)
        self.statbar.SetStatusText(help, 0)


    def add_icon(self):
        bmp = wx.ArtProvider.GetBitmap("gtk-page-setup")
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(bmp)
        self.SetIcon(icon)


    def getSelectedText(self):
        return self.lstpan.getSelectedText()

    def reloadFileList(self):
        return self.lstpan.reloadFileList()





if __name__ == '__main__':
    app = wx.App()
    PlotListFrame()
    app.MainLoop()



