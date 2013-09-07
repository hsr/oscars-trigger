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
        self._shouldStop.set()
        return

    def shouldStop(self):
        return self._shouldStop.is_set()

    def isStopped(self):
        self._stopped.is_set()
        return

    def run(self):
        raise NotImplementedError