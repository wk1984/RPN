
This is not the interface to the rpn files anymore, it is just a project that uses 
the interface (which is now refactored in a separate python project [pyrmnlib] (https://github.com/guziy/pylibrmn/) ).


This is a collection of scripts I have used for analysis and plotting of model and obs data. You can find here examples of working with shapefiles, pytables, plotting over different map projections, extensive use of matplotlib and basemap....


Author: Oleksandr Huziy
Python interface to rmnlib using ctypes and wrapper dynamic library,
the wrapper .so library is created in the RPNc(also here at github) project.

The main class is in rpn.py. The level_kinds.py and data_types.py
contain constants and the other files are the examples of how I am using 
the RPN class.

In order to use it to read rpn files you need the rmnlib.so, and for interfacing it
from python only the following files are required:
 -- rpn.py
 -- level_kinds.py
 -- data_types.py
