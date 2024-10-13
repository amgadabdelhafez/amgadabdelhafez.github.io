import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('default.py'):
            print(f'default.py has been modified. Running build.py...')
            subprocess.run(['python', 'build.py'], check=True)

if __name__ == "__main__":
    path = 'repo/repository.skipintro'
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
