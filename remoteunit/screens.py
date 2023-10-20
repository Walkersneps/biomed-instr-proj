from tkinter import ttk
from itertools import cycle
import random

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class Screen:
    def __init__(self) -> None:
        self.anim = None
        self.canvas = None

    def _animateFrame(self, _):
        pass

    def animate(self):
        self.anim = FuncAnimation(plt.gcf(), self._animateFrame, interval= 16, blit= False, frames= [0, 1])
    
    def stop(self):
        del self.anim
        del self.canvas

class Screen1(Screen):
    def build(self, container):
        print("build s1")

        self.frame = container
        # Setup Plots
        self.x_vals = [t for t in range(0, 121)]
        self.y_vals = [0 for t in range(0, len(self.x_vals))]
        self.y_vals2 = self.y_vals
        self.c = cycle(self.x_vals)
        plt.close()
        plt.gcf().subplots(2, 1)

        # Draw GUI
        self.frame.grid()
        label = ttk.Label(self.frame, text= "Pagina 1").grid(column= 0, row= 0)

        self.canvas = FigureCanvasTkAgg(plt.gcf(), master= self.frame)
        self.canvas.get_tk_widget().grid(column= 0, row= 1)

    def _animateFrame(self, _):
        # Generate values
        i = next(self.c)
        self.y_vals[i] = random.randint(0, 5)
        self.y_vals2[i] = random.randint(0, 5)
        # Get all axes of figure
        ax1, ax2 = plt.gcf().get_axes()
        # Clear current data
        ax1.cla()
        ax2.cla()
        # Plot new data
        ax1.plot(self.x_vals, self.y_vals)
        ax2.plot(self.x_vals, self.y_vals2)


class Screen2(Screen):
    def build(self, container):
        print("build s2")

        self.frame = container
        # Setup Plots
        self.x_vals = [t for t in range(0, 121)]
        self.y_vals = [0 for t in range(0, len(self.x_vals))]
        self.c = cycle(self.x_vals)
        plt.close()
        plt.gcf().subplots(1, 1)

        # Draw GUI
        self.frame.grid()
        label = ttk.Label(self.frame, text= "Pagina 2").grid(column= 0, row= 0)

        self.canvas = FigureCanvasTkAgg(plt.gcf(), master= self.frame)
        self.canvas.get_tk_widget().grid(column= 0, row= 1)

    def _animateFrame(self, _):
        # Generate values
        i = next(self.c)
        self.y_vals[i] = random.randint(0, 6)
        # Get all axes of figure
        ax1 = plt.gcf().get_axes()
        ax1 = ax1[0]
        # Clear current data
        ax1.cla()
        # Plot new data
        ax1.plot(self.x_vals, self.y_vals)