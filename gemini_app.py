import os
import threading
import queue
import subprocess
import ast
import configparser
import time
from datetime import datetime
import re
import shutil
import json
import traceback
import tkinter as tk
import tkinter.font # Add this import for tk.font
from tkinter import ttk, simpledialog, messagebox, scrolledtext
from pathlib import Path
from dataclasses import dataclass

# Third-party imports
from PIL import Image, ImageTk

# pip install google-genai Pillow Pygments
try:
    from google import genai
    from google.genai import types
    GENAI_IMPORTED = True
except ImportError:
    GENAI_IMPORTED = False

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
CONFIG_PATH = Path('config.ini')
VM_DIR = Path('vm')
TRASH_DIR_NAME = ".trash" # For storing discarded images
APP_TITLE = "Enhanced Multi-Agent IDE"
TEXT_MODEL_NAME = "gemini-2.5-flash" #"gemini-2.5-flash-preview-05-20"
IMAGE_MODEL_NAME = "gemini-2.0-flash-preview-image-generation"

# -----------------------------------------------------------------------------
# Application Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    VM_DIR.mkdir(exist_ok=True)
    app = EnhancedGeminiIDE()
    app.mainloop()
