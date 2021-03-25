#!/usr/bin/python

import signal
import sys
from threading import current_thread, Thread
from src import node, util

# global node object
n = None


def is_main_thread():
    return current_thread().__class__.__name__ == '_MainThread'


def sig_handler(signum, frame):
    if not n:
        return

    # worker thread terminated, just ignore it
    if signum == signal.SIGCHLD:
        return

    # we only care if a signal was sent to the main thread (i.e. the driver)
    if is_main_thread():
        print("Node: received signal %d, going down" % signum)
        n.disconnect()

    sys.exit(signum)


# accept new connections from peers
def accepter():
    while True:
        n.accept()


# receive new messages from the tracker
def tracker_receiver():
    while n.recv_tracker():
        continue


def main():
    def check_port(port, name):
        if port < 0 or port > 65535:
            print("Node: invalid %s port %d (must be between 0 and 65535)" %
                  (name, port))
            sys.exit(1)

    # do some sanity checks
    tracker_port = int(sys.argv[1])
    check_port(tracker_port, "tracker")
    port = int(sys.argv[2])
    check_port(port, "listening")
    if util.is_port_in_use(port):
        print("Node: port %d is already in use" % port)
        sys.exit(1)

    # create our node
    global n
    n = node.Node("localhost", tracker_port, port)

    # establish a connection with the tracker
    if not n.connect():
        print("Node: failed to connect to tracker on %s:%d" %
              (n.tracker_addr[0], n.tracker_addr[1]))
        sys.exit(1)

    def new_thread(f):
        thread = Thread(target=f, daemon=True)
        thread.start()
        return thread

    # the accepter thread will run forever
    # but we don't care about when it finishes
    new_thread(accepter)

    # the tracker_receiver thread will finish when
    # the connection with the tracker is broken,
    # so we want to wait for that event in main()
    r = new_thread(tracker_receiver)
    r.join()


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
