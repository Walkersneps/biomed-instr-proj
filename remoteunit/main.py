# Copyright (c) 2023 Walter Carli. All Rights Reserved.
"""This script implements a Graphical User Interface monitoring several physiological parameters,
as sensed and proactively communicated by a compatible proximal unit.

This program is part of a project developed by students
Walter Carli and Dario Lucchini,
in the framework of the course
"Biomedical Instrumentation Project [717.318]", offered by
Technische Universität Graz
during the Winter Semester of the Academic Year 2023/2024.
"""

import tkinter as Tk
from tkinter import ttk

import pages
import settings as cfg
from communication import MQTTManager

import matplotlib.pyplot as plt
plt.style.use('dark_background')



# o-o-o-o GUI Functions o-o-o-o #
def _quit():
    """Quits the GUI window and terminates the environment.
    """
    window.quit()
    window.destroy()

def _makePage():
    """Draws and kickstarts animations on the currently selected page.
    """
    global pageframe, windowframe
    pageframe = ttk.Frame(windowframe)
    pageframe.grid(row= 0, column= 0)
    screens[currentPage].build(pageframe)
    screens[currentPage].animate()

def nextPage():
    """Kills the currently active page and shows the next one.
    """
    global currentPage, nextpagebtn, prevpagebtn, screens, pageframe

    screens[currentPage].stop()
    currentPage += 1

    # Check buttons availability
    if currentPage >= (len(screens) - 1):
        nextpagebtn.state(["disabled"])
    if currentPage > 0:
        prevpagebtn.state(["!disabled"])

    # Destroy old page and build the new one
    pageframe.destroy()
    _makePage()

def prevPage():
    """Kills the currently active page and shows the previous one.
    """
    global currentPage, nextpagebtn, prevpagebtn, screens, pageframe

    screens[currentPage].stop()
    currentPage -= 1
    
     # Check buttons availability
    if currentPage == 0:
        prevpagebtn.state(["disabled"])
    if currentPage < len(screens):
        nextpagebtn.state(["!disabled"])

    # Destroy old page and build the new one
    pageframe.destroy()
    _makePage()
# o-o-o-o-o-o-o-o-o-o-o-o-o-o-o #


# o-o-o-o Global Variables o-o-o-o #
# === Operative Vars ===
currentPage = 0


# === Data ===
# Holds two lists (`old` and `new`) of samples for each biosignal variable. Will be overwritten by MQTT logic with data coming from the `proximalunit`, and read by the graphing functions for live data display.
samples: dict[str, dict[str, list[int]]] = {signal: {arr: [0
                                                           for _ in range(cfg.PACKET_SIZES[signal])]
                                                     for arr in ['new', 'old']}
                                            for signal in cfg.BIOSIGNALS}
# For each biosignals, holds a flag signalling whether a new MQTT data packet has arrived.
newData: dict[str, bool] = { signal: False for signal in cfg.BIOSIGNALS }


# === Communication ===
mqtt = MQTTManager(samples, newData)


# === GUI Objects ===
# == Window and Frames ==
window = Tk.Tk() # Create Tcl interpreter + main window
windowframe = ttk.Frame(window, padding= 10) # Will contain whole window
footerframe = ttk.Frame(windowframe) # Will contain the footer

# == Widgets ==
closebtn = ttk.Button(footerframe, text= "Quit", command= _quit)
prevpagebtn = ttk.Button(footerframe, text= "<--", command= prevPage)
nextpagebtn = ttk.Button(footerframe, text= "-->", command= nextPage)

# == Pages ==
screens = [pages.Page1(samples, newData, "1st Page"),
           pages.Page2(samples, newData, "2nd Page")
           ]
# o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o #



# o-o-o-o MAIN o-o-o-o #
# === Preliminary GUI Setup ===
window.title("Live Data Monitor")
window.protocol("WM_DELETE_WINDOW", _quit) # What happens when the Window Manager tries to delete the window

# Place widgets
windowframe.grid()
footerframe.grid(row= 1, column= 0)
closebtn.grid(row= 0, column= 0)
prevpagebtn.grid(row= 0, column= 2)
nextpagebtn.grid(row= 0, column= 3)


# === The juicy part ===
print("[MAIN] Starting MQTT loop...")
mqtt.c.loop_start()

print("[MAIN] Starting Tk graphics loop...")
_makePage()
Tk.mainloop()