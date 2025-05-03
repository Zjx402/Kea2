import re
import os
import threading
import time

PATTERN = re.compile(r"\[Fastbot\].+Internal\serror\n([\s\S]*)")

def thread_excepthook(args):
    print(args.exc_value)
    os._exit(1)



class LogWatcher:

    def watcher(self, log_path, poll_interval=1):
        buffer = ""
        last_pos = 0

        while True:
            with open(log_path, 'r', encoding='utf-8') as f:
                f.seek(last_pos)
                new_data = f.read()
                last_pos = f.tell()

            if new_data:
                buffer += new_data
                match = PATTERN.search(buffer)
                if match:
                    exception_body = match.group(1).strip()
                    if exception_body:
                        raise RuntimeError(
                            "[Error] Execption while running fastbot:\n" + 
                            exception_body + 
                            "\nSee fastbot.log for details."
                        )

            time.sleep(poll_interval)
    
    def _init_log_file(self, log_file):
        with open(log_file, "w") as fp:
            pass

    def __init__(self):
        log_file = "fastbot.log"
        
        threading.excepthook = thread_excepthook
        t = threading.Thread(target=self.watcher, args=(log_file,), daemon=False)
        t.start()
        # self.watcher(log_file)

if __name__ == "__main__":
    LogWatcher()