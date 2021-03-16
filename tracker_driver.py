#!/usr/bin/python

import signal
import sys
from threading import Thread
from src import tracker, util

# global tracker object
t = None


def sig_handler(signum, frame):
    print("Server: received signal %d, going down" % signum)
    if t:
        t.stop()
        sys.exit(signum)


# accept new nodes into the network
def accepter():
    while True:
        t.accept()


def main():
    port = int(sys.argv[1])
    if util.is_port_in_use(port):
        print("Server: port %d is already in use" % port)
        sys.exit(1)

    # create the tracker
    global t
    t = tracker.Tracker(port)

    try:
        t.start()
    except Exception:
        print("Server: failed to start tracker on %s:%d" %
              (t.addr[0], t.addr[1]))
        sys.exit(1)

    def new_thread(f):
        thread = Thread(target=f, daemon=True)
        thread.start()
        return thread

    # this is our only thread which will run forever
    a = new_thread(accepter)
    a.join()


if __name__ == "__main__":
    sigs = set([signal.SIGHUP,
                signal.SIGINT,
                signal.SIGQUIT,
                signal.SIGKILL,
                signal.SIGILL,
                signal.SIGABRT,
                signal.SIGBUS,
                signal.SIGFPE,
                signal.SIGSEGV,
                signal.SIGPIPE,
                signal.SIGTERM,
                signal.SIGCHLD])

    for sig in sigs:
        try:
            signal.signal(sig, sig_handler)
        except OSError:
            pass

    main()
