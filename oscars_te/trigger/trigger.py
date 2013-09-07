import os
import sys
import json
import time
import socket
import urllib2
import threading
from datetime import datetime as dt
import json
import requests
from runnable import Runnable

class Trigger(Runnable):
    """Periodically monitor flows"""
    def __init__(self):
        super(Trigger, self).__init__()

class SFlowTrigger(Trigger):
    """docstring for SFlowTrigger"""
    def __init__(self, trigger_url):
        super(SFlowTrigger, self).__init__()
        
        os.popen('sflow-rt/start.sh &')
        
        self.groups = {'external':['0.0.0.0/0'],'internal':['0.0.0.0/0']}
        self.flows = {'value':'frames',
            'keys':'ipsource,ipdestination,tcpsourceport,tcpdestinationport',
            'filter':'sourcegroup=external&destinationgroup=internal'}
        self.threshold = {'metric':'incoming','value':100}
        self.target = 'http://%s' % trigger_url
        r = requests.put(target + '/group/json',
            data=json.dumps(groups))
        r = requests.put(target + '/flow/incoming/json',
            data=json.dumps(flows))
        r = requests.put(target + '/threshold/incoming/json',
            data=json.dumps(threshold))

        self.eventurl = target + '/events/json?maxEvents=10&timeout=60'
        self.eventID = -1
        
    def run():
        while 1 == 1:
          r = requests.get(self.eventurl + '&eventID=' + str(eventID))
          if r.status_code != 200:
              sys.stderr.write("Error, return code = %d\n" % r.status_code )
          events = r.json()
          if len(events) == 0: continue

          eventID = events[0]["eventID"]
          for e in events:
            if 'incoming' == e['metric']:
              r = requests.get(target + '/metric/' + e['agent'] + '/' + \
                               e['dataSource'] + '.' + e['metric'] + '/json')
              metric = r.json()
              if len(metric) > 0:
                sys.stderr.write(metric[0]["topKeys"][0]["key"])
        
        
