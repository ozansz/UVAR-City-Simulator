class Logger(object):
    def __init__(self, log: bool = True):
        self.do_log = log

    def info(self, *args):
        if self.do_log:
            print(f"[i]", *args)

    def warn(self, *args):
        if self.do_log:
            print(f"[!]", *args)

    def err(self, *args):
        if self.do_log:
            print(f"[ERROR]", *args)
        
    def debug(self, *args):
        if self.do_log:
            print(f"[DEBUG]", *args)