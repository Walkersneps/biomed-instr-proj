from tkinter import ttk
from itertools import cycle
import random
from numpy import sin, pi, linspace

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import settings as cfg

class BasePage:
    """Base class for a page of the health monitor.
    Each actual page can be defined as a subclass of `BasePage`.

    Don't forget to implement function `_animateFrame(...)` specifically.
    """
    def __init__(self,
                 samples: dict[str, dict[str, list[int]]],
                 newData: dict[str, bool]) -> None:
        """Create new instance of a Page.

        Args:
            samples (dict[str, dict[str, list[int]]]): Reference to the dictionary holding all current and 1-step old sample packets, for each signal
            newData (dict[str, bool]): Dictionary specifying, for each signal, if a new packet containing samples has arrived.
        """
        self.anim = None
        self.canvas = None
        self.samples = samples
        self.newData = newData
        self.totDataPoints = 120

    def _animateFrame(self, _):
        """Defines the animation logic of the page.
        Implement here plotting, etc...

        Args:
            _ (_type_): _description_
        """
        pass

    def animate(self, refreshInterval: int= 100):
        """Initialize and start animation of plots in this page.

    The animation can be stopped by deleting the reference to property `anim`

        Args:
            refreshInterval (int): Interval between subsequent plottings [ms]. Defaults to 100.
        """
        self.anim = FuncAnimation(fig= plt.gcf(),
                                  func= self._animateFrame,
                                  interval= refreshInterval,
                                  blit= False,
                                  frames= range(self.totDataPoints))
    
    def stop(self):
        """Stops the animation and removes canvas from memory.
        Call `build(...)` and then `animate()` to reinitialize the regimen graphics state.
        """
        del self.anim
        del self.canvas

    def sampleExtractor(self, signalName: str):
        """Generates the next sample which needs plotting.
        Internally handles the event of new sample packet.

        Args:
            signalName (str): The name of the signal

        Yields:
            int: The next sample which needs to be plotted 
        """
        x = 0
        leftovers = False
        unplottedSamples = 0

        while True:
            #print(self.samples)
            #print(signalName)
            if leftovers:
                if self.newData[signalName] is True:
                    print(f"[WARN] Fatal: I'm plotting data way slower than I'm receiving it! Samples are being lost!!")
                if unplottedSamples > cfg.OVERLAY_SIZES[signalName]: # I'm still consuming the backlog
                    yield self.samples[signalName]['old'][x]
                    x += 1
                    unplottedSamples -= 1
                else: # Done consuming the backlog! The next sample I have to plot is the first overlayed one --> I can find it @ start of 'new' array
                    x = 0
                    leftovers = False
                    yield self.samples[signalName]['new'][0]
                    x += 1
            else: # no leftovers
                if self.newData[signalName] is True: # just received a new data packet --> the series I was reading is now in the 'old' array, while new data is the 'new' array
                    unplottedSamples = cfg.PACKET_SIZES[signalName] - x
                    if unplottedSamples > cfg.OVERLAY_SIZES[signalName]: # Data packet arrived earlier than expected --> I have leftovers sample to use from old array
                        leftovers = True
                        yield self.samples[signalName]['old'][x]
                        x += 1
                        unplottedSamples -= 1
                    else: # Good situation: data packet arrived while I was plotting overlayed data
                        x = cfg.OVERLAY_SIZES[signalName] - unplottedSamples
                        yield self.samples[signalName]['new'][x]
                        x += 1
                    self.newData[signalName] = False
                else: # no new data packet received
                    if x < (self.totDataPoints - 1):
                        yield self.samples[signalName]['new'][x]
                        x += 1
                    else: # aka: x==(totDataPoints-1). NB: that should never happen, bc due to sample frames overlapping, I should have received new data well before running out of samples.
                        print(f"[WARN] A data packet of {signalName} is late!")
                        yield self.samples[signalName]['new'][x]
                        x = 0




class Page1(BasePage):
    def build(self, container):
        print("build s1")

        self.frame = container
        # Setup Plots
        self.x_vals = [t for t in range(0, 121)]
        self.y_vals = [0 for t in range(0, len(self.x_vals))]
        self.y_vals2 = [val for val in self.y_vals]
        self.c = cycle(self.x_vals)
        plt.close()
        plt.gcf().subplots(2, 1)

        # Draw GUI
        self.frame.grid()
        label = ttk.Label(self.frame, text= "Pagina 1").grid(column= 0, row= 0)

        self.canvas = FigureCanvasTkAgg(plt.gcf(), master= self.frame)
        self.canvas.get_tk_widget().grid(column= 0, row= 1)

    def _animateFrame(self, t):
        # Generate values
        i = next(self.c)
        self.y_vals[i] = sin(t)
        self.y_vals2[i] = random.randint(0, 128)
        # Get all axes of figure
        ax1, ax2 = plt.gcf().get_axes()
        # Clear current data
        ax1.cla()
        ax2.cla()
        # Plot new data
        ax1.plot(self.x_vals, self.y_vals)
        ax2.plot(self.x_vals, self.y_vals2)
    
    def animate(self, refreshInterval: int = 100):
        self.anim = FuncAnimation(fig= plt.gcf(),
                                    func= self._animateFrame,
                                    interval= refreshInterval,
                                    blit= False,
                                    frames= linspace(0, 2*pi, 121))


class Page2(BasePage):
    def build(self, container):
        print("build s2")
        self.frame = container # save parent container in object instance

        # Setup Plots
        self.xdata = [i for i in range(self.totDataPoints)]
        self.ecgLine, = plt.plot([])
        self.ecgLine.set_xdata(self.xdata)
        self.ecgData = [0 for i in self.xdata]
        plt.close()
        plt.gcf().subplots(1, 1)
        self.ax1 = plt.gcf().get_axes()[0]

        # Draw GUI
        self.frame.grid() # Draw main container
        label = ttk.Label(self.frame, text= "Pagina 2").grid(column= 0, row= 0) # Draw label
        self.canvas = FigureCanvasTkAgg(plt.gcf(), master= self.frame) # instantiate matplotlib canvas...
        self.canvas.get_tk_widget().grid(column= 0, row= 1) # ... and draw it

        # Define data sources
        self.ecgSample = self.sampleExtractor('ECG')

    def _animateFrame(self, cursor):
        nxt = next(self.ecgSample)
        print(f'at frame {cursor}, extracted {nxt}')
        self.ecgData[cursor] = nxt
        #self.ecgLine.set_ydata(self.ecgData)
        #plt.draw()
        self.ax1.cla()
        plt.plot(self.xdata, self.ecgData)

