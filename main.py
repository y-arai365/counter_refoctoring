import csv
from datetime import datetime
import math
import multiprocessing
from multiprocessing import freeze_support
from multiprocessing.pool import ThreadPool as Pool
import os
import pickle
import tkinter as tk
import tkinter.font as font
import tkinter.ttk as ttk
import tkinter.filedialog as tkfd
import sqlite3
import subprocess
import shutil
import re
import webbrowser

import cv2
import numpy as np
from PIL import Image, ImageTk

from gui_main import MainWindow


if __name__ == "__main__":
    freeze_support()

    icon_file = "count_icon.ico"

    MainWindow(icon_file=icon_file)
