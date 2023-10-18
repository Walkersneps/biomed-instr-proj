import tkinter as Tk
from tkinter import ttk

import screens as s
from communication import initMQTT

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
screens = [s.Screen1(),
           s.Screen2()]

closebtn = ttk.Button(footerframe, text= "Quit", command= _quit).grid(row= 0, column= 0)
prevpagebtn = ttk.Button(footerframe, text= "<--", command= prevPage)
prevpagebtn.grid(row= 0, column= 2)
nextpagebtn = ttk.Button(footerframe, text= "-->", command= nextPage)
nextpagebtn.grid(row= 0, column= 3)


mqtt = initMQTT()

print("[MAIN] Starting MQTT loop...")
mqtt.loop_start()

print("[MAIN] Starting Tk graphics loop...")
_makePage()
Tk.mainloop()