# detector_watchdog.py
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from analyzer import analyze_file, Verdict
from router import route_file

WATCH_DIR = "/mnt/incoming"      # shared from host
LOG_FILE = "/var/log/detector.log"

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        self.process(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self.process(event.src_path)

    def process(self, path):
        verdict = analyze_file(path)
        route_file(path, verdict)
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.time()},{path},{verdict.name}\n")

if __name__ == "__main__":
    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
