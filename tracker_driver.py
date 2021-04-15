#!/usr/bin/python

import signal
import sys
import cmd
from threading import Thread
from src import tracker, util

# global tracker object
t = None


def sig_handler(signum, frame):
    util.printts("Tracker: received signal %d, going down" % signum)

    if t:
        t.stop()
        sys.exit(signum)


# accept new nodes into the network
def accepter():
    while t.accept():
        continue


class TrackerShell(cmd.Cmd):
    prompt = "> "

    def do_stop(self, line):
        "Stop the tracker."
        t.stop()
        return True

    def do_EOF(self, line):
        "End-of-file; stops the tracker."
        t.stop()
        return True

    def do_nodes(self, line):
        "Show peers"
        for n in t.nodes.values():
            print(n.serialize())

    def do_chain(self, line):
        "Show chain"
        print(t.chain.serialize())

    def emptyline(self):
        pass


def main():
    port = int(sys.argv[1])
    if util.is_port_in_use(port):
        util.printts("Tracker: port %d is already in use" % port)
        sys.exit(1)

    # create the tracker
    global t
    t = tracker.Tracker(port)

    try:
        t.start()
    except Exception:
        util.printts("Tracker: failed to start tracker on %s:%d" %
                     (t.addr[0], t.addr[1]))
        sys.exit(1)

    def new_thread(f):
        thread = Thread(target=f, daemon=False)
        thread.start()
        return thread

    # this is our only thread which will run forever
    new_thread(accepter)

    TrackerShell().cmdloop()


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
