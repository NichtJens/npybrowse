#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("filenames", help="names of files to browse", nargs="*", default=None)
clargs = parser.parse_args()


from glob import glob
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


class PlotPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizerAndFit(self.sizer)

        self.add_canvas()
        self.add_toolbar()


    def add_canvas(self):
        figure = Figure()
        self.axes = figure.add_subplot(111)
        self.canvas = FigureCanvas(self, wx.ID_ANY, figure)
        self.sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.EXPAND)

    def add_toolbar(self):
        toolbar = NavigationToolbar(self.canvas)
        toolbar.Realize()
        toolbar.update()
        self.sizer.Add(toolbar, 0, wx.LEFT|wx.EXPAND)

    def __getattr__(self, name):
        f = getattr(self.axes, name)
        def plotting(*args, **kwargs):
            self.axes.clear()
            f(*args, **kwargs)
            self.canvas.draw()
            self.canvas.flush_events()
        return plotting



class ListPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(hbox)

        self.listbox = wx.ListBox(self, -1)
        hbox.Add(self.listbox, 1, wx.EXPAND|wx.ALL, 1)


    def getSelectedText(self):
        sel  = self.listbox.GetSelection()
        if not sel < 0:
            return self.listbox.GetString(sel)
        else:
            #nothing selected...
            if self.listbox.GetCount() > 0:
                #...but something available, take the first line
                self.listbox.SetSelection(0)
                return self.getSelectedText()

    def add(self, string):
        self.listbox.Append(string)



class PlotListFrame(wx.Frame):

    def __init__(self, fileext="npy"):
        if not fileext.startswith("."):
            fileext = "." + fileext

        wx.Frame.__init__(self, None, title=fileext + " browser", size=(800, 600))

        self.fileext = fileext
        self.fileextlen = len(fileext)

        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        self.pltpan = PlotPanel(self.splitter)
        self.lstpan = ListPanel(self.splitter)

        self.splitter.SplitVertically(self.pltpan, self.lstpan, -100)
        self.splitter.SetSashGravity(0.75)

        self.Bind(wx.EVT_LISTBOX, self.update)

        self.Show()
        self.update(None)


    def update(self, event):
        self.update_list()
        self.update_plot()


    def update_list(self):
        files = clargs.filenames or sorted(glob("*" + self.fileext))
        for e in files:
            e = e[:-self.fileextlen]
            if e not in self.getListItems():
                self.add(e)


    def update_plot(self):
        text = self.getSelectedText()
        if text is None:
            return

        A = np.load(text + self.fileext)
        if A.ndim == 1:
            self.pltpan.plot(A)
        elif A.ndim == 2:
            if A.shape[0] == 2:
                self.pltpan.plot(*A)
            else:
                self.pltpan.imshow(A, interpolation="none", norm=LogNorm())
                #self.pltpan.pcolor(A)


    def getListItems(self):
        return self.lstpan.listbox.GetItems()

    def getSelectedText(self):
        return self.lstpan.getSelectedText()

    def add(self, title):
        self.lstpan.add(title)





if __name__ == '__main__':
    app = wx.App()
    PlotListFrame()
    app.MainLoop()



