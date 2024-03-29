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
                 newData: dict[str, bool],
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
        self.newData = newData
        self.title = pageTitle
        self.totDataPoints = 300

    def _animateFrame(self, _) -> tuple[Line2D, ...]:
        """Defines the animation logic of the page.
        Override this function to implement plotting, etc...

        Args:
            _ (_type_): _description_
        """
        return (Line2D([], []),)

    def animate(self, refreshInterval = 50):#cfg.PERIOD_PLOT['ECG']):
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
        outOfSamples = True
        unplottedSamples = 0

        overlay = cfg.OVERLAY_SIZES[signalName]
        pktsize = cfg.PACKET_SIZES[signalName]

        while True:
            #print(self.samples)
            #print(signalName)
            if leftovers:
                if self.newData[signalName] is True:
                    print(f"[WARN] Fatal: I'm plotting data way slower than I'm receiving it! Samples are being lost!!")
                    # TODO: handle this
                if unplottedSamples > overlay: # I'm still consuming the backlog
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
                    unplottedSamples = pktsize - x
                    if x == 0: # That's either the first pkt we got, or we had already consumed all samples in the previous pkt (and x was set to 0 after yielding the last sample in that batch)
                        yield self.samples[signalName]['new'][0]
                        x += 1
                    elif unplottedSamples > overlay: # Data packet arrived earlier than expected --> I have leftovers sample to use from old array
                        leftovers = True
                        yield self.samples[signalName]['old'][x]
                        x += 1
                        unplottedSamples -= 1
                    else: # Good situation: data packet arrived while I was plotting overlayed data
                        x = overlay - unplottedSamples
                        yield self.samples[signalName]['new'][x]
                        x += 1
                    self.newData[signalName] = False
                    outOfSamples = False

                else: # no new data packet received
                    if outOfSamples:
                        yield 0
                    elif x < (pktsize - 1):
                        yield self.samples[signalName]['new'][x]
                        x += 1
                    else: # aka: x==(totDataPoints-1). NB: that should never happen, bc due to sample frames overlapping, I should have received new data well before running out of samples.
                        print(f"[WARN] A data packet of {signalName} is late!")
                        yield self.samples[signalName]['new'][x]
                        x = 0
                        outOfSamples = True

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
    """Test Page.
    Plots a sinusoid and random noise.
    """
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
    """Page for ECG + PPG IR.
    """
    def build(self, container):
        super().build(container)

        # Create Axes where the data will be plotted
        plt.gcf().subplots(2, 1)
        self.axECG = plt.gcf().get_axes()[0]
        self.axPPGir = plt.gcf().get_axes()[1]

        # Aesthetics
        self.axECG.set_title("ECG Signal")
        self.axPPGir.set_title("PPG IR Signal")
        self.axECG.set_xticks([])
        self.axPPGir.set_xticks([])

        # X-Axis vector
        self.xdata = [i for i in range(self.totDataPoints)]

        # Initialize Y-Axes vectors
        self.ecgData = [0 for _ in self.xdata]
        self.ppgIrData = [0 for _ in self.xdata]

        # Do the plots (aka draw and get Line2D objs)
        self.ecgLine, = self.axECG.plot(self.xdata, self.ecgData)
        self.ppgIrLine, = self.axPPGir.plot(self.xdata, self.ppgIrData)

        # Set Plot vertical limits
        self.axECG.set_ylim(bottom= -2000.1, top= 3000)
        self.axPPGir.set_ylim(bottom= 0, top= 10000)

        # Define data sources
        self.ecgSample = self.sampleExtractor('ECG')
        self.ppgIRSample = self.sampleExtractor('PPGIR')

        self.ecgIdx = 0


    def _animateFrame(self, cursor) -> tuple[Line2D, ...]:
        for i in range(self.ecgIdx, self.ecgIdx+10):
            self.ecgData[i] = next(self.ecgSample)
            self.ppgIrData[i] = next(self.ppgIRSample)
        self.ecgIdx = self.ecgIdx + 10
        if self.ecgIdx >= self.totDataPoints:
            self.ecgIdx = 0
        self.ecgLine.set_ydata(self.ecgData)
        self.ppgIrLine.set_ydata(self.ppgIrData)
        #print(self.ecgData)

        #self.ppgIrData[cursor] = next(self.ppgIRSample)
        #self.ppgIrLine.set_ydata(self.ppgIrData)

        return (self.ecgLine, self.ppgIrLine)#, self.ppgIrLine)
        #plt.draw()
        #self.ax1.cla()
        #plt.plot(self.xdata, self.ecgData)


class Page3(BasePage):
    """Page for FLOWMETER.
    """
    def build(self, container):
        super().build(container)

        # Create Axes where the data will be plotted
        self.axFLOW = plt.gcf().gca()

        # Aesthetics
        self.axFLOW.set_title("Respiratory Flow")
        self.axFLOW.set_xticks([])

        # X-Axis vector
        self.xdata = [i for i in range(self.totDataPoints)]

        # Initialize Y-Axes vectors
        self.flowData = [0 for _ in self.xdata]

        # Do the plots (aka draw and get Line2D objs)
        self.flowLine, = self.axFLOW.plot(self.xdata, self.flowData)

        # Set Plot vertical limits
        self.axFLOW.set_ylim(bottom= -1, top= 2000)

        # Define data sources
        self.flowSample = self.sampleExtractor('FLOW')

        self.flowIdx = 0


    def _animateFrame(self, cursor) -> tuple[Line2D, ...]:
        self.flowData[cursor] = next(self.flowSample)
        self.flowLine.set_ydata(self.flowData)

        return (self.flowLine, )


class Page4(BasePage):
    """Page for TEMP and GSR.
    """
    def build(self, container):
        super().build(container)

        # Create Axes where the data will be plotted
        plt.gcf().subplots(2, 1)
        self.axTEMP = plt.gcf().get_axes()[0]
        self.axGSR = plt.gcf().get_axes()[1]

        # Aesthetics
        self.axTEMP.set_title("Body Temperature")
        self.axGSR.set_title("Galvanic Skin Response")
        self.axTEMP.set_xticks([])
        self.axGSR.set_xticks([])

        # X-Axis vector
        self.xdata = [i for i in range(self.totDataPoints)]

        # Initialize Y-Axes vectors
        self.tempData = [0 for _ in self.xdata]
        self.gsrData = [0 for _ in self.xdata]

        # Do the plots (aka draw and get Line2D objs)
        self.tempLine, = self.axTEMP.plot(self.xdata, self.tempData)
        self.gsrLine, = self.axGSR.plot(self.xdata, self.gsrData)

        # Set Plot vertical limits
        self.axTEMP.set_ylim(bottom= -1, top= 2000)
        self.axGSR.set_ylim(bottom= -1, top= 2000)

        # Define data sources
        self.tempSample = self.sampleExtractor('TEMP')
        self.gsrSample = self.sampleExtractor('GSR')

        self.tempIdx = 0


    def _animateFrame(self, cursor) -> tuple[Line2D, ...]:
        self.tempData[cursor] = next(self.tempSample)
        self.gsrData[cursor] = next(self.gsrSample)
        self.tempLine.set_ydata(self.tempData)
        self.gsrLine.set_ydata(self.gsrData)

        return (self.tempLine, self.gsrLine)