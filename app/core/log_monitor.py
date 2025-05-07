# app/core/log_monitor.py
import time
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .analyzer import LogAnalyzer  # Relative import from the same package

class LogHandler(FileSystemEventHandler):
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.current_size = 0
    
    def on_modified(self, event):
        if event.src_path.endswith('.log'):
            try:
                # Only process new lines
                with open(event.src_path, 'r') as f:
                    f.seek(self.current_size)
                    new_lines = f.readlines()
                    self.current_size = f.tell()
                
                if new_lines:
                    # Convert new lines to DataFrame
                    new_data = pd.DataFrame(
                        [line.strip().split() for line in new_lines],
                        columns=['time', 'ip', 'method', 'resource', 'status']
                    )
                    self.analyzer.process_new_entries(new_data)
                    
            except Exception as e:
                print(f"Error processing log update: {str(e)}")

def start_monitoring(log_path, initial_data=None):
    """Start monitoring a log file for changes
    
    Args:
        log_path (str): Path to the log file
        initial_data (pd.DataFrame): Existing log data to initialize with
    """
    # Initialize analyzer with existing data
    analyzer = LogAnalyzer(initial_data if initial_data is not None else pd.DataFrame())
    
    # Set up observer
    event_handler = LogHandler(analyzer)
    observer = Observer()
    observer.schedule(event_handler, path=log_path if log_path.endswith('/') else None)
    
    # Record initial file size
    try:
        with open(log_path, 'r') as f:
            event_handler.current_size = f.tell()
    except:
        event_handler.current_size = 0
    
    observer.start()
    print(f"Started monitoring {log_path}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.join()