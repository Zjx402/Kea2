import re
import os
import threading
import time


PATTERN_EXCEPTION = re.compile(r"\[Fastbot\].+Internal\serror\n([\s\S]*)")
PATTERN_STATISTIC = re.compile(r".+Monkey\sis\sover!\n([\s\S]+)\n.+Monkey\sfinished")


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
                exception_match = PATTERN_EXCEPTION.search(buffer)
                if exception_match:
                    exception_body = exception_match.group(1).strip()
                    if exception_body:
                        raise RuntimeError(
                            "[Error] Execption while running fastbot:\n" + 
                            exception_body + 
                            "\nSee fastbot.log for details."
                        )
                statistic_match = PATTERN_STATISTIC.search(buffer)
                if statistic_match:
                    statistic_body = statistic_match.group(1).strip()
                    if statistic_body:
                        print(
                            "[INFO] Fastbot exit:\n" + 
                            statistic_body
                        )

            time.sleep(poll_interval)

    def _init_log_file(self, log_file):
        with open(log_file, "w") as fp:
            pass

    def __init__(self):
        log_file = "fastbot.log"

        self._init_log_file(log_file)
        threading.excepthook = thread_excepthook
        t = threading.Thread(target=self.watcher, args=(log_file,), daemon=False)
        t.start()
        
        self.t = t
    
    def join(self):
        self.t.join()


if __name__ == "__main__":
    LogWatcher()