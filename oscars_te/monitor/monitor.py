import os
import sys
import json
import time
import socket
import urllib2
import threading
from datetime import datetime as dt

class Flow(object):
    """This represents a flow being monitored"""
    def __init__(self, arg):
        super(Flow, self).__init__()
        self.arg = arg

class Monitor(threading.Thread):
    """Periodically monitor flows"""
    def __init__(self, interval = 5):
        super(Monitor, self).__init__()

        self.stats = []
        self.interval = float(interval)

        self._shouldStop = threading.Event()
        self._stopped     = threading.Event()
        self._shouldStop.clear()
        self._stopped.clear()

    def getAllStats(self):
        if len(self.stats):
            return str(self.stats)
        return ''

    def getLatestStats(self):
        if len(self.stats):
            return str(self.stats[-1])
        return ''

    def requestStats(self):
        raise NotImplementedError

    def stop(self): 
        self._shouldStop.set()
        return

    def shouldStop(self):
        return self._shouldStop.is_set()

    def isStopped(self):
        self._stopped.is_set()
        return

    def run(self):
        """
        Periodically fetch stats using method self.requestStats()
        that should be implemented by sub classes
        """
        try:
            while not self.shouldStop():
                runTime = dt.now()
                if len(self.stats) > 10:
                    self.stats = self.stats[1:] + [self.requestStats()]
                else:
                    self.stats += [self.requestStats()]

                elapsed = dt.now() - runTime
                seconds = float(elapsed.seconds - (elapsed.microseconds*1e-6))
                wait4   = float(self.interval) - seconds
                if wait4 < 0:
                    # TODO: replace by logger
                    sys.stderr.write("Command is taking more than %f to execute!" % \
                                    self.interval)
                    wait4 = 0
                self._shouldStop.wait(wait4)
        except:
            None
        self._stopped.set()

class FloodlightMonitor(Monitor):
    def __init__(self, controller, interval):
        super(FloodlightMonitor, self).__init__(interval)
        self.setController(controller)

    def setController(self, controller): 
        host,port = (controller,8080)
        if len(host.split(':')) > 1:
            host,port = host.split(':')

        try:
            host = socket.gethostbyname(host)
            self.controller = dict(host=str(host),port=int(port))
        except Exception:
            raise Exception('Could not resolve controller hostname.')

class FloodlightFlowMonitor(FloodlightMonitor):
    def __init__(self, controller, interval):
        super(FloodlightFlowMonitor, self).__init__(controller, interval)

    def requestStats(self):
        url = "http://%s:%d/wm/core/switch/all/flow/json" % \
            (self.controller['host'], self.controller['port'])            
        try:
            response = urllib2.urlopen(url, timeout=10).read();
        except Exception, e:
            raise Exception('Could not fetch OFStats: %s ' % e.message)
        return response
        
class FloodlightPortMonitor(FloodlightMonitor):
    def __init__(self, controller, interval):
        super(FloodlightFlowMonitor, self).__init__(controller, interval)

    def requestStats(self):
        url = "http://%s:%d/wm/core/switch/all/port/json" % \
            (self.controller['host'], self.controller['port'])            
        try:
            response = urllib2.urlopen(url, timeout=10).read();
        except Exception, e:
            raise Exception('Could not fetch port stats: %s ' % e.message)
        return response
        
class FloodlightDefaultMonitor(FloodlightFlowMonitor):
    def __init__(self, controller='localhost', interval=4):
        super(FloodlightDefaultMonitor, self).__init__(controller, interval)
    
    