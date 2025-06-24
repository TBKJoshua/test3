#!/usr/bin/env python3
"""
AI Code Editor - A professional Python desktop application with Gemini AI integration
Mimics Claude's artifact editing system for precise code modifications
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import threading
import subprocess
import sys
import os
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re # For cleanup logic

# Import required libraries with fallback handling
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    # The main function will handle informing the user and attempting installation.
    # print("Warning: google-generativeai not installed. AI features will be disabled.")

try:
    import pygments # Check if the base module is available
    from pygments.lexers import PythonLexer # Keep if planning to use lexing
    # from pygments.formatters import NullFormatter # Not used
    # from pygments import highlight # Not used
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    # The main function will handle informing the user and attempting installation.

@dataclass
class EditSuggestion:
    """Represents a single edit suggestion from the AI"""
    line_start: int
    line_end: int
    original_code: str
    suggested_code: str
    explanation: str
    edit_type: str  # 'replace', 'insert', 'delete'
    confidence: float
    selected: bool = True

class ModernStyle:
    """Modern dark theme styling constants"""
    # Colors
    BG_MAIN = "#1e1e1e"
    BG_PANEL = "#2d2d2d"
    BG_HOVER = "#3d3d3d"
    BG_SELECTED = "#404040"
    
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#cccccc" 
    TEXT_TERTIARY = "#888888"
    
    ACCENT_BLUE = "#007acc"
    ACCENT_TEAL = "#4ec9b0"
    ACCENT_RED = "#f44747"
    ACCENT_YELLOW = "#ffcc02"
    ACCENT_GREEN = "#4caf50"
    
    # Fonts
    FONT_MAIN = ("Segoe UI", 10)
    # Define font families as a comma-separated string for fallbacks.
    # Quotes can be used around names with spaces, though often not strictly necessary.
    FONT_FAMILY_CODE = "Consolas, 'Courier New', Courier, monospace"
    FONT_CODE = (FONT_FAMILY_CODE, 11) 
    FONT_SMALL = ("Segoe UI", 9)
    FONT_LARGE = ("Segoe UI", 12, "bold")

class AICodeEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_variables()
        self.setup_ui()
        self.setup_bindings()
        self.apply_modern_styling()
        
        # Load sample code
        self.load_sample_code()
        
        # Initialize AI
        self.setup_gemini()
        
    def setup_window(self):
        """Configure the main window"""
        self.root.title("AI Code Editor - Gemini Integration")
        self.root.geometry("1200x800")
        self.root.configure(bg=ModernStyle.BG_MAIN)
        self.root.minsize(800, 600)
        
        # Configure grid weights
        self.root.grid_rowconfigure(2, weight=1)  # Code editor area
        self.root.grid_columnconfigure(0, weight=1)
        
    def setup_variables(self):
        """Initialize instance variables"""
        self.current_file = None
        self.is_modified = False
        self.gemini_model = None
        self.api_key = None
        self.pending_edits = []
        self.is_ai_processing = False
        
    def setup_gemini(self):
        """Initialize Gemini AI integration"""
        if not GENAI_AVAILABLE:
            self.ai_status_label.config(text="AI: Not Available (Install google-generativeai)")
            return
            
        # Try to load API key from environment or prompt user
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            self.api_key = simpledialog.askstring(
                "Gemini API Key", 
                "Enter your Gemini API key:",
                show='*',
                parent=self.root 
            )
            
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                self.ai_status_label.config(
                    text="AI: Connected ✓", 
                    foreground=ModernStyle.ACCENT_GREEN
                )
            except Exception as e:
                self.ai_status_label.config(
                    text=f"AI: Error - {str(e)[:20]}...", 
                    foreground=ModernStyle.ACCENT_RED
                )
        else:
            self.ai_status_label.config(
                text="AI: No API Key", 
                foreground=ModernStyle.ACCENT_YELLOW
            )
            
    def setup_ui(self):
        """Create the user interface"""
        self.create_menu_bar()
        self.create_toolbar()
        self.create_ai_prompt_section()
        self.create_code_editor()
        self.create_status_bar()
        
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root, bg=ModernStyle.BG_PANEL, fg=ModernStyle.TEXT_PRIMARY)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg=ModernStyle.BG_PANEL, fg=ModernStyle.TEXT_PRIMARY)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S") 
        file_menu.add_command(label="Save As...", command=self.save_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0, bg=ModernStyle.BG_PANEL, fg=ModernStyle.TEXT_PRIMARY)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=lambda: self.code_text.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", command=lambda: self.code_text.event_generate("<<Redo>>"))
        
        # AI menu
        ai_menu = tk.Menu(menubar, tearoff=0, bg=ModernStyle.BG_PANEL, fg=ModernStyle.TEXT_PRIMARY)
        menubar.add_cascade(label="AI", menu=ai_menu)
        ai_menu.add_command(label="Configure API Key", command=self.configure_api_key)
        ai_menu.add_command(label="Test Connection", command=self.test_ai_connection)
        
    def create_toolbar(self):
        """Create the application toolbar"""
        toolbar_frame = tk.Frame(self.root, bg=ModernStyle.BG_PANEL, height=40)
        toolbar_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        toolbar_frame.grid_propagate(False)
        
        # Buttons with modern styling
        btn_style = {
            'bg': ModernStyle.BG_HOVER,
            'fg': ModernStyle.TEXT_PRIMARY,
            'font': ModernStyle.FONT_MAIN,
            'relief': 'flat',
            'borderwidth': 0,
            'padx': 15,
            'pady': 5
        }
        
        tk.Button(toolbar_frame, text="📄 New", command=self.new_file, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar_frame, text="📁 Open", command=self.open_file, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar_frame, text="💾 Save", command=self.save_file, **btn_style).pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(toolbar_frame, width=2, bg=ModernStyle.TEXT_TERTIARY).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        tk.Button(toolbar_frame, text="▶️ Run", command=self.run_code, **btn_style).pack(side=tk.LEFT, padx=2)
        
        # AI Status on the right
        self.ai_status_label = tk.Label(
            toolbar_frame, 
            text="AI: Initializing...", 
            bg=ModernStyle.BG_PANEL,
            fg=ModernStyle.TEXT_TERTIARY,
            font=ModernStyle.FONT_SMALL
        )
        self.ai_status_label.pack(side=tk.RIGHT, padx=10)
        
    def create_ai_prompt_section(self):
        """Create the AI prompt input section"""
        ai_frame = tk.Frame(self.root, bg=ModernStyle.BG_PANEL) # No fixed height, allow propagation
        ai_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        # Ensure the frame column holding the entry can expand if needed.
        # Entry is in column 0, spanning 2 (effectively using 0 and 1), button in 2.
        # So, column 0 of ai_frame should have weight if we want entry to expand.
        # Or, more simply, let column 1 (which is part of entry's span) take the weight.
        ai_frame.grid_columnconfigure(1, weight=1) # Original configuration
        
        # Label
        tk.Label(
            ai_frame, 
            text="What would you like to change?", 
            bg=ModernStyle.BG_PANEL,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_MAIN
        ).grid(row=0, column=0, sticky="w", padx=5, pady=5) # Label in column 0
        
        # Input field
        self.ai_prompt_var = tk.StringVar()
        self.ai_prompt_entry = tk.Entry(
            ai_frame,
            textvariable=self.ai_prompt_var,
            bg=ModernStyle.BG_MAIN,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_MAIN,
            relief='solid',
            borderwidth=1,
            insertbackground=ModernStyle.TEXT_PRIMARY,
            state=tk.NORMAL
        )
        # Add some internal padding to make the entry taller and easier to click
        self.ai_prompt_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,10), ipady=8) # Increased ipady
        
        if hasattr(self, 'ai_prompt_entry') and self.ai_prompt_entry.winfo_exists():
            self.ai_prompt_entry.focus_set() # Use focus_set, not focus_force
        else:
            print("DEBUG: ai_prompt_entry was not created or accessible when focus_set was attempted.")

        # Ask AI Button
        self.ask_ai_btn = tk.Button(
            ai_frame,
            text="🤖 Ask AI",
            command=self.ask_ai, # Restore command
            bg=ModernStyle.ACCENT_BLUE,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_MAIN,
            relief='flat',
            borderwidth=0,
            padx=20,
            pady=8
        )
        self.ask_ai_btn.grid(row=1, column=2, sticky="e", padx=5, pady=5)
        
    def create_code_editor(self):
        """Create the main code editor area"""
        editor_frame = tk.Frame(self.root, bg=ModernStyle.BG_MAIN)
        editor_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(1, weight=1)
        
        # Line numbers
        self.line_numbers = tk.Text(
            editor_frame,
            width=4,
            padx=5,
            pady=5,
            bg=ModernStyle.BG_PANEL,
            fg=ModernStyle.TEXT_TERTIARY,
            font=ModernStyle.FONT_CODE,
            relief='flat',
            state='disabled',
            wrap='none'
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns")
        
        # Code text area
        self.code_text = tk.Text(
            editor_frame,
            bg=ModernStyle.BG_MAIN,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_CODE,
            relief='flat',
            insertbackground=ModernStyle.TEXT_PRIMARY,
            selectbackground=ModernStyle.ACCENT_BLUE,
            wrap='none',
            undo=True,
            maxundo=50
        )
        self.code_text.grid(row=0, column=1, sticky="nsew")
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(editor_frame, orient="vertical", command=self.on_scroll)
        v_scrollbar.grid(row=0, column=2, sticky="ns")
        self.code_text.config(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = tk.Scrollbar(editor_frame, orient="horizontal", command=self.code_text.xview)
        h_scrollbar.grid(row=1, column=1, sticky="ew")
        self.code_text.config(xscrollcommand=h_scrollbar.set)
        
        # Bind events
        self.code_text.bind('<KeyRelease>', self.on_text_change)
        self.code_text.bind('<Button-1>', self.on_text_change)
        self.code_text.bind('<Return>', self.on_text_change)
        
    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = tk.Label(
            self.root,
            text="Ready",
            bg=ModernStyle.BG_PANEL,
            fg=ModernStyle.TEXT_SECONDARY,
            font=ModernStyle.FONT_SMALL,
            anchor="w",
            relief='sunken',
            padx=10
        )
        self.status_bar.grid(row=3, column=0, sticky="ew")
        
    def setup_bindings(self):
        """Setup keyboard shortcuts and event bindings"""
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_file_as())
        self.root.bind('<F5>', lambda e: self.run_code())
        self.root.bind('<Return>', self.on_enter_pressed)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def apply_modern_styling(self):
        """Apply modern styling to ttk widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure ttk styles
        style.configure('Modern.TButton',
                       background=ModernStyle.BG_HOVER,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       borderwidth=0,
                       focuscolor='none')
        
    def load_sample_code(self):
        """Load sample Python code with various issues for testing"""
        sample_code = '''import sys
import requests

def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def fetch_user_data(user_id):
    url = f"https://api.example.com/users/{user_id}"
    response = requests.get(url)
    return response.json()

def process_data(data):
    results = []
    for item in data:
        if item > 0:
            results.append(item * 2)
    return results

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add_data(self, value):
        self.data.append(value)
    
    def get_stats(self):
        if len(self.data) == 0:
            return None
        return {
            'mean': sum(self.data) / len(self.data),
            'max': max(self.data),
            'min': min(self.data)
        }

if __name__ == "__main__":
    processor = DataProcessor()
    numbers = [1, 2, 3, 4, 5]
    
    for num in numbers:
        processor.add_data(num)
    
    stats = processor.get_stats()
    print("Statistics:", stats)
    
    avg = calculate_average(numbers)
    print(f"Average: {avg}")
'''
        self.code_text.insert('1.0', sample_code)
        self.update_line_numbers()
        
    def on_scroll(self, *args):
        """Handle scrolling for synchronized line numbers"""
        self.code_text.yview(*args)
        self.line_numbers.yview(*args)
        
    def on_text_change(self, event=None):
        """Handle text changes in the editor"""
        self.update_line_numbers()
        self.is_modified = True
        self.update_title()
        
    def update_line_numbers(self):
        """Update the line numbers display"""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', 'end')
        
        line_count = int(self.code_text.index('end-1c').split('.')[0])
        line_numbers_text = '\n'.join(str(i) for i in range(1, line_count + 1))
        
        self.line_numbers.insert('1.0', line_numbers_text)
        self.line_numbers.config(state='disabled')
        
    def update_title(self):
        """Update the window title"""
        title = "AI Code Editor - Gemini Integration"
        if self.current_file:
            title += f" - {os.path.basename(self.current_file)}"
        if self.is_modified:
            title += " *"
        self.root.title(title)
        
    def new_file(self):
        """Create a new file"""
        if self.is_modified and not self.confirm_unsaved_changes():
            return
            
        self.code_text.delete('1.0', 'end')
        self.current_file = None
        self.is_modified = False
        self.update_title()
        self.update_line_numbers()
        self.status_bar.config(text="New file created")
        
    def open_file(self):
        """Open an existing file"""
        if self.is_modified and not self.confirm_unsaved_changes():
            return
            
        file_path = filedialog.askopenfilename(
            title="Open File",
            filetypes=[
                ("Python files", "*.py"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                self.code_text.delete('1.0', 'end')
                self.code_text.insert('1.0', content)
                self.current_file = file_path
                self.is_modified = False
                self.update_title()
                self.update_line_numbers()
                self.status_bar.config(text=f"Opened: {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}", parent=self.root)
                
    def save_file(self):
        """Save the current file"""
        if self.current_file:
            self.save_to_file(self.current_file)
        else:
            self.save_file_as()
            
    def save_file_as(self):
        """Save the file with a new name"""
        file_path = filedialog.asksaveasfilename(
            title="Save File",
            defaultextension=".py",
            filetypes=[
                ("Python files", "*.py"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.save_to_file(file_path)
            
    def save_to_file(self, file_path):
        """Save content to the specified file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                content = self.code_text.get('1.0', 'end-1c')
                file.write(content)
                
            self.current_file = file_path
            self.is_modified = False
            self.update_title()
            self.status_bar.config(text=f"Saved: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {str(e)}", parent=self.root)
            
    def confirm_unsaved_changes(self):
        """Ask user about unsaved changes"""
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save them?",
            parent=self.root
        )
        
        if result is True:  # Yes, save
            self.save_file()
            return not self.is_modified  # Only proceed if save was successful
        elif result is False:  # No, don't save
            return True
        else:  # Cancel
            return False
            
    def run_code(self):
        """Execute the current Python code"""
        if not self.current_file:
            # Save to temporary file
            temp_file = "temp_code.py"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(self.code_text.get('1.0', 'end-1c'))
            file_to_run = temp_file
        else:
            if self.is_modified:
                self.save_file()
            file_to_run = self.current_file
            
        # Run in separate thread to prevent UI blocking
        threading.Thread(target=self._execute_code, args=(file_to_run,), daemon=True).start()
        
    def _execute_code(self, file_path):
        """Execute code in a separate thread"""
        try:
            self.status_bar.config(text="Running code...")
            start_time = time.time()
            
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            # Show results in a popup window
            self.root.after(0, self.show_execution_results, result, execution_time)
            
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self.status_bar.config(text="Code execution timed out"))
        except Exception as e:
            self.root.after(0, lambda: self.status_bar.config(text=f"Execution error: {str(e)}"))
            
    def show_execution_results(self, result, execution_time):
        """Show code execution results in a popup"""
        results_window = tk.Toplevel(self.root)
        results_window.title("Code Execution Results")
        results_window.geometry("600x400")
        results_window.configure(bg=ModernStyle.BG_MAIN)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(results_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Output tab
        output_frame = tk.Frame(notebook, bg=ModernStyle.BG_MAIN)
        notebook.add(output_frame, text="Output")
        
        output_text = tk.Text(
            output_frame,
            bg=ModernStyle.BG_MAIN,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_CODE,
            wrap=tk.WORD
        )
        output_text.pack(fill=tk.BOTH, expand=True)
        output_text.insert('1.0', result.stdout if result.stdout else "(No output)")
        
        # Error tab (if there are errors)
        if result.stderr:
            error_frame = tk.Frame(notebook, bg=ModernStyle.BG_MAIN)
            notebook.add(error_frame, text="Errors")
            
            error_text = tk.Text(
                error_frame,
                bg=ModernStyle.BG_MAIN,
                fg=ModernStyle.ACCENT_RED,
                font=ModernStyle.FONT_CODE,
                wrap=tk.WORD
            )
            error_text.pack(fill=tk.BOTH, expand=True)
            error_text.insert('1.0', result.stderr)
            
        # Status info
        status_text = f"Exit code: {result.returncode} | Execution time: {execution_time:.2f}s"
        self.status_bar.config(text=status_text)
        
    def ask_ai(self):
        """Send prompt to AI and get edit suggestions"""
        if not self.gemini_model:
            messagebox.showerror("Error", "AI model not available. Please configure your API key.", parent=self.root)
            return
            
        prompt = self.ai_prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning("Warning", "Please enter a description of what you'd like to change.", parent=self.root)
            return
            
        # Disable AI button and show processing
        self.ask_ai_btn.config(state='disabled', text="🤖 Processing...")
        self.is_ai_processing = True
        
        # Run AI request in separate thread
        threading.Thread(target=self._process_ai_request, args=(prompt,), daemon=True).start()
        
    def _process_ai_request(self, prompt):
        """Process AI request in separate thread"""
        try:
            current_code = self.code_text.get('1.0', 'end-1c')
            
            ai_prompt = f"""You are a precise code editor assistant. Analyze the provided code and suggest specific edits based on the user's request.

ALWAYS respond with valid JSON in this exact format:
{{
  "analysis": "Brief summary of what you found and will change",
  "edits": [
    {{
      "line_start": 5,
      "line_end": 5,
      "original_code": "def old_function():",
      "suggested_code": "def improved_function() -> None:",
      "explanation": "Added type hint for better code documentation",
      "edit_type": "replace",
      "confidence": 0.95
    }}
  ]
}}

Rules:
- Be surgical - only change what's necessary
- Line numbers start from 1
- For insertions: line_start = line_end, original_code = ""
- For deletions: suggested_code = ""
- Match original code exactly (including whitespace)
- Focus on the specific user request
- Only suggest changes that directly address the request

- **IF YOU DECIDE TO REPLACE AN ENTIRE FUNCTION/METHOD (e.g., user asks to refactor or add features to a whole function):**
    1. First, internally generate the complete new version of the function.
    2. Then, carefully identify the *exact* starting line (e.g., `def function_name(...):`) and the *exact* ending line of the ORIGINAL function/method in the provided code.
    3. `line_start` in your JSON output MUST be the line number of the original function's/method's starting `def` line.
    4. `line_end` in your JSON output MUST be the line number of the original function's/method's final line (including all its body).
    5. `original_code` in your JSON MUST be the complete, verbatim text of the entire original function/method from `line_start` to `line_end`.
    6. `suggested_code` in your JSON MUST be the complete new version of the entire function/method you generated in step 1.
    7. Set `edit_type: "replace"`.
    8. **CRUCIAL**: Your `suggested_code` must be self-contained and a full replacement. Do not let any part of the old function's body automatically carry over unless it's explicitly part of your new `suggested_code`.
    9. Ensure standard Python PEP 8 spacing (e.g., typically two blank lines) between top-level function/class definitions if your `suggested_code` replaces a block and affects this spacing.

- **FOR SMALLER, TARGETED CHANGES (e.g., fixing a typo on a single line, changing one expression, adding a parameter with its type hint):**
    1. Precisely identify `line_start`, `line_end` (often the same for single-line changes), and the exact `original_code` for the small segment.
    2. Provide the `suggested_code` for that specific segment.
    3. Set `edit_type: "replace"` (or "insert"/"delete" if more appropriate for the very specific small change).
    4. This mode is for surgical changes that do NOT replace an entire function body.

- **AVOID DUPLICATION**: Do not suggest inserting a new function if the user's intent is to modify an existing one. Prefer replacing using the guidelines above.

Current code:
```python
{current_code}
```

User request: {prompt}"""

            response = self.gemini_model.generate_content(ai_prompt)
            
            # Parse AI response
            try:
                # Extract JSON from response
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3]
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3]
                    
                ai_data = json.loads(response_text)
                
                # Validate response structure
                if 'analysis' not in ai_data or 'edits' not in ai_data:
                    raise ValueError("Invalid AI response structure")
                    
                # Convert to EditSuggestion objects
                edit_suggestions = []
                for edit_data in ai_data['edits']:
                    suggestion = EditSuggestion(
                        line_start=edit_data['line_start'],
                        line_end=edit_data['line_end'],
                        original_code=edit_data['original_code'],
                        suggested_code=edit_data['suggested_code'],
                        explanation=edit_data['explanation'],
                        edit_type=edit_data['edit_type'],
                        confidence=edit_data['confidence']
                    )
                    edit_suggestions.append(suggestion)
                    
                # Show edit preview on main thread
                self.root.after(0, self.show_edit_preview, ai_data['analysis'], edit_suggestions)
                self.root.after(0, lambda: self.status_bar.config(text="AI suggestions ready for review."))
                
            except json.JSONDecodeError as e:
                error_message = f"Could not parse AI response (JSONDecodeError): {str(e)}\n"
                error_message += f"Position: {e.pos}, Line: {e.lineno}, Column: {e.colno}\n"
                error_message += f"\nRaw response excerpt:\n{response.text[:500]}..."
                self.root.after(0, lambda: messagebox.showerror("AI Response Error", error_message, parent=self.root))
                self.root.after(0, lambda: self.status_bar.config(text="AI Error: Invalid JSON response."))
            except (KeyError, ValueError) as e:
                error_message = f"Invalid AI response structure ({type(e).__name__}): {str(e)}\n"
                error_message += "\nThe AI response did not match the expected format (e.g., missing 'analysis' or 'edits' keys).\n"
                error_message += f"\nRaw response excerpt:\n{response.text[:500]}..."
                self.root.after(0, lambda: messagebox.showerror("AI Response Error", error_message, parent=self.root))
                self.root.after(0, lambda: self.status_bar.config(text="AI Error: Unexpected response structure."))
                
        except Exception as e:
            # This catches errors from self.gemini_model.generate_content() or other unexpected issues
            self.root.after(0, lambda: messagebox.showerror(
                "AI Processing Error",
                f"An unexpected error occurred while communicating with the AI: {str(e)}",
                parent=self.root
            ))
            self.root.after(0, lambda: self.status_bar.config(text=f"AI Error: {str(e)[:50]}..."))
        finally:
            # Re-enable AI button and reset processing flag
            self.root.after(0, self._reset_ai_interaction)
            
    def _reset_ai_interaction(self, status_message: Optional[str] = None):
        """Reset AI button state, processing flag, and optionally update status bar."""
        self.ask_ai_btn.config(state='normal', text="🤖 Ask AI")
        self.is_ai_processing = False
        if status_message:
            self.status_bar.config(text=status_message)

    def apply_single_edit_action(self, edit_index: int, preview_window_ref):
        """Handles the 'Apply this Fix' button click on a card."""
        if edit_index in self.applied_edit_indices:
            # Optionally show a message, or just do nothing if already actioned
            # messagebox.showinfo("Info", "This suggestion has already been actioned.", parent=preview_window_ref)
            return

        self.edit_checkboxes[edit_index].set(True)  # Check the box

        card_widgets = self.edit_card_widgets.get(edit_index)
        if card_widgets:
            card_widgets['apply_button'].config(state='disabled', text="Selected ✓")
            card_widgets['skip_button'].config(state='disabled')
            # Optional: disable checkbox to prevent further changes after card button click
            # card_widgets['checkbox_widget'].config(state='disabled')

        self.applied_edit_indices.add(edit_index)

    def skip_single_edit_action(self, edit_index: int, preview_window_ref):
        """Handles the 'Skip this Fix' button click on a card."""
        if edit_index in self.applied_edit_indices:
            # messagebox.showinfo("Info", "This suggestion has already been actioned.", parent=preview_window_ref)
            return

        self.edit_checkboxes[edit_index].set(False)  # Uncheck the box

        card_widgets = self.edit_card_widgets.get(edit_index)
        if card_widgets:
            card_widgets['apply_button'].config(state='disabled')
            card_widgets['skip_button'].config(state='disabled', text="Skipped ✕")
            # Optional: disable checkbox
            # card_widgets['checkbox_widget'].config(state='disabled')

        self.applied_edit_indices.add(edit_index)

    def cleanup_code_post_edit(self, code_content: str) -> str:
        cleaned_lines = [] # Ensure this is the very first line of substantive code.
        # Pass 1: Remove duplicate signatures (existing logic)
        lines = code_content.split('\n')
        i = 0
        while i < len(lines):
            line_a = lines[i]

            # Regex to capture 'def func_name(params):' or 'def func_name(params) -> type:'
            # Captures: 1=indent, 2=full_def_line, 3=func_name, 4=params_with_parens_and_return_type, 5=colon_and_rest (should be just colon)
            func_def_pattern = r"^(\s*)(def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(\((?:[^)]|\([^)]*\))*\)\s*(?:->\s*[\w\.\[\], \s]+)?)\s*:)"
            match_a = re.match(func_def_pattern, line_a)

            if match_a:
                indent_a = match_a.group(1)
                func_name_a = match_a.group(3)
                # Group 4 contains params and optional return type, e.g., "(param1: int, param2) -> str"
                params_and_return_a_str = match_a.group(4)

                # Look for the next non-empty line, collecting any blank lines in between
                temp_intermediate_lines = []
                j = i + 1
                line_b_content = None
                while j < len(lines):
                    if lines[j].strip():
                        line_b_content = lines[j]
                        break
                    temp_intermediate_lines.append(lines[j]) # Store blank line
                    j += 1

                if line_b_content is not None:
                    match_b = re.match(func_def_pattern, line_b_content)
                    if match_b:
                        indent_b = match_b.group(1)
                        func_name_b = match_b.group(3)
                        params_and_return_b_str = match_b.group(4)

                        if indent_a == indent_b and func_name_a == func_name_b:
                            is_b_more_complete = False
                            # Check for presence of return type hint "->"
                            has_return_b = "->" in params_and_return_b_str
                            has_return_a = "->" in params_and_return_a_str
                            if has_return_b and not has_return_a:
                                is_b_more_complete = True

                            if not is_b_more_complete:
                                # Check for presence of parameter type hints ": "
                                # This is a simplification; proper parsing would be more robust.
                                has_param_typing_b = ": " in params_and_return_b_str
                                has_param_typing_a = ": " in params_and_return_a_str
                                if has_param_typing_b and not has_param_typing_a:
                                    is_b_more_complete = True

                            if not is_b_more_complete:
                                # Compare length of the params + return string as a heuristic
                                # Add a bias if B has type hints and A doesn't, or if B has return and A doesn't
                                len_a = len(params_and_return_a_str)
                                len_b = len(params_and_return_b_str)
                                if has_param_typing_b and not has_param_typing_a: len_b += 5 # Arbitrary bonus
                                if has_return_b and not has_return_a: len_b += 5 # Arbitrary bonus

                                if len_b > len_a + 1 : # B is significantly longer
                                    is_b_more_complete = True

                            if not is_b_more_complete:
                                # Case: A is '()' and has no types/return, B is not '()' or has types/return
                                is_a_simple_empty_params = params_and_return_a_str == "()" and not has_return_a and not (": " in params_and_return_a_str)
                                is_b_complex_or_has_types = params_and_return_b_str != "()" or has_return_b or (": " in params_and_return_b_str)
                                if is_a_simple_empty_params and is_b_complex_or_has_types:
                                    is_b_more_complete = True

                            if is_b_more_complete:
                                cleaned_lines.extend(temp_intermediate_lines) # Add collected blank lines
                                cleaned_lines.append(line_b_content) # Ensure this appends to cleaned_lines
                                i = j + 1
                                continue

            cleaned_lines.append(line_a) # Ensure this appends to cleaned_lines
            i += 1

        return "\n".join(cleaned_lines) # Ensure this joins cleaned_lines
        
    def show_edit_preview(self, analysis, edit_suggestions):
        """Show edit preview dialog"""
        if not edit_suggestions:
            # Parent for this messagebox should be self.root as preview_window doesn't exist.
            messagebox.showinfo("No Changes", "AI didn't suggest any changes for your request.", parent=self.root)
            self.status_bar.config(text="AI found no changes to suggest for your request.")
            # _reset_ai_interaction is already called in the finally block of _process_ai_request
            return
            
        preview_window = tk.Toplevel(self.root)
        preview_window.title("AI Edit Suggestions")
        preview_window.geometry("900x700")
        preview_window.configure(bg=ModernStyle.BG_MAIN)

        # Ensure grab is released when the preview window is destroyed
        def on_preview_destroy(event, window=preview_window): # Capture window in lambda default
            if event.widget == window:
                # print("DEBUG: Preview window destroyed, releasing grab.") # For debugging
                window.grab_release()

        preview_window.bind("<Destroy>", on_preview_destroy)
        preview_window.transient(self.root) # Keep on top of main window
        preview_window.grab_set() # Make modal
        
        # Main frame
        main_frame = tk.Frame(preview_window, bg=ModernStyle.BG_MAIN)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Analysis section
        analysis_frame = tk.Frame(main_frame, bg=ModernStyle.BG_PANEL, relief='solid', bd=1)
        analysis_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            analysis_frame,
            text=analysis,
            bg=ModernStyle.BG_PANEL,
            fg=ModernStyle.TEXT_SECONDARY,
            font=ModernStyle.FONT_MAIN,
            wraplength=850,
            justify='left'
        ).pack(anchor='w', padx=10, pady=(0, 10))
        
        # Edit suggestions section
        suggestions_frame = tk.Frame(main_frame, bg=ModernStyle.BG_MAIN)
        suggestions_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with controls
        header_frame = tk.Frame(suggestions_frame, bg=ModernStyle.BG_MAIN)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header_frame,
            text=f"Edit Suggestions ({len(edit_suggestions)} changes):",
            bg=ModernStyle.BG_MAIN,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_LARGE
        ).pack(side=tk.LEFT)
        
        # Bulk selection buttons
        btn_frame = tk.Frame(header_frame, bg=ModernStyle.BG_MAIN)
        btn_frame.pack(side=tk.RIGHT)
        
        tk.Button(
            btn_frame,
            text="Select All",
            command=lambda: self.toggle_all_edits(edit_suggestions, True),
            bg=ModernStyle.BG_HOVER,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_SMALL,
            relief='flat',
            padx=10
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_frame,
            text="Select None",
            command=lambda: self.toggle_all_edits(edit_suggestions, False),
            bg=ModernStyle.BG_HOVER,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_SMALL,
            relief='flat',
            padx=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Scrollable frame for edit cards
        canvas = tk.Canvas(suggestions_frame, bg=ModernStyle.BG_MAIN, highlightthickness=0)
        scrollbar = tk.Scrollbar(suggestions_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=ModernStyle.BG_MAIN)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create edit cards
        self.edit_checkboxes = {} # Stores BooleanVars for checkboxes
        self.edit_card_widgets = {} # To store references to card frames' buttons and checkbox widgets
        self.applied_edit_indices = set() # Tracks indices actioned by card buttons
        # self.active_edit_suggestions = edit_suggestions # Store for reference by card actions if needed

        for i, edit in enumerate(edit_suggestions):
            # Pass preview_window to card creation for messageboxes if needed by actions
            self.create_edit_card(scrollable_frame, edit, i, preview_window)
            
        # Action buttons
        action_frame = tk.Frame(main_frame, bg=ModernStyle.BG_MAIN)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(
            action_frame,
            text="Apply Selected Changes",
            command=lambda: self.apply_selected_edits(edit_suggestions, preview_window),
            bg=ModernStyle.ACCENT_GREEN,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_MAIN,
            relief='flat',
            padx=20,
            pady=8
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            action_frame,
            text="Cancel",
            command=preview_window.destroy,
            bg=ModernStyle.BG_HOVER,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_MAIN,
            relief='flat',
            padx=20,
            pady=8
        ).pack(side=tk.RIGHT, padx=5)
        
    def create_edit_card(self, parent, edit: EditSuggestion, index: int, preview_window_ref):
        """Create a card for displaying an edit suggestion"""
        card_frame = tk.Frame(
            parent, 
            bg=ModernStyle.BG_PANEL, 
            relief='solid', 
            bd=1
        )
        card_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Header with checkbox and info
        header_frame = tk.Frame(card_frame, bg=ModernStyle.BG_PANEL)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Checkbox
        checkbox_var = tk.BooleanVar(value=edit.selected)
        self.edit_checkboxes[index] = checkbox_var # Storing the BooleanVar
        
        checkbox_widget = tk.Checkbutton(
            header_frame,
            variable=checkbox_var,
            bg=ModernStyle.BG_PANEL,
            fg=ModernStyle.TEXT_PRIMARY,
            selectcolor=ModernStyle.BG_HOVER,
            activebackground=ModernStyle.BG_PANEL,
            activeforeground=ModernStyle.TEXT_PRIMARY
        )
        checkbox_widget.pack(side=tk.LEFT)
        
        # Edit info
        info_text = f"Lines {edit.line_start}-{edit.line_end} • {edit.edit_type} • Confidence: {edit.confidence:.0%}"
        tk.Label(
            header_frame,
            text=info_text,
            bg=ModernStyle.BG_PANEL,
            fg=ModernStyle.TEXT_TERTIARY,
            font=ModernStyle.FONT_SMALL
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Explanation
        tk.Label(
            card_frame,
            text=edit.explanation,
            bg=ModernStyle.BG_PANEL,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_MAIN,
            wraplength=800,
            justify='left'
        ).pack(fill=tk.X, padx=10, pady=(0, 5))

        # Card action buttons (Apply this, Skip this)
        card_action_frame = tk.Frame(card_frame, bg=ModernStyle.BG_PANEL)
        card_action_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

        apply_this_btn = tk.Button(
            card_action_frame,
            text="Apply this Fix",
            bg=ModernStyle.ACCENT_GREEN,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_SMALL,
            relief='flat',
            padx=10,
            command=lambda idx=index, pw=preview_window_ref: self.apply_single_edit_action(idx, pw)
        )
        apply_this_btn.pack(side=tk.LEFT, padx=5)

        skip_this_btn = tk.Button(
            card_action_frame,
            text="Skip this Fix",
            bg=ModernStyle.BG_HOVER,
            fg=ModernStyle.TEXT_PRIMARY,
            font=ModernStyle.FONT_SMALL,
            relief='flat',
            padx=10,
            command=lambda idx=index, pw=preview_window_ref: self.skip_single_edit_action(idx, pw)
        )
        skip_this_btn.pack(side=tk.LEFT, padx=5)

        self.edit_card_widgets[index] = {
            'apply_button': apply_this_btn,
            'skip_button': skip_this_btn,
            'checkbox_widget': checkbox_widget  # Storing the actual checkbox widget
        }
        
        # Code diff section
        diff_frame = tk.Frame(card_frame, bg=ModernStyle.BG_MAIN)
        diff_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        if edit.edit_type == 'replace':
            # Show original code (red background)
            if edit.original_code.strip():
                original_frame = tk.Frame(diff_frame, bg=ModernStyle.ACCENT_RED)
                original_frame.pack(fill=tk.X, pady=1)
                
                tk.Label(
                    original_frame,
                    text="- Remove:",
                    bg=ModernStyle.ACCENT_RED,
                    fg=ModernStyle.TEXT_PRIMARY,
                    font=ModernStyle.FONT_SMALL
                ).pack(anchor='w', padx=5, pady=2)
                
                tk.Text(
                    original_frame,
                    height=min(3, edit.original_code.count('\n') + 1),
                    bg='#2d1b1b',
                    fg=ModernStyle.TEXT_PRIMARY,
                    font=ModernStyle.FONT_CODE,
                    wrap=tk.NONE,
                    state='normal'
                ).pack(fill=tk.X, padx=5, pady=2)
                
                original_text = original_frame.winfo_children()[-1]
                original_text.insert('1.0', edit.original_code)
                original_text.config(state='disabled')
            
            # Show suggested code (green background)
            if edit.suggested_code.strip():
                suggested_frame = tk.Frame(diff_frame, bg=ModernStyle.ACCENT_GREEN)
                suggested_frame.pack(fill=tk.X, pady=1)
                
                tk.Label(
                    suggested_frame,
                    text="+ Add:",
                    bg=ModernStyle.ACCENT_GREEN,
                    fg=ModernStyle.TEXT_PRIMARY,
                    font=ModernStyle.FONT_SMALL
                ).pack(anchor='w', padx=5, pady=2)
                
                tk.Text(
                    suggested_frame,
                    height=min(3, edit.suggested_code.count('\n') + 1),
                    bg='#1b2d1b',
                    fg=ModernStyle.TEXT_PRIMARY,
                    font=ModernStyle.FONT_CODE,
                    wrap=tk.NONE,
                    state='normal'
                ).pack(fill=tk.X, padx=5, pady=2)
                
                suggested_text = suggested_frame.winfo_children()[-1]
                suggested_text.insert('1.0', edit.suggested_code)
                suggested_text.config(state='disabled')
                
        elif edit.edit_type == 'insert':
            # Show only suggested code for insertions
            suggested_frame = tk.Frame(diff_frame, bg=ModernStyle.ACCENT_GREEN)
            suggested_frame.pack(fill=tk.X, pady=1)
            
            tk.Label(
                suggested_frame,
                text=f"+ Insert at line {edit.line_start}:",
                bg=ModernStyle.ACCENT_GREEN,
                fg=ModernStyle.TEXT_PRIMARY,
                font=ModernStyle.FONT_SMALL
            ).pack(anchor='w', padx=5, pady=2)
            
            tk.Text(
                suggested_frame,
                height=min(3, edit.suggested_code.count('\n') + 1),
                bg='#1b2d1b',
                fg=ModernStyle.TEXT_PRIMARY,
                font=ModernStyle.FONT_CODE,
                wrap=tk.NONE,
                state='normal'
            ).pack(fill=tk.X, padx=5, pady=2)
            
            suggested_text = suggested_frame.winfo_children()[-1]
            suggested_text.insert('1.0', edit.suggested_code)
            suggested_text.config(state='disabled')
            
        elif edit.edit_type == 'delete':
            # Show only original code for deletions
            original_frame = tk.Frame(diff_frame, bg=ModernStyle.ACCENT_RED)
            original_frame.pack(fill=tk.X, pady=1)
            
            tk.Label(
                original_frame,
                text=f"- Delete lines {edit.line_start}-{edit.line_end}:",
                bg=ModernStyle.ACCENT_RED,
                fg=ModernStyle.TEXT_PRIMARY,
                font=ModernStyle.FONT_SMALL
            ).pack(anchor='w', padx=5, pady=2)
            
            tk.Text(
                original_frame,
                height=min(3, edit.original_code.count('\n') + 1),
                bg='#2d1b1b',
                fg=ModernStyle.TEXT_PRIMARY,
                font=ModernStyle.FONT_CODE,
                wrap=tk.NONE,
                state='normal'
            ).pack(fill=tk.X, padx=5, pady=2)
            
            original_text = original_frame.winfo_children()[-1]
            original_text.insert('1.0', edit.original_code)
            original_text.config(state='disabled')
            
    def toggle_all_edits(self, edit_suggestions, select_all):
        """Toggle all edit selections"""
        for i in range(len(edit_suggestions)):
            if i in self.edit_checkboxes:
                self.edit_checkboxes[i].set(select_all)
                # edit_suggestions[i].selected is not directly used by apply_selected_edits,
                # which relies on the BooleanVar from self.edit_checkboxes.
                # So, updating edit_suggestions[i].selected here is redundant.
                
    def apply_selected_edits(self, edit_suggestions, preview_window):
        """Apply the selected edits to the code"""
        # Get selected edits
        selected_edits = []
        for i, edit in enumerate(edit_suggestions):
            if i in self.edit_checkboxes and self.edit_checkboxes[i].get():
                selected_edits.append(edit)
                
        if not selected_edits:
            messagebox.showwarning("No Selection", "Please select at least one edit to apply.", parent=preview_window)
            return
            
        # Sort edits by line number (descending) to avoid line number shifts
        selected_edits.sort(key=lambda x: x.line_start, reverse=True)
        
        # Apply edits
        try:
            current_lines = self.code_text.get('1.0', 'end-1c').split('\n')
            
            for edit in selected_edits:
                # Line numbers from AI are 1-based, convert to 0-based for list indexing
                start_index = edit.line_start - 1
                end_index = edit.line_end - 1 # For deletion/replacement, this is the last line to remove

                if edit.edit_type == 'replace':
                    # Validate line numbers
                    if not (0 <= start_index < len(current_lines) and 0 <= end_index < len(current_lines) and start_index <= end_index):
                        print(f"Warning: Invalid line numbers for replace: {edit.line_start}-{edit.line_end}. Skipping edit.")
                        continue

                    # Remove original lines (from start_index to end_index inclusive)
                    del current_lines[start_index : end_index + 1]
                    
                    # Insert new lines (split suggested code into lines)
                    suggested_lines = edit.suggested_code.split('\n')
                    for i, line_content in enumerate(suggested_lines):
                        current_lines.insert(start_index + i, line_content)
                        
                elif edit.edit_type == 'insert':
                    # Validate line number (insertion happens *before* this line)
                    # So, if line_start is 1, it inserts at index 0.
                    # If line_start is len(current_lines) + 1, it inserts at the end.
                    insert_at_index = edit.line_start - 1
                    if not (0 <= insert_at_index <= len(current_lines)):
                        print(f"Warning: Invalid line number for insert: {edit.line_start}. Skipping edit.")
                        continue

                    suggested_lines = edit.suggested_code.split('\n')
                    for i, line_content in enumerate(suggested_lines):
                        current_lines.insert(insert_at_index + i, line_content)
                    
                elif edit.edit_type == 'delete':
                    # Validate line numbers
                    if not (0 <= start_index < len(current_lines) and 0 <= end_index < len(current_lines) and start_index <= end_index):
                        print(f"Warning: Invalid line numbers for delete: {edit.line_start}-{edit.line_end}. Skipping edit.")
                        continue
                        
                    # Delete lines (from start_index to end_index inclusive)
                    del current_lines[start_index : end_index + 1]
            
            # Update the editor
            new_content = '\n'.join(current_lines)
            cleaned_content = self.cleanup_code_post_edit(new_content)
            self.code_text.delete('1.0', 'end')
            self.code_text.insert('1.0', cleaned_content)
            
            # Update UI
            self.update_line_numbers()
            self.is_modified = True
            self.update_title()
            
            # Close preview window
            preview_window.destroy()
            
            # Show success message
            self.status_bar.config(text=f"Applied {len(selected_edits)} changes successfully")
            
            # Clear AI prompt
            self.ai_prompt_var.set("")
            
        except Exception as e:
            # If preview_window is already destroyed, parent to self.root
            parent_window = self.root if not preview_window.winfo_exists() else preview_window
            messagebox.showerror("Error", f"Error applying edits: {str(e)}", parent=parent_window)
            
    def configure_api_key(self):
        """Configure the Gemini API key"""
        new_key = simpledialog.askstring(
            "Configure API Key",
            "Enter your Gemini API key:",
            show='*',
            initialvalue=self.api_key if self.api_key else "",
            parent=self.root
        )
        
        if new_key:
            self.api_key = new_key
            self.setup_gemini()
            
    def test_ai_connection(self):
        """Test the AI connection"""
        if not GENAI_AVAILABLE:
            messagebox.showerror("Error", "Gemini AI library not available. Please install 'google-generativeai'.", parent=self.root)
            return

        if not self.api_key:
            messagebox.showerror("Error", "API key not set. Please configure your API key first.", parent=self.root)
            return

        if not self.gemini_model:
            messagebox.showerror("Error", "AI model not initialized. This might be due to an invalid API key or connection issue during setup.", parent=self.root)
            # Optionally, try to re-initialize
            # self.setup_gemini() 
            # if not self.gemini_model:
            #     return # Still not initialized
            return
            
        try:
            self.status_bar.config(text="Testing AI connection...")
            test_response = self.gemini_model.generate_content("Hello, please respond with 'Connection successful'")
            
            if "Connection successful" in test_response.text:
                messagebox.showinfo("Connection Test Successful", f"AI Response: {test_response.text}", parent=self.root)
                self.ai_status_label.config(text="AI: Connected ✓", foreground=ModernStyle.ACCENT_GREEN)
            else:
                messagebox.showwarning("Connection Test", f"AI responded, but not as expected: {test_response.text}", parent=self.root)
            self.status_bar.config(text="AI connection test complete.")
        except Exception as e:
            messagebox.showerror("Connection Test Failed", f"Error during AI connection test: {str(e)}", parent=self.root)
            self.ai_status_label.config(text="AI: Connection Error", foreground=ModernStyle.ACCENT_RED)
            self.status_bar.config(text="AI connection test failed.")
            
    def on_enter_pressed(self, event):
        """Handle Enter key press in AI prompt"""
        if (event.widget == self.ai_prompt_entry and 
            not self.is_ai_processing and 
            self.ai_prompt_var.get().strip()):
            self.ask_ai()
            
    def on_closing(self):
        """Handle application closing"""
        if self.is_modified and not self.confirm_unsaved_changes():
            return
            
        self.root.destroy()
        
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main function to run the application"""
    # Check for required dependencies
    missing_core_deps = []
    if not GENAI_AVAILABLE:
        missing_core_deps.append("google-generativeai")
    # Pygments is for syntax highlighting, potentially optional but good to have.
    # For now, let's treat it as core for the app's intended functionality.
    if not PYGMENTS_AVAILABLE:
        missing_core_deps.append("Pygments") # Package name for pip install
    
    if missing_core_deps:
        missing_deps_str = ", ".join(missing_core_deps)
        message = (
            f"Critical dependencies missing: {missing_deps_str}.\n\n"
            "The application will attempt to install them now. "
            "This may take a moment.\n\n"
            "If this fails, please install them manually by running:\n"
            f"pip install {' '.join(missing_core_deps)}\n\n"
            "Do you want to proceed with automatic installation?"
        )
        
        # Need a temporary root for messagebox if app hasn't started
        # However, this main() is before app = AICodeEditor(), so no Tk root yet.
        # Print to console is the most straightforward here.
        print(message.replace("\n\n", "\n")) # Condense for console
        
        # For a GUI app, a simple console prompt for this is okay before GUI starts.
        # Or, we could pop a simple Tk dialog if Tk is available at this stage.
        # For now, let's assume console interaction for this pre-flight check.
        proceed = input("Proceed with installation? (yes/no): ").strip().lower()

        if proceed == 'yes' or proceed == 'y':
            print(f"\nAttempting to install: {missing_deps_str}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_core_deps)
                print("\nDependencies installed successfully.")
                print("Please restart the application for changes to take effect.")
                # Inform that a restart is needed.
                # For a GUI, could show a messagebox here, but console is fine.
                # simpledialog won't work without a root window.
                return # Exit after installing, user needs to restart
            except subprocess.CalledProcessError as e:
                print(f"\nError: Failed to install dependencies automatically: {e}")
                print(f"Please manually run: pip install {' '.join(missing_core_deps)}")
                return # Exit, cannot run without dependencies
            except FileNotFoundError: # E.g. pip not found
                print("\nError: 'pip' command not found. Please ensure pip is installed and in your PATH.")
                print(f"Please manually run: pip install {' '.join(missing_core_deps)}")
                return
        else:
            print("\nInstallation cancelled by user. Application cannot start without dependencies.")
            print(f"Please manually run: pip install {' '.join(missing_core_deps)}")
            return # Exit

    # Create and run the application
    app = AICodeEditor()
    app.run()


if __name__ == "__main__":
    main()
