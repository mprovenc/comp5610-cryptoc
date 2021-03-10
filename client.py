#!/usr/bin/python

import signal
import sys
from threading import Thread
from src import node, util

# global node object
n = None


def sig_handler(signum, frame):
    print("Client: received signal %d, going down" % signum)
    global n
    if n is not None:
        n.disconnect()
        sys.exit(signum)


# accept new connections from peers
def accepter():
    global n
    while n.accept():
        pass


# receive new messages from the tracker
def tracker_receiver():
    global n
    while n.recv_tracker():
        pass


def main():
    def check_port(port, name):
        if port < 0 or port > 65535:
            print("Client: invalid %s port %d (must be between 0 and 65535)" %
                  (name, port))
            sys.exit(1)

    # create our node
    global n
    tracker_port = int(sys.argv[1])
    check_port(tracker_port, "tracker")
    port = int(sys.argv[2])
    check_port(port, "listening")
    if util.is_port_in_use(port):
        print("Client: port %d is already in use" % port)
        sys.exit(1)
    n = node.Node("localhost", tracker_port, port)

    def fail():
        global n
        print("Client: failed to connect to tracker on %s:%d" %
              (n.tracker_addr[0], n.tracker_addr[1]))
        sys.exit(1)

    # establish a connection with the tracker
    if not n.connect():
        fail()

    def new_thread(f):
        thread = Thread(target=f, daemon=True)
        thread.start()
        return thread

    # these are our two threads which should run forever
    a = new_thread(accepter)
    r = new_thread(tracker_receiver)
    a.join()
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
