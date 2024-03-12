from tkinter import ttk
from itertools import cycle
import random
from numpy import sin, pi, linspace

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D

import settings as cfg

class BasePage:
    """Base class for a page of the health monitor.
    Each actual page can be defined as a subclass of `BasePage`.

    Don't forget to implement functions `_animateFrame(...)` and `build(...)` specifically.
    """
    def __init__(self,
                 samples: dict[str, dict[str, list[int]]],
                 pageTitle: str = "Generic Page"
                ) -> None:
        """Create new instance of a Page.

        Args:
            samples (dict[str, dict[str, list[int]]]): Reference to the dictionary holding all current and 1-step old sample packets, for each signal
            newData (dict[str, bool]): Dictionary specifying, for each signal, if a new packet containing samples has arrived.
        """
        self.anim = None
        self.canvas = None
        self.samples = samples
        self.title = pageTitle
        self.totDataPoints = 300

    def _animateFrame(self, _) -> tuple[Line2D, ...]:
        """Defines the animation logic of the page.
        Override this function to implement plotting, etc...

        Args:
            _ (_type_): _description_
        """
        return (Line2D([], []),)

    def animate(self, refreshInterval = 1):#cfg.PERIOD_PLOT['ECG']):
        """Initialize and start animation of plots in this page.

        The animation can be stopped by deleting the reference to property `anim`

        Args:
            refreshInterval (int): Interval between subsequent plottings [ms]. Defaults to 100.
        """
        self.anim = FuncAnimation(fig= plt.gcf(),
                                  func= self._animateFrame,
                                  interval= refreshInterval,
                                  blit= True,
                                  frames= self.totDataPoints)
    
    def stop(self):
        """Stops the animation and removes canvas from memory.
        Call `build(...)` and then `animate()` to reinitialize the regimen graphics state.
        """
        del self.anim
        del self.canvas

    def build(self, container: ttk.Frame):
        """Builds the main graphical elements of the page.
        Each subclass should implement its own `build()` method, to define the actual content of the page.

        Parameters
        ----------
        container : tkinter.ttk.Frame
            Frame element which will be used as parent for each widget belonging to the page.
        """
        print(f"Building page '{self.title}'")
        self.frame = container # save parent container in object instance

        plt.close() # Close any old figures

        # Draw GUI
        self.frame.grid() # Draw main container
        label = ttk.Label(self.frame, text= self.title).grid(column= 0, row= 0) # Draw label
        self.canvas = FigureCanvasTkAgg(plt.gcf(), master= self.frame) # instantiate matplotlib canvas...
        self.canvas.get_tk_widget().grid(column= 0, row= 1) # ... and draw it



class Page1(BasePage):
    def build(self, container):
        super().build(container)

        # Setup Plots
        self.x_vals = [t for t in range(0, 121)]
        self.y_vals = [0 for t in range(0, len(self.x_vals))]
        self.y_vals2 = [val for val in self.y_vals]
        self.c = cycle(self.x_vals)
        plt.gcf().subplots(2, 1)

        # Get all axes of figure
        ax1, ax2 = plt.gcf().get_axes()
        ax1.set_ylim(bottom= -1.1, top= 1.1)
        ax2.set_ylim(bottom= -0.1, top= 128.1)
        self.g1, = ax1.plot(self.x_vals, self.y_vals)
        self.g2, = ax2.plot(self.x_vals, self.y_vals2)

    def _animateFrame(self, t):
        # Generate values
        i = next(self.c)
        self.y_vals[i] = sin(t)
        self.y_vals2[i] = random.randint(0, 128)
        
        # Clear current data
        #self.ax1.cla()
        #self.ax2.cla()
        # Plot new data
        #self.ax1.plot(self.x_vals, self.y_vals)
        #self.ax2.plot(self.x_vals, self.y_vals2)

        self.g1.set_ydata(self.y_vals)
        self.g2.set_ydata(self.y_vals2)

        return (self.g1, self.g2)

    
    def animate(self, refreshInterval: int = 100):
        self.anim = FuncAnimation(fig= plt.gcf(),
                                    func= self._animateFrame,
                                    interval= refreshInterval,
                                    blit= True,
                                    frames= linspace(0, 2*pi, 121))


class Page2(BasePage):
    def __init__(self, samples: dict[str, dict[str, list[int]]], bluetoothSocket, pageTitle: str = "Generic Page") -> None:
        super().__init__(samples, pageTitle)
        self.btSocket = bluetoothSocket

    def build(self, container):
        super().build(container)

        # Create Axes where the data will be plotted
        #plt.gcf().subplots(2, 1)
        plt.gcf().subplots(1, 1)
        self.axECG = plt.gcf().get_axes()[0]
        #self.axPPGir = plt.gcf().get_axes()[1]

        # Aesthetics
        self.axECG.set_title("ECG Signal")
        #self.axPPGir.set_title("PPG IR Signal")
        self.axECG.set_xticks([])
        #self.axPPGir.set_xticks([])

        # X-Axis vector
        self.xdata = [i for i in range(self.totDataPoints)]

        # Initialize Y-Axes vectors
        self.ecgData = [0 for _ in self.xdata]
        #self.ppgIrData = [0 for _ in self.xdata]

        # Do the plots (aka draw and get Line2D objs)
        self.ecgLine, = self.axECG.plot(self.xdata, self.ecgData)
        #self.ppgIrLine, = self.axPPGir.plot(self.xdata, self.ppgIrData)

        # Set Plot vertical limits
        self.axECG.set_ylim(bottom= -2000.1, top= 3000)
        #self.axPPGir.set_ylim(bottom= 0, top= 10000)

        self.ecgIdx = 0


    def _animateFrame(self, _) -> tuple[Line2D, ...]:
        data = self.btSocket.recv(2048).decode()
        if data:
            samps = data.splitlines()

            i = 0
            while i < len(samps):
                self.ecgData[self.ecgIdx + i] = int(data[i])
                if self.ecgIdx + i >= self.totDataPoints:
                    self.ecgIdx = 0

            self.ecgLine.set_ydata(self.ecgData)

        #self.ppgIrData[cursor] = next(self.ppgIRSample)
        #self.ppgIrLine.set_ydata(self.ppgIrData)

        return (self.ecgLine, )#, self.ppgIrLine)
        #plt.draw()
        #self.ax1.cla()
        #plt.plot(self.xdata, self.ecgData)

