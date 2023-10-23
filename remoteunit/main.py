import tkinter as Tk
from tkinter import ttk

import pages
import settings as cfg
from communication import MQTTManager

import matplotlib.pyplot as plt
plt.style.use('dark_background')

def _quit():
    window.quit()
    window.destroy()

def _makePage():
    global pageframe, windowframe
    pageframe = ttk.Frame(windowframe)
    pageframe.grid(row= 0, column= 0)
    print(currentPage)
    screens[currentPage].build(pageframe)
    screens[currentPage].animate()

def nextPage():
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

samples: dict[str, dict[str, list[int]]] = {signal: {arr: [0
                                                           for _ in range(int(sett['fsample']/sett['fpacket']))]
                                                     for arr in ['new', 'old']}
                                            for (signal, sett) in cfg.BIOSIGNALS.items()}
newData: dict[str, bool] = {signal: False for signal in cfg.BIOSIGNALS}

window = Tk.Tk() # Create Tcl interpreter + main window
window.title("Live Data Monitor")
window.protocol("WM_DELETE_WINDOW", _quit)

windowframe = ttk.Frame(window, padding= 10) # Contains whole window
windowframe.grid()
#pageframe = ttk.Frame(windowframe) # Contains page-dependant top portion
#pageframe.grid(row= 0, column= 0)
footerframe = ttk.Frame(windowframe) # Contains footer
footerframe.grid(row= 1, column= 0)

# Initialize screens
currentPage = 0
screens = [pages.Page1(samples, newData),
           pages.Page2(samples, newData)]

closebtn = ttk.Button(footerframe, text= "Quit", command= _quit).grid(row= 0, column= 0)
prevpagebtn = ttk.Button(footerframe, text= "<--", command= prevPage)
prevpagebtn.grid(row= 0, column= 2)
nextpagebtn = ttk.Button(footerframe, text= "-->", command= nextPage)
nextpagebtn.grid(row= 0, column= 3)


mqtt = MQTTManager(samples, newData)

print("[MAIN] Starting MQTT loop...")
mqtt.c.loop_start()

print("[MAIN] Starting Tk graphics loop...")
_makePage()
Tk.mainloop()