import os
import sys
import json
import time
import socket
import urllib2
import threading
from datetime import datetime as dt

class Runnable(threading.Thread):
    """An object that has an execution context"""
    def __init__(self):
        super(Runnable, self).__init__()

        self._shouldStop = threading.Event()
        self._stopped     = threading.Event()
        self._shouldStop.clear()
        self._stopped.clear()

    def stop(self): 
        """
        This method should be called from the context of 
        the object creator. It instructs a runnable object
        to stop its execution. This causes future calls
        to shouldStop() to return true.
        """
        self._shouldStop.set()
        return

    def terminate(self): 
        """
        This method should be called after the main thread
        finishes its execution, usually before returning from
        the run() method implementation. If causes future
        calls to isStopped() to return true.
        """
        self._stopped.set()
        return

    def shouldStop(self):
        """
        Returns true if stop() was called, false otherwise.
        Useful to determine if the Runnable object should
        stop its execution from an infite loop.
        """
        return self._shouldStop.is_set()

    def isStopped(self):
        """
        Returns true if terminate() was called, false otherwise.
        Useful to determine if the Runnable object had
        stopped its execution.
        """
        self._stopped.is_set()
        return
    
    def waitInterruptible(self, duration=-1):
        """
        Handy function to wait until stop() method is called
        up to 'duration' seconds. If duration isn't provided
        or it has a negative value, waits until stop() is
        called.
        """
        if duration < 0:
            return self._shouldStop.wait()
        return self._shouldStop.wait(duration)


    def run(self):
        raise NotImplementedError