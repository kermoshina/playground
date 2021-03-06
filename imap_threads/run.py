from __future__ import print_function

import threading
import re
import random
import queue
import time



class AppState:
    # FOREGROUND is true if the app is running in the foreground
    # and false if it is running in the background.
    # in this demo script we set it from the "ui_thread" by typing
    # in "bg" and "fg" respectively
    FOREGROUND = True

    # this event is used to signal that an ongoing imap_idle() call
    # shall be interrupted which happens if there is user-generated
    # activity (sending/deleting a message etc.)
    e_interrupt_idle = threading.Event()


    # we keep an imap_thread and a queue to communicate with it
    imap_thread = None
    imap_queue = queue.Queue()



def interrupt_idle():
    log("triggering interrupt_idle")
    AppState.e_interrupt_idle.set()


def imap_idle():
    AppState.e_interrupt_idle.clear()
    log("***************** IMAP-IDLE BEGIN")
    if AppState.e_interrupt_idle.wait(timeout=10):
        log("IDLE INTERRUPTED")
    log("***************** IMAP-IDLE FINISH")


def imap_poll():
    """ poll for new messages in a non-blocking way (not long-running). """
    log("***************** IMAP-poll called (non-blocking)")


class ImapThread(threading.Thread):
    def run(self):
        log("==== thread starting")
        try:
            self._run()
        finally:
            log("==== thread finishing")

    def _run(self):
        while 1:
            perform_jobs()
            if AppState.FOREGROUND:
                imap_idle()
            else:
                imap_poll()
                break




def perform_jobs():
    log("** perform_jobs: starting loop")
    while 1:
        try:
            x = AppState.imap_queue.get(timeout=0.1)
        except queue.Empty:
            break
        else:
            log("- processing job:", x)
    log("** perform_jobs: finished loop")



def on_receive():
    if not AppState.imap_thread.is_alive():
        log("no imap thread active: starting one")
        start_imap_thread()
    else:
        log("imap thread is already active, doing nothing")


def start_imap_thread():
    if AppState.imap_thread and AppState.imap_thread.is_alive():
        log("skipped restart imap_thread (still running)")
    else:
        AppState.imap_thread = ImapThread()
        AppState.imap_thread.start()


def ui_thread():
    while 1:
        raw = raw_input()
        if raw == "bg":
            AppState.FOREGROUND = False
            interrupt_idle()
        elif raw == "fg":
            AppState.FOREGROUND = True
            on_receive()
        else:
            # we simulate some imap related activity
            AppState.imap_queue.put(raw)
            interrupt_idle()



# support code for emulating "on_receive" calls from Android
# which happen timer-based

def periodically_call(on_receive):
    periodic_thread = OnReceiveT(on_receive)
    periodic_thread.start()


class OnReceiveT(threading.Thread):
    def __init__(self, on_receive):
        self.on_receive = on_receive
        super(OnReceiveT, self).__init__()

    def run(self):
        while 1:
            on_receive()
            sleeptime = random.randint(1, 10)
            log("sleeping for", sleeptime, "seconds")
            time.sleep(sleeptime)

_loglock = threading.RLock()
def log(*args):
    t = threading.current_thread()
    r = repr(t)
    r = re.sub(", started \d+", "", r)
    with _loglock:
        print("%0.2f" % (time.time()-time_started), r, *args)


if __name__ == "__main__":
    time_started = time.time()
    log("starting")
    start_imap_thread()
    periodically_call(on_receive)
    ui_thread()
